"""Corpus query helpers -- read-only access to the ledger.

Each helper uses session_scope() (singleton engine) so tests can inject a
temp DB via PLAN_FORGE_CORPUS_URL + db._reset_engine().  All helpers accept
an optional limit: int | None = None to cap result sets without coupling
callers to a pagination DSL now.
"""
from __future__ import annotations

from plan_forge.corpus import db
from plan_forge.corpus.models import (
    Arbitration,
    Finding,
    LLMEvidence,
    Outcome,
    PlanRun,
)


def get_run(run_id: int) -> PlanRun | None:
    """Return the PlanRun row for run_id, or None if not found."""
    with db.session_scope() as session:
        row = session.get(PlanRun, run_id)
        if row is None:
            return None
        session.expunge(row)
        return row


def list_findings(
    run_id: int,
    *,
    limit: int | None = None,
) -> list[Finding]:
    """Return Finding rows for a run, ordered by finding_id."""
    with db.session_scope() as session:
        q = (
            session.query(Finding)
            .filter(Finding.run_id == run_id)
            .order_by(Finding.finding_id)
        )
        if limit is not None:
            q = q.limit(limit)
        rows = q.all()
        for r in rows:
            session.expunge(r)
        return rows


def list_evidence(
    run_id: int,
    *,
    tier: str | None = None,
    gate_id: str | None = None,
    limit: int | None = None,
) -> list[LLMEvidence]:
    """Return LLMEvidence rows for a run with optional filters.

    tier filters on the TEXT value stored in the DB (e.g. "T1", "T2",
    "UNCLASSIFIED").  gate_id is an exact match (e.g. "G6.B").
    Rows are ordered by evidence_id.
    """
    with db.session_scope() as session:
        q = (
            session.query(LLMEvidence)
            .filter(LLMEvidence.run_id == run_id)
        )
        if tier is not None:
            q = q.filter(LLMEvidence.tier == tier)
        if gate_id is not None:
            q = q.filter(LLMEvidence.gate_id == gate_id)
        q = q.order_by(LLMEvidence.evidence_id)
        if limit is not None:
            q = q.limit(limit)
        rows = q.all()
        for r in rows:
            session.expunge(r)
        return rows


def list_outcomes(
    run_id: int,
    *,
    limit: int | None = None,
) -> list[Outcome]:
    """Return Outcome rows for a run, ordered by outcome_id."""
    with db.session_scope() as session:
        q = (
            session.query(Outcome)
            .filter(Outcome.run_id == run_id)
            .order_by(Outcome.outcome_id)
        )
        if limit is not None:
            q = q.limit(limit)
        rows = q.all()
        for r in rows:
            session.expunge(r)
        return rows


def list_arbitrations(
    run_id: int,
    *,
    limit: int | None = None,
) -> list[Arbitration]:
    """Return Arbitration rows for a run, ordered by arbitration_id."""
    with db.session_scope() as session:
        q = (
            session.query(Arbitration)
            .filter(Arbitration.run_id == run_id)
            .order_by(Arbitration.arbitration_id)
        )
        if limit is not None:
            q = q.limit(limit)
        rows = q.all()
        for r in rows:
            session.expunge(r)
        return rows
