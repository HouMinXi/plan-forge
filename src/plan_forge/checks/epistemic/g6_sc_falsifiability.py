"""G6 SC Falsifiability -- Part A (mechanical) + Part B (LLM).

Part A: every SC must have an explicit fail_condition.
Part B: per-SC search_vote on measurability; UNVERIFIED -> HIGH;
>30% UNVERIFIED -> aggregate BLOCKER.
"""
from __future__ import annotations

import json

from plan_forge.checks.epistemic._evidence import (
    G6_UNVERIFIED,
    responses_to_evidence,
    schema_for,
    verdict_matches,
)
from plan_forge.llm.client import LLMClient
from plan_forge.llm.prompts import load as load_prompt
from plan_forge.llm.search_vote import search_vote
from plan_forge.parser import ParsedPlan
from plan_forge.verdict import Finding, Severity

_PROMPT_VERSION = "g6_sc_measurability_v0"


def check(
    parsed: ParsedPlan,
    llm_clients: list[LLMClient],
) -> list[Finding]:
    """G6: SC fail-condition presence (Part A) + measurability (Part B)."""
    findings: list[Finding] = []

    # --- Part A (mechanical): missing fail_condition -> BLOCKER ---
    for sc in parsed.sc_table:
        if not sc.fail_condition:
            findings.append(Finding(
                check_id="G6.A.mechanical",
                severity=Severity.BLOCKER,
                location=sc.full_id,
                message="missing fail_condition column",
                fix_hint="add 'FAILS if ...' clause to SC",
            ))

    # --- Part B (LLM): per-SC measurability vote ---
    if not llm_clients:
        # no_providers: skip Part B entirely (LLM unavailable)
        return findings

    template = load_prompt(_PROMPT_VERSION)
    schemas = {c.name: schema_for(c.name) for c in llm_clients}

    unverified_count = 0
    for sc in parsed.sc_table:
        if not sc.fail_condition:
            continue  # already failed Part A; skip Part B

        payload = {
            "sc_id": sc.number,
            "sc_text": sc.name,
            "fail_condition_text": sc.fail_condition,
        }
        full_prompt = (
            template + "\n\nACTUAL INPUT:\n" + json.dumps(payload)
        )

        vote = search_vote(
            full_prompt,
            llm_clients,
            cache_key_inputs={
                "gate": "G6.B",
                "sc_id": sc.number,
                "prompt_version": _PROMPT_VERSION,
            },
            tool_use_schemas=schemas,
        )

        if vote.status == "no_providers":
            # LLM unavailable at runtime; skip Part B
            break

        evidence = responses_to_evidence(
            vote, llm_clients, _PROMPT_VERSION,
        )

        if verdict_matches(vote.verdict, G6_UNVERIFIED):
            unverified_count += 1
            findings.append(Finding(
                check_id="G6.B.llm",
                severity=Severity.HIGH,
                location=sc.full_id,
                message=(
                    "LLM majority: fail-condition not measurable"
                ),
                fix_hint=(
                    "strengthen with concrete observable state"
                    " + detection procedure"
                ),
                llm_evidence=evidence,
            ))

    # Aggregate threshold: >30% UNVERIFIED -> BLOCKER
    if (
        parsed.sc_table
        and unverified_count / len(parsed.sc_table) > 0.30
    ):
        findings.append(Finding(
            check_id="G6.B.aggregate",
            severity=Severity.BLOCKER,
            location="plan.sc_table",
            message=(
                f"{unverified_count}/{len(parsed.sc_table)}"
                " SCs not measurable (>30% threshold)"
            ),
            fix_hint="rewrite SCs with concrete fail-conditions",
        ))

    return findings
