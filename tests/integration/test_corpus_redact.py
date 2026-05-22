"""Integration tests for run lifecycle wiring, redaction, and corpus_private.

Each test sets up its own isolated SQLite DB so tests are fully independent.
The env var PLAN_FORGE_CORPUS_URL is restored after each test.
"""
from __future__ import annotations

import hashlib
import os
import subprocess
import sys
import warnings
from pathlib import Path
from unittest.mock import patch

import pytest
from sqlalchemy import create_engine

from plan_forge.corpus import CorpusRecorder
from plan_forge.corpus import db as corpus_db
from plan_forge.corpus import redact as redact_mod
from plan_forge.corpus.models import Base, PlanRun
from plan_forge.corpus import query


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

class _FakePlan:
    """Minimal ParsedPlan stand-in."""
    def __init__(self, text: str = "# Plan\nsome content") -> None:
        self.raw_text = text


def _make_db(tmp_path: Path) -> str:
    """Create isolated SQLite DB, apply schema, set env var."""
    db_path = tmp_path / "redact_test.db"
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


MINIMAL_PLAN = """\
# My Plan

## Scope Challenge
Some text.

## Decision Log
- decided to do X

## Risk Register
No major risks.
"""


# ---------------------------------------------------------------------------
# compute_plan_hash
# ---------------------------------------------------------------------------

def test_compute_plan_hash_deterministic():
    """Same input always yields the same hash."""
    h1 = redact_mod.compute_plan_hash("hello world")
    h2 = redact_mod.compute_plan_hash("hello world")
    assert h1 == h2


def test_compute_plan_hash_is_sha256_prefix():
    """Hash matches first 16 chars of SHA-256(text.encode(utf-8))."""
    text = "test plan content"
    expected = hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]
    assert redact_mod.compute_plan_hash(text) == expected


def test_compute_plan_hash_length():
    """Hash is always exactly 16 hex characters."""
    assert len(redact_mod.compute_plan_hash("")) == 16
    assert len(redact_mod.compute_plan_hash("a" * 10000)) == 16


def test_compute_plan_hash_utf8_encoding():
    """Multi-byte code points hash consistently via encode('utf-8')."""
    # Build a multi-byte string at runtime from code points to avoid literals.
    text = "plantext" + chr(0xE9) + chr(0xE0)
    expected = hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]
    assert redact_mod.compute_plan_hash(text) == expected


# ---------------------------------------------------------------------------
# redact_plan_text
# ---------------------------------------------------------------------------

def test_redact_plan_text_returns_none_and_hash():
    """redact_plan_text returns (None, hash) tuple."""
    text = "# Confidential Plan\ncontent"
    result = redact_mod.redact_plan_text(text)
    assert result[0] is None
    assert isinstance(result[1], str) and len(result[1]) == 16


def test_redact_plan_text_hash_matches_compute():
    """The hash returned by redact_plan_text equals compute_plan_hash."""
    text = "some plan text"
    _, returned_hash = redact_mod.redact_plan_text(text)
    assert returned_hash == redact_mod.compute_plan_hash(text)


# ---------------------------------------------------------------------------
# corpus_private=True: plan_text IS NULL, hash preserved
# ---------------------------------------------------------------------------

def test_corpus_private_true_omits_plan_text(tmp_path):
    """When corpus_private=True, plan_runs.plan_text is NULL."""
    _make_db(tmp_path)
    try:
        rec = CorpusRecorder(redact=True)
        plan = _FakePlan("# Secret Plan\ncontent")
        run_id = rec.start_run(
            plan, "/tmp/secret.md",
            plan_forge_version="0.1.0",
            arbitration_mode="off",
            cost_cap_usd=0.0,
        )
        with corpus_db.session_scope() as s:
            row = s.get(PlanRun, run_id)
            assert row.plan_text is None
            assert row.plan_hash == redact_mod.compute_plan_hash(plan.raw_text)
    finally:
        _teardown()


