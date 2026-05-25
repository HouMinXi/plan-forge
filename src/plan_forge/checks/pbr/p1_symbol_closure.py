"""P1: Symbol closure check.

Every plan-structural identifier introduced in the plan body must be either
defined in the plan (appears >= 2 times) or explicitly cross-referenced to
an upstream artifact.  Orphan identifiers (used exactly once in a main-body
section, no cross-ref section, no author exemption marker) are reported as
HIGH findings.

Code symbols (dunders, dotted paths, filenames, lowercase tokens, ALL_CAPS
constants) are illustrative mentions of implementation details, not plan-
structural identifiers, and are skipped by the backtick scanner.  Structured
plan IDs (SC-N, T-NN, phase-N, subplan) and CapWords plan-defined terms are
still flagged when orphaned, with two further exceptions: a structured ID
that is defined as the first cell of a markdown table row is not orphaned,
and a CapWords token that appears as a type annotation or class definition
inside a fenced code block is not orphaned.

P1 vs F1 distinction: F1 checks SC-N cross-plan traceability (does every
SC- ID in this plan map to a requirement in a parent plan?).  P1 checks
within-plan closure (is a plan-structural identifier used once with no
definition or cross-ref in the same document?).  P1 is document-local;
F1 is inter-plan.
"""
from __future__ import annotations

import re
from plan_forge.parser import ParsedPlan
from plan_forge.verdict import Finding, Severity


# Regex patterns for identifier extraction

_BACKTICK_RE = re.compile(r"`([A-Za-z_][A-Za-z0-9_.]{2,})`")
_SC_ID_RE = re.compile(r"\bSC-\d+[a-z]?\b")
_T_TASK_RE = re.compile(r"\bT\d{2,3}\b")
_PHASE_ID_RE = re.compile(r"\bphase[-\s]\d+\b", re.IGNORECASE)
_SUBPLAN_ID_RE = re.compile(r"\b0[1-9]-\d{2}\b")

# Fence-width state machine (same as parser.py _extract_hedge_words)
_FENCE_RE = re.compile(r"^(`{3,})")

# Author exemption marker
_P1_OK_RE = re.compile(r"<!--\s*plan-forge:\s*p1-ok")

# Code-symbol shape detectors: tokens matching these are illustrative, not
# plan-structural, and are not flagged by the backtick scanner.
_DUNDER_RE = re.compile(r"^__[A-Za-z][A-Za-z0-9_]*__$")
_DOTTED_PATH_RE = re.compile(r"\.")
_ALL_CAPS_CONST_RE = re.compile(r"^[A-Z][A-Z0-9_]+$")
_KNOWN_EXTENSIONS = frozenset({
    ".py", ".md", ".sql", ".json", ".toml", ".txt", ".yaml", ".yml",
    ".sh", ".cfg", ".ini", ".rst", ".html", ".css", ".js", ".ts",
})

# Table-cell definition: a structured ID at the START of the first non-empty
# data cell of a markdown table row is being defined there, not referenced.
# Cells may contain parenthetical notes after the ID (e.g. a qualifier in
# parentheses).  Pattern: line starts with | then optional spaces then the
# structured ID followed by whitespace, an open paren, or the next delimiter.
_TABLE_FIRST_CELL_RE = re.compile(
    r"^\|\s*(SC-\d+[a-z]?|T\d{2,3}|phase[-\s]\d+|0[1-9]-\d{2})"
    r"(?:\s|\(|\|)"
)

# Type-annotation shapes inside fenced code blocks that define a CapWords
# token as a code type rather than merely referencing a value.
# Matches: "class Foo", "-> Foo", ": Foo" (annotation context)
_TYPE_DEF_RE = re.compile(
    r"(?:^|\s)(?:class\s+|->[\s]*|:\s+)([A-Z][a-z][A-Za-z0-9]*)\b"
)

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

# Built-in exemptions: common Python/prose/library names that survive the
# backtick regex but are not plan identifiers.
_BUILTIN_EXEMPT = frozenset({
    "python", "none", "true", "false", "null", "optional",
    "int", "str", "bool", "list", "dict", "set", "tuple", "bytes",
    "float", "any", "type", "self", "class", "def", "import", "from",
    "as", "if", "else", "for", "while", "return", "yield", "pass",
    # common library/framework names used as illustrative mentions
    "anthropic", "openai", "sqlalchemy", "pydantic", "pytest",
    "pathlib", "dataclasses", "typing", "asyncio", "logging",
    "json", "os", "sys", "re", "abc", "enum", "uuid",
})


def _is_xref_section(heading: str) -> bool:
    """Return True if this section heading is a cross-reference section."""
    hl = heading.lower()
    return any(kw in hl for kw in _XREF_SECTION_KEYWORDS)


