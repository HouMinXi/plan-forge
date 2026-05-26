"""G2 Risk Taxonomy 3-class gate (pure mechanical).

Checks that parsed.risks contains entries in all three required buckets
(known / gray_rhino / black_swan), and that gray rhinos carry a
denial_reason and black swans carry a survival_plan.

Reuses the parser's ParsedRisk list directly; no body re-parsing needed.

The G2.no_risks finding is suppressed when a section whose heading
contains 'risks' exists at the heading level, even if the parser could not
populate parsed.risks (e.g. a flat table without Known/Gray/Black sub-
sections).  This avoids a false positive for headings like '## Risks &
Mitigations'.  The match is restricted to ATX headings, not prose.
"""
from __future__ import annotations

from plan_forge.parser import ParsedPlan
from plan_forge.verdict import Finding, Severity

_REQUIRED_BUCKETS = ("known", "gray_rhino", "black_swan")


def _has_risks_section(parsed: ParsedPlan) -> bool:
    """Return True when an H2+ heading contains 'risk' (case-insensitive).

    Only ATX headings at level 2 or deeper are checked; the H1 document
    title is excluded so a title like '# Risk Management Plan' with no
    ## Risks section does not falsely suppress G2.no_risks.
    """
    for heading, section in parsed.sections.items():
        if section.level >= 2 and 'risk' in heading.lower():
            return True
    return False


def check(parsed: ParsedPlan) -> list[Finding]:
    """G2: verify 3-class risk taxonomy structure and per-risk fields."""
    findings: list[Finding] = []

    if not parsed.risks:
        if _has_risks_section(parsed):
            # Section exists but parser found no bucket structure.
            # Do not fire no_risks -- the author has a risks section;
            # they need to add Known/Gray Rhino/Black Swan sub-sections.
            return findings
        findings.append(Finding(
            check_id="G2.no_risks",
            severity=Severity.BLOCKER,
            location="plan",
            message="## Risks section absent or empty",
            fix_hint=(
                "add ## Risks with ### Known Risks / "
                "### Gray Rhinos / ### Black Swans"
            ),
        ))
        return findings

    buckets = {r.bucket for r in parsed.risks}

    for bucket in _REQUIRED_BUCKETS:
        if bucket not in buckets:
            findings.append(Finding(
                check_id=f"G2.missing_{bucket}",
                severity=Severity.BLOCKER,
                location="plan.risks",
                message=(
                    f"no {bucket} risks; "
                    "all-in-one bucket is not a 3-class taxonomy"
                ),
                fix_hint="add at least one risk to this bucket",
            ))

    for risk in parsed.risks:
        if risk.bucket == "gray_rhino" and not risk.denial_reason:
            findings.append(Finding(
                check_id="G2.gray_rhino_no_denial",
                severity=Severity.HIGH,
                location=risk.description[:40],
                message="Gray Rhino lacks a denial_reason",
                fix_hint=(
                    "state why this obvious risk is being ignored/deferred"
                ),
            ))

        if risk.bucket == "black_swan" and not risk.survival_plan:
            findings.append(Finding(
                check_id="G2.black_swan_no_survival",
                severity=Severity.HIGH,
                location=risk.description[:40],
                message="Black Swan lacks a survival_plan",
                fix_hint=(
                    "state how the plan survives this "
                    "low-probability high-impact event"
                ),
            ))

    return findings
