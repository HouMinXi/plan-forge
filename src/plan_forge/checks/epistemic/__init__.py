"""Epistemic gates (G-layer): G4/G6/G8.

Remaining gates (G1-G3, G5, G7, G9-G10) are not yet implemented.
Imports are deferred until run() is called so the package can be
imported before all gate modules exist.
"""
from __future__ import annotations

from plan_forge.llm.client import LLMClient
from plan_forge.parser import ParsedPlan
from plan_forge.verdict import Finding


def run(parsed: ParsedPlan, llm_clients: list[LLMClient]) -> list[Finding]:
    """Run G4 + G6 + G8 in order; return combined findings."""
    # Deferred imports so the package can load before all gate modules exist
    from plan_forge.checks.epistemic import (
        g4_calibration,
        g6_sc_falsifiability,
        g8_source_diversity,
    )

    findings: list[Finding] = []
    findings.extend(g4_calibration.check(parsed, llm_clients))
    findings.extend(g6_sc_falsifiability.check(parsed, llm_clients))
    findings.extend(g8_source_diversity.check(parsed, llm_clients))
    return findings
