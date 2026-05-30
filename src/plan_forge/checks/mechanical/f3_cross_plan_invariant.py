"""F3: Cross-plan invariant verification.

Finds references to other plans/tasks in raw_text and verifies each
has a corresponding entry in audit/reference/appendix sections.

Two false-positive classes are explicitly suppressed:
  1. Self-references: the plan's own sub-plan id (e.g. "02-01" in a plan
     titled "02-01 State Machine Rewrite") is not a cross-plan reference.
  2. Date fragments: "05-17" inside "2026-05-17" matched the subplan
     pattern; a negative lookbehind for digit-hyphen prevents this.
"""
from __future__ import annotations

import re

from plan_forge.parser import ParsedPlan
from plan_forge.verdict import Finding, Severity

# Patterns for cross-plan references.
# The _SUBPLAN_RE includes (?<!\d-) to reject fragments inside ISO dates
# (e.g. "05-17" in "2026-05-17").  The lookbehind is fixed-length (2 chars)
# so Python's re engine accepts it.
_PHASE_RE = re.compile(r'\bphase[-\s]\d+\b', re.IGNORECASE)
_SUBPLAN_RE = re.compile(r'(?<!\d-)\b0[1-9]-\d{2}\b')
_TASK_RE = re.compile(r'\bT\d{2,3}\b')

# Section headings that constitute verified/exempt sections
_EXEMPT_KEYWORDS = (
    'audit notes',
    'cross-plan references',
    'references',
    'appendix',
    'implementation tasks',
)

# U+FEFF BOM is not removed by str.strip(). Files saved by some editors or
# exported from Windows tools begin with this byte sequence. Strip it before
# comparing the opening --- delimiter.
# Note: Phase 10+ IDs (two-digit phase numbers like 10-02) are not matched
# by _SUBPLAN_RE in document body, so frontmatter extraction adds them to
# the verified set but suppression has no practical effect on body scanning.
# Extending the subplan pattern to cover Phase 10+ is deferred.
_BOM = chr(0xFEFF)


def _heading_is_exempt(heading: str) -> bool:
    """Return True if heading is an audit/reference/appendix section."""
    hl = heading.lower()
    for kw in _EXEMPT_KEYWORDS:
        if kw in hl:
            return True
    return False


def _own_id_set(parsed: ParsedPlan) -> set[str]:
    """Derive the plan's own identifier tokens from frontmatter and headings.

    Scans YAML frontmatter for phase:/plan: fields, then scans the first
    ATX heading for subplan IDs. Results are unioned -- both sources
    contribute to the own-ID set. Frontmatter detection strips U+FEFF BOM
    before the --- check.

    Returns a set of lowercase own-id strings (may be empty if neither
    source yields a subplan id).
    """
    own: set[str] = set()
    lines = parsed.raw_text.splitlines()
    if not lines:
        return own

    # Frontmatter: opening --- must be on line 1 (or line 2 if line 1 empty)
    first = lines[0].lstrip(_BOM).strip()
    second = lines[1].lstrip(_BOM).strip() if len(lines) > 1 else ""
    fm_start = None
    if first == "---":
        fm_start = 1
    elif first == "" and second == "---":
        fm_start = 2

    if fm_start is not None:
        phase_num = plan_num = None
        for line in lines[fm_start:]:
            stripped = line.strip()
            if stripped.startswith("#") or stripped == "---":
                break
            if m := re.match(r'phase:\s*["\']?(\d+)', stripped):
                phase_num = m.group(1).zfill(2)
            if m := re.match(r'plan:\s*["\']?(\d+)', stripped):
                plan_num = m.group(1).zfill(2)
        if phase_num and plan_num:
            own.add(f"{phase_num}-{plan_num}")

    # Heading scan (always runs -- union with frontmatter result)
    for line in lines:
        if line.strip().startswith("#"):
            heading = line.strip().lstrip("#").strip()
            for m in _SUBPLAN_RE.finditer(heading):
                own.add(m.group(0).lower())
            break  # first heading only

    return own


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
        List of F3 findings (one per unique unverified claim).
    """
    # Build verified set: tokens found inside exempt sections.
    # Normalized to lowercase so "Phase-1" in body is exempted by "phase-1"
    # in audit notes (patterns use re.IGNORECASE; comparison is case-insensitive).
    verified: set[str] = set()
    for heading, section in parsed.sections.items():
        if _heading_is_exempt(heading):
            for pattern in (_PHASE_RE, _SUBPLAN_RE, _TASK_RE):
                for m in pattern.finditer(section.body):
                    verified.add(m.group(0).lower())

    # Add plan's own ids to the verified set so self-references are exempt.
    verified.update(_own_id_set(parsed))

    # Collect all claims from raw_text
    all_claims = _extract_all_claims(parsed.raw_text)

    findings: list[Finding] = []
    seen: set[str] = set()

    for claim, lineno in all_claims:
        if claim.lower() in verified:
            continue
        key = claim.lower()
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
