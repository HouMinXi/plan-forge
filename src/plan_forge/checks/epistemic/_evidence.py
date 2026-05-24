"""Verdict-token constants and evidence adapter for epistemic gates.

Single source of truth for verdict tokens used in G6/G8 prompts.
Comparison is case-insensitive via verdict_matches().
"""
from __future__ import annotations

from plan_forge.llm.client import LLMClient, LLMResponse
from plan_forge.llm.search_vote import VoteResult
from plan_forge.llm import tool_use
from plan_forge.verdict import EvidenceTier, LLMEvidence

# G6 tokens -- MUST match llm/prompts/g6_sc_measurability_v0.txt OUTPUT
G6_VERIFIED = "VERIFIED"
G6_UNVERIFIED = "UNVERIFIED"

# G8 tokens -- MUST match llm/prompts/g8_citation_resolvability_v0.txt
G8_RESOLVED_VIA_SEARCH = "RESOLVED_VIA_SEARCH"
G8_RESOLVED_BY_KNOWLEDGE = "RESOLVED_BY_KNOWLEDGE"
G8_UNCERTAIN = "UNCERTAIN"
G8_UNRESOLVABLE = "UNRESOLVABLE"

# Provenance keys for VoteResult.provenance (guard_unbacked_search)
PROV_UNBACKED_SEARCH_CLAIM = "unbacked_search_claim"
PROV_FABRICATED_SEARCH_EVIDENCE = "fabricated_search_evidence"

# Provider -> web-search tool schema lookup (tool_use.py is read-only).
#
# openai-SDK clients (kimi, deepseek) make a single completion call with no
# client-side tool-result loop.  Giving them a tool schema makes the model
# stall on a tool_call instead of returning a verdict.  They answer directly
# when schema is None, like mimo.
#
# anthropic's web_search is server-side: the API executes the search and
# returns result blocks alongside the final text; call() reads both.  No
# client-side loop is needed, so the tool stays.
_TOOL_BY_PROVIDER = {
    "anthropic": tool_use.ANTHROPIC_WEB_SEARCH_TOOL,
    "kimi": None,      # openai SDK, no tool-call loop; answers direct
    "deepseek": None,  # openai SDK, no tool-call loop; answers direct
    "mimo": tool_use.MIMO_WEB_SEARCH_TOOL,  # None -> no tool_use
}


def verdict_matches(vote_verdict: str | None, token: str) -> bool:
    """Case-insensitive match of a vote verdict against a token constant."""
    return vote_verdict is not None and vote_verdict.strip().upper() == token


def is_genuine_split(vote: VoteResult) -> bool:
    """True when an indeterminate vote is a real disagreement.

    Requires >=2 DISTINCT non-empty verdicts. Verdicts are
    normalized (strip + upper) to match verdict_matches()'s
    case-insensitive semantics, and empty/None verdicts (error
    responses) are filtered so an all-errored vote does not
    masquerade as a disagreement worth human arbitration.
    """
    distinct = {
        e.verdict.strip().upper()
        for e in vote.evidences
        if e.verdict and e.verdict.strip()
    }
    return len(distinct) > 1


def responses_to_evidence(
    vote: VoteResult,
    llm_clients: list[LLMClient],
    prompt_version: str,
) -> list[LLMEvidence]:
    """Convert VoteResult.evidences to Finding-ready LLMEvidence list."""
    model_by_name = {c.name: c.model for c in llm_clients}
    out: list[LLMEvidence] = []
    for provider_name, resp in zip(vote.active_providers, vote.evidences):
        tier = (
            EvidenceTier.T4_SUSPECT
            if provider_name in vote.provenance
            else EvidenceTier.UNCLASSIFIED
        )
        out.append(LLMEvidence(
            provider=provider_name,
            model=model_by_name.get(provider_name, "unknown"),
            verdict=resp.verdict,
            reasoning=resp.reasoning,
            prompt_version=prompt_version,
            run_id=0,  # sentinel: not yet persisted to corpus
            cited_instances=resp.cited_instances,
            search_evidence=resp.search_evidence,
            tier=tier,
        ))
    return out


def guard_unbacked_search(
    active_providers: list[str],
    evidences: list[LLMResponse],
    tool_use_schemas: dict,
    *,
    search_claim_verdict: str | None = None,
    downgrade_verdict: str | None = None,
) -> dict[str, str]:
    """Guard against unbacked search claims from tool-less providers.

    Args:
        active_providers: list of provider names (parallel to evidences).
        evidences: LLMResponse instances (verdict mutated in place).
        tool_use_schemas: provider_name -> tool schema dict | None.
        search_claim_verdict: verdict token to downgrade (e.g.
            "RESOLVED_VIA_SEARCH"); optional.
        downgrade_verdict: verdict to assign after downgrade (e.g.
            "UNCERTAIN"); optional.

    Returns:
        dict[provider_name, provenance_key] for providers flagged.
        Empty dict if no flags.

    Raises:
        ValueError: if exactly one of search_claim_verdict or
            downgrade_verdict is set (must be both or neither).

    Provenance keys:
        PROV_UNBACKED_SEARCH_CLAIM: tool-less provider claimed a
            search-based verdict; verdict was downgraded.
        PROV_FABRICATED_SEARCH_EVIDENCE: tool-less provider has
            non-empty search_evidence; verdict unchanged (may not be a
            search-claim verdict).

    The guard mutates evidences[i].verdict in place and may raise.
    """
    if (search_claim_verdict is None) != (downgrade_verdict is None):
        raise ValueError(
            "search_claim_verdict and downgrade_verdict "
            "must be set together or both omitted"
        )

    assert len(active_providers) == len(evidences), (
        "active_providers and evidences length mismatch"
    )

    prov: dict[str, str] = {}

    for name, resp in zip(active_providers, evidences):
        if tool_use_schemas.get(name) is not None:
            continue

        if (
            search_claim_verdict is not None
            and verdict_matches(resp.verdict, search_claim_verdict)
        ):
            resp.verdict = downgrade_verdict
            prov[name] = PROV_UNBACKED_SEARCH_CLAIM
        elif resp.search_evidence:
            prov[name] = PROV_FABRICATED_SEARCH_EVIDENCE

    return prov


def schema_for(provider_name: str) -> dict | None:
    """Return the web-search tool schema for a provider, or None."""
    return _TOOL_BY_PROVIDER.get(provider_name)
