"""PBR (Perspective-Based Reading) checks package.

Exposes run(parsed) which aggregates P1, P2, P5 findings in stable
order.  P6 (metadata-currency) is planned for T17 and not yet integrated.
"""
from __future__ import annotations

from plan_forge.parser import ParsedPlan
from plan_forge.verdict import Finding

from . import (
    p1_symbol_closure,
    p2_null_propagation,
    p5_interface_symmetry,
)


def run(parsed: ParsedPlan) -> list[Finding]:
    """Run all PBR checks P1, P2, P5 on a parsed plan.

    Args:
        parsed: ParsedPlan produced by parser.parse().

    Returns:
        Concatenated Finding list in P1, P2, P5 order.
    """
    findings: list[Finding] = []
    findings.extend(p1_symbol_closure.check(parsed))
    findings.extend(p2_null_propagation.check(parsed))
    findings.extend(p5_interface_symmetry.check(parsed))
    return findings
