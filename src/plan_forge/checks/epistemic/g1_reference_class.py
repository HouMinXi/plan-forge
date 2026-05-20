"""G1 Reference Class Forecasting gate (pure mechanical).

Requires a ## Reference Class section with at least 2 historical projects,
each showing a plan-vs-actual ratio (e.g. "1.8x", "3 X", "ratio 2.0").
"""
from __future__ import annotations

import re

from plan_forge.checks.epistemic._sections import find_section
from plan_forge.parser import ParsedPlan
from plan_forge.verdict import Finding, Severity

# Detect plan-vs-actual ratio: digit(s) optionally followed by decimal,
# then optional whitespace, then x/X (word boundary).
# Examples: "1.8x", "3X", "3 X".
_RATIO_RE = re.compile(r'\b\d+(?:\.\d+)?\s*[xX]\b')

# Fallback: the literal word "ratio" adjacent to a number on the same line.
_RATIO_WORD_RE = re.compile(r'ratio\s+\d+(?:\.\d+)?|\d+(?:\.\d+)?\s*ratio',
                             re.IGNORECASE)


def _count_ratio_lines(body: str) -> int:
    """Count lines in body that contain a plan-vs-actual ratio."""
    count = 0
    for line in body.splitlines():
        if _RATIO_RE.search(line) or _RATIO_WORD_RE.search(line):
            count += 1
    return count


def check(parsed: ParsedPlan) -> list[Finding]:
    """G1: verify Reference Class section has >= 2 projects with ratios."""
    findings: list[Finding] = []

    section = find_section(parsed, "reference class")
    if section is None:
        findings.append(Finding(
            check_id="G1.no_section",
            severity=Severity.BLOCKER,
            location="plan",
            message="## Reference Class section absent",
            fix_hint=(
                "add ## Reference Class with 2+ historical "
                "similar-scope projects and plan-vs-actual ratios"
            ),
        ))
        return findings

    n_projects = _count_ratio_lines(section.body)
    if n_projects < 2:
        findings.append(Finding(
            check_id="G1.insufficient_reference_class",
            severity=Severity.BLOCKER,
            location="## Reference Class",
            message=(
                f"only {n_projects} project(s) with a plan-vs-actual "
                "ratio; need >= 2"
            ),
            fix_hint=(
                "add more historical reference projects with "
                "actual durations and ratios"
            ),
        ))

    return findings
