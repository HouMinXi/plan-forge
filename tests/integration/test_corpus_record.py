"""Integration tests for CorpusRecorder -- the sole write path into the ledger.

Each test gets its own isolated SQLite DB via tmp_path to avoid cross-test
state.  The corpus singleton is reset after each test.
"""
from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError

from plan_forge.corpus import CorpusRecorder
from plan_forge.corpus import db as corpus_db
from plan_forge.corpus.models import Base, PlanRun
from plan_forge.verdict import (
    EvidenceTier,
    Finding,
    LLMEvidence,
    Severity,
)


# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------

class _FakePlan:
    """Minimal ParsedPlan stand-in with only raw_text."""
    def __init__(self, text: str = "# Plan\nsome text") -> None:
        self.raw_text = text


def _make_db(tmp_path: Path) -> str:
    """Create isolated SQLite DB, run schema creation, set env var."""
    db_path = tmp_path / "corpus.db"
    url = f"sqlite:///{db_path}"
    engine = create_engine(url)
    Base.metadata.create_all(engine)
    engine.dispose()
    os.environ["PLAN_FORGE_CORPUS_URL"] = url
    corpus_db._reset_engine()
    return url


def _teardown() -> None:
    corpus_db._reset_engine()
    os.environ.pop("PLAN_FORGE_CORPUS_URL", None)


def _make_evidence(run_id: int = 0) -> LLMEvidence:
    return LLMEvidence(
        provider="anthropic",
        model="claude-opus-4",
        verdict="PASS",
        reasoning="looks good",
        prompt_version="v1",
        run_id=run_id,
    )


def _make_finding() -> Finding:
    return Finding(
        check_id="F1",
        severity=Severity.HIGH,
        location="line 5",
        message="missing scope challenge",
    )


# ---------------------------------------------------------------------------
# start_run happy path
# ---------------------------------------------------------------------------

def test_start_run_inserts_row(tmp_path):
    _make_db(tmp_path)
    try:
        rec = CorpusRecorder()
        plan = _FakePlan("# My Plan\ncontent")
        run_id = rec.start_run(
            plan,
            plan_path="/tmp/plan.md",
            plan_forge_version="0.1.0",
            arbitration_mode="auto",
            cost_cap_usd=1.0,
        )
        assert isinstance(run_id, int) and run_id > 0

        with corpus_db.session_scope() as s:
            row = s.get(PlanRun, run_id)
            import hashlib
            expected_hash = hashlib.sha256(
                plan.raw_text.encode()
            ).hexdigest()[:16]
            assert row.plan_hash == expected_hash
            assert row.plan_text == plan.raw_text
            assert row.plan_path == "/tmp/plan.md"
            assert row.plan_forge_version == "0.1.0"
            assert row.arbitration_mode == "auto"
            assert row.cost_cap_usd == 1.0
            assert row.completed_at is None
    finally:
        _teardown()


def test_start_run_none_plan_path(tmp_path):
    _make_db(tmp_path)
    try:
        rec = CorpusRecorder()
        run_id = rec.start_run(
            _FakePlan(), None, "0.1.0", "auto", 0.5
        )
        with corpus_db.session_scope() as s:
            row = s.get(PlanRun, run_id)
            assert row.plan_path is None
    finally:
        _teardown()


# ---------------------------------------------------------------------------
# finalize_run
# ---------------------------------------------------------------------------

def test_finalize_run_sets_completion_fields(tmp_path):
    _make_db(tmp_path)
    try:
        rec = CorpusRecorder()
        run_id = rec.start_run(
            _FakePlan(), None, "0.1.0", "auto", 1.0
        )
        # Snapshot immutable fields before finalize
        with corpus_db.session_scope() as s:
            before = s.get(PlanRun, run_id)
            plan_hash_before = before.plan_hash
            plan_text_before = before.plan_text
            started_at_before = before.started_at

        rec.finalize_run(run_id, "PASS", "PASS", 0.42)

        with corpus_db.session_scope() as s:
            after = s.get(PlanRun, run_id)
            # Completion fields set
            assert after.completed_at is not None
            assert after.engineering_verdict == "PASS"
            assert after.epistemic_verdict == "PASS"
            assert after.actual_cost_usd == pytest.approx(0.42)
            # Immutable fields unchanged
            assert after.plan_hash == plan_hash_before
            assert after.plan_text == plan_text_before
            assert after.started_at == started_at_before
    finally:
        _teardown()


def test_finalize_run_idempotent_guard(tmp_path):
    _make_db(tmp_path)
    try:
        rec = CorpusRecorder()
        run_id = rec.start_run(
            _FakePlan(), None, "0.1.0", "auto", 1.0
        )
        rec.finalize_run(run_id, "PASS", "PASS", 0.1)
        with pytest.raises(ValueError, match="already finalized"):
            rec.finalize_run(run_id, "FAIL", "FAIL", 0.9)
    finally:
        _teardown()


