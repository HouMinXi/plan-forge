"""Tests for tools/outcomes_cli.py -- real SQLite corpus DB (no mocks)."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

_TOOLS_DIR = str(
    Path(__file__).resolve().parents[2] / "tools"
)
if _TOOLS_DIR not in sys.path:
    sys.path.insert(0, _TOOLS_DIR)

import outcomes_cli  # noqa: E402
from plan_forge.corpus.query import list_outcomes  # noqa: E402


def _make_run(corpus_engine) -> int:
    """Insert a minimal PlanRun row and return its run_id."""
    from datetime import datetime, timezone
    from plan_forge.corpus.models import PlanRun
    from sqlalchemy.orm import Session

    with Session(corpus_engine) as session:
        row = PlanRun(
            plan_hash="abc123",
            plan_text="test plan",
            plan_path=None,
            plan_forge_version="0.1.0",
            arbitration_mode="none",
            cost_cap_usd=0.0,
            started_at=datetime.now(timezone.utc),
        )
        session.add(row)
        session.commit()
        return row.run_id


def _args(**kwargs):
    """Build a Namespace with record-outcome defaults."""
    defaults = dict(
        run_id=1,
        type="plan_succeeded",
        date=None,
        evidence=None,
        recorder="test-user",
        finding_id=None,
        notes=None,
    )
    defaults.update(kwargs)
    return argparse.Namespace(**defaults)


class TestRecordOutcome:
    def test_inserts_row_into_real_db(self, corpus_engine):
        """record() writes one outcome row; list_outcomes confirms it."""
        run_id = _make_run(corpus_engine)
        args = _args(
            run_id=run_id,
            type="plan_succeeded",
            recorder="alice",
            evidence="PR merged successfully",
            date="2025-11-01",
        )

        rc = outcomes_cli.record(args)

        assert rc == 0
        rows = list_outcomes(run_id)
        assert len(rows) == 1
        row = rows[0]
        assert row.outcome_type == "plan_succeeded"
        assert row.recorder == "alice"
        assert row.evidence == "PR merged successfully"

    def test_all_valid_outcome_types_accepted(self, corpus_engine):
        """Each of the four allowed outcome_type values is accepted."""
        run_id = _make_run(corpus_engine)
        for ot in sorted(outcomes_cli.ALLOWED_OUTCOME_TYPES):
            args = _args(run_id=run_id, type=ot, recorder="tester")
            rc = outcomes_cli.record(args)
            assert rc == 0, f"expected rc=0 for type={ot!r}"

        rows = list_outcomes(run_id)
        assert len(rows) == 4

    def test_invalid_type_rejected_nonzero_exit(
        self, corpus_engine, capsys
    ):
        """An unknown outcome_type yields rc=1, no row written."""
        run_id = _make_run(corpus_engine)
        args = _args(run_id=run_id, type="bad_type", recorder="bot")

        rc = outcomes_cli.record(args)

        assert rc == 1
        stderr = capsys.readouterr().err
        assert "unknown outcome type" in stderr
        assert len(list_outcomes(run_id)) == 0

    def test_default_date_is_today(self, corpus_engine):
        """When --date is omitted the outcome_date is set to today UTC."""
        from datetime import date
        run_id = _make_run(corpus_engine)
        args = _args(run_id=run_id, recorder="ci")

        rc = outcomes_cli.record(args)

        assert rc == 0
        row = list_outcomes(run_id)[0]
        today = date.today()
        assert row.outcome_date.year == today.year
        assert row.outcome_date.month == today.month
        assert row.outcome_date.day == today.day

    def test_invalid_date_rejected(self, corpus_engine, capsys):
        """A non-ISO date string yields rc=1 with a message."""
        run_id = _make_run(corpus_engine)
        args = _args(run_id=run_id, date="not-a-date", recorder="ci")

        rc = outcomes_cli.record(args)

        assert rc == 1
        err = capsys.readouterr().err
        assert "invalid date" in err

    def test_optional_fields_notes_finding_id(self, corpus_engine):
        """notes and finding_id are stored when provided."""
        run_id = _make_run(corpus_engine)
        args = _args(
            run_id=run_id,
            recorder="dev",
            notes="observed in prod",
            finding_id=None,
        )

        rc = outcomes_cli.record(args)

        assert rc == 0
        row = list_outcomes(run_id)[0]
        assert row.notes == "observed in prod"
        assert row.finding_id is None

    def test_allowed_outcome_types_constant(self):
        """ALLOWED_OUTCOME_TYPES matches the model CHECK constraint exactly."""
        expected = {
            "predicted_manifested",
            "predicted_did_not_manifest",
            "unpredicted_occurred",
            "plan_succeeded",
        }
        assert outcomes_cli.ALLOWED_OUTCOME_TYPES == expected
