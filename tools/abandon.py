"""abandonment-check: self-falsifying clause for plan-forge.

After 6 calendar months, if plan_runs has at least one entry older
than 6 months and the outcomes table has 0 rows, generate ABANDONMENT.md
at the repo root.  Returns the tombstone path, or None when not triggered.
"""
from __future__ import annotations

from datetime import date, datetime, timezone
from pathlib import Path

from plan_forge.corpus.query import (
    count_all_outcomes,
    oldest_plan_run_date,
)

_SIX_MONTHS_DAYS = 183


def _today_utc() -> date:
    return datetime.now(timezone.utc).date()


def _tombstone_text(
    today: date,
    plan_forge_version: str,
    oldest_run_date: date,
    db_path: str,
) -> str:
    return (
        "# plan-forge ABANDONED\n"
        "\n"
        f"Date: {today}\n"
        f"Version at abandonment: {plan_forge_version}\n"
        f"First-run date: {oldest_run_date}\n"
        "\n"
        "Reason: 6+ months elapsed since first plan-forge run with 0\n"
        "outcomes recorded; tool has not been empirically validated by\n"
        "practice per MANIFESTO Section 6.\n"
        "\n"
        "## Revival criteria (any one):\n"
        "- 3+ post-implementation failures within 6 months that fit\n"
        "  G1-G10 patterns (recorded as outcomes after abandonment)\n"
        "- New domain emerges where plan rollback cost is irreversibly\n"
        "  high (per MANIFESTO scope)\n"
        "- Independent third-party LEARNINGS-style failure corpus reaches\n"
        "  N >= 20 entries, providing ground truth absent at abandonment\n"
        "\n"
        "## Revival process:\n"
        f"1. `git tag v{plan_forge_version}-revived`\n"
        "2. Update MANIFESTO Section 6 empirical-grounding statement with\n"
        "   new evidence\n"
        f"3. Run retroactive audit on the new failure cases (corpus_db\n"
        f"   preserved at {db_path})\n"
        "4. If catches >= 60% of independent failure patterns per the\n"
        "   plan's empirical-grounding criterion, revive is justified\n"
        "5. Resume work on next v0.x or v0.x+1\n"
        "\n"
        f"corpus_db preserved at: {db_path}\n"
    )


def check_abandonment(
    db_path: Path, plan_forge_version: str
) -> Path | None:
    """Generate ABANDONMENT.md when the abandonment trigger fires.

    Trigger conditions (both must hold):
      - At least one plan_run started more than 6 calendar months ago.
      - The outcomes table contains 0 rows across all runs.

    Returns the Path to the generated tombstone, or None if not triggered.
    """
    oldest = oldest_plan_run_date()
    if oldest is None:
        return None

    if isinstance(oldest, datetime):
        oldest_date = oldest.date()
    else:
        oldest_date = oldest

    today = _today_utc()
    age_days = (today - oldest_date).days
    if age_days <= _SIX_MONTHS_DAYS:
        return None

    if count_all_outcomes() > 0:
        return None

    tombstone_path = Path(db_path).resolve().parent / "ABANDONMENT.md"
    tombstone_path.write_text(
        _tombstone_text(today, plan_forge_version, oldest_date, str(db_path)),
        encoding="utf-8",
    )
    return tombstone_path
