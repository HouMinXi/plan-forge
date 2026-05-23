"""Arbitration capture: persist a human verdict + rationale to corpus."""

from plan_forge.corpus.record import CorpusRecorder

_VALID_HUMAN_VERDICTS = frozenset(
    {"verified", "unverified", "deferred", "abstain"}
)


def capture_arbitration(
    recorder: CorpusRecorder,
    run_id: int,
    finding_id: int | None,
    bundle_text: str,
    human_verdict: str | None,
    human_rationale: str | None,
) -> int:
    """Persist a human arbitration verdict; return its arbitration_id.

    overrode_llm is derived from human_verdict (gate-agnostic):
      - "unverified" -> True  (human rejected the flagged finding)
      - "verified"   -> False (human confirmed the flagged finding)
      - "deferred" / "abstain" / None -> None (no determination)

    Raises:
        ValueError: if human_verdict is not None and not one of the
            canonical four values (fail-loud; mirrors the arbitrations
            table CHECK constraint).
    """
    if (
        human_verdict is not None
        and human_verdict not in _VALID_HUMAN_VERDICTS
    ):
        raise ValueError(f"invalid human_verdict: {human_verdict!r}")
    if human_verdict == "unverified":
        overrode_llm: bool | None = True
    elif human_verdict == "verified":
        overrode_llm = False
    else:
        overrode_llm = None
    return recorder.record_arbitration(
        run_id=run_id,
        finding_id=finding_id,
        bundle_text=bundle_text,
        human_verdict=human_verdict,
        human_rationale=human_rationale,
        overrode_llm=overrode_llm,
    )
