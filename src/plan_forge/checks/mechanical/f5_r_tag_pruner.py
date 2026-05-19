"""F5: R-tag pruner.

Counts inline R-tag annotations (R<N> <BHML><N>) per SC body.
SCs with more than 2 inline R-tags are flagged; excess should move
to the CHANGELOG section.
"""
from __future__ import annotations

import re

from plan_forge.parser import ParsedPlan
from plan_forge.verdict import Finding, Severity

# R-tag pattern: R<digit(s)> followed by B/H/M/L and digit(s)
_RTAG_RE = re.compile(r'\bR\d+\s+[BHML]\d+\b')

# Maximum inline R-tags allowed per SC
_RTAG_CAP = 2


def check(parsed: ParsedPlan, **kwargs) -> list[Finding]:
    """Check for SC entries with more than 2 inline R-tags.

    Args:
        parsed: ParsedPlan to inspect.

    Returns:
        List of F5 findings (one per SC exceeding the cap).
    """
    findings: list[Finding] = []

    for sc in parsed.sc_table:
        count = len(_RTAG_RE.findall(sc.body))
        if count > _RTAG_CAP:
            # Use sc.number + sc.suffix per SUBSPEC: "SC-{sc.number}{sc.suffix or ''}:line:{sc.line}".
            # full_id already contains the "SC-" prefix; using it would produce "SC-SC-1:line:0".
            location = f"SC-{sc.number}{sc.suffix or ''}:line:{sc.line}"
            findings.append(Finding(
                check_id="F5.r_tag_overflow",
                severity=Severity.LOW,
                location=location,
                message=(
                    f"SC-{sc.number} has {count} inline R-tags (cap is 2)"
                ),
                fix_hint=(
                    f"move {count - _RTAG_CAP} tag(s) to ## CHANGELOG"
                    f" section with full review context"
                ),
            ))

    return findings
