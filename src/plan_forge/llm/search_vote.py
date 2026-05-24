"""Multi-provider search-and-vote orchestration.

Dispatches a prompt to N active LLM clients and aggregates verdicts
via majority vote.  Handles four arities:

  N=0  no_providers   -- all providers unavailable; caller falls back
  N=1  single_opinion -- one provider; verdict returned with warning
  N=2  consensus      -- both agree -> consensus; disagree -> indeterminate
  N=3+ majority       -- floor(N/2)+1 strict majority; else indeterminate

"""
from __future__ import annotations

import copy
import warnings
from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass, field

from plan_forge.llm.client import LLMClient, LLMResponse


@dataclass
class VoteResult:
    """Aggregated voting outcome across N providers."""
    status: str       # majority / consensus / indeterminate / single_opinion / no_providers
    verdict: str | None
    evidences: list[LLMResponse] = field(default_factory=list)
    active_providers: list[str] = field(default_factory=list)
    threshold: int | None = None
    provenance: dict[str, str] = field(default_factory=dict)


def search_vote(
    prompt: str,
    active_clients: list[LLMClient],
    *,
    cache_key_inputs: dict,
    tool_use_schemas: dict,
    evidence_guard: Callable[[list[str], list[LLMResponse]], dict[str, str]]
                    | None = None,
) -> VoteResult:
    """Call each active client and aggregate verdicts by majority vote.

    Args:
        prompt: prompt text sent to each provider.
        active_clients: list of LLMClient instances (may be empty).
        cache_key_inputs: base dict for cache key; provider name injected
            per-call so keys differ by provider.
        tool_use_schemas: provider_name -> tool schema dict | None.
        evidence_guard: optional pre-tally hook; receives
            (active_providers, evidences) and returns
            {provider_name: provenance_key} for flagged providers.
            The hook MUTATES evidences[i].verdict in place and may
            raise. Runs BEFORE verdicts are extracted for the tally.

    Returns:
        VoteResult with status, optional consensus verdict, and evidences.
    """
    n = len(active_clients)

    if n == 0:
        return VoteResult(
            status="no_providers",
            verdict=None,
            evidences=[],
            active_providers=[],
            threshold=None,
            provenance={},
        )

    evidences: list[LLMResponse] = []
    for client in active_clients:
        schema = tool_use_schemas.get(client.name)
        resp = client.call(
            prompt,
            tool_use_schema=schema,
            cache_key_inputs={**cache_key_inputs, "provider": client.name},
        )
        evidences.append(copy.copy(resp))

    active_names = [c.name for c in active_clients]

    prov = evidence_guard(active_names, evidences) if evidence_guard else {}

    if n == 1:
        warnings.warn(
            f"search_vote: single provider ({active_names[0]}); "
            "verdict reliability reduced",
            stacklevel=2,
        )
        return VoteResult(
            status="single_opinion",
            verdict=evidences[0].verdict,
            evidences=evidences,
            active_providers=active_names,
            threshold=None,
            provenance=prov,
        )

    verdicts = [e.verdict for e in evidences]

    if n == 2:
        if verdicts[0] == verdicts[1]:
            return VoteResult(
                status="consensus",
                verdict=verdicts[0],
                evidences=evidences,
                active_providers=active_names,
                threshold=None,
                provenance=prov,
            )
        return VoteResult(
            status="indeterminate",
            verdict=None,
            evidences=evidences,
            active_providers=active_names,
            threshold=None,
            provenance=prov,
        )

    # N >= 3: strict majority requires floor(N/2)+1 votes (= n//2 + 1)
    counts = Counter(verdicts)
    top_verdict, top_count = counts.most_common(1)[0]
    threshold = (n // 2) + 1
    if top_count >= threshold:
        return VoteResult(
            status="majority",
            verdict=top_verdict,
            evidences=evidences,
            active_providers=active_names,
            threshold=threshold,
            provenance=prov,
        )
    return VoteResult(
        status="indeterminate",
        verdict=None,
        evidences=evidences,
        active_providers=active_names,
        threshold=threshold,
        provenance=prov,
    )
