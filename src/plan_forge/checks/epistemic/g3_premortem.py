"""G3 Pre-mortem gate (pure mechanical).

Requires a ## Pre-mortem section with >= 5 failure-cause entries and
the keywords "early warning" and "counter" present somewhere in the
section body.

# SUBSPEC interpretation: the gate verifies section-level keyword
# presence (early warning + counter) as a v0.1 mechanical proxy for
# per-entry field completeness. Strict per-entry field validation is
# deferred. A comment is required by the spec to document this.
"""
from __future__ import annotations

import re

from plan_forge.checks.epistemic._sections import find_section
from plan_forge.parser import ParsedPlan
from plan_forge.verdict import Finding, Severity

# Numbered list item (e.g. "1." or "  3.")
_NUMBERED_RE = re.compile(r'^\s*\d+\.', re.MULTILINE)
# Markdown table data row: starts with | and is not a separator row
_TABLE_ROW_RE = re.compile(r'^\s*\|(?![-: ]*\|)', re.MULTILINE)
# Bullet item
_BULLET_RE = re.compile(r'^\s*[-*]', re.MULTILINE)


def _count_cause_entries(body: str) -> int:
    """Count distinct failure-cause entries in the section body.

    Accepts numbered list items, table data rows, and bullets.
    Numbered items take precedence; if present, only those are counted
    to avoid double-counting lines that also look like bullets.
    """
    numbered = _NUMBERED_RE.findall(body)
    if numbered:
        return len(numbered)
    table_rows = _TABLE_ROW_RE.findall(body)
    if table_rows:
        # subtract 1 for the mandatory header row; the regex cannot
        # distinguish header from data rows by structure alone
        return max(0, len(table_rows) - 1)
    return len(_BULLET_RE.findall(body))


def check(parsed: ParsedPlan) -> list[Finding]:
    """G3: verify Pre-mortem section has >= 5 causes and required keywords."""
    findings: list[Finding] = []

    section = (
        find_section(parsed, "pre-mortem")
        or find_section(parsed, "premortem")
    )
    if section is None:
        findings.append(Finding(
            check_id="G3.no_section",
            severity=Severity.BLOCKER,
            location="plan",
            message="## Pre-mortem section absent",
            fix_hint=(
                "add ## Pre-mortem with >= 5 ranked failure causes, "
                "each with an early warning and a counter"
            ),
        ))
        return findings

    n_causes = _count_cause_entries(section.body)
    if n_causes < 5:
        findings.append(Finding(
            check_id="G3.insufficient_causes",
            severity=Severity.BLOCKER,
            location="## Pre-mortem",
            message=f"only {n_causes} failure cause(s); need >= 5",
            fix_hint="add more ranked failure causes",
        ))

    body_lower = section.body.lower()

    # SUBSPEC interpretation: accept "early_warning" (underscore) as an
    # equivalent to "early warning" (space); both are common field name
    # styles in structured plan sections.
    has_early_warning = (
        "early warning" in body_lower or "early_warning" in body_lower
    )
    if not has_early_warning:
        findings.append(Finding(
            check_id="G3.no_early_warning",
            severity=Severity.HIGH,
            location="## Pre-mortem",
            message="no early-warning indicators found",
            fix_hint=(
                "add an early-warning signal to each failure cause"
            ),
        ))

    # substring match: "encounter" also contains "counter", accepted as v0.1 proxy
    if "counter" not in body_lower:
        findings.append(Finding(
            check_id="G3.no_counter",
            severity=Severity.HIGH,
            location="## Pre-mortem",
            message="no counter-measures found",
            fix_hint="add a counter to each failure cause",
        ))

    return findings