def _is_code_symbol(token: str) -> bool:
    """Return True if a backtick token is a code symbol, not a plan ID.

    Code symbols are illustrative mentions of implementation details:
    dunders (__exit__), dotted paths (a.b.c), filenames (foo.py),
    all-lowercase identifiers, and ALL_CAPS constants / env-var names.
    """
    if _DUNDER_RE.match(token):
        return True
    if _DOTTED_PATH_RE.search(token):
        return True
    for ext in _KNOWN_EXTENSIONS:
        if token.lower().endswith(ext):
            return True
    if token == token.lower():
        return True
    # ALL_CAPS with at least one underscore: constant or env-var name
    if "_" in token and _ALL_CAPS_CONST_RE.match(token):
        return True
    return False


def _build_defined_types(raw_text: str) -> frozenset[str]:
    """Collect CapWords names that appear as types in fenced code blocks.

    A name is a defined code type when it appears in a code block as a
    class definition, return-type annotation, or variable type annotation
    (e.g. "class Foo", "-> Foo", ": Foo").  Mere value-assignment
    appearances ("x = Foo") do not qualify.
    """
    defined: set[str] = set()
    in_code_block = False
    fence_width = ""

    for line in raw_text.splitlines():
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
            continue

        if in_code_block:
            for m in _TYPE_DEF_RE.finditer(line):
                defined.add(m.group(1))

    return frozenset(defined)


def _build_table_defined_ids(raw_text: str) -> frozenset[str]:
    """Collect structured IDs defined as the first data cell of a table row.

    A structured ID (SC-N, T-NN, phase-N, or subplan) that is the leading
    token of the first non-empty cell of a markdown table row is being
    defined in that table, not orphaned.  Cells may carry parenthetical
    qualifiers after the ID.
    """
    defined: set[str] = set()
    for line in raw_text.splitlines():
        stripped = line.strip()
        if not stripped.startswith("|"):
            continue
        # Skip header-separator rows like |---|---|
        if re.match(r"^\|[\s|:-]+\|$", stripped):
            continue
        m = _TABLE_FIRST_CELL_RE.match(stripped)
        if m:
            defined.add(m.group(1))
    return frozenset(defined)


def _extract_identifiers_with_lines(
    raw_text: str,
) -> tuple[dict[str, list[int]], set[int]]:
    """Scan raw_text for all plan-structural identifiers.

    Returns (all_occurrences, code_block_line_set) where:
      all_occurrences maps identifier -> list of 1-based line numbers.
      code_block_line_set is the set of lines inside fenced code blocks.

    Occurrences inside code blocks count as uses (not definitions);
    the >= 2 threshold in the caller handles this correctly.
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
            continue

        if in_code_block:
            code_block_line_set.add(lineno)
        _collect_identifiers_from_line(line, lineno, all_occurrences)

    return all_occurrences, code_block_line_set


def _collect_identifiers_from_line(
    line: str,
    lineno: int,
    occurrences: dict[str, list[int]],
) -> None:
    """Extract all identifier patterns from one line, add to occurrences."""
    # Backtick tokens: skip code-symbol shapes (dunders, dotted paths,
    # filenames, lowercase, ALL_CAPS constants).
    for m in _BACKTICK_RE.finditer(line):
        ident = m.group(1)
        if ident.lower() in _BUILTIN_EXEMPT:
            continue
        if _is_code_symbol(ident):
            continue
        occurrences.setdefault(ident, []).append(lineno)

    # Structured plan IDs: always collected regardless of case or shape.
    for pattern in (_SC_ID_RE, _T_TASK_RE, _PHASE_ID_RE, _SUBPLAN_ID_RE):
        for m in pattern.finditer(line):
            ident = m.group(0)
            occurrences.setdefault(ident, []).append(lineno)


def _build_line_to_section(sections: dict, raw_text: str) -> dict[int, str]:
    """Map each 1-based line number to the deepest enclosing section heading."""
    line_to_best: dict[int, tuple[int, str]] = {}
    for heading, section in sections.items():
        for ln in range(section.line_start, section.line_end + 1):
            current = line_to_best.get(ln)
            if current is None or section.level > current[0]:
                line_to_best[ln] = (section.level, heading)
    return {ln: heading for ln, (_, heading) in line_to_best.items()}


def _has_p1_ok_marker(lines: list[str], lineno: int) -> bool:
    """Return True if line lineno or the line above carries a p1-ok marker."""
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

    all_occurrences, _ = _extract_identifiers_with_lines(parsed.raw_text)
    line_to_section = _build_line_to_section(parsed.sections, parsed.raw_text)
    table_defined = _build_table_defined_ids(parsed.raw_text)
    code_types = _build_defined_types(parsed.raw_text)

    for ident, linenos in all_occurrences.items():
        unique_linenos = sorted(set(linenos))

        if len(unique_linenos) >= 2:
            continue

        # Structured ID defined as first cell of a markdown table row
        if ident in table_defined:
            continue

        # CapWords token defined as a code type in a fenced code block
        if ident in code_types:
            continue

        sole_line = unique_linenos[0]
        section_heading = line_to_section.get(sole_line, "")

        if _is_xref_section(section_heading):
            continue

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
