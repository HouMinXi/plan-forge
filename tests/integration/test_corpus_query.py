"""Integration tests for corpus query helpers.

Seed a run with findings/evidence/arbitrations/outcomes then verify each
helper returns the right rows and that filters and limit work.
"""
from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path

import pytest
from sqlalchemy import create_engine

from plan_forge.corpus import CorpusRecorder
from plan_forge.corpus import db as corpus_db
from plan_forge.corpus import query
from plan_forge.corpus.models import Base
from plan_forge.verdict import (
    EvidenceTier,
    Finding,
    LLMEvidence,
    Severity,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

class _FakePlan:
    def __init__(self, text: str = "# Query test plan") -> None:
        self.raw_text = text


def _make_db(tmp_path: Path) -> str:
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


def _make_evidence(run_id: int, tier: EvidenceTier, gate: str) -> LLMEvidence:
    return LLMEvidence(
        provider="anthropic",
        model="claude-opus-4",
        verdict="PASS",
        reasoning="ok",
        prompt_version="v1",
        run_id=run_id,
        tier=tier,
    )


# ---------------------------------------------------------------------------
# Seed fixture -- uses tmp_path (function scope)
# ---------------------------------------------------------------------------

@pytest.fixture()
def seeded(tmp_path):
    """Seed one run with 2 findings, 3 evidence rows, 1 outcome."""
    _make_db(tmp_path)
    rec = CorpusRecorder()
    run_id = rec.start_run(
        _FakePlan(), "/tmp/q.md", "0.1.0", "auto", 2.0
    )

    f1 = Finding(
        check_id="F1", severity=Severity.HIGH,
        location="line 1", message="msg1",
    )
    f2 = Finding(
        check_id="F2", severity=Severity.LOW,
        location="line 2", message="msg2",
    )
    fid1 = rec.record_finding(run_id, f1)
    fid2 = rec.record_finding(run_id, f2)

    ev1 = _make_evidence(run_id, EvidenceTier.UNCLASSIFIED, "G6.B")
    ev2 = _make_evidence(run_id, EvidenceTier.UNCLASSIFIED, "G6.B")
    ev3 = _make_evidence(run_id, EvidenceTier.UNCLASSIFIED, "G8.B")
    eid1 = rec.record_evidence(run_id, "G6.B", "SC-1", ev1)
    eid2 = rec.record_evidence(run_id, "G6.B", "SC-2", ev2)
    eid3 = rec.record_evidence(run_id, "G8.B", "SC-3", ev3)

    # Classify ev1 as T1
    ev1.tier = EvidenceTier.T1_GOLD
    rec.update_evidence_tier(ev1)

    now = datetime.now(timezone.utc)
    oid = rec.record_outcome(
        run_id, fid1, "predicted_manifested", now, "pr#42", "tester"
    )

    yield {
        "run_id": run_id,
        "fid1": fid1, "fid2": fid2,
        "eid1": eid1, "eid2": eid2, "eid3": eid3,
        "oid": oid,
    }
    _teardown()


# ---------------------------------------------------------------------------
# get_run
# ---------------------------------------------------------------------------

def test_get_run_returns_correct_row(seeded):
    run_id = seeded["run_id"]
    row = query.get_run(run_id)
    assert row is not None
    assert row.run_id == run_id
    assert row.plan_forge_version == "0.1.0"
    assert row.plan_path == "/tmp/q.md"


def test_get_run_missing_returns_none(seeded):
    assert query.get_run(99999) is None


# ---------------------------------------------------------------------------
# list_findings
# ---------------------------------------------------------------------------

def test_list_findings_returns_all(seeded):
    rows = query.list_findings(seeded["run_id"])
    assert len(rows) == 2
    ids = {r.finding_id for r in rows}
    assert ids == {seeded["fid1"], seeded["fid2"]}


def test_list_findings_limit(seeded):
    rows = query.list_findings(seeded["run_id"], limit=1)
    assert len(rows) == 1
    # First by finding_id order
    assert rows[0].finding_id == seeded["fid1"]


def test_list_findings_empty_run(tmp_path):
    _make_db(tmp_path)
    try:
        rec = CorpusRecorder()
        run_id = rec.start_run(
            _FakePlan(), None, "0.1.0", "auto", 1.0
        )
        assert query.list_findings(run_id) == []
    finally:
        _teardown()


# ---------------------------------------------------------------------------
# list_evidence
# ---------------------------------------------------------------------------

def test_list_evidence_returns_all(seeded):
    rows = query.list_evidence(seeded["run_id"])
    assert len(rows) == 3


def test_list_evidence_tier_filter(seeded):
    rows = query.list_evidence(seeded["run_id"], tier="T1")
    assert len(rows) == 1
    assert rows[0].evidence_id == seeded["eid1"]


def test_list_evidence_unclassified_filter(seeded):
    rows = query.list_evidence(
        seeded["run_id"], tier="UNCLASSIFIED"
    )
    # ev2 and ev3 are still UNCLASSIFIED
    assert len(rows) == 2
    ids = {r.evidence_id for r in rows}
    assert seeded["eid2"] in ids
    assert seeded["eid3"] in ids


def test_list_evidence_gate_filter(seeded):
    rows = query.list_evidence(seeded["run_id"], gate_id="G8.B")
    assert len(rows) == 1
    assert rows[0].evidence_id == seeded["eid3"]


def test_list_evidence_combined_filters(seeded):
    rows = query.list_evidence(
        seeded["run_id"], tier="T1", gate_id="G6.B"
    )
    assert len(rows) == 1
    assert rows[0].evidence_id == seeded["eid1"]


def test_list_evidence_limit(seeded):
    rows = query.list_evidence(seeded["run_id"], limit=2)
    assert len(rows) == 2


def test_list_evidence_filter_no_match(seeded):
    rows = query.list_evidence(seeded["run_id"], tier="T4")
    assert rows == []


# ---------------------------------------------------------------------------
# list_outcomes
# ---------------------------------------------------------------------------

def test_list_outcomes_returns_all(seeded):
    rows = query.list_outcomes(seeded["run_id"])
    assert len(rows) == 1
    assert rows[0].outcome_id == seeded["oid"]
    assert rows[0].outcome_type == "predicted_manifested"
    assert rows[0].recorder == "tester"
    assert rows[0].evidence == "pr#42"


def test_list_outcomes_limit(seeded):
    rows = query.list_outcomes(seeded["run_id"], limit=1)
    assert len(rows) == 1


def test_list_outcomes_empty(tmp_path):
    _make_db(tmp_path)
    try:
        rec = CorpusRecorder()
        run_id = rec.start_run(
            _FakePlan(), None, "0.1.0", "auto", 1.0
        )
        assert query.list_outcomes(run_id) == []
    finally:
        _teardown()


# ---------------------------------------------------------------------------
# list_arbitrations
# ---------------------------------------------------------------------------

def test_list_arbitrations_empty(seeded):
    rows = query.list_arbitrations(seeded["run_id"])
    assert rows == []


def test_list_arbitrations_returns_row(tmp_path):
    _make_db(tmp_path)
    try:
        rec = CorpusRecorder()
        run_id = rec.start_run(
            _FakePlan(), None, "0.1.0", "auto", 1.0
        )
        aid = rec.record_arbitration(
            run_id, None, "evidence bundle", "verified", "rationale", False
        )
        rows = query.list_arbitrations(run_id)
        assert len(rows) == 1
        assert rows[0].arbitration_id == aid
        assert rows[0].human_verdict == "verified"
    finally:
        _teardown()
