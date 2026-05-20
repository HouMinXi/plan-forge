"""G7 Scope Challenge / Barbell gate (pure mechanical).

Requires a ## Scope Challenge section answering four questions:
  Q1 - necessity: why this needs to exist
  Q2 - consumers: three real consumers or public-artifact alternative
  Q3 - do-nothing cost: cost of inaction / status quo cost
  Q4 - barbell: barbell vs middle-ground analysis

Each missing question group emits a HIGH finding.
"""
from __future__ import annotations

from plan_forge.checks.epistemic._sections import find_section
from plan_forge.parser import ParsedPlan
from plan_forge.verdict import Finding, Severity

# Per-question keyword groups (case-insensitive substring match).
_QUESTIONS: list[tuple[str, str, frozenset[str], str]] = [
    (
        "G7.missing_necessity",
        "Q1 necessity not addressed",
        frozenset({"need to exist", "does this need", "why this exists",
                   "justif"}),
        "add a statement explaining why this work needs to exist",
    ),
    (
        "G7.missing_consumers",
        "Q2 consumers not addressed",
        frozenset({"consumer", "public artifact", "public-artifact",
                   "demand signal"}),
        "name 3 real consumers or state the public-artifact alternative",
    ),
    (
        "G7.missing_donothing_cost",
        "Q3 do-nothing cost not addressed",
        frozenset({"do nothing", "do-nothing", "cost of inaction",
                   "status quo cost"}),
        "quantify the cost of inaction or status quo",
    ),
    (
        "G7.missing_barbell",
        "Q4 barbell not addressed",
        frozenset({"barbell", "middle ground", "middle-ground"}),
        "add a barbell vs middle-ground analysis",
    ),
]


def check(parsed: ParsedPlan) -> list[Finding]:
    """G7: verify Scope Challenge section answers all four question groups."""
    findings: list[Finding] = []

    # "scope" fallback accepts any section whose heading contains the word;
    # intentional: plans may use "Scope" without the "Challenge" qualifier
    section = (
        find_section(parsed, "scope challenge")
        or find_section(parsed, "scope")
    )
    if section is None:
        findings.append(Finding(
            check_id="G7.no_section",
            severity=Severity.BLOCKER,
            location="plan",
            message="## Scope Challenge section absent",
            fix_hint=(
                "add ## Scope Challenge answering Q1-Q4 "
                "(need to exist / 3 consumers / do-nothing cost / barbell)"
            ),
        ))
        return findings

    body_lower = section.body.lower()

    for check_id, message, keywords, fix_hint in _QUESTIONS:
        if not any(kw in body_lower for kw in keywords):
            findings.append(Finding(
                check_id=check_id,
                severity=Severity.HIGH,
                location="## Scope Challenge",
                message=message,
                fix_hint=fix_hint,
            ))

    return findings
