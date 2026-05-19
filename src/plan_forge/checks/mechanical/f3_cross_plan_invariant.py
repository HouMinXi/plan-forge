"""F3: Cross-plan invariant verification.

Finds references to other plans/tasks in raw_text and verifies each
has a corresponding entry in audit/reference/appendix sections.
"""
from __future__ import annotations

import re

from plan_forge.parser import ParsedPlan
from plan_forge.verdict import Finding, Severity

# Patterns for cross-plan references
_PHASE_RE = re.compile(r'\bphase[-\s]\d+\b', re.IGNORECASE)
_SUBPLAN_RE = re.compile(r'\b0[1-9]-\d{2}\b')
_TASK_RE = re.compile(r'\bT\d{2,3}\b')

# Section headings that constitute verified/exempt sections
_EXEMPT_KEYWORDS = (
    'audit notes',
    'cross-plan references',
    'references',
    'appendix',
    'implementation tasks',
)


def _heading_is_exempt(heading: str) -> bool:
    """Return True if heading is an audit/reference/appendix section."""
    hl = heading.lower()
    for kw in _EXEMPT_KEYWORDS:
        if kw in hl:
            return True
    return False


def _extract_all_claims(text: str) -> list[tuple[str, int]]:
    """Return list of (matched_string, 1-based_line_number) for all patterns."""
    results: list[tuple[str, int]] = []
    for lineno, line in enumerate(text.splitlines(), 1):
        for pattern in (_PHASE_RE, _SUBPLAN_RE, _TASK_RE):
            for m in pattern.finditer(line):
                results.append((m.group(0), lineno))
    return results


def check(parsed: ParsedPlan, **kwargs) -> list[Finding]:
    """Check cross-plan references for audit-note coverage.

    Args:
        parsed: ParsedPlan to inspect.

    Returns:
        List of F3 findings (one per unverified claim per line).
    """
    # Build verified set: tokens found inside exempt sections.
    # Normalized to lowercase so "Phase-1" in body is exempted by "phase-1" in audit notes
    # (patterns use re.IGNORECASE; comparison must be case-insensitive too).
    verified: set[str] = set()
    for heading, section in parsed.sections.items():
        if _heading_is_exempt(heading):
            for pattern in (_PHASE_RE, _SUBPLAN_RE, _TASK_RE):
                for m in pattern.finditer(section.body):
                    verified.add(m.group(0).lower())

    # Collect all claims from raw_text
    all_claims = _extract_all_claims(parsed.raw_text)

    findings: list[Finding] = []
    seen: set[tuple[str, int]] = set()

    for claim, lineno in all_claims:
        if claim.lower() in verified:
            continue
        key = (claim, lineno)
        if key in seen:
            continue
        seen.add(key)
        findings.append(Finding(
            check_id="F3.unverified_cross_plan_ref",
            severity=Severity.HIGH,
            location=f"line:{lineno}",
            message=(
                f"reference {claim!r} is used but has no audit-notes"
                f" / appendix / cross-plan-references entry"
            ),
            fix_hint=(
                f"add an entry under ## References or ## Audit Notes"
                f" documenting what {claim!r} refers to"
            ),
        ))

    return findings
