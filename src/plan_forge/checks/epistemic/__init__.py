"""Epistemic gates (G-layer): G1 through G8.

G9 and G10 are not yet implemented (planned for later milestones).
Imports are deferred until run() is called so the package can be
imported before all gate modules exist.

Pure-mechanical gates (G1/G2/G3/G5/G7) receive only `parsed`.
LLM gates (G4/G6/G8) receive `parsed` and `llm_clients`.
"""
from __future__ import annotations

from plan_forge.llm.client import LLMClient
from plan_forge.parser import ParsedPlan
from plan_forge.verdict import Finding


def run(parsed: ParsedPlan, llm_clients: list[LLMClient]) -> list[Finding]:
    """Run G1-G8 in numeric order; return combined findings."""
    # Deferred imports so the package can load before all gate modules exist
    from plan_forge.checks.epistemic import (
        g1_reference_class,
        g2_risk_taxonomy,
        g3_premortem,
        g4_calibration,
        g5_antifragility,
        g6_sc_falsifiability,
        g7_scope_challenge,
        g8_source_diversity,
    )

    findings: list[Finding] = []
    findings.extend(g1_reference_class.check(parsed))
    findings.extend(g2_risk_taxonomy.check(parsed))
    findings.extend(g3_premortem.check(parsed))
    findings.extend(g4_calibration.check(parsed, llm_clients))
    findings.extend(g5_antifragility.check(parsed))
    findings.extend(g6_sc_falsifiability.check(parsed, llm_clients))
    findings.extend(g7_scope_challenge.check(parsed))
    findings.extend(g8_source_diversity.check(parsed, llm_clients))
    return findings
