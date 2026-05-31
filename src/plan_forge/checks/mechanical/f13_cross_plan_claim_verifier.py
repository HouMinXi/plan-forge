"""F13: Cross-plan claim verifier for thin-prose audit references.

Returns an empty list until the gate logic is implemented.
"""
from __future__ import annotations

from plan_forge.parser import ParsedPlan
from plan_forge.verdict import Finding


def check(parsed: ParsedPlan, **kwargs) -> list[Finding]:
    return []
