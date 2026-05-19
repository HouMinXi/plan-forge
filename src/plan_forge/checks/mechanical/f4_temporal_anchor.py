"""F4: Temporal anchor lint.

Detects imprecise before/after temporal phrases adjacent to fuzzy
lifecycle verbs (return, exit, complete, finish, done).  Skips
fenced code blocks using the fence-width-aware state machine from
parser.py (R3 RN-5 compatible pattern).
"""
from __future__ import annotations

import re

from plan_forge.parser import ParsedPlan
from plan_forge.verdict import Finding, Severity

# Main pattern: before/after followed by 1-4 words
_TEMPORAL_RE = re.compile(
    r'\b(before|after)\s+(\w+(?:\s+\w+){0,3})',
    re.IGNORECASE,
)

# Fuzzy lifecycle verbs that trigger evaluation
_FUZZY_VERBS = frozenset({'return', 'exit', 'complete', 'finish', 'done'})

# Precise anchor tokens that suppress the finding
_DUNDER_RE = re.compile(r'__\w+__')

# Acceptable multi-word anchor phrases (lowercase)
_ACCEPTABLE_PHRASES = (
    'return statement executed',
    'return statement evaluated',
    'return statement processed',
    'caller assignment',
    'caller returns',
    'caller assigns',
)

# Self-reference exemption string
_SELF_REF = 'F4 Temporal Anchor'


def _phrase_contains_fuzzy(phrase: str) -> bool:
    """Return True if phrase contains any fuzzy lifecycle verb."""
    words = set(phrase.lower().split())
    return bool(words & _FUZZY_VERBS)


def _is_acceptable(verb: str, phrase: str) -> bool:
    """Return True if this before/after + phrase is a precise anchor.

    Acceptable cases per SUBSPEC:
    1. phrase matches one of the known acceptable multi-word patterns.
    2. phrase contains a dunder (__exit__, __enter__, etc.).
    3. Token immediately after return/exit starts with _ or is capitalized.
    """
    phrase_lower = phrase.lower().strip()

    # Check 1: known acceptable multi-word phrases
    for ap in _ACCEPTABLE_PHRASES:
        if phrase_lower.startswith(ap):
            return True

    # Check 2: dunder in phrase
    if _DUNDER_RE.search(phrase):
        return True

    # Check 3: first token after return/exit is precise symbol
    # Split phrase into words; if first word is return/exit, examine second
    words = phrase.split()
    if not words:
        return False
    first = words[0].lower()
    if first in ('return', 'exit') and len(words) >= 2:
        second = words[1]
        if second.startswith('_') or re.match(r'^[A-Z][A-Za-z0-9_]*$', second):
            return True

    return False


def check(parsed: ParsedPlan, **kwargs) -> list[Finding]:
    """Check for imprecise temporal anchor phrases.

    Uses fence-width-aware state machine (same pattern as parser.py
    _extract_hedge_words) to skip fenced code blocks.

    Args:
        parsed: ParsedPlan to inspect.

    Returns:
        List of F4 findings.
    """
    findings: list[Finding] = []

    # Fence-width-aware state machine (canonical pattern from parser.py)
    in_code_block = False
    fence_width = ''

    for lineno, line in enumerate(parsed.raw_text.splitlines(), 1):
        stripped = line.strip()

        # Update code-block state
        fence_match = re.match(r'^(`{3,})', stripped)
        if fence_match:
            fence = fence_match.group(1)
            if not in_code_block:
                in_code_block = True
                fence_width = fence
            elif fence == fence_width:
                in_code_block = False
                fence_width = ''
            continue
        if in_code_block:
            continue

        # Self-reference exemption
        if _SELF_REF in line:
            continue

        for m in _TEMPORAL_RE.finditer(line):
            verb = m.group(1)
            phrase = m.group(2)

            if not _phrase_contains_fuzzy(phrase):
                continue

            if _is_acceptable(verb, phrase):
                continue

            findings.append(Finding(
                check_id="F4.imprecise_temporal_anchor",
                severity=Severity.LOW,
                location=f"line:{lineno}",
                message=(
                    f"temporal phrase 'before/after X' lacks precise"
                    f" anchor: {m.group(0)!r}"
                ),
                fix_hint=(
                    "specify which exact point: __exit__, return statement"
                    " executed, caller assignment, etc."
                ),
            ))

    return findings
