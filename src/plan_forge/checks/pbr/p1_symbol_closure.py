"""P1: Symbol closure check.

Every identifier introduced in the plan body must be either defined
in the plan (appears >= 2 times) or explicitly cross-referenced to
an upstream artifact.  Orphan identifiers (used exactly once in a
main-body section, no cross-ref section, no author exemption marker)
are reported as HIGH findings.
"""
from __future__ import annotations

import re
from plan_forge.parser import ParsedPlan
from plan_forge.verdict import Finding, Severity


# ---------------------------------------------------------------------------
# Regex patterns for identifier extraction
# ---------------------------------------------------------------------------

_BACKTICK_RE = re.compile(r"`([A-Za-z_][A-Za-z0-9_.]{2,})`")
_SC_ID_RE = re.compile(r"\bSC-\d+[a-z]?\b")
_T_TASK_RE = re.compile(r"\bT\d{2,3}\b")
_PHASE_ID_RE = re.compile(r"\bphase[-\s]\d+\b", re.IGNORECASE)
_SUBPLAN_ID_RE = re.compile(r"\b0[1-9]-\d{2}\b")

# Fence-width state machine pattern (same as parser.py _extract_hedge_words)
_FENCE_RE = re.compile(r"^(`{3,})")

# Author exemption marker
_P1_OK_RE = re.compile(r"<!--\s*plan-forge:\s*p1-ok")

# Cross-reference section heading keywords (case-insensitive)
_XREF_SECTION_KEYWORDS = (
    "audit notes",
    "references",
    "appendix",
    "implementation tasks",
    "cross-plan references",
    "external voices",
    "open questions",
    "changelog",
    "glossary",
)

# Built-in exemptions: common Python/prose words that survive regex
# but are not plan identifiers
_BUILTIN_EXEMPT = frozenset({
    "python", "none", "true", "false", "null", "optional",
    "int", "str", "bool", "list", "dict", "set", "tuple", "bytes",
    "float", "any", "type", "self", "class", "def", "import", "from",
    "as", "if", "else", "for", "while", "return", "yield", "pass",
})


def _is_xref_section(heading: str) -> bool:
    """Return True if this section heading is a cross-reference section."""
    hl = heading.lower()
    return any(kw in hl for kw in _XREF_SECTION_KEYWORDS)


def _extract_identifiers_with_lines(
    raw_text: str,
) -> tuple[dict[str, list[int]], dict[str, list[int]]]:
    """Scan raw_text and return two dicts:
      - all_occurrences: identifier -> all line numbers (1-based)
      - code_block_lines: set of line numbers that are inside fenced code blocks

    Identifiers appearing inside fenced code blocks count as a use but
    NOT as a definition (code blocks are illustrative).  We track which
    lines are inside code blocks so the caller can distinguish them.
    """
    lines = raw_text.splitlines()
    all_occurrences: dict[str, list[int]] = {}
    code_block_line_set: set[int] = set()

    in_code_block = False
    fence_width = ""

    for lineno, line in enumerate(lines, 1):
        stripped = line.strip()
        fence_match = _FENCE_RE.match(stripped)
        if fence_match:
            fence = fence_match.group(1)
            if not in_code_block:
                in_code_block = True
                fence_width = fence
            elif fence == fence_width:
                in_code_block = False
                fence_width = ""
            # fence lines themselves: skip for identifier extraction
            continue

        if in_code_block:
            code_block_line_set.add(lineno)
            # Still record occurrences (count as use, not definition)
            _collect_identifiers_from_line(line, lineno, all_occurrences)
        else:
            _collect_identifiers_from_line(line, lineno, all_occurrences)

    return all_occurrences, code_block_line_set


def _collect_identifiers_from_line(
    line: str,
    lineno: int,
    occurrences: dict[str, list[int]],
) -> None:
    """Extract all identifier patterns from one line, add to occurrences."""
    for pattern in (
        _BACKTICK_RE,
        _SC_ID_RE,
        _T_TASK_RE,
        _PHASE_ID_RE,
        _SUBPLAN_ID_RE,
    ):
        for m in pattern.finditer(line):
            # Backtick pattern has a captured group; others match the whole token
            ident = m.group(1) if m.lastindex and m.lastindex >= 1 else m.group(0)
            ident_lower = ident.lower()
            if ident_lower in _BUILTIN_EXEMPT:
                continue
            if ident not in occurrences:
                occurrences[ident] = []
            occurrences[ident].append(lineno)


def _build_line_to_section(sections: dict, raw_text: str) -> dict[int, str]:
    """Map each 1-based line number to the MOST SPECIFIC section heading.

    When a line belongs to multiple nested sections (parent and child),
    assign it to the section with the highest level (deepest nesting),
    since the parent section body includes all its children's content.
    Uses ParsedSection.line_start / line_end and ParsedSection.level.
    """
    # line -> (level, heading): keep the deepest (highest level number)
    line_to_best: dict[int, tuple[int, str]] = {}
    for heading, section in sections.items():
        for ln in range(section.line_start, section.line_end + 1):
            current = line_to_best.get(ln)
            if current is None or section.level > current[0]:
                line_to_best[ln] = (section.level, heading)
    return {ln: heading for ln, (_, heading) in line_to_best.items()}


def _has_p1_ok_marker(lines: list[str], lineno: int) -> bool:
    """Check if line lineno or the line immediately above has p1-ok marker."""
    # lineno is 1-based; lines is 0-based
    target_idx = lineno - 1
    for idx in (target_idx, target_idx - 1):
        if 0 <= idx < len(lines):
            if _P1_OK_RE.search(lines[idx]):
                return True
    return False


def check(parsed: ParsedPlan) -> list[Finding]:
    """Run P1 symbol closure check on a parsed plan.

    Returns a list of Finding objects, one per orphan identifier.
    """
    findings: list[Finding] = []
    lines = parsed.raw_text.splitlines()

    # code_block_lines not used in the check loop: code-block occurrences
    # count as use, not definition; the >= 2 occurrence rule covers this.
    all_occurrences, _ = _extract_identifiers_with_lines(
        parsed.raw_text
    )
    line_to_section = _build_line_to_section(parsed.sections, parsed.raw_text)

    for ident, linenos in all_occurrences.items():
        # De-duplicate line numbers (same identifier may match multiple patterns
        # on the same line from different regexes)
        unique_linenos = sorted(set(linenos))

        if len(unique_linenos) >= 2:
            # Multiple occurrences implies definition + reference -> no finding
            continue

        # Single occurrence; determine if it's in a cross-reference section
        sole_line = unique_linenos[0]
        section_heading = line_to_section.get(sole_line, "")

        if _is_xref_section(section_heading):
            # Cross-reference section is its own evidence
            continue

        # Check for author exemption marker on same line or line above
        if _has_p1_ok_marker(lines, sole_line):
            continue

        findings.append(Finding(
            check_id="P1.orphan_identifier",
            severity=Severity.HIGH,
            location=f"line:{sole_line}",
            message=(
                f"identifier {ident!r} appears once in plan with no"
                " upstream cross-reference"
            ),
            fix_hint=(
                "add a definition / cross-reference under ## References,"
                " ## Audit Notes, or ## Glossary; or add inline"
                " <!-- plan-forge: p1-ok (reason) --> if the identifier"
                " is intentionally external and self-explanatory"
            ),
        ))

    return findings
