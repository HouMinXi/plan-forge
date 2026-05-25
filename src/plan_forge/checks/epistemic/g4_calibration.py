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

# Canonical hedge words (must match parser._HEDGE_RE exactly).
_ALL_HEDGES = frozenset({
    'maybe', 'likely', 'probably', 'perhaps', 'possibly',
    'seems', 'appears', 'should', 'could', 'might', 'may',
})

# Strong probability hedges: qualify explicit uncertainty claims.
# Fire regardless of adjacent context when not otherwise exempted.
_STRONG_HEDGES = frozenset({
    'maybe', 'likely', 'probably', 'perhaps', 'possibly',
})

# Generic modals: routine in planning prose; only flag when a numeric
# probability is present on the same line (handled by _NUMERIC_PROB_RE).
_BARE_MODALS = _ALL_HEDGES - _STRONG_HEDGES


def _build_definition_line_set(parsed: ParsedPlan) -> frozenset[int]:
    """Return 1-based line numbers inside G4 gate-definition sections.

    A section qualifies when its heading contains both 'g4' and
    'calibration' (case-insensitive) and is not a file-path heading
    (e.g. '### checks/epistemic/g4_calibration.py').  These sections
    are self-referential: they describe the gate's own vocabulary,
    not plan predictions.
    """
    result: set[int] = set()
    for heading, sec in parsed.sections.items():
        h = heading.lower()
        if 'g4' in h and 'calibration' in h and '.' not in h:
            result.update(range(sec.line_start, sec.line_end + 1))
    return frozenset(result)


def _is_hedge_enumeration_line(line: str) -> bool:
    """Return True when the line is a definitional list of hedge words.

    Detects patterns like:
      `maybe / likely / probably / perhaps / possibly / seems / ...`
    where the slash-delimited tokens are canonical hedge words.
    Requires '/' as a structural delimiter before counting, so prose
    sentences with many hedge words (e.g. "we should probably maybe
    possibly likely consider this") are not exempted.
    Threshold: >= 5 distinct hedge words on one line.
    """
    if '/' not in line:
        return False
    count = sum(
        1 for w in _ALL_HEDGES
        if re.search(r'\b' + w + r'\b', line, re.IGNORECASE)
    )
    return count >= 5


def check(
    parsed: ParsedPlan,
    llm_clients: list[LLMClient],
) -> list[Finding]:
    """G4 Part A: flag hedge words without numeric probability or marker.

    Exemption order applied before firing a finding:
      1. Definition-region: lines inside a section whose heading names
         G4 Calibration are self-referential; skip them.
      2. Hedge-enumeration line: a line listing >= 5 canonical hedge words
         is a vocabulary definition; skip the whole line.
      3. Numeric probability on the same line (NN%).
      4. Explicit marker (<!-- plan-forge: hedge-ok -->).
      5. Bare-modal scope: may/should/could/might/seems/appears are
         routine in planning prose and are not flagged unless rule 3
         already fires (i.e. a numeric probability is present).

    Each unexempted strong hedge -> MEDIUM.
    >10 unexempted -> aggregate BLOCKER.
    """
    # llm_clients intentionally unused: Part B (LLM hedge-anchor lookup)
    # is deferred to v0.1.1.
    findings: list[Finding] = []
    lines = parsed.raw_text.splitlines()
    definition_lines = _build_definition_line_set(parsed)

    for line_number, word in parsed.hedge_word_locations:
        if line_number < 1 or line_number > len(lines):
            continue
        line_text = lines[line_number - 1]

        # Rule 1: definition-region exemption
        if line_number in definition_lines:
            continue

        # Rule 2: hedge-enumeration line exemption
        if _is_hedge_enumeration_line(line_text):
            continue

        has_marker = bool(_MARKER_RE.search(line_text))
        has_numeric = bool(_NUMERIC_PROB_RE.search(line_text))

        # Rules 3 & 4: calibrated or explicitly marked
        if has_marker or has_numeric:
            continue

        # Rule 5: bare modals in ordinary prose are out of scope
        if word in _BARE_MODALS:
            continue

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
