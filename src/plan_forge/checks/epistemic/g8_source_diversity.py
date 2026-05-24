"""G8 Source Diversity -- Part A (mechanical) + Part B (LLM).

Part A: External Voices section must exist, contain at least one
citation, a dissenting view, and a historical failure case.

Part B: per-citation search_vote on resolvability; UNRESOLVABLE ->
BLOCKER, UNCERTAIN -> MEDIUM.

"""
from __future__ import annotations

import hashlib
import json
import warnings

from plan_forge.checks.epistemic._evidence import (
    G8_RESOLVED_VIA_SEARCH,
    G8_UNCERTAIN,
    G8_UNRESOLVABLE,
    _format_evidence_block,
    canon,
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
    host_evidence: dict[str, list] | None = None,
) -> list[Finding]:
    """G8: External Voices structure (Part A) + citation check (Part B).

    Args:
        parsed: parsed plan document.
        llm_clients: LLM client instances for Part B.
        host_evidence: optional dict of citation -> evidence hits or
            search_failed sentinel. Keys are canonicalized before lookup.

    Returns:
        List of findings from Part A (mechanical) and Part B (LLM).
    """
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

    schemas = {c.name: schema_for(c.name) for c in llm_clients}

    canon_evidence = (
        {canon(k): v for k, v in host_evidence.items()}
        if host_evidence else None
    )

    for citation in parsed.citations:
        citation_canon = canon(citation)
        raw = canon_evidence.get(citation_canon) if canon_evidence else None

        inject = isinstance(raw, list)
        guard_skip = isinstance(raw, list) and len(raw) > 0

        if (
            canon_evidence
            and citation_canon not in canon_evidence
        ):
            warnings.warn(
                f"evidence expected but missing for citation: {citation!r}",
                stacklevel=2
            )
            findings.append(Finding(
                check_id="G8.B.missing_evidence",
                severity=Severity.MEDIUM,
                location="External Voices",
                message=(
                    f"host evidence missing for citation: {citation!r}"
                ),
                fix_hint=(
                    "provide evidence for all citations when using "
                    "--evidence-file"
                ),
            ))

        prompt_version = (
            "g8_citation_resolvability_v1" if inject
            else "g8_citation_resolvability_v0"
        )
        template = load_prompt(prompt_version)

        payload = {
            "citation_text": citation,
            "context": "External Voices",
        }
        full_prompt = template + "\n\nACTUAL INPUT:\n" + json.dumps(payload)

        if inject:
            evidence_block = _format_evidence_block(raw)
            full_prompt += "\n\nHOST-PROVIDED EVIDENCE:\n" + evidence_block

        per_citation_schemas = (
            {name: None for name in schemas} if inject else schemas
        )

        evidence_hash = "none"
        if guard_skip:
            evidence_hash = hashlib.sha256(
                json.dumps(raw, sort_keys=True).encode()
            ).hexdigest()

        ttl_class = "recent" if inject else "canonical"

        def build_evidence_guard(should_skip: bool):
            """Build guard callback that conditionally skips downgrade."""
            def _guard(names, evs):
                if should_skip:
                    return {}
                return guard_unbacked_search(
                    names,
                    evs,
                    schemas,
                    search_claim_verdict=G8_RESOLVED_VIA_SEARCH,
                    downgrade_verdict=G8_UNCERTAIN,
                )
            return _guard

        evidence_guard = build_evidence_guard(guard_skip)

        vote = search_vote(
            full_prompt,
            llm_clients,
            cache_key_inputs={
                "gate": "G8.B",
                "citation": citation,
                "prompt_version": prompt_version,
                "evidence_hash": evidence_hash,
                "ttl_class": ttl_class,
            },
            tool_use_schemas=per_citation_schemas,
            evidence_guard=evidence_guard,
        )

        if vote.status == "no_providers":
            break

        evidence = responses_to_evidence(
            vote, llm_clients, prompt_version,
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
