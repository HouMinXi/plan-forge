"""P2: Null propagation check.

A function that returns an optional type (T | None or Optional[T])
creates an obligation on callers to handle the None case.  When a
fenced code block declares such a return type and no prose escape hatch
appears in the 10 lines before the block, P2 reports a HIGH finding.

Prose escape hatches: a 'non-null invariant enforced by ...' sentence or
a '<!-- plan-forge: p2-ok (reason) -->' HTML comment suppresses the
finding.

Field declarations (name: T | None) inside model or schema blocks are
data-shape annotations, not propagation hazards.  P2 does not flag
them; only function return types are in scope.
"""
from __future__ import annotations

import re
from plan_forge.parser import ParsedPlan
from plan_forge.verdict import Finding, Severity


# ---------------------------------------------------------------------------
# Nullable function-return patterns (scanned inside fenced code blocks)
# ---------------------------------------------------------------------------

# def func(...) -> T | None
_FUNC_RETURN_OR_RE = re.compile(
    r"def\s+(\w+)\s*\([^)]*\)\s*->\s*\w+(?:\[[^\]]+\])?\s*\|\s*None\b"
)
# def func(...) -> Optional[T]
_FUNC_RETURN_OPT_RE = re.compile(
    r"def\s+(\w+)\s*\([^)]*\)\s*->\s*Optional\["
)

# Fence-width state machine (same pattern as parser.py _extract_hedge_words)
_FENCE_RE = re.compile(r"^(`{3,})")

# Prose escape hatches (searched in 10 lines before the block opening)
_NON_NULL_INVARIANT_RE = re.compile(r"non-null invariant enforced by\b")
_P2_OK_RE = re.compile(r"<!--\s*plan-forge:\s*p2-ok")


def _has_prose_escape(lines: list[str], block_open_lineno: int) -> bool:
    """Return True if any of the 10 lines before the block open have an escape.

    block_open_lineno is the 1-based line number of the fence opening line.
    Check lines max(1, block_open_lineno-10) .. block_open_lineno-1.
    """
    start = max(0, block_open_lineno - 11)  # 0-based inclusive
    end = block_open_lineno - 1              # 0-based exclusive (fence line)
    for line in lines[start:end]:
        if _NON_NULL_INVARIANT_RE.search(line):
            return True
        if _P2_OK_RE.search(line):
            return True
    return False


def _flush_block(
    block_lines: list[tuple[int, str]],
    block_open: int,
    all_lines: list[str],
) -> list[Finding]:
    """Analyze one completed fenced block for orphan optional returns."""
    result: list[Finding] = []
    has_escape = _has_prose_escape(all_lines, block_open)

    # Collect nullable function-return declarations only.
    # Field declarations (name: T | None) are data-shape annotations and
    # are intentionally excluded from this scan.
    nullables: list[tuple[str, int]] = []  # (name, 1-based lineno in file)

    for lineno, ln in block_lines:
        for pattern in (_FUNC_RETURN_OR_RE, _FUNC_RETURN_OPT_RE):
            for m in pattern.finditer(ln):
                name = m.group(1)
                nullables.append((name, lineno))

    seen_names: set[str] = set()
    for name, decl_lineno in nullables:
        if name in seen_names:
            continue
        seen_names.add(name)

        if has_escape:
            continue

        result.append(Finding(
            check_id="P2.orphan_optional",
            severity=Severity.HIGH,
            location=f"line:{decl_lineno}",
            message=(
                f"function {name!r} returns an optional type"
                " with no null-handling in scope"
            ),
            fix_hint=(
                "add a '<!-- plan-forge: p2-ok (reason) -->' marker"
                " within 10 lines before the code block, or add prose"
                " 'non-null invariant enforced by <reason>' near the"
                " function definition"
            ),
        ))

    return result


def check(parsed: ParsedPlan) -> list[Finding]:
    """Run P2 null propagation check on a parsed plan.

    Scans fenced code blocks for functions whose return type is optional
    (T | None or Optional[T]).  Reports a HIGH finding when no null-handling
    pattern or prose escape hatch covers the return value.
    """
    findings: list[Finding] = []
    lines = parsed.raw_text.splitlines()

    in_code_block = False
    fence_width = ""
    block_open_lineno = 0
    block_lines: list[tuple[int, str]] = []

    for lineno, line in enumerate(lines, 1):
        stripped = line.strip()
        fence_match = _FENCE_RE.match(stripped)
        if fence_match:
            fence = fence_match.group(1)
            if not in_code_block:
                in_code_block = True
                fence_width = fence
                block_open_lineno = lineno
                block_lines = []
            elif fence == fence_width:
                in_code_block = False
                fence_width = ""
                findings.extend(
                    _flush_block(block_lines, block_open_lineno, lines)
                )
                block_lines = []
            continue

        if in_code_block:
            block_lines.append((lineno, line))

    # Handle unclosed block at end-of-file (treat as closed)
    if in_code_block and block_lines:
        findings.extend(_flush_block(block_lines, block_open_lineno, lines))

    return findings