def test_corpus_private_true_run_id_returned(tmp_path):
    """corpus_private=True still yields a valid integer run_id."""
    _make_db(tmp_path)
    try:
        rec = CorpusRecorder(redact=True)
        plan = _FakePlan()
        run_id = rec.start_run(
            plan, None,
            plan_forge_version="0.1.0",
            arbitration_mode="off",
            cost_cap_usd=0.0,
        )
        assert isinstance(run_id, int) and run_id > 0
    finally:
        _teardown()


# ---------------------------------------------------------------------------
# corpus_private=False: plan_text verbatim, hash preserved
# ---------------------------------------------------------------------------

def test_corpus_private_false_stores_plan_text(tmp_path):
    """When corpus_private=False (default), plan_text is stored verbatim."""
    _make_db(tmp_path)
    try:
        rec = CorpusRecorder(redact=False)
        plan = _FakePlan("# Open Plan\ncontent")
        run_id = rec.start_run(
            plan, None,
            plan_forge_version="0.1.0",
            arbitration_mode="off",
            cost_cap_usd=0.0,
        )
        with corpus_db.session_scope() as s:
            row = s.get(PlanRun, run_id)
            assert row.plan_text == plan.raw_text
            assert row.plan_hash == redact_mod.compute_plan_hash(plan.raw_text)
    finally:
        _teardown()


# ---------------------------------------------------------------------------
# run lifecycle: completed_at set after finalize, verdict strings correct
# ---------------------------------------------------------------------------

def test_run_lifecycle_completed_at(tmp_path):
    """After finalize_run, completed_at is set."""
    _make_db(tmp_path)
    try:
        rec = CorpusRecorder()
        run_id = rec.start_run(
            _FakePlan(), None, "0.1.0", "off", 0.0,
        )
        with corpus_db.session_scope() as s:
            before = s.get(PlanRun, run_id)
            assert before.completed_at is None

        rec.finalize_run(run_id, "PASS", "PASS", None)

        with corpus_db.session_scope() as s:
            after = s.get(PlanRun, run_id)
            assert after.completed_at is not None
            assert after.engineering_verdict == "PASS"
            assert after.epistemic_verdict == "PASS"
            assert after.actual_cost_usd is None
    finally:
        _teardown()


def test_run_lifecycle_verdict_strings(tmp_path):
    """Engineering and epistemic verdict strings are stored verbatim."""
    _make_db(tmp_path)
    try:
        rec = CorpusRecorder()
        run_id = rec.start_run(
            _FakePlan(), None, "0.1.0", "off", 0.0,
        )
        rec.finalize_run(run_id, "FAIL", "VISION", None)
        with corpus_db.session_scope() as s:
            row = s.get(PlanRun, run_id)
            assert row.engineering_verdict == "FAIL"
            assert row.epistemic_verdict == "VISION"
    finally:
        _teardown()


# ---------------------------------------------------------------------------
# partial-wire: query.list_findings returns [] (no findings recorded yet)
# ---------------------------------------------------------------------------

def test_partial_wire_no_findings(tmp_path):
    """After start_run + finalize_run, list_findings returns empty list."""
    _make_db(tmp_path)
    try:
        rec = CorpusRecorder()
        run_id = rec.start_run(
            _FakePlan(), None, "0.1.0", "off", 0.0,
        )
        rec.finalize_run(run_id, "PASS", "PASS", None)
        findings = query.list_findings(run_id)
        assert findings == []
    finally:
        _teardown()


# ---------------------------------------------------------------------------
# env-var OFF: Verdict.corpus_run_id is None, no DB writes attempted
# ---------------------------------------------------------------------------

def test_env_var_off_no_corpus_run():
    """When PLAN_FORGE_CORPUS_URL is unset, check() sets corpus_run_id=None."""
    saved = os.environ.pop("PLAN_FORGE_CORPUS_URL", None)
    corpus_db._reset_engine()
    try:
        from plan_forge import api

        verdict = api.check(MINIMAL_PLAN, llm_clients=[])
        assert verdict.corpus_run_id is None
    finally:
        if saved is not None:
            os.environ["PLAN_FORGE_CORPUS_URL"] = saved
        corpus_db._reset_engine()


# ---------------------------------------------------------------------------
# check() end-to-end with corpus recording active
# ---------------------------------------------------------------------------

