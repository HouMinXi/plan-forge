"""Finding bundle builder: render one Finding's evidence for a human."""

from plan_forge.verdict import Finding

_DECISION = (
    "## Decision\n"
    "Please respond with one of: verified / unverified / deferred / "
    "abstain\n"
    "and a rationale."
)


def build_evidence_bundle(finding: Finding) -> str:
    """Render finding + per-provider evidence as human-readable markdown.

    Presents an LLM-split finding to a human arbiter. Every
    evidence-dict access is defensive (.get): cited_instances and
    search_evidence are pass-through JSON from provider responses
    (client.py parse_verdict_response performs no inner-key validation),
    so key presence is not guaranteed.
    """
    lines: list[str] = [
        f"# Arbitration: {finding.check_id} at {finding.location}",
        "",
        "## Finding",
        f"- Severity: {finding.severity.value}",
        f"- Message: {finding.message}",
        f"- Fix hint: {finding.fix_hint or '(none)'}",
        "",
        "## LLM evidence",
    ]
    if not finding.llm_evidence:
        lines += ["", "(no LLM evidence)"]
    for ev in finding.llm_evidence:
        lines.append("")
        lines.append(
            f"### Provider {ev.provider}: verdict = {ev.verdict} "
            f"(tier {ev.tier.value})"
        )
        lines.append(f"- Reasoning: {ev.reasoning}")
        lines.append("- Cited instances:")
        if ev.cited_instances:
            for ci in ev.cited_instances:
                lines.append(
                    f"  - {ci.get('snippet', '') or ''}: "
                    f"{ci.get('issue', '') or ''}"
                )
        else:
            lines.append("  - (none)")
        lines.append("- Search evidence:")
        if ev.search_evidence:
            for se in ev.search_evidence:
                lines.append(
                    f"  - Query: {se.get('query', '') or ''} -> "
                    f"{se.get('result_summary', '') or ''} "
                    f"({se.get('url', '') or ''})"
                )
        else:
            lines.append("  - (none)")
    lines += ["", _DECISION, ""]
    return "\n".join(lines)
