"""P5: Interface symmetry check.

Every public API method introduced in Module Designs must appear in
the Implementation Tasks T-row output column.  Conversely, every T-row
output method must trace back to Module Designs.  Asymmetry in either
direction is reported as HIGH findings.
"""
from __future__ import annotations

import re
from plan_forge.parser import ParsedPlan
from plan_forge.verdict import Finding, Severity


# ---------------------------------------------------------------------------
# Patterns for API extraction
# ---------------------------------------------------------------------------

# Top-level def inside code blocks
_TOP_DEF_RE = re.compile(r"^def\s+(\w+)\s*\(", re.MULTILINE)
# 4-space indented method (class method)
_METHOD_DEF_RE = re.compile(r"^    def\s+(\w+)\s*\(", re.MULTILINE)

# T-row output extraction patterns
_BACKTICK_IDENT_RE = re.compile(r"`(\w+)`")
_INLINE_DEF_RE = re.compile(r"def\s+(\w+)\s*\(")
_FILE_FUNC_RE = re.compile(r"(\w+)\.py:(\w+)")

# Fence pattern for code block extraction within section bodies
_FENCE_RE = re.compile(r"^(`{3,})", re.MULTILINE)

# Built-in convention names exempt by design (entry points shared across all checks)
_EXEMPT_NAMES = frozenset({"check", "run"})


def _is_exempt(name: str) -> bool:
    """Return True if name is exempt from P5 symmetry check."""
    if name.startswith("_"):
        return True
    if re.match(r"^(test_|_test)", name):
        return True
    if name in _EXEMPT_NAMES:
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


def _extract_t_row_outputs(sections: dict) -> set[str]:
    """Extract output identifiers from Implementation Tasks T-rows."""
    outputs: set[str] = set()

    for heading, section in sections.items():
        hl = heading.lower()
        if "implementation tasks" not in hl:
            continue

        for line in section.body.splitlines():
            stripped = line.strip()
            if not stripped.startswith("|"):
                continue
            # Skip separator rows
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

            # Extract identifiers from all cells in the row (Output column
            # is not always at a fixed index; scan all cells)
            for cell in cells:
                for m in _BACKTICK_IDENT_RE.finditer(cell):
                    name = m.group(1)
                    if not _is_exempt(name):
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
      - P5.module_design_orphan: API in Module Designs but not in T-row
      - P5.t_row_orphan: T-row output not in Module Designs
    """
    findings: list[Finding] = []

    module_designs_apis = _extract_module_designs_apis(parsed.sections)
    t_row_outputs = _extract_t_row_outputs(parsed.sections)

    # If either set is empty, no symmetry check is possible; skip silently.
    # (Plans with no Module Designs section or no Implementation Tasks
    # section are out of scope for P5 -- they will be caught by other checks.)
    if not module_designs_apis or not t_row_outputs:
        return findings

    # APIs in Module Designs not listed in any T-row
    for name in sorted(module_designs_apis - t_row_outputs):
        findings.append(Finding(
            check_id="P5.module_design_orphan",
            severity=Severity.HIGH,
            location="section:Module Designs:line:0",
            message=(
                f"API {name!r} appears in Module Designs but is not"
                " listed as a T-row output"
            ),
            fix_hint=(
                f"add {name!r} to the Output column of the relevant T-row,"
                " or add inline <!-- plan-forge: p5-ok (reason) --> if"
                " intentionally internal-only"
            ),
        ))

    # T-row outputs not found in Module Designs
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
