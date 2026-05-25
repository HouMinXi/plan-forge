"""P5: Interface symmetry check.

Every public API method introduced in Module Designs must appear in
the Implementation Tasks T-row output column.  Conversely, every T-row
output method must trace back to Module Designs.  Asymmetry in either
direction is reported as HIGH findings.

Granularity note: T-rows often describe outputs at file/module level
("record.py + query.py") rather than per-function.  A Module Designs
API is considered covered when either the function name itself or a
plausible owning file (derived from the function name) appears anywhere
in the Implementation Tasks section text.

Mode-string note: bare config/mode-name strings are not APIs and must
not trigger t_row_orphan.  Specifically: common boolean/enum keyword
tokens (`off`, `on`, `true`, `false`, `none`, `null`, `auto`,
`default`) and feature-flag patterns (`on_*`, `off_*`) are exempt.
"""
from __future__ import annotations

import re
from plan_forge.parser import ParsedPlan
from plan_forge.verdict import Finding, Severity


# Top-level def inside code blocks
_TOP_DEF_RE = re.compile(r"^def\s+(\w+)\s*\(", re.MULTILINE)
# 4-space indented method (class method)
_METHOD_DEF_RE = re.compile(r"^    def\s+(\w+)\s*\(", re.MULTILINE)

# T-row output extraction patterns
_BACKTICK_IDENT_RE = re.compile(r"`(\w+)`")
_INLINE_DEF_RE = re.compile(r"def\s+(\w+)\s*\(")
_FILE_FUNC_RE = re.compile(r"(\w+)\.py:(\w+)")

# All .py filenames mentioned anywhere in a section body
_PY_FILE_RE = re.compile(r"\b(\w+)\.py\b")

# Built-in convention names exempt by design
_EXEMPT_NAMES = frozenset({"check", "run"})

# Config/mode-name tokens that are not APIs.
# Exact keyword set: common boolean/enum/null literals.
# Pattern prefix set: feature-flag style (on_*, off_*).
_MODE_STRING_KEYWORDS = frozenset({
    "off", "on", "true", "false", "none", "null", "auto", "default",
})
_MODE_STRING_PREFIXES = ("on_", "off_")


def _is_exempt(name: str) -> bool:
    """Return True if name is exempt from P5 symmetry check."""
    if name.startswith("_"):
        return True
    if re.match(r"^(test_|_test)", name):
        return True
    if name in _EXEMPT_NAMES:
        return True
    return False


def _is_mode_string(name: str, plan_text: str) -> bool:
    """Return True if name reads as a config/mode value, not a function.

    Exempt tokens: common boolean/enum/null literals and feature-flag
    prefixes (on_*, off_*), but only when no ``def name(`` definition
    exists anywhere in the plan text.  A token with a real function
    definition is never a mode string regardless of its prefix.
    """
    if name.lower() in _MODE_STRING_KEYWORDS:
        return True
    if name.startswith(_MODE_STRING_PREFIXES):
        if re.search(
            r"\bdef\s+" + re.escape(name) + r"\s*\(", plan_text
        ):
            return False
        return True
    return False


def _extract_code_block_texts(section_body: str) -> list[str]:
    """Extract the contents of all fenced code blocks in a section body.

    Uses fence-width state machine same as parser.py.
    Returns list of block content strings (not including fence lines).
    """
    blocks: list[str] = []
    lines = section_body.splitlines()
    in_block = False
    fence_width = ""
    current: list[str] = []

    for line in lines:
        stripped = line.strip()
        m = re.match(r"^(`{3,})", stripped)
        if m:
            fence = m.group(1)
            if not in_block:
                in_block = True
                fence_width = fence
                current = []
            elif fence == fence_width:
                in_block = False
                fence_width = ""
                blocks.append("\n".join(current))
                current = []
            continue
        if in_block:
            current.append(line)

    # Unclosed block at end of section
    if in_block and current:
        blocks.append("\n".join(current))

    return blocks


def _extract_module_designs_apis(sections: dict) -> set[str]:
    """Extract public API names from Module Designs section code blocks."""
    apis: set[str] = set()

    for heading, section in sections.items():
        hl = heading.lower()
        if "module designs" not in hl:
            continue

        for block_text in _extract_code_block_texts(section.body):
            for m in _TOP_DEF_RE.finditer(block_text):
                name = m.group(1)
                if not _is_exempt(name):
                    apis.add(name)
            for m in _METHOD_DEF_RE.finditer(block_text):
                name = m.group(1)
                if not _is_exempt(name):
                    apis.add(name)

    return apis


def _impl_tasks_raw_text(sections: dict) -> str:
    """Return concatenated body text of all Implementation Tasks sections."""
    parts: list[str] = []
    for heading, section in sections.items():
        if "implementation tasks" in heading.lower():
            parts.append(section.body)
    return "\n".join(parts)


