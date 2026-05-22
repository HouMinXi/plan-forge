"""Arbitration surface logic: which findings escalate to a human."""

from plan_forge.verdict import Finding

VALID_MODES = frozenset(
    {"off", "always", "on_split", "on_split_evidence_rich"}
)


def decide_when_to_arbitrate(
    findings: list[Finding],
    mode: str,
) -> tuple[bool, list[Finding]]:
    """Returns (should_surface, findings_to_arbitrate).

    Modes:
      - "always": surface all LLM-derived findings
      - "on_split": surface when any LLM finding has split votes
      - "on_split_evidence_rich": surface when split AND
        every provider in the split cited >= 1 concrete instance with
        per-instance reasoning
      - "off": never surface

    Findings with no LLM evidence are never surfaced (arbitration is
    only meaningful for LLM-derived disagreement).

    Raises:
        ValueError: if mode is not one of VALID_MODES (fail-loud so a
            mistyped mode cannot silently disable arbitration).
    """
    if mode not in VALID_MODES:
        raise ValueError(f"unknown arbitration mode: {mode!r}")
    if mode == "off":
        return False, []
    to_arbitrate: list[Finding] = []
    for f in findings:
        if not f.llm_evidence:
            continue
        verdicts = [ev.verdict for ev in f.llm_evidence]
        unique_verdicts = set(verdicts)
        is_split = len(unique_verdicts) > 1
        if mode == "always":
            to_arbitrate.append(f)
        elif is_split:
            if mode == "on_split":
                to_arbitrate.append(f)
            elif mode == "on_split_evidence_rich":
                if all(
                    len(ev.cited_instances) >= 1
                    for ev in f.llm_evidence
                ):
                    to_arbitrate.append(f)
    return bool(to_arbitrate), to_arbitrate
