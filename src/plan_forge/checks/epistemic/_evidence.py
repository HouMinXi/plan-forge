"""Verdict-token constants and evidence adapter for epistemic gates.

Single source of truth for verdict tokens used in G6/G8 prompts.
Comparison is case-insensitive via verdict_matches().
"""
from __future__ import annotations

from plan_forge.llm.client import LLMClient
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
        out.append(LLMEvidence(
            provider=provider_name,
            model=model_by_name.get(provider_name, "unknown"),
            verdict=resp.verdict,
            reasoning=resp.reasoning,
            prompt_version=prompt_version,
            run_id=0,  # sentinel: not yet persisted to corpus
            cited_instances=resp.cited_instances,
            search_evidence=resp.search_evidence,
            tier=EvidenceTier.UNCLASSIFIED,  # G10 fills later
        ))
    return out


def schema_for(provider_name: str) -> dict | None:
    """Return the web-search tool schema for a provider, or None."""
    return _TOOL_BY_PROVIDER.get(provider_name)