def _py_file_stems_in_text(text: str) -> set[str]:
    """Return the set of .py file stems mentioned in the given text."""
    return {m.group(1) for m in _PY_FILE_RE.finditer(text)}


def _api_covered_by_file_ref(name: str, file_stems: set[str]) -> bool:
    """Return True if a plausible owning .py file for `name` is in file_stems.

    Checks each underscore-prefix of the function name as a candidate
    file stem.  For example, `record_outcome` tries stems `record` and
    `record_outcome`; if `record.py` is mentioned in the T-rows the API
    is considered covered at file granularity.
    """
    parts = name.split("_")
    for i in range(1, len(parts) + 1):
        candidate = "_".join(parts[:i])
        if len(candidate) >= 3 and candidate in file_stems:
            return True
    return False


def _extract_t_row_outputs(
    sections: dict, plan_text: str
) -> set[str]:
    """Extract output identifiers from Implementation Tasks T-rows.

    Backtick-quoted tokens that are config/mode-name values (e.g. `off`,
    `on_split_evidence_rich`) are silently ignored.  Tokens that look like
    function names are included and checked against Module Designs.
    """
    outputs: set[str] = set()

    for heading, section in sections.items():
        hl = heading.lower()
        if "implementation tasks" not in hl:
            continue

        for line in section.body.splitlines():
            stripped = line.strip()
            if not stripped.startswith("|"):
                continue
            cells_raw = stripped.split("|")
            cells = [c.strip() for c in cells_raw]
            if cells and cells[0] == "":
                cells = cells[1:]
            if cells and cells[-1] == "":
                cells = cells[:-1]
            if not cells:
                continue
            if all(re.match(r"^[-: ]+$", c) for c in cells):
                continue

            for cell in cells:
                for m in _BACKTICK_IDENT_RE.finditer(cell):
                    name = m.group(1)
                    if not _is_exempt(name) and not _is_mode_string(
                        name, plan_text
                    ):
                        outputs.add(name)
                for m in _INLINE_DEF_RE.finditer(cell):
                    name = m.group(1)
                    if not _is_exempt(name):
                        outputs.add(name)
                for m in _FILE_FUNC_RE.finditer(cell):
                    name = m.group(2)
                    if not _is_exempt(name):
                        outputs.add(name)

    return outputs


def check(parsed: ParsedPlan) -> list[Finding]:
    """Run P5 interface symmetry check on a parsed plan.

    Reports HIGH findings for:
      - P5.module_design_orphan: API in Module Designs where neither its
        name nor a plausible owning file appears in Implementation Tasks
      - P5.t_row_orphan: T-row output (mode strings excluded) not found
        in Module Designs
    """
    findings: list[Finding] = []

    plan_text = parsed.raw_text
    module_designs_apis = _extract_module_designs_apis(parsed.sections)
    t_row_outputs = _extract_t_row_outputs(parsed.sections, plan_text)

    # If either set is empty, no symmetry check is possible; skip silently.
    if not module_designs_apis or not t_row_outputs:
        return findings

    impl_text = _impl_tasks_raw_text(parsed.sections)
    file_stems = _py_file_stems_in_text(impl_text)

    # APIs in Module Designs not covered by any T-row at function or
    # file-module granularity
    _word_re_cache: dict[str, re.Pattern[str]] = {}
    for name in sorted(module_designs_apis - t_row_outputs):
        if name not in _word_re_cache:
            _word_re_cache[name] = re.compile(
                r"\b" + re.escape(name) + r"\b", re.IGNORECASE
            )
        if _word_re_cache[name].search(impl_text):
            continue
        if _api_covered_by_file_ref(name, file_stems):
            continue
        findings.append(Finding(
            check_id="P5.module_design_orphan",
            severity=Severity.HIGH,
            location="section:Module Designs:line:0",
            message=(
                f"API {name!r} appears in Module Designs but is not"
                " listed as a T-row output"
            ),
            fix_hint=(
                f"add {name!r} to the Output column of the relevant"
                " T-row, or add inline"
                " <!-- plan-forge: p5-ok (reason) --> if intentionally"
                " internal-only"
            ),
        ))

    # T-row outputs not found in Module Designs (mode strings already excluded)
    for name in sorted(t_row_outputs - module_designs_apis):
        findings.append(Finding(
            check_id="P5.t_row_orphan",
            severity=Severity.HIGH,
            location="section:Implementation Tasks:line:0",
            message=(
                f"T-row claims output {name!r} but no matching"
                " Module Designs entry"
            ),
            fix_hint=(
                f"add {name!r} to ## Module Designs as a documented"
                " public API, or remove from T-row Output column"
            ),
        ))

    return findings
