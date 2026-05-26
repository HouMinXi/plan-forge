"""F9: Plan length gate.

Plans that exceed a calibrated line threshold exhaust reviewer attention
and correlate with scope-overload failures.  This check flags overlong
plans as advisory (MEDIUM) so the author considers splitting.

Threshold is calibrated from v2.0 retrospective data: plans past ~500
lines consistently received incomplete reviews.  700+ lines is clearly
too long.  The constant is defined here for easy future recalibration.
"""
from __future__ import annotations

from plan_forge.parser import ParsedPlan
from plan_forge.verdict import Finding, Severity

# Line count beyond which a plan is flagged as overlong.
# Calibrated from retrospective data: reviewer attention degrades
# past this point.  Adjust here if corpus evidence changes.
_LENGTH_THRESHOLD = 500


def check(parsed: ParsedPlan, **kwargs) -> list[Finding]:
    """Flag plans that exceed the line-count threshold.

    Args:
        parsed: ParsedPlan to inspect.

    Returns:
        A single MEDIUM finding when raw_text exceeds the threshold;
        empty list otherwise.
    """
    line_count = len(parsed.raw_text.splitlines())
    if line_count <= _LENGTH_THRESHOLD:
        return []

    return [Finding(
        check_id="F9.plan_too_long",
        severity=Severity.MEDIUM,
        location="plan",
        message=(
            f"plan is {line_count} lines"
            f" (threshold: {_LENGTH_THRESHOLD});"
            f" long plans exhaust reviewer attention"
        ),
        fix_hint=(
            "consider splitting into a parent summary plan"
            " and child sub-plans per phase or concern"
        ),
    )]
