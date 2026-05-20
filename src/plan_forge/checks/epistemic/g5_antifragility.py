"""G5 Antifragility Audit gate (pure mechanical).

Requires a ## Chaos Response section with >= 3 classified stressor
scenarios. Each scenario entry (numbered / bullet / table row) must
contain at least one classification word: benefit, survive, degrade,
break. If ALL scenarios are classified only as "break", the plan is
considered fragile and a BLOCKER is emitted.
"""
from __future__ import annotations

import re

from plan_forge.checks.epistemic._sections import find_section
from plan_forge.parser import ParsedPlan
from plan_forge.verdict import Finding, Severity

# Classification words (word-boundary match, case-insensitive).
_CLASSIFY_RE = re.compile(
    r'\b(benefit|survive|degrade|break)\b', re.IGNORECASE
)

# Entry patterns: numbered item, bullet, or table data row.
_NUMBERED_RE = re.compile(r'^\s*\d+\..*', re.MULTILINE)
_BULLET_RE = re.compile(r'^\s*[-*].*', re.MULTILINE)
_TABLE_ROW_RE = re.compile(r'^\s*\|(?![-: ]*\|).*', re.MULTILINE)


def _extract_entries(body: str) -> list[str]:
    """Return individual entry lines from the section body."""
    numbered = _NUMBERED_RE.findall(body)
    if numbered:
        return numbered
    table_rows = _TABLE_ROW_RE.findall(body)
    if table_rows:
        return table_rows
    return _BULLET_RE.findall(body)


def check(parsed: ParsedPlan) -> list[Finding]:
    """G5: verify Chaos Response section has >= 3 classified scenarios."""
    findings: list[Finding] = []

    section = (
        find_section(parsed, "chaos response")
        or find_section(parsed, "chaos")
    )
    if section is None:
        findings.append(Finding(
            check_id="G5.no_section",
            severity=Severity.BLOCKER,
            location="plan",
            message="## Chaos Response section absent",
            fix_hint=(
                "add ## Chaos Response with 3 stressor scenarios "
                "classified benefit/survive/degrade/break"
            ),
        ))
        return findings

    entries = _extract_entries(section.body)

    # Classify each entry: collect those containing at least one keyword.
    classified: list[set[str]] = []
    for entry in entries:
        words = {m.group(1).lower() for m in _CLASSIFY_RE.finditer(entry)}
        if words:
            classified.append(words)

    n_scenarios = len(classified)
    if n_scenarios < 3:
        findings.append(Finding(
            check_id="G5.insufficient_scenarios",
            severity=Severity.BLOCKER,
            location="## Chaos Response",
            message=(
                f"only {n_scenarios} classified stressor scenario(s); "
                "need >= 3"
            ),
            fix_hint="add more stressor scenarios",
        ))
        return findings

    # All-break check: every classified scenario's word set contains only
    # "break" (no benefit/survive/degrade in any scenario).
    all_break = all(words == {"break"} for words in classified)
    if all_break:
        findings.append(Finding(
            check_id="G5.all_break",
            severity=Severity.BLOCKER,
            location="## Chaos Response",
            message=(
                "all stressor scenarios break; "
                "the plan is fragile under every stressor"
            ),
            fix_hint=(
                "redesign so at least one stressor is "
                "survived or benefited from"
            ),
        ))

    return findings
