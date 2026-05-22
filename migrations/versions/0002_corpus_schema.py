"""Create the 6 corpus event-sourcing tables and seed schema_version.

Revision ID: 0002_corpus_schema
Revises: 0001_llm_cache
Create Date: 2026-05-22

The schema_version row (version="1") is seeded so the corpus-integrity
check finds a non-empty marker on a fresh database.

Two CHECK constraints on externally/human-fed columns only:
  - arbitrations.human_verdict: one of the 4 canonical values
  - outcomes.outcome_type: one of the 4 outcome type values
Internal enum columns (severity, verdict, arbitration_mode) carry no DB
constraint; the application layer enforces those.

FKs are declared but SQLite does not enforce them without
PRAGMA foreign_keys=ON, which belongs in corpus/db.py (first writer).
"""
from alembic import op
import sqlalchemy as sa

revision = "0002_corpus_schema"
down_revision = "0001_llm_cache"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. schema_version -- no FKs; created first
    op.create_table(
        "schema_version",
        sa.Column("version", sa.String(), primary_key=True),
        sa.Column(
            "applied_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    # 2. plan_runs -- root entity; all others FK here
    op.create_table(
        "plan_runs",
        sa.Column("run_id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("plan_hash", sa.Text(), nullable=False),
        sa.Column("plan_text", sa.Text(), nullable=True),
        sa.Column("plan_path", sa.Text(), nullable=True),
        sa.Column("plan_forge_version", sa.Text(), nullable=False),
        sa.Column("arbitration_mode", sa.Text(), nullable=False),
        sa.Column("cost_cap_usd", sa.Float(), nullable=False),
        sa.Column("actual_cost_usd", sa.Float(), nullable=True),
        sa.Column("started_at", sa.DateTime(), nullable=False),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("engineering_verdict", sa.Text(), nullable=True),
        sa.Column("epistemic_verdict", sa.Text(), nullable=True),
    )
    op.create_index("idx_plan_runs_plan_hash", "plan_runs", ["plan_hash"])

    # 3. findings -- FK to plan_runs
    op.create_table(
        "findings",
        sa.Column("finding_id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "run_id",
            sa.Integer(),
            sa.ForeignKey("plan_runs.run_id"),
            nullable=False,
        ),
        sa.Column("check_id", sa.Text(), nullable=False),
        sa.Column("severity", sa.Text(), nullable=False),
        sa.Column("location", sa.Text(), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("fix_hint", sa.Text(), nullable=True),
    )
    op.create_index("idx_findings_run_id", "findings", ["run_id"])
    op.create_index("idx_findings_check_id", "findings", ["check_id"])

    # 4. llm_evidence -- FK to plan_runs
    op.create_table(
        "llm_evidence",
        sa.Column("evidence_id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "run_id",
            sa.Integer(),
            sa.ForeignKey("plan_runs.run_id"),
            nullable=False,
        ),
        sa.Column("gate_id", sa.Text(), nullable=False),
        sa.Column("target_id", sa.Text(), nullable=True),
        sa.Column("provider", sa.Text(), nullable=False),
        sa.Column("model", sa.Text(), nullable=False),
        sa.Column("prompt_version", sa.Text(), nullable=False),
        sa.Column("verdict", sa.Text(), nullable=False),
        sa.Column("reasoning", sa.Text(), nullable=True),
        sa.Column("cited_instances", sa.JSON(), nullable=True),
        sa.Column("search_evidence", sa.JSON(), nullable=True),
        sa.Column("tier", sa.Text(), nullable=True),
        sa.Column(
            "g10_run", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
        sa.Column("cost_usd", sa.Float(), nullable=True),
        sa.Column(
            "recorded_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("idx_llm_evidence_run_id", "llm_evidence", ["run_id"])
    op.create_index("idx_llm_evidence_tier", "llm_evidence", ["tier"])

    # 5. arbitrations -- FK to plan_runs + findings; CHECK on human_verdict
    op.create_table(
        "arbitrations",
        sa.Column("arbitration_id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "run_id",
            sa.Integer(),
            sa.ForeignKey("plan_runs.run_id"),
            nullable=False,
        ),
        sa.Column(
            "finding_id",
            sa.Integer(),
            sa.ForeignKey("findings.finding_id"),
            nullable=True,
        ),
        sa.Column("triggered_at", sa.DateTime(), nullable=False),
        sa.Column("bundle_text", sa.Text(), nullable=False),
        sa.Column("human_verdict", sa.Text(), nullable=True),
        sa.Column("human_rationale", sa.Text(), nullable=True),
        sa.Column("overrode_llm", sa.Boolean(), nullable=True),
        sa.Column("captured_at", sa.DateTime(), nullable=True),
        sa.CheckConstraint(
            "human_verdict IS NULL OR human_verdict IN "
            "('verified', 'unverified', 'deferred', 'abstain')",
            name="ck_arbitrations_human_verdict",
        ),
    )
    op.create_index("idx_arbitrations_run_id", "arbitrations", ["run_id"])

    # 6. outcomes -- FK to plan_runs + findings; CHECK on outcome_type
    op.create_table(
        "outcomes",
        sa.Column("outcome_id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "run_id",
            sa.Integer(),
            sa.ForeignKey("plan_runs.run_id"),
            nullable=False,
        ),
        sa.Column(
            "finding_id",
            sa.Integer(),
            sa.ForeignKey("findings.finding_id"),
            nullable=True,
        ),
        sa.Column("outcome_type", sa.Text(), nullable=False),
        sa.Column("outcome_date", sa.DateTime(), nullable=False),
        sa.Column("evidence", sa.Text(), nullable=True),
        sa.Column("recorder", sa.Text(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "recorded_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint(
            "outcome_type IN ("
            "'predicted_manifested', "
            "'predicted_did_not_manifest', "
            "'unpredicted_occurred', "
            "'plan_succeeded'"
            ")",
            name="ck_outcomes_outcome_type",
        ),
    )
    op.create_index("idx_outcomes_run_id", "outcomes", ["run_id"])
    op.create_index("idx_outcomes_type", "outcomes", ["outcome_type"])

    # Seed the corpus-integrity marker so a fresh DB is never empty
    op.execute("INSERT INTO schema_version (version) VALUES ('1')")


def downgrade() -> None:
    # Drop in reverse FK order (outcomes and arbitrations reference findings,
    # which references plan_runs; schema_version is independent)
    op.drop_index("idx_outcomes_type", table_name="outcomes")
    op.drop_index("idx_outcomes_run_id", table_name="outcomes")
    op.drop_table("outcomes")

    op.drop_index("idx_arbitrations_run_id", table_name="arbitrations")
    op.drop_table("arbitrations")

    op.drop_index("idx_llm_evidence_tier", table_name="llm_evidence")
    op.drop_index("idx_llm_evidence_run_id", table_name="llm_evidence")
    op.drop_table("llm_evidence")

    op.drop_index("idx_findings_check_id", table_name="findings")
    op.drop_index("idx_findings_run_id", table_name="findings")
    op.drop_table("findings")

    op.drop_index("idx_plan_runs_plan_hash", table_name="plan_runs")
    op.drop_table("plan_runs")

    op.drop_table("schema_version")
