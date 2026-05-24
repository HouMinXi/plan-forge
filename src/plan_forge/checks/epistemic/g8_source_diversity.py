"""G8 Source Diversity -- Part A (mechanical) + Part B (LLM).

Part A: External Voices section must exist, contain at least one
citation, a dissenting view, and a historical failure case.

Part B: per-citation search_vote on resolvability; UNRESOLVABLE ->
BLOCKER, UNCERTAIN -> MEDIUM.

"""
from __future__ import annotations

import json

from plan_forge.checks.epistemic._evidence import (
    G8_RESOLVED_VIA_SEARCH,
    G8_UNCERTAIN,
    G8_UNRESOLVABLE,
    guard_unbacked_search,
    is_genuine_split,
    responses_to_evidence,
    schema_for,
    verdict_matches,
)
from plan_forge.llm.client import LLMClient
from plan_forge.llm.prompts import load as load_prompt
from plan_forge.llm.search_vote import search_vote
from plan_forge.parser import ParsedPlan
from plan_forge.verdict import Finding, Severity

_PROMPT_VERSION = "g8_citation_resolvability_v0"

# Dissent keywords (case-insensitive search in section body)
_DISSENT_KEYWORDS = frozenset({
    "dissent", "disagree", "counter", "critic",
    "objection", "however", "contrary", "opposing",
})

# Failure-case keywords (case-insensitive search in section body)
_FAILURE_KEYWORDS = frozenset({
    "failure", "failed", "postmortem", "post-mortem",
    "went wrong", "lesson", "incident", "retrospective",
})


def _find_external_voices_body(parsed: ParsedPlan) -> str | None:
    """Return the body of the External Voices section, or None."""
    for heading, section in parsed.sections.items():
        if "external voices" in heading.lower():
            return section.body
    return None


def _body_contains_any(body: str, keywords: frozenset[str]) -> bool:
    """Check if body contains any keyword (case-insensitive)."""
    lower = body.lower()
    return any(kw in lower for kw in keywords)


def check(
    parsed: ParsedPlan,
    llm_clients: list[LLMClient],
) -> list[Finding]:
    """G8: External Voices structure (Part A) + citation check (Part B)."""
    findings: list[Finding] = []

    # --- Part A (mechanical) ---
    body = _find_external_voices_body(parsed)

    if body is None:
        findings.append(Finding(
            check_id="G8.A.no_section",
            severity=Severity.BLOCKER,
            location="plan",
            message="## External Voices section absent",
            fix_hint=(
                "add ## External Voices with a primary source, "
                "a dissenting view, and a historical failure case"
            ),
        ))
        return findings  # no point checking sub-requirements

    # "non-AI primary source" cannot be reliably detected mechanically;
    # we treat "at least one citation present" as the mechanical proxy.
    # True non-AI provenance is a Part B / human concern.
    if len(parsed.citations) == 0:
        findings.append(Finding(
            check_id="G8.A.no_citation",
            severity=Severity.BLOCKER,
            location="External Voices",
            message="no citation found in External Voices section",
            fix_hint="add at least one citation in Author (Year) format",
        ))

    if not _body_contains_any(body, _DISSENT_KEYWORDS):
        findings.append(Finding(
            check_id="G8.A.no_dissent",
            severity=Severity.BLOCKER,
            location="External Voices",
            message="no dissenting view found in External Voices",
            fix_hint=(
                "add a dissenting or contrary perspective "
                "(e.g. 'However, critics argue...')"
            ),
        ))

    if not _body_contains_any(body, _FAILURE_KEYWORDS):
        findings.append(Finding(
            check_id="G8.A.no_failure_case",
            severity=Severity.BLOCKER,
            location="External Voices",
            message="no historical failure case in External Voices",
            fix_hint=(
                "add a historical failure case or post-mortem "
                "(e.g. 'the 2016 incident... lesson learned')"
            ),
        ))

    # --- Part B (LLM): per-citation resolvability ---
    if not llm_clients:
        return findings

    if len(parsed.citations) == 0:
        return findings

    template = load_prompt(_PROMPT_VERSION)
    schemas = {c.name: schema_for(c.name) for c in llm_clients}

    for citation in parsed.citations:
        payload = {
            "citation_text": citation,
            "context": "External Voices",
        }
        full_prompt = (
            template + "\n\nACTUAL INPUT:\n" + json.dumps(payload)
        )

        vote = search_vote(
            full_prompt,
            llm_clients,
            cache_key_inputs={
                "gate": "G8.B",
                "citation": citation,
                "prompt_version": _PROMPT_VERSION,
            },
            tool_use_schemas=schemas,
            evidence_guard=lambda names, evs: guard_unbacked_search(
                names,
                evs,
                schemas,
                search_claim_verdict=G8_RESOLVED_VIA_SEARCH,
                downgrade_verdict=G8_UNCERTAIN,
            ),
        )

        if vote.status == "no_providers":
            break

        evidence = responses_to_evidence(
            vote, llm_clients, _PROMPT_VERSION,
        )

        if verdict_matches(vote.verdict, G8_UNRESOLVABLE):
            findings.append(Finding(
                check_id="G8.B.llm",
                severity=Severity.BLOCKER,
                location="External Voices",
                message=(
                    f"citation unresolvable (likely fabricated):"
                    f" {citation!r}"
                ),
                fix_hint="replace with a verifiable citation",
                llm_evidence=evidence,
            ))
        elif verdict_matches(vote.verdict, G8_UNCERTAIN):
            findings.append(Finding(
                check_id="G8.B.uncertain",
                severity=Severity.MEDIUM,
                location="External Voices",
                message=(
                    f"citation uncertain; needs human verification:"
                    f" {citation!r}"
                ),
                fix_hint=(
                    "confirm the source manually or provide a "
                    "stronger citation"
                ),
                llm_evidence=evidence,
            ))
        elif (
            vote.status == "indeterminate"
            and is_genuine_split(vote)
        ):
            findings.append(Finding(
                check_id="G8.B.llm",
                severity=Severity.ARBITRATION,
                location="External Voices",
                message=(
                    f"LLM providers split on citation resolvability:"
                    f" {citation!r}; needs human arbitration"
                ),
                fix_hint=(
                    "review the per-provider evidence and arbitrate"
                ),
                llm_evidence=evidence,
            ))
        # RESOLVED_VIA_SEARCH / RESOLVED_BY_KNOWLEDGE: no finding

    return findings
