"""Mechanical checks package.

Exposes run(parsed, preamble=None) which aggregates F1-F15 findings
in stable order (F1 first, F15 last).
"""
from __future__ import annotations

from plan_forge.parser import ParsedPlan
from plan_forge.verdict import Finding

from plan_forge.checks import pbr

from . import (
    f1_sc_traceability,
    f2_duplicate_fact,
    f3_cross_plan_invariant,
    f4_temporal_anchor,
    f5_r_tag_pruner,
    f6_preamble_body,
    f7_ascii,
    f8_plan_consistency,
    f9_plan_length,
    f10_noun_phrase_duplicate,
    f11_ac_test_traceability,
    f12_temporal_anchor_lint,
    f13_cross_plan_claim_verifier,
    f14_task_without_ac,
    f15_read_first_validity,
)


def run(parsed: ParsedPlan, preamble: str | None = None) -> list[Finding]:
    """Run all mechanical checks F1-F15 on a parsed plan.

    Args:
        parsed: ParsedPlan produced by parser.parse().
        preamble: optional orchestrator preamble text for F6.
                  When None, F6 returns [].

    Returns:
        Concatenated Finding list in F1..F15, P1, P2, P5, P6 order.
    """
    findings: list[Finding] = []
    findings.extend(f1_sc_traceability.check(parsed))
    findings.extend(f2_duplicate_fact.check(parsed))
    findings.extend(f3_cross_plan_invariant.check(parsed))
    findings.extend(f4_temporal_anchor.check(parsed))
    findings.extend(f5_r_tag_pruner.check(parsed))
    findings.extend(f6_preamble_body.check(parsed, preamble=preamble))
    findings.extend(f7_ascii.check(parsed))
    findings.extend(f8_plan_consistency.check(parsed))
    findings.extend(f9_plan_length.check(parsed))
    findings.extend(f10_noun_phrase_duplicate.check(parsed))
    findings.extend(f11_ac_test_traceability.check(parsed))
    findings.extend(f12_temporal_anchor_lint.check(parsed))
    findings.extend(f13_cross_plan_claim_verifier.check(parsed))
    findings.extend(f14_task_without_ac.check(parsed))
    findings.extend(f15_read_first_validity.check(parsed))
    findings.extend(pbr.run(parsed))
    return findings