def test_finalize_run_unknown_run_id(tmp_path):
    _make_db(tmp_path)
    try:
        rec = CorpusRecorder()
        with pytest.raises(ValueError, match="not found"):
            rec.finalize_run(999, "PASS", "PASS", 0.0)
    finally:
        _teardown()


# ---------------------------------------------------------------------------
# record_finding
# ---------------------------------------------------------------------------

def test_record_finding_round_trips(tmp_path):
    _make_db(tmp_path)
    try:
        rec = CorpusRecorder()
        run_id = rec.start_run(
            _FakePlan(), None, "0.1.0", "auto", 1.0
        )
        finding = _make_finding()
        fid = rec.record_finding(run_id, finding)
        assert isinstance(fid, int) and fid > 0

        from plan_forge.corpus.models import Finding as DBFinding
        with corpus_db.session_scope() as s:
            row = s.get(DBFinding, fid)
            assert row.run_id == run_id
            assert row.check_id == "F1"
            assert row.severity == "HIGH"
            assert row.location == "line 5"
            assert row.message == "missing scope challenge"
    finally:
        _teardown()


def test_record_finding_fk_enforced(tmp_path):
    """record_finding with nonexistent run_id must raise IntegrityError."""
    _make_db(tmp_path)
    try:
        rec = CorpusRecorder()
        finding = _make_finding()
        with pytest.raises(IntegrityError):
            rec.record_finding(99999, finding)
    finally:
        _teardown()


# ---------------------------------------------------------------------------
# record_evidence + ID backfill
# ---------------------------------------------------------------------------

def test_record_evidence_round_trips(tmp_path):
    _make_db(tmp_path)
    try:
        rec = CorpusRecorder()
        run_id = rec.start_run(
            _FakePlan(), None, "0.1.0", "auto", 1.0
        )
        ev = _make_evidence(run_id=0)  # stale run_id on object
        eid = rec.record_evidence(run_id, "G6.B", "SC-3", ev)
        assert isinstance(eid, int) and eid > 0
        # evidence_id backfilled after INSERT
        assert ev.evidence_id == eid
        # run_id backfilled from canonical param
        assert ev.run_id == run_id

        from plan_forge.corpus.models import LLMEvidence as DBEv
        with corpus_db.session_scope() as s:
            row = s.get(DBEv, eid)
            assert row.run_id == run_id
            assert row.gate_id == "G6.B"
            assert row.target_id == "SC-3"
            assert row.provider == "anthropic"
            assert row.tier == "UNCLASSIFIED"
    finally:
        _teardown()


def test_record_evidence_stale_run_id_overwritten(tmp_path):
    """Canonical run_id param overwrites any stale run_id on the evidence object."""
    _make_db(tmp_path)
    try:
        rec = CorpusRecorder()
        run_id = rec.start_run(
            _FakePlan(), None, "0.1.0", "auto", 1.0
        )
        ev = _make_evidence(run_id=9999)  # stale value
        rec.record_evidence(run_id, "G6.B", None, ev)
        assert ev.run_id == run_id  # backfilled to canonical
    finally:
        _teardown()


def test_record_evidence_fk_enforced(tmp_path):
    """record_evidence with nonexistent run_id must raise IntegrityError."""
    _make_db(tmp_path)
    try:
        rec = CorpusRecorder()
        ev = _make_evidence()
        with pytest.raises(IntegrityError):
            rec.record_evidence(99999, "G6.B", "SC-1", ev)
    finally:
        _teardown()


# ---------------------------------------------------------------------------
# update_evidence_tier -- 3-way monotonic rule
# ---------------------------------------------------------------------------

def _run_with_evidence(tmp_path) -> tuple[CorpusRecorder, int, LLMEvidence]:
    """Helper: start a run and record one evidence row."""
    _make_db(tmp_path)
    rec = CorpusRecorder()
    run_id = rec.start_run(_FakePlan(), None, "0.1.0", "auto", 1.0)
    ev = _make_evidence(run_id)
    rec.record_evidence(run_id, "G10.B", "SC-1", ev)
    return rec, run_id, ev


def test_update_evidence_tier_unclassified_to_t1(tmp_path):
    rec, _, ev = _run_with_evidence(tmp_path)
    try:
        ev.tier = EvidenceTier.T1_GOLD
        rec.update_evidence_tier(ev)
        from plan_forge.corpus.models import LLMEvidence as DBEv
        with corpus_db.session_scope() as s:
            row = s.get(DBEv, ev.evidence_id)
            assert row.tier == "T1"
    finally:
        _teardown()


