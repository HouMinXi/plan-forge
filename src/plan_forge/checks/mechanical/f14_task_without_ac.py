"""F14: Task-without-acceptance-criteria detection.

Flags <task> elements that lack an <acceptance_criteria> or <verify> block.
Checkpoint tasks (type starts with "checkpoint:") are exempt.
"""
from __future__ import annotations

import re

from plan_forge.parser import ParsedPlan
from plan_forge.verdict import Finding, Severity

_TASK_FULL_RE = re.compile(r'<task\b([^>]*)>(.*?)</task>', re.DOTALL)
_TYPE_ATTR_RE = re.compile(r'\btype=["\']([^"\']*)["\']')


def _has_ac_or_verify(task_body: str) -> bool:
    """Return True if the task body contains acceptance_criteria or verify."""
    return bool(
        re.search(r'<acceptance_criteria\b', task_body)
        or re.search(r'<verify\b', task_body)
    )


def check(parsed: ParsedPlan, **kwargs) -> list[Finding]:
    """Check for tasks missing acceptance criteria or verify blocks.

    Args:
        parsed: ParsedPlan to inspect.

    Returns:
        One F14 finding per task that lacks <acceptance_criteria> or <verify>.
    """
    findings: list[Finding] = []
    for m in _TASK_FULL_RE.finditer(parsed.raw_text):
        attrs = m.group(1)
        body = m.group(2)
        type_match = _TYPE_ATTR_RE.search(attrs)
        type_val = type_match.group(1) if type_match else ""
        if type_val.startswith("checkpoint:"):
            continue
        if _has_ac_or_verify(body):
            continue
        lineno = parsed.raw_text[:m.start()].count('\n') + 1
        findings.append(Finding(
            check_id="F14.task_without_ac",
            severity=Severity.HIGH,
            location=f"line:{lineno}",
            message="task has no <acceptance_criteria> or <verify> block",
            fix_hint=(
                "add an <acceptance_criteria> block with verifiable exit conditions"
            ),
        ))
    return findings
