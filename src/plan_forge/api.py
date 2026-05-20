"""Public API: check_mechanical() now; check() and scaffold() in later tasks."""
from __future__ import annotations

from pathlib import Path

from .parser import parse
from .checks import mechanical, epistemic
from .llm.registry import build_active_list
from .llm.client import LLMClient
from .verdict import (
    Verdict,
    EngineeringVerdict,
    EpistemicVerdict,
    Severity,
    Finding,
)


def check_mechanical(
    plan_text: str,
    preamble: str | None = None,
) -> Verdict:
    """Run mechanical checks (F1-F7 + PBR P1/P2/P5) only.

    Does NOT run epistemological gates (G1-G10).  Use check()
    for the full pipeline.

    Args:
        plan_text: raw markdown text of the plan document.
        preamble: optional orchestrator preamble for F6 preamble-body
                  diff check.  When None, F6 returns no findings.

    Returns:
        Verdict with engineering computed from findings (D2),
        epistemic always VISION (D3), and findings list from
        F1-F7 + P1/P2/P5.
    """
    parsed = parse(plan_text)
    findings = mechanical.run(parsed, preamble=preamble)
    engineering = _compute_engineering(findings)
    return Verdict(
        engineering=engineering,
        epistemic=EpistemicVerdict.VISION,
        findings=findings,
    )


def _compute_engineering(findings: list[Finding]) -> EngineeringVerdict:
    """Engineering verdict: FAIL iff any finding has severity BLOCKER or HIGH.

    HIGH and BLOCKER both indicate plan-failure; MEDIUM and LOW do not.
    MEDIUM and LOW are informational and do not flip engineering to FAIL.
    """
    fail_severities = {Severity.BLOCKER, Severity.HIGH}
    if any(f.severity in fail_severities for f in findings):
        return EngineeringVerdict.FAIL
    return EngineeringVerdict.PASS


def _bootstrap_llm_clients() -> list[LLMClient]:
    """Build LLM client list from environment credentials.

    Thin wrapper around the registry's build_active_list().
    Returns all clients whose credentials resolve (may be empty if no
    env vars are set).  Silently skips providers with missing credentials.
    """
    # SUBSPEC interpretation: get_all_clients() was the original name in
    # the spec, but the registry exposes build_active_list() which performs
    # the same credential resolution + health check filtering.
    return build_active_list()


def check(
    plan_text: str,
    *,
    llm_clients: list[LLMClient] | None = None,
    preamble: str | None = None,
) -> Verdict:
    """Run all gates (F1-F7 + PBR + G1-G8) and return aggregated Verdict.

    Args:
        plan_text: raw markdown text of the plan document.
        llm_clients: optional list of LLMClient instances for G4/G6/G8
            Part B.  If None, bootstraps from environment via registry +
            credentials.  If empty list [], skips LLM Part B
            (mechanical-only mode).
        preamble: optional orchestrator preamble for F6 preamble-body
            diff check.  When None, F6 returns no findings.

    Returns:
        Verdict with engineering (PASS/FAIL), epistemic (PASS/FAIL/VISION),
        and combined findings from all three layers.
    """
    parsed = parse(plan_text)
    findings: list[Finding] = []

    # Layer 1: mechanical F1-F7 (includes PBR via mechanical.run)
    findings.extend(mechanical.run(parsed, preamble=preamble))

    # Layer 2: epistemic G1-G8
    # Bootstrap LLM clients from environment when caller passes None.
    # Passing llm_clients=[] explicitly skips LLM Part B (mechanical-only).
    if llm_clients is None:
        llm_clients = _bootstrap_llm_clients()
    findings.extend(epistemic.run(parsed, llm_clients))

    engineering = _compute_engineering(findings)
    epistemic_verdict = _compute_epistemic(findings, engineering)
    return Verdict(
        engineering=engineering,
        epistemic=epistemic_verdict,
        findings=findings,
        active_providers=[c.name for c in llm_clients],
    )


def _compute_epistemic(
    findings: list[Finding],
    engineering: EngineeringVerdict,
) -> EpistemicVerdict:
    """Compute epistemic verdict from findings + engineering verdict.

    Decision rules per PLAN lines 383-422:
    - VISION if any G1/G2/G3/G5/G7 mechanical BLOCKER (plan-level
      structure absent).
    - FAIL if engineering == FAIL OR any G4/G6/G8 aggregate BLOCKER.
    - PASS otherwise.
    - Precedence: FAIL > VISION > PASS.
    """
    # SUBSPEC interpretation: G1/G2/G3/G5/G7 mechanical BLOCKERs are the
    # "plan-level structure absent" findings.  Heuristic: check_id starts
    # with one of the vision-gate prefixes AND severity is BLOCKER.
    # This matches check_ids like G1.no_section, G2.missing_gray_rhino,
    # G3.insufficient_causes, G5.insufficient_scenarios, G5.all_break,
    # G7.no_section, G7.missing_*.
    vision_gate_prefixes = ("G1.", "G2.", "G3.", "G5.", "G7.")
    has_vision_trigger = any(
        f.check_id.startswith(vision_gate_prefixes)
        and f.severity == Severity.BLOCKER
        for f in findings
    )

    # SUBSPEC interpretation: G4/G6/G8 aggregate BLOCKERs have check_id
    # containing "aggregate" OR starting with one of the fail-gate prefixes
    # AND severity BLOCKER.  This covers G4.A.aggregate, G6.A.mechanical,
    # G6.B.aggregate, G8.A.no_section, G8.B.llm.
    # Warning: "aggregate" is a substring match; if a future non-G4/G6/G8
    # check_id contains "aggregate", revisit this heuristic.
    fail_gate_prefixes = ("G4.", "G6.", "G8.")
    has_fail_trigger = engineering == EngineeringVerdict.FAIL or any(
        (
            f.check_id.startswith(fail_gate_prefixes)
            or "aggregate" in f.check_id
        )
        and f.severity == Severity.BLOCKER
        for f in findings
    )

    # Precedence: FAIL > VISION > PASS (PLAN line 420).
    if has_fail_trigger:
        return EpistemicVerdict.FAIL
    if has_vision_trigger:
        return EpistemicVerdict.VISION
    return EpistemicVerdict.PASS


def scaffold(name: str, output_dir: Path | None = None) -> Path:
    """Generate a plan skeleton from the default template.

    Not yet implemented.
    """
    raise NotImplementedError
