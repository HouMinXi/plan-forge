"""Integration tests for capture_arbitration (T27).

Each test uses the corpus_engine fixture (function-scoped SQLite) from
conftest.py and a real CorpusRecorder.  Tests query the persisted row
directly via SQLAlchemy to assert ground-truth DB state.
"""
from __future__ import annotations

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session

from plan_forge.arbitration.capture import capture_arbitration
from plan_forge.corpus import query as corpus_query
from plan_forge.corpus.models import Arbitration
from plan_forge.corpus.record import CorpusRecorder


class _FakePlan:
    """Minimal ParsedPlan stand-in."""

    def __init__(self, txt: str = "# Plan\nsome text") -> None:
        self.raw_text = txt


def _run_id(recorder: CorpusRecorder) -> int:
    return recorder.start_run(
        _FakePlan(), None, "0.1.0", "auto", 1.0
    )


def _row(engine, arb_id: int) -> Arbitration:
    """Fetch the Arbitration ORM row for arb_id."""
    with Session(engine) as s:
        row = s.get(Arbitration, arb_id)
        assert row is not None
        s.expunge(row)
    return row


def _count(engine) -> int:
    with Session(engine) as s:
        return (
            s.execute(
                text("SELECT COUNT(*) FROM arbitrations")
            ).scalar_one()
        )


def test_unverified_overrode_llm_true(corpus_engine):
    rec = CorpusRecorder()
    run = _run_id(rec)
    arb_id = capture_arbitration(
        rec, run, None, "bundle", "unverified", "rationale"
    )
    row = _row(corpus_engine, arb_id)
    assert row.overrode_llm is True


def test_verified_overrode_llm_false(corpus_engine):
    rec = CorpusRecorder()
    run = _run_id(rec)
    arb_id = capture_arbitration(
        rec, run, None, "bundle", "verified", "rationale"
    )
    row = _row(corpus_engine, arb_id)
    assert row.overrode_llm is False


def test_deferred_overrode_llm_none(corpus_engine):
    rec = CorpusRecorder()
    run = _run_id(rec)
    arb_id = capture_arbitration(
        rec, run, None, "bundle", "deferred", "rationale"
    )
    row = _row(corpus_engine, arb_id)
    assert row.overrode_llm is None


def test_abstain_overrode_llm_none(corpus_engine):
    rec = CorpusRecorder()
    run = _run_id(rec)
    arb_id = capture_arbitration(
        rec, run, None, "bundle", "abstain", "rationale"
    )
    row = _row(corpus_engine, arb_id)
    assert row.overrode_llm is None


def test_none_verdict_overrode_llm_none_and_captured_at_none(
    corpus_engine,
):
    rec = CorpusRecorder()
    run = _run_id(rec)
    arb_id = capture_arbitration(
        rec, run, None, "bundle", None, None
    )
    row = _row(corpus_engine, arb_id)
    assert row.overrode_llm is None
    assert row.captured_at is None


def test_bogus_verdict_raises_no_row_written(corpus_engine):
    rec = CorpusRecorder()
    run = _run_id(rec)
    before = _count(corpus_engine)
    with pytest.raises(ValueError, match="invalid human_verdict"):
        capture_arbitration(
            rec, run, None, "bundle", "bogus", None
        )
    assert _count(corpus_engine) == before


def test_returns_int_arbitration_id(corpus_engine):
    rec = CorpusRecorder()
    run = _run_id(rec)
    arb_id = capture_arbitration(
        rec, run, None, "bundle", "verified", None
    )
    assert isinstance(arb_id, int) and arb_id > 0
    row = _row(corpus_engine, arb_id)
    assert row.arbitration_id == arb_id


def test_human_rationale_persisted_verbatim(corpus_engine):
    rec = CorpusRecorder()
    run = _run_id(rec)
    rationale = "This is a detailed rationale with special chars: <>&"
    arb_id = capture_arbitration(
        rec, run, None, "bundle", "verified", rationale
    )
    row = _row(corpus_engine, arb_id)
    assert row.human_rationale == rationale

    arb_id2 = capture_arbitration(
        rec, run, None, "bundle2", "deferred", None
    )
    row2 = _row(corpus_engine, arb_id2)
    assert row2.human_rationale is None


def test_bundle_text_persisted_verbatim(corpus_engine):
    rec = CorpusRecorder()
    run = _run_id(rec)
    bundle = "## Finding\nline1\nline2"
    arb_id = capture_arbitration(
        rec, run, None, bundle, "verified", None
    )
    row = _row(corpus_engine, arb_id)
    assert row.bundle_text == bundle


def test_finding_id_none_stored_null_and_real_finding_id(corpus_engine):
    from plan_forge.verdict import Finding, Severity

    rec = CorpusRecorder()
    run = _run_id(rec)

    arb_id_null = capture_arbitration(
        rec, run, None, "bundle", "verified", None
    )
    row_null = _row(corpus_engine, arb_id_null)
    assert row_null.finding_id is None

    fid = rec.record_finding(
        run,
        Finding(
            check_id="C1",
            severity=Severity.HIGH,
            location="plan.md:1",
            message="test finding",
        ),
    )
    arb_id_fid = capture_arbitration(
        rec, run, fid, "bundle", "unverified", None
    )
    row_fid = _row(corpus_engine, arb_id_fid)
    assert row_fid.finding_id == fid


def test_run_id_stored_fk_to_plan_run(corpus_engine):
    rec = CorpusRecorder()
    run = _run_id(rec)
    arb_id = capture_arbitration(
        rec, run, None, "bundle", "verified", None
    )
    row = _row(corpus_engine, arb_id)
    assert row.run_id == run


def test_two_captures_produce_two_distinct_rows(corpus_engine):
    rec = CorpusRecorder()
    run = _run_id(rec)
    id1 = capture_arbitration(
        rec, run, None, "bundle-a", "verified", "r1"
    )
    id2 = capture_arbitration(
        rec, run, None, "bundle-b", "unverified", "r2"
    )
    assert id1 != id2
    assert _count(corpus_engine) >= 2
    rows = corpus_query.list_arbitrations(run)
    assert len(rows) == 2
    assert rows[0].arbitration_id == id1
    assert rows[1].arbitration_id == id2
