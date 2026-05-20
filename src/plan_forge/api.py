"""Public API: check_mechanical() now; check() and scaffold() in later tasks."""
from __future__ import annotations

from pathlib import Path

from .parser import parse
from .checks import mechanical
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


def check(plan_text: str, **kwargs) -> Verdict:
    """Run all gates on plan_text and return a Verdict.

    Not yet implemented.
    """
    raise NotImplementedError


def scaffold(name: str, output_dir: Path | None = None) -> Path:
    """Generate a plan skeleton from the default template.

    Not yet implemented.
    """
    raise NotImplementedError
