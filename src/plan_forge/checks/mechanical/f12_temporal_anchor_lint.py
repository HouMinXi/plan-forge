"""F12: Temporal anchor lint for unanchored temporal phrases.

Flags temporal phrases of the form "before/after/once/when/until ...
commit/merge/run/..." that lack a concrete anchor (backtick command,
snake_case identifier, or git command) on the same line.
"""
from __future__ import annotations

import re

from plan_forge.parser import ParsedPlan
from plan_forge.verdict import Finding, Severity

_AC_RE = re.compile(r'<acceptance_criteria>(.*?)</acceptance_criteria>', re.DOTALL)
_ACTION_RE = re.compile(r'<action>(.*?)</action>', re.DOTALL)

_TEMPORAL_ACTION_RE = re.compile(
    r'\b(before|after|once|when|until)\b'
    r'(?:(?!\n).){0,60}'
    r'\b(commit|merge|run|execute|complete|finish|pass|fail)\b',
    re.IGNORECASE,
)

_ANCHOR_SIGNALS = (
    re.compile(r'`'),
    re.compile(r'\buv\s+run\b'),
    re.compile(r'\b[a-z]+_[a-z]'),
    re.compile(r'\bgit\s+\w+'),
)


def check(parsed: ParsedPlan, **kwargs) -> list[Finding]:
    """Check acceptance_criteria and action blocks for unanchored temporal phrases.

    Args:
        parsed: ParsedPlan to inspect.

    Returns:
        One F12 finding per vague temporal phrase lacking a concrete anchor.
    """
    findings: list[Finding] = []
    blocks: list[tuple[str, int]] = []

    for m in _AC_RE.finditer(parsed.raw_text):
        blocks.append((m.group(1), parsed.raw_text[:m.start()].count('\n') + 1))
    for m in _ACTION_RE.finditer(parsed.raw_text):
        blocks.append((m.group(1), parsed.raw_text[:m.start()].count('\n') + 1))

    for block_text, block_lineno in blocks:
        for line in block_text.splitlines():
            if not _TEMPORAL_ACTION_RE.search(line):
                continue
            if any(sig.search(line) for sig in _ANCHOR_SIGNALS):
                continue
            findings.append(Finding(
                check_id="F12.temporal_anchor_unanchored",
                severity=Severity.LOW,
                location=f"line:{block_lineno}",
                message=f"temporal phrase lacks a concrete anchor: {line.strip()!r}",
                fix_hint=(
                    "anchor the phrase with a backtick command,"
                    " snake_case identifier, or git command"
                ),
            ))
    return findings
