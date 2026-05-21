"""F7: ASCII / non-ASCII grep.

Detects non-ASCII characters in the plan text.  Equivalent to
CLAUDE.md Step 0c -- guards against silently-emitted lookalikes
(em dash, smart quotes, arrows, etc.).
"""
from __future__ import annotations

from plan_forge.parser import ParsedPlan
from plan_forge.verdict import Finding, Severity

# Maximum findings before suppression summary kicks in
_FINDING_CAP = 50

# Fix-hint table: codepoint -> suggestion
_FIX_HINTS: dict[int, str] = {
    0x2014: "use ASCII `--`",          # em dash
    0x2013: "use ASCII `-`",           # en dash
    0x2018: "use ASCII `'`",           # left single quote
    0x2019: "use ASCII `'`",           # right single quote
    0x201C: 'use ASCII `"`',           # left double quote
    0x201D: 'use ASCII `"`',           # right double quote
    0x2026: "use ASCII `...`",         # ellipsis
    0x2192: "use ASCII `->`",          # right arrow
    0x2190: "use ASCII `<-`",          # left arrow
}

_DEFAULT_FIX_HINT = "remove or transliterate to ASCII"


def _fix_hint(cp: int) -> str:
    """Return fix hint for a given Unicode codepoint."""
    return _FIX_HINTS.get(cp, _DEFAULT_FIX_HINT)


def check(parsed: ParsedPlan, **kwargs) -> list[Finding]:
    """Scan plan text for non-ASCII characters.

    Args:
        parsed: ParsedPlan to inspect.

    Returns:
        List of F7 findings.  At most 50 position findings; if more
        are found a summary finding is appended.
    """
    findings: list[Finding] = []
    seen: set[tuple[int, int, int]] = set()
    total_count = 0

    for lineno, line in enumerate(parsed.raw_text.splitlines(), 1):
        for col, c in enumerate(line, 1):
            cp = ord(c)
            if cp <= 127:
                continue
            total_count += 1
            dedup_key = (lineno, col, cp)
            if dedup_key in seen:
                continue
            seen.add(dedup_key)

            if len(findings) < _FINDING_CAP:
                findings.append(Finding(
                    check_id="F7.non_ascii_char",
                    severity=Severity.HIGH,
                    location=f"line:{lineno}:col:{col}",
                    message=f"non-ASCII U+{cp:04X} ({c!r}) found",
                    fix_hint=_fix_hint(cp),
                ))

    if total_count > _FINDING_CAP:
        findings.append(Finding(
            check_id="F7.non_ascii_char",
            severity=Severity.HIGH,
            location="line:0",
            message=(
                f"... {total_count - _FINDING_CAP} more non-ASCII"
                f" characters suppressed"
            ),
            fix_hint=(
                r"run `git diff | grep -P '[^\x00-\x7F]'` for full list"
            ),
        ))

    return findings
