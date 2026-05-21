"""P2: Null propagation check.

Every nullable field or return type declared in a fenced code block must
have explicit null-handling semantics.  Orphan optionals (declared but
never null-checked in the same block, and with no prose escape hatch in
the 10 lines before the block opening) are reported as HIGH findings.
"""
from __future__ import annotations

import re
from plan_forge.parser import ParsedPlan
from plan_forge.verdict import Finding, Severity


# ---------------------------------------------------------------------------
# Nullable declaration patterns (scanned inside fenced code blocks)
# ---------------------------------------------------------------------------

# Pattern 1: name: Type | None
_NULLABLE_TYPE_OR_RE = re.compile(
    r"(\w+)\s*:\s*\w+(?:\[[^\]]+\])?\s*\|\s*None\b"
)
# Pattern 2: name: Optional[Type]
_NULLABLE_OPTIONAL_RE = re.compile(
    r"(\w+)\s*:\s*Optional\[[^\]]+\]"
)
# Pattern 3: def func(...) -> T | None
_FUNC_RETURN_OR_RE = re.compile(
    r"def\s+(\w+)\s*\([^)]*\)\s*->\s*\w+(?:\[[^\]]+\])?\s*\|\s*None\b"
)
# Pattern 4: def func(...) -> Optional[
_FUNC_RETURN_OPT_RE = re.compile(
    r"def\s+(\w+)\s*\([^)]*\)\s*->\s*Optional\["
)

# Fence-width state machine (same pattern as parser.py _extract_hedge_words)
_FENCE_RE = re.compile(r"^(`{3,})")

# Prose escape hatches (searched in 10 lines before the block opening)
_NON_NULL_INVARIANT_RE = re.compile(r"non-null invariant enforced by\b")
_P2_OK_RE = re.compile(r"<!--\s*plan-forge:\s*p2-ok")


def _null_check_patterns(name: str) -> list[re.Pattern]:
    """Return list of null-handling patterns for the given nullable name."""
    n = re.escape(name)
    return [
        re.compile(r"\bif\s+" + n + r"\s+is\s+None\b"),
        re.compile(r"\bif\s+not\s+" + n + r"\b"),
        re.compile(r"\bif\s+" + n + r"\s+is\s+not\s+None\b"),
        re.compile(r"\bassert\s+" + n + r"\s+is\s+not\s+None\b"),
        # default-value pattern: X or <anything> (word, string literal, etc.)
        re.compile(n + r"\s+or\s+\S"),
    ]


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
    """Analyze one completed fenced block for orphan optionals."""
    result: list[Finding] = []
    has_escape = _has_prose_escape(all_lines, block_open)
    block_text = "\n".join(ln for _, ln in block_lines)

    # Collect all nullable declarations
    nullables: list[tuple[str, int]] = []  # (name, 1-based lineno in file)

    for lineno, ln in block_lines:
        for pattern in (
            _NULLABLE_TYPE_OR_RE,
            _NULLABLE_OPTIONAL_RE,
            _FUNC_RETURN_OR_RE,
            _FUNC_RETURN_OPT_RE,
        ):
            for m in pattern.finditer(ln):
                name = m.group(1)
                nullables.append((name, lineno))

    seen_names: set[str] = set()
    for name, decl_lineno in nullables:
        if name in seen_names:
            continue
        seen_names.add(name)

        # Check prose escape hatch (10 lines before block)
        if has_escape:
            continue

        # Check null-handling patterns in the entire block
        handled = False
        for pat in _null_check_patterns(name):
            if pat.search(block_text):
                handled = True
                break

        if not handled:
            result.append(Finding(
                check_id="P2.orphan_optional",
                severity=Severity.HIGH,
                location=f"line:{decl_lineno}",
                message=(
                    f"nullable {name!r} declared but no null-check or"
                    " non-null invariant comment found"
                ),
                fix_hint=(
                    "add 'if X is None' branch, 'assert X is not None'"
                    " guard, default-value pattern ('X or default'),"
                    " prose 'non-null invariant enforced by ...'"
                    " within 10 lines before the block, or inline"
                    " <!-- plan-forge: p2-ok (reason) --> marker"
                ),
            ))

    return result


def check(parsed: ParsedPlan) -> list[Finding]:
    """Run P2 null propagation check on a parsed plan.

    Scans only content inside fenced code blocks.  For each nullable
    declaration, checks whether a null-handling pattern or prose escape
    hatch exists.  Returns HIGH finding per unhandled nullable.
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
                findings.extend(_flush_block(block_lines, block_open_lineno, lines))
                block_lines = []
            continue

        if in_code_block:
            block_lines.append((lineno, line))

    # Handle unclosed block at end-of-file (treat as closed)
    if in_code_block and block_lines:
        findings.extend(_flush_block(block_lines, block_open_lineno, lines))

    return findings