def test_check_records_corpus_run_id(tmp_path):
    """When PLAN_FORGE_CORPUS_URL is set, check() returns a valid corpus_run_id."""
    _make_db(tmp_path)
    try:
        from plan_forge import api

        verdict = api.check(
            MINIMAL_PLAN,
            plan_path="/tmp/test.md",
            llm_clients=[],
            corpus_private=False,
        )
        assert isinstance(verdict.corpus_run_id, int) and verdict.corpus_run_id > 0
    finally:
        _teardown()


def test_check_corpus_private_sets_null_text(tmp_path):
    """check(corpus_private=True) causes plan_runs.plan_text IS NULL."""
    _make_db(tmp_path)
    try:
        from plan_forge import api

        verdict = api.check(
            MINIMAL_PLAN,
            llm_clients=[],
            corpus_private=True,
        )
        assert verdict.corpus_run_id is not None
        with corpus_db.session_scope() as s:
            row = s.get(PlanRun, verdict.corpus_run_id)
            assert row.plan_text is None
            assert row.plan_hash == redact_mod.compute_plan_hash(MINIMAL_PLAN)
    finally:
        _teardown()


# ---------------------------------------------------------------------------
# failure isolation: monkeypatch start_run to raise -> valid Verdict returned
# ---------------------------------------------------------------------------

def test_failure_isolation_start_run_raises(tmp_path):
    """If start_run raises, check() returns a valid Verdict with corpus_run_id=None."""
    _make_db(tmp_path)
    try:
        from plan_forge import api

        with patch.object(
            CorpusRecorder, "start_run", side_effect=RuntimeError("db gone")
        ):
            with warnings.catch_warnings(record=True) as caught:
                warnings.simplefilter("always")
                verdict = api.check(MINIMAL_PLAN, llm_clients=[])

        assert verdict.corpus_run_id is None
        assert any("corpus start_run failed" in str(w.message) for w in caught)
    finally:
        _teardown()


def test_failure_isolation_finalize_raises(tmp_path):
    """If finalize_run raises, check() still returns a valid Verdict."""
    _make_db(tmp_path)
    try:
        from plan_forge import api

        with patch.object(
            CorpusRecorder, "finalize_run", side_effect=RuntimeError("commit failed")
        ):
            with warnings.catch_warnings(record=True) as caught:
                warnings.simplefilter("always")
                verdict = api.check(MINIMAL_PLAN, llm_clients=[])

        # corpus_run_id IS set because start_run succeeded
        assert isinstance(verdict.corpus_run_id, int)
        assert any("corpus finalize_run failed" in str(w.message) for w in caught)
    finally:
        _teardown()


def test_gate_exceptions_propagate(tmp_path):
    """Errors from functional gates (mechanical/epistemic) propagate; not swallowed."""
    _make_db(tmp_path)
    try:
        from plan_forge import api
        from plan_forge.checks import mechanical

        with patch.object(
            mechanical, "run", side_effect=ValueError("gate internal error")
        ):
            with pytest.raises(ValueError, match="gate internal error"):
                api.check(MINIMAL_PLAN, llm_clients=[])
    finally:
        _teardown()


# ---------------------------------------------------------------------------
# actual_cost=None stored as NULL
# ---------------------------------------------------------------------------

def test_actual_cost_none_stored_as_null(tmp_path):
    """finalize_run(actual_cost_usd=None) stores NULL in plan_runs."""
    _make_db(tmp_path)
    try:
        rec = CorpusRecorder()
        run_id = rec.start_run(
            _FakePlan(), None, "0.1.0", "off", 0.0,
        )
        rec.finalize_run(run_id, "PASS", "PASS", None)
        with corpus_db.session_scope() as s:
            row = s.get(PlanRun, run_id)
            assert row.actual_cost_usd is None
    finally:
        _teardown()


# ---------------------------------------------------------------------------
# circular-import regression
# ---------------------------------------------------------------------------

def test_no_circular_import():
    """import plan_forge must succeed without ImportError (circular-import gate)."""
    result = subprocess.run(
        [sys.executable, "-c", "import plan_forge; print('ok')"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        f"circular import detected. stderr:\n{result.stderr}"
    )
    assert "ok" in result.stdout
