"""G4 Probability Calibration -- Part A (mechanical hedge detection).

Part A reuses parsed.hedge_word_locations (the parser's fence-width-aware
code-block skip state machine -- do NOT re-implement here).

Part B (LLM hedge-anchor lookup) is deferred to v0.1.1.
"""
from __future__ import annotations

import re

from plan_forge.llm.client import LLMClient
from plan_forge.parser import ParsedPlan
from plan_forge.verdict import Finding, Severity

_MARKER_RE = re.compile(r'<!--\s*plan-forge:\s*hedge-ok\s*-->')
_NUMERIC_PROB_RE = re.compile(r'\b\d{1,3}%')


def check(
    parsed: ParsedPlan,
    llm_clients: list[LLMClient],  # accepted for uniformity; Part B deferred to v0.1.1
) -> list[Finding]:
    """G4 Part A: flag hedge words without numeric probability or marker.

    Each unexempted hedge -> MEDIUM.  >10 unexempted -> aggregate BLOCKER.
    """
    # llm_clients intentionally unused: Part B (LLM hedge-anchor lookup)
    # is deferred to v0.1.1.
    findings: list[Finding] = []
    lines = parsed.raw_text.splitlines()

    for line_number, word in parsed.hedge_word_locations:
        # Bounds check (hedge_word_locations is 1-based)
        if line_number < 1 or line_number > len(lines):
            continue
        line_text = lines[line_number - 1]

        # Self-reference exemption: skip lines mentioning the gate name
        if "G4 Probability Calibration" in line_text:
            continue

        has_marker = _MARKER_RE.search(line_text)
        has_numeric = _NUMERIC_PROB_RE.search(line_text)

        if not has_marker and not has_numeric:
            findings.append(Finding(
                check_id="G4.A.mechanical",
                severity=Severity.MEDIUM,
                location=f"line {line_number}",
                message=(
                    f"hedge word {word!r} without numeric probability"
                    " or exemption marker"
                ),
                fix_hint=(
                    "add adjacent numeric probability (e.g. '70%') or "
                    "<!-- plan-forge: hedge-ok --> if uncertainty is "
                    "intentional"
                ),
            ))

    # Threshold: >10 unexempted hedges -> aggregate BLOCKER
    count = len(findings)
    if count > 10:
        findings.append(Finding(
            check_id="G4.A.aggregate",
            severity=Severity.BLOCKER,
            location="plan",
            message=(
                f"{count} hedge instances without calibration"
                " (>10 threshold)"
            ),
            fix_hint="calibrate probabilities or add exemption markers",
        ))

    return findings