def test_update_evidence_tier_same_value_noop(tmp_path):
    """T1 -> T1 is a no-op; does not raise."""
    rec, _, ev = _run_with_evidence(tmp_path)
    try:
        ev.tier = EvidenceTier.T1_GOLD
        rec.update_evidence_tier(ev)
        # Second call with same tier -- must not raise
        rec.update_evidence_tier(ev)
        from plan_forge.corpus.models import LLMEvidence as DBEv
        with corpus_db.session_scope() as s:
            row = s.get(DBEv, ev.evidence_id)
            assert row.tier == "T1"
    finally:
        _teardown()


def test_update_evidence_tier_conflict_raises(tmp_path):
    """T1 -> T2 raises ValueError (conflict)."""
    rec, _, ev = _run_with_evidence(tmp_path)
    try:
        ev.tier = EvidenceTier.T1_GOLD
        rec.update_evidence_tier(ev)
        ev.tier = EvidenceTier.T2_SILVER
        with pytest.raises(ValueError, match="conflict"):
            rec.update_evidence_tier(ev)
    finally:
        _teardown()


def test_update_evidence_tier_downgrade_raises(tmp_path):
    """T1 -> UNCLASSIFIED raises ValueError (downgrade violates monotonic rule)."""
    rec, _, ev = _run_with_evidence(tmp_path)
    try:
        ev.tier = EvidenceTier.T1_GOLD
        rec.update_evidence_tier(ev)
        ev.tier = EvidenceTier.UNCLASSIFIED
        with pytest.raises(ValueError, match="conflict"):
            rec.update_evidence_tier(ev)
    finally:
        _teardown()


def test_update_evidence_tier_missing_id_raises(tmp_path):
    _make_db(tmp_path)
    try:
        rec = CorpusRecorder()
        ev = _make_evidence()
        # evidence_id is None (never recorded)
        ev.tier = EvidenceTier.T1_GOLD
        with pytest.raises(ValueError, match="evidence_id is None"):
            rec.update_evidence_tier(ev)
    finally:
        _teardown()


# ---------------------------------------------------------------------------
# record_arbitration -- CHECK constraint coverage
# ---------------------------------------------------------------------------

def test_record_arbitration_valid_verdicts(tmp_path):
    _make_db(tmp_path)
    try:
        rec = CorpusRecorder()
        run_id = rec.start_run(
            _FakePlan(), None, "0.1.0", "auto", 1.0
        )
        for verdict in ("verified", "unverified", "deferred", "abstain"):
            aid = rec.record_arbitration(
                run_id, None, "bundle text", verdict, "rationale", False
            )
            assert isinstance(aid, int) and aid > 0
    finally:
        _teardown()


def test_record_arbitration_invalid_verdict_raises(tmp_path):
    _make_db(tmp_path)
    try:
        rec = CorpusRecorder()
        run_id = rec.start_run(
            _FakePlan(), None, "0.1.0", "auto", 1.0
        )
        with pytest.raises(IntegrityError):
            rec.record_arbitration(
                run_id, None, "bundle", "bogus", None, None
            )
    finally:
        _teardown()


# ---------------------------------------------------------------------------
# record_outcome -- CHECK constraint coverage
# ---------------------------------------------------------------------------

def test_record_outcome_valid_types(tmp_path):
    _make_db(tmp_path)
    try:
        rec = CorpusRecorder()
        run_id = rec.start_run(
            _FakePlan(), None, "0.1.0", "auto", 1.0
        )
        valid = [
            "predicted_manifested",
            "predicted_did_not_manifest",
            "unpredicted_occurred",
            "plan_succeeded",
        ]
        now = datetime.now(timezone.utc)
        for otype in valid:
            oid = rec.record_outcome(
                run_id, None, otype, now, None, "tester"
            )
            assert isinstance(oid, int) and oid > 0
    finally:
        _teardown()


def test_record_outcome_invalid_type_raises(tmp_path):
    _make_db(tmp_path)
    try:
        rec = CorpusRecorder()
        run_id = rec.start_run(
            _FakePlan(), None, "0.1.0", "auto", 1.0
        )
        with pytest.raises(IntegrityError):
            rec.record_outcome(
                run_id, None, "bogus",
                datetime.now(timezone.utc), None, "tester"
            )
    finally:
        _teardown()


# ---------------------------------------------------------------------------
# append-only: no delete / generic update methods
# ---------------------------------------------------------------------------

def test_corpus_recorder_has_no_delete_or_update_methods():
    """CorpusRecorder exposes no delete or generic update methods."""
    rec = CorpusRecorder()
    names = {n for n in dir(rec) if not n.startswith("_")}
    forbidden = {n for n in names if "delete" in n or "remove" in n}
    assert not forbidden, f"delete/remove methods found: {forbidden}"
    # Only the two controlled updates are allowed
    update_methods = {n for n in names if "update" in n}
    assert update_methods == {"update_evidence_tier"}, (
        f"unexpected update methods: {update_methods}"
    )
