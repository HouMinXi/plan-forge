"""Corpus record writer -- sole write path into the ledger.

All public methods INSERT new rows (append-only).  Exactly two controlled
UPDATEs exist:

  finalize_run   -- sets plan_runs.completed_at, verdicts, actual_cost_usd
                    once; raises if the run is already finalized.
  update_evidence_tier -- sets llm_evidence.tier monotonically; same value
                    is a no-op; any change from a classified tier raises.

No delete, no generic update.
"""
from __future__ import annotations

import hashlib
from datetime import datetime, timezone

from plan_forge.corpus import db
from plan_forge.corpus.models import (
    Arbitration,
    Finding as DBFinding,
    LLMEvidence as DBLLMEvidence,
    Outcome,
    PlanRun,
)
from plan_forge.verdict import (
    EvidenceTier,
    Finding,
    LLMEvidence,
)


class CorpusRecorder:
    """Write-only interface to the corpus ledger.

    Construction is no-arg; each method opens a session via the
    singleton engine so tests can inject a temp DB via
    PLAN_FORGE_CORPUS_URL + db._reset_engine().
    """

    def __init__(self) -> None:
        pass

    def start_run(
        self,
        plan,
        plan_path: str | None,
        plan_forge_version: str,
        arbitration_mode: str,
        cost_cap_usd: float,
    ) -> int:
        """Open a new plan-run row and return its run_id.

        plan is a ParsedPlan; plan_path is passed separately because
        ParsedPlan carries no path field (it may be None for stdin/tmp).
        plan_hash is the first 16 hex chars of SHA-256(plan.raw_text).
        """
        plan_hash = hashlib.sha256(
            plan.raw_text.encode("utf-8")
        ).hexdigest()[:16]
        row = PlanRun(
            plan_hash=plan_hash,
            plan_text=plan.raw_text,
            plan_path=plan_path,
            plan_forge_version=plan_forge_version,
            arbitration_mode=arbitration_mode,
            cost_cap_usd=cost_cap_usd,
            started_at=datetime.now(timezone.utc),
        )
        with db.session_scope() as session:
            session.add(row)
            session.flush()
            run_id: int = row.run_id
        return run_id

    def finalize_run(
        self,
        run_id: int,
        engineering_verdict: str,
        epistemic_verdict: str,
        actual_cost_usd: float,
    ) -> None:
        """Stamp completion fields on an open run.

        Raises ValueError if the run is already finalized (completed_at
        is set).  Only completion fields are written; plan_hash,
        plan_text, started_at, etc. are never touched.
        """
        with db.session_scope() as session:
            row = session.get(PlanRun, run_id)
            if row is None:
                raise ValueError(f"run_id {run_id} not found")
            if row.completed_at is not None:
                raise ValueError(
                    f"run_id {run_id} is already finalized"
                )
            row.completed_at = datetime.now(timezone.utc)
            row.engineering_verdict = engineering_verdict
            row.epistemic_verdict = epistemic_verdict
            row.actual_cost_usd = actual_cost_usd

    def record_finding(self, run_id: int, finding: Finding) -> int:
        """Insert one finding row and return its finding_id."""
        row = DBFinding(
            run_id=run_id,
            check_id=finding.check_id,
            severity=finding.severity.value,
            location=finding.location,
            message=finding.message,
            fix_hint=finding.fix_hint or None,
        )
        with db.session_scope() as session:
            session.add(row)
            session.flush()
            finding_id: int = row.finding_id
        return finding_id

    def record_evidence(
        self,
        run_id: int,
        gate_id: str,
        target_id,
        evidence: LLMEvidence,
    ) -> int:
        """Insert one LLM evidence row and return its evidence_id.

        The param run_id is canonical: it is written to the row and
        backfilled onto evidence.run_id even if the object already
        carries a stale value.  evidence.evidence_id is also backfilled
        after INSERT.
        """
        row = DBLLMEvidence(
            run_id=run_id,
            gate_id=gate_id,
            target_id=str(target_id) if target_id is not None else None,
            provider=evidence.provider,
            model=evidence.model,
            prompt_version=evidence.prompt_version,
            verdict=evidence.verdict,
            reasoning=evidence.reasoning,
            cited_instances=evidence.cited_instances or None,
            search_evidence=evidence.search_evidence or None,
            tier=evidence.tier.value,
            g10_run=False,
        )
        with db.session_scope() as session:
            session.add(row)
            session.flush()
            evidence_id: int = row.evidence_id
        # Backfill both IDs so callers have a consistent object.
        evidence.run_id = run_id
        evidence.evidence_id = evidence_id
        return evidence_id

    def update_evidence_tier(self, evidence: LLMEvidence) -> None:
        """Update the tier of an existing evidence row.

        Requires evidence.evidence_id (set by record_evidence).
        Three-way monotonic rule:
          UNCLASSIFIED -> T* : allowed, UPDATE
          T* -> same T*      : no-op (idempotent retry)
          T* -> any change   : raises ValueError (downgrade or conflict)
        """
        if evidence.evidence_id is None:
            raise ValueError(
                "evidence.evidence_id is None; "
                "call record_evidence first"
            )
        new_tier = evidence.tier.value
        with db.session_scope() as session:
            row = session.get(DBLLMEvidence, evidence.evidence_id)
            if row is None:
                raise ValueError(
                    f"evidence_id {evidence.evidence_id} not found"
                )
            current = row.tier  # TEXT stored in DB, e.g. "T1"
            if current == new_tier:
                return  # idempotent no-op
            if current != EvidenceTier.UNCLASSIFIED.value:
                raise ValueError(
                    f"evidence_id {evidence.evidence_id}: tier "
                    f"conflict {current!r} -> {new_tier!r}"
                )
            row.tier = new_tier

    def record_arbitration(
        self,
        run_id: int,
        finding_id: int | None,
        bundle_text: str,
        human_verdict: str | None,
        human_rationale: str | None,
        overrode_llm: bool | None,
    ) -> int:
        """Insert one arbitration row and return its arbitration_id."""
        row = Arbitration(
            run_id=run_id,
            finding_id=finding_id,
            triggered_at=datetime.now(timezone.utc),
            bundle_text=bundle_text,
            human_verdict=human_verdict,
            human_rationale=human_rationale,
            overrode_llm=overrode_llm,
            captured_at=(
                datetime.now(timezone.utc)
                if human_verdict is not None
                else None
            ),
        )
        with db.session_scope() as session:
            session.add(row)
            session.flush()
            arb_id: int = row.arbitration_id
        return arb_id

    def record_outcome(
        self,
        run_id: int,
        finding_id: int | None,
        outcome_type: str,
        outcome_date: datetime,
        evidence: str | None,
        recorder: str,
        notes: str | None = None,
    ) -> int:
        """Insert one outcome row and return its outcome_id."""
        row = Outcome(
            run_id=run_id,
            finding_id=finding_id,
            outcome_type=outcome_type,
            outcome_date=outcome_date,
            evidence=evidence,
            recorder=recorder,
            notes=notes,
        )
        with db.session_scope() as session:
            session.add(row)
            session.flush()
            outcome_id: int = row.outcome_id
        return outcome_id
