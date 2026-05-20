"""Public API: check_mechanical(), check(), and scaffold() stub."""
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
    # Epistemic is hardcoded VISION: mechanical-only mode
    # makes no epistemic assessment; VISION signals "no G-gate ran".
    # Do NOT replace with _compute_epistemic() here -- that would break
    # the intentional separation between mechanical and epistemic layers.
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
    # SUBSPEC interpretation: spec names get_all_clients(); the registry
    # exposes build_active_list() which performs the same credential resolution
    # and active-provider filtering.  build_active_list() is the correct symbol.
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
        and combined findings from all three layers.  The two dimensions
        are computed independently: a plan whose only serious findings are
        on vision gates (G1/G2/G3/G5/G7) will produce engineering=FAIL
        (any BLOCKER/HIGH fails engineering) and epistemic=VISION (no
        non-vision serious finding fires the FAIL trigger).  A plan with
        non-vision-gate BLOCKERs (e.g. G4 aggregate, G8 absent section,
        F1 orphan SC) produces engineering=FAIL and epistemic=FAIL.
    """
    parsed = parse(plan_text)
    findings: list[Finding] = []

    # Layer 1: mechanical F1-F7 + PBR P1/P2/P5 (PBR delegated inside mechanical.run)
    findings.extend(mechanical.run(parsed, preamble=preamble))

    # Layer 2: epistemic G1-G8
    # Bootstrap LLM clients from environment when caller passes None.
    # Passing llm_clients=[] explicitly skips LLM Part B (mechanical-only).
    if llm_clients is None:
        llm_clients = _bootstrap_llm_clients()
    findings.extend(epistemic.run(parsed, llm_clients))

    engineering = _compute_engineering(findings)
    epistemic_verdict = _compute_epistemic(findings)
    return Verdict(
        engineering=engineering,
        epistemic=epistemic_verdict,
        findings=findings,
        active_providers=[c.name for c in llm_clients],
    )


def _compute_epistemic(findings: list[Finding]) -> EpistemicVerdict:
    """Compute epistemic verdict from findings alone.

    Serious (BLOCKER/HIGH) findings are partitioned by check_id prefix:
    - Vision gates G1/G2/G3/G5/G7 (section absent or partial-field HIGH)
      yield a VISION trigger.
    - All other gates (F*, P*, G4.*mechanical, G4.*aggregate, G6.*,
      G8.*) yield a FAIL trigger.
    Precedence: FAIL > VISION > PASS.
    The engineering verdict is deliberately not consulted: if it were,
    engineering FAIL (which fires on any BLOCKER/HIGH, vision gates
    included) would make VISION unreachable via the FAIL > VISION rule.
    """
    # G4/G6/G8 are epistemic quality gates (FAIL triggers), not structural
    # absences, so they are intentionally excluded from this tuple.
    # (G4 has no LLM Part B; G6 and G8 each have Part A mechanical + Part B LLM.)
    # INVARIANT: this partition relies on each gate's check_ids starting with
    # its own Gx. prefix (e.g. G4.A.aggregate, G6.B.llm). A gate emitting a
    # check_id with a different gate's prefix would silently misroute findings.
    # The test test_check_id_prefix_invariant enforces this invariant.
    vision_gate_prefixes = ("G1.", "G2.", "G3.", "G5.", "G7.")
    # HIGH is included because vision gates emit partial-field findings at HIGH
    # (e.g. G2.gray_rhino_no_denial, G2.black_swan_no_survival,
    #  G3.no_early_warning, G7.missing_barbell).
    # Both BLOCKER (section absent) and HIGH (partial-field) on vision gates
    # are VISION triggers.
    serious = (Severity.BLOCKER, Severity.HIGH)
    has_fail_trigger = any(
        f.severity in serious
        and not f.check_id.startswith(vision_gate_prefixes)
        for f in findings
    )
    has_vision_trigger = any(
        f.severity in serious
        and f.check_id.startswith(vision_gate_prefixes)
        for f in findings
    )
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
