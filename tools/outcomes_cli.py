"""record-outcome: write a predicted-vs-actual row into the corpus.

Validates outcome_type against the DB model's CHECK constraint before
inserting, so an unknown type is rejected with a nonzero exit rather
than a DB error at write time.
"""
from __future__ import annotations

import sys
from datetime import date, datetime, timezone

from plan_forge.corpus.record import CorpusRecorder

ALLOWED_OUTCOME_TYPES = frozenset(
    {
        "predicted_manifested",
        "predicted_did_not_manifest",
        "unpredicted_occurred",
        "plan_succeeded",
    }
)


def record(args) -> int:
    """Handle the record-outcome subcommand."""
    if args.type not in ALLOWED_OUTCOME_TYPES:
        allowed = ", ".join(sorted(ALLOWED_OUTCOME_TYPES))
        print(
            f"error: unknown outcome type {args.type!r};"
            f" allowed: {allowed}",
            file=sys.stderr,
        )
        return 1

    if args.date:
        try:
            parsed_date = date.fromisoformat(args.date)
            outcome_dt = datetime(
                parsed_date.year,
                parsed_date.month,
                parsed_date.day,
                tzinfo=timezone.utc,
            )
        except ValueError:
            print(
                f"error: invalid date {args.date!r}; use YYYY-MM-DD",
                file=sys.stderr,
            )
            return 1
    else:
        today = date.today()
        outcome_dt = datetime(
            today.year, today.month, today.day, tzinfo=timezone.utc
        )

    recorder = CorpusRecorder()
    outcome_id = recorder.record_outcome(
        run_id=args.run_id,
        finding_id=args.finding_id,
        outcome_type=args.type,
        outcome_date=outcome_dt,
        evidence=args.evidence,
        recorder=args.recorder,
        notes=args.notes,
    )
    print(outcome_id)
    return 0
