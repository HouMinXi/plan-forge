"""Tests for tools/abandon.py -- abandonment truth table against real SQLite.

All three truth-table rows drive a real corpus DB, no mocks.
"""
from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

_TOOLS_DIR = str(
    Path(__file__).resolve().parents[2] / "tools"
)
if _TOOLS_DIR not in sys.path:
    sys.path.insert(0, _TOOLS_DIR)

import abandon  # noqa: E402
from plan_forge.corpus.models import Outcome, PlanRun  # noqa: E402


_SIX_MONTHS_DAYS = abandon._SIX_MONTHS_DAYS
_VERSION = "0.1.0"


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _insert_run(session, started_at: datetime) -> int:
    """Insert a PlanRun row with the given started_at; return run_id."""
    row = PlanRun(
        plan_hash="cafebabe",
        plan_text="test",
        plan_path=None,
        plan_forge_version=_VERSION,
        arbitration_mode="none",
        cost_cap_usd=0.0,
        started_at=started_at,
    )
    session.add(row)
    session.flush()
    return row.run_id


def _insert_outcome(session, run_id: int) -> None:
    """Insert one outcome row linked to run_id."""
    row = Outcome(
        run_id=run_id,
        finding_id=None,
        outcome_type="plan_succeeded",
        outcome_date=_now(),
        evidence=None,
        recorder="test",
        notes=None,
    )
    session.add(row)


def _old_date() -> datetime:
    """A started_at that is clearly older than 6 months."""
    return _now() - timedelta(days=_SIX_MONTHS_DAYS + 10)


def _recent_date() -> datetime:
    """A started_at clearly within the 6-month window."""
    return _now() - timedelta(days=30)


class TestCheckAbandonmentTruthTable:
    """Abandonment truth table: all three cases against a real SQLite DB.

    The abandon condition in check_abandonment() is:
      age_days > _SIX_MONTHS_DAYS  AND  count_all_outcomes() == 0
    """

    def test_case1_old_run_no_outcomes_generates_tombstone(
        self, corpus_engine, tmp_path
    ):
        """Oldest run > 6 months, 0 outcomes -> ABANDONMENT.md generated."""
        from sqlalchemy.orm import Session

        with Session(corpus_engine) as session:
            _insert_run(session, _old_date())
            session.commit()

        db_path = tmp_path / "corpus.db"
        result = abandon.check_abandonment(db_path, _VERSION)

        assert result is not None
        assert result.name == "ABANDONMENT.md"
        assert result.exists()
        text = result.read_text(encoding="utf-8")
        assert "# plan-forge ABANDONED" in text
        assert "Version at abandonment:" in text
        assert "First-run date:" in text
        assert "Revival criteria" in text
        assert "Revival process" in text

    def test_case2_old_run_with_outcome_not_generated(
        self, corpus_engine, tmp_path
    ):
        """Old run + outcome present -> ABANDONMENT.md NOT generated."""
        from sqlalchemy.orm import Session

        with Session(corpus_engine) as session:
            run_id = _insert_run(session, _old_date())
            _insert_outcome(session, run_id)
            session.commit()

        db_path = tmp_path / "corpus.db"
        result = abandon.check_abandonment(db_path, _VERSION)

        assert result is None

    def test_case3_recent_run_no_outcomes_not_generated(
        self, corpus_engine, tmp_path
    ):
        """Oldest run < 6 months, 0 outcomes -> ABANDONMENT.md NOT generated."""
        from sqlalchemy.orm import Session

        with Session(corpus_engine) as session:
            _insert_run(session, _recent_date())
            session.commit()

        db_path = tmp_path / "corpus.db"
        result = abandon.check_abandonment(db_path, _VERSION)

        assert result is None

    def test_no_runs_at_all_not_generated(self, corpus_engine, tmp_path):
        """Empty plan_runs table -> not triggered (nothing to be old)."""
        db_path = tmp_path / "corpus.db"
        result = abandon.check_abandonment(db_path, _VERSION)

        assert result is None


class TestTombstoneContent:
    def test_tombstone_contains_version_and_db_path(
        self, corpus_engine, tmp_path
    ):
        """Tombstone text embeds plan_forge_version and db_path."""
        from sqlalchemy.orm import Session

        version = "0.9.9"
        with Session(corpus_engine) as session:
            _insert_run(session, _old_date())
            session.commit()

        db_path = tmp_path / "mydb.db"
        result = abandon.check_abandonment(db_path, version)

        assert result is not None
        text = result.read_text(encoding="utf-8")
        assert version in text
        assert str(db_path) in text

    def test_tombstone_includes_revival_tag_line(
        self, corpus_engine, tmp_path
    ):
        """Tombstone revival process step 1 cites a git tag."""
        from sqlalchemy.orm import Session

        with Session(corpus_engine) as session:
            _insert_run(session, _old_date())
            session.commit()

        db_path = tmp_path / "corpus.db"
        result = abandon.check_abandonment(db_path, _VERSION)

        assert result is not None
        text = result.read_text(encoding="utf-8")
        assert "git tag" in text
        assert "-revived" in text

    def test_tombstone_written_at_parent_of_db_path(
        self, corpus_engine, tmp_path
    ):
        """ABANDONMENT.md lands in the parent directory of db_path."""
        from sqlalchemy.orm import Session

        subdir = tmp_path / "data"
        subdir.mkdir()
        db_path = subdir / "corpus.db"

        with Session(corpus_engine) as session:
            _insert_run(session, _old_date())
            session.commit()

        result = abandon.check_abandonment(db_path, _VERSION)

        assert result is not None
        assert result.parent == subdir.resolve()


class TestBoundaryConditions:
    def test_exactly_six_months_not_triggered(
        self, corpus_engine, tmp_path
    ):
        """A run exactly _SIX_MONTHS_DAYS old is NOT old enough to trigger.

        The condition is strictly greater-than, not greater-or-equal.
        """
        from sqlalchemy.orm import Session

        boundary = _now() - timedelta(days=_SIX_MONTHS_DAYS)
        with Session(corpus_engine) as session:
            _insert_run(session, boundary)
            session.commit()

        db_path = tmp_path / "corpus.db"
        result = abandon.check_abandonment(db_path, _VERSION)

        assert result is None

    def test_one_day_past_six_months_triggers(
        self, corpus_engine, tmp_path
    ):
        """A run _SIX_MONTHS_DAYS + 1 days old with 0 outcomes triggers."""
        from sqlalchemy.orm import Session

        past = _now() - timedelta(days=_SIX_MONTHS_DAYS + 1)
        with Session(corpus_engine) as session:
            _insert_run(session, past)
            session.commit()

        db_path = tmp_path / "corpus.db"
        result = abandon.check_abandonment(db_path, _VERSION)

        assert result is not None

    def test_multiple_runs_oldest_governs(self, corpus_engine, tmp_path):
        """A recent run does not hide an older one that triggers."""
        from sqlalchemy.orm import Session

        with Session(corpus_engine) as session:
            _insert_run(session, _old_date())
            _insert_run(session, _recent_date())
            session.commit()

        db_path = tmp_path / "corpus.db"
        result = abandon.check_abandonment(db_path, _VERSION)

        assert result is not None
