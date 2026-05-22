"""SQLAlchemy ORM models for the plan-forge corpus DB.

All column types use SQLAlchemy generic types so the same models work on
SQLite (default) and Postgres (opt-in); no dialect-specific extensions.
"""
from __future__ import annotations


from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    Text,
)
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.sql import func


class Base(DeclarativeBase):
    pass


class LLMCache(Base):
    """LLM prompt/response cache.

    key: SHA-256 hex digest (64 chars) of cache_key_inputs + provider +
         model + tool_use schema version.
    payload: full LLMResponse as dict; generic JSON maps to JSONB on
             Postgres and TEXT (auto-encoded) on SQLite.
    ttl_class: "canonical" (7 days) / "recent" (24 h) / "never_expire".
    expires_at: None for never_expire; set for others.
    """
    __tablename__ = "llm_cache"

    key = Column(String(64), primary_key=True)
    provider = Column(String(32), nullable=False)
    model = Column(String(64), nullable=False)
    prompt_version = Column(String(32), nullable=False)
    # generic JSON: JSONB on Postgres, TEXT on SQLite
    payload = Column(JSON, nullable=False)
    ttl_class = Column(String(16), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


# Plain b-tree indexes only (no GIN/GiST -- those are PG-specific)
Index("idx_llm_cache_expires_at", LLMCache.expires_at)
Index("idx_llm_cache_provider_model", LLMCache.provider, LLMCache.model)


class SchemaVersion(Base):
    """Single-row corpus-integrity marker (SC-16).

    version: corpus schema version string (e.g. "1").
    applied_at: when this version was stamped (auto-set on insert).
    """
    __tablename__ = "schema_version"

    version = Column(String, primary_key=True)
    applied_at = Column(
        DateTime,
        nullable=False,
        server_default=func.now(),
    )


class PlanRun(Base):
    """One plan-forge run over a plan document (append-only)."""
    __tablename__ = "plan_runs"

    run_id = Column(Integer, primary_key=True, autoincrement=True)
    plan_hash = Column(Text, nullable=False)          # sha256(plan_text)[:16]
    plan_text = Column(Text, nullable=True)           # NULL if --corpus-private
    plan_path = Column(Text, nullable=True)           # source path (may be /tmp)
    plan_forge_version = Column(Text, nullable=False) # e.g. "0.1.0"
    arbitration_mode = Column(Text, nullable=False)
    cost_cap_usd = Column(Float, nullable=False)
    actual_cost_usd = Column(Float, nullable=True)
    started_at = Column(DateTime, nullable=False)
    completed_at = Column(DateTime, nullable=True)
    engineering_verdict = Column(Text, nullable=True) # "PASS" / "FAIL"
    epistemic_verdict = Column(Text, nullable=True)   # "PASS" / "FAIL" / "VISION"


Index("idx_plan_runs_plan_hash", PlanRun.plan_hash)


class Finding(Base):
    """One check finding within a plan run (append-only)."""
    __tablename__ = "findings"

    finding_id = Column(Integer, primary_key=True, autoincrement=True)
    run_id = Column(
        Integer, ForeignKey("plan_runs.run_id"), nullable=False
    )
    check_id = Column(Text, nullable=False)  # "F1" / "G6.A.mechanical"
    severity = Column(Text, nullable=False)
    location = Column(Text, nullable=False)
    message = Column(Text, nullable=False)
    fix_hint = Column(Text, nullable=True)


Index("idx_findings_run_id", Finding.run_id)
Index("idx_findings_check_id", Finding.check_id)


class LLMEvidence(Base):
    """LLM call record associated with a run (append-only; tier is monotonic)."""
    __tablename__ = "llm_evidence"

    evidence_id = Column(Integer, primary_key=True, autoincrement=True)
    run_id = Column(
        Integer, ForeignKey("plan_runs.run_id"), nullable=False
    )
    gate_id = Column(Text, nullable=False)        # "G6.B" / "G8.B" / "G10.B"
    target_id = Column(Text, nullable=True)        # SC number / anchor line
    provider = Column(Text, nullable=False)
    model = Column(Text, nullable=False)
    prompt_version = Column(Text, nullable=False)
    verdict = Column(Text, nullable=False)         # provider's verdict
    reasoning = Column(Text, nullable=True)
    # JSON arrays: generic JSON maps to JSONB on Postgres, TEXT on SQLite
    cited_instances = Column(JSON, nullable=True)
    search_evidence = Column(JSON, nullable=True)
    tier = Column(Text, nullable=True)             # T1 / T2 / T3 / T4
    g10_run = Column(Boolean, nullable=False, default=False)
    cost_usd = Column(Float, nullable=True)
    recorded_at = Column(
        DateTime,
        nullable=False,
        server_default=func.now(),
    )


Index("idx_llm_evidence_run_id", LLMEvidence.run_id)
Index("idx_llm_evidence_tier", LLMEvidence.tier)


class Arbitration(Base):
    """Human-in-the-loop arbitration event (append-only)."""
    __tablename__ = "arbitrations"

    arbitration_id = Column(Integer, primary_key=True, autoincrement=True)
    run_id = Column(
        Integer, ForeignKey("plan_runs.run_id"), nullable=False
    )
    finding_id = Column(
        Integer, ForeignKey("findings.finding_id"), nullable=True
    )
    triggered_at = Column(DateTime, nullable=False)
    bundle_text = Column(Text, nullable=False)     # evidence bundle shown to human
    # CHECK enforces the canonical 4-value vocabulary (see bundle.py)
    human_verdict = Column(Text, nullable=True)
    human_rationale = Column(Text, nullable=True)
    overrode_llm = Column(Boolean, nullable=True)  # True if user disagreed
    captured_at = Column(DateTime, nullable=True)

    __table_args__ = (
        CheckConstraint(
            "human_verdict IS NULL OR human_verdict IN "
            "('verified', 'unverified', 'deferred', 'abstain')",
            name="ck_arbitrations_human_verdict",
        ),
    )


Index("idx_arbitrations_run_id", Arbitration.run_id)


class Outcome(Base):
    """Post-hoc outcome record linking a prediction to real-world result."""
    __tablename__ = "outcomes"

    outcome_id = Column(Integer, primary_key=True, autoincrement=True)
    run_id = Column(
        Integer, ForeignKey("plan_runs.run_id"), nullable=False
    )
    finding_id = Column(
        Integer, ForeignKey("findings.finding_id"), nullable=True
    )
    outcome_type = Column(Text, nullable=False)
    outcome_date = Column(DateTime, nullable=False)
    evidence = Column(Text, nullable=True)         # post-hoc evidence
    recorder = Column(Text, nullable=False)        # "Minxi" / CI
    notes = Column(Text, nullable=True)
    recorded_at = Column(
        DateTime,
        nullable=False,
        server_default=func.now(),
    )

    __table_args__ = (
        CheckConstraint(
            "outcome_type IN ("
            "'predicted_manifested', "
            "'predicted_did_not_manifest', "
            "'unpredicted_occurred', "
            "'plan_succeeded'"
            ")",
            name="ck_outcomes_outcome_type",
        ),
    )


Index("idx_outcomes_run_id", Outcome.run_id)
Index("idx_outcomes_type", Outcome.outcome_type)
