"""Unit tests for api.check() and _compute_epistemic().

Covers bootstrap, mechanical-only mode, VISION trigger,
FAIL precedence, G6 aggregate, and PASS path.
"""
from __future__ import annotations

from unittest.mock import patch

from plan_forge.api import check, _compute_epistemic
from plan_forge.verdict import (
    EngineeringVerdict,
    EpistemicVerdict,
    Severity,
    Finding,
)


# ---------------------------------------------------------------------------
# Minimal plan with no G1-G7 structure (used in mechanical-only tests)
# ---------------------------------------------------------------------------
_MINIMAL_PLAN = "# Minimal Plan\n\nNo sections at all.\n"


# ---------------------------------------------------------------------------
# Helper: build a minimal Finding
# ---------------------------------------------------------------------------

def _finding(check_id: str, severity: Severity) -> Finding:
    """Build a minimal Finding for unit tests."""
    return Finding(
        check_id=check_id,
        severity=severity,
        location="test:1",
        message="unit test finding",
    )


# ---------------------------------------------------------------------------
# test_check_mechanical_only_mode
# ---------------------------------------------------------------------------

def test_check_mechanical_only_mode():
    """llm_clients=[] (empty list, not None) runs only mechanical gates.

    A minimal plan with no sections triggers both VISION conditions (G1-G7
    absent) and FAIL conditions (G8.A.no_section absent is a G8 BLOCKER).
    FAIL > VISION, so epistemic resolves to FAIL.
    Engineering is also FAIL (G1/G2/G3/G5/G7/G8 BLOCKERs present).
    No LLM Part B findings since llm_clients=[].
    """
    # SUBSPEC interpretation: a plan with no structure triggers both VISION
    # (G1-G7 absent) and FAIL (G8.A.no_section absent) conditions.
    # Precedence FAIL > VISION means epistemic = FAIL.
    result = check(_MINIMAL_PLAN, llm_clients=[])
    # No LLM-specific findings (no G4.B / G6.B / G8.B check_ids)
    llm_check_ids = {f.check_id for f in result.findings
                     if ".B." in f.check_id or f.check_id.endswith(".llm")}
    assert len(llm_check_ids) == 0
    # Both vision and fail triggers are present; FAIL wins
    assert result.epistemic == EpistemicVerdict.FAIL
    assert result.engineering == EngineeringVerdict.FAIL


# ---------------------------------------------------------------------------
# test_check_bootstrap_llm_clients_none
# ---------------------------------------------------------------------------

def test_check_bootstrap_llm_clients_none():
    """llm_clients=None triggers _bootstrap_llm_clients().

    Mock build_active_list to return [] so no network calls are made.
    Assert no crash and epistemic is computed (not None).
    """
    with patch(
        "plan_forge.api.build_active_list",
        return_value=[],
    ):
        result = check(_MINIMAL_PLAN, llm_clients=None)

    assert result is not None
    assert result.epistemic in (
        EpistemicVerdict.PASS,
        EpistemicVerdict.FAIL,
        EpistemicVerdict.VISION,
    )


# ---------------------------------------------------------------------------
# test_compute_epistemic_vision_trigger
# ---------------------------------------------------------------------------

def test_compute_epistemic_vision_trigger():
    """G1.no_section BLOCKER with engineering PASS -> VISION."""
    findings = [_finding("G1.no_section", Severity.BLOCKER)]
    result = _compute_epistemic(findings, EngineeringVerdict.PASS)
    assert result == EpistemicVerdict.VISION


# ---------------------------------------------------------------------------
# test_compute_epistemic_fail_precedence
# ---------------------------------------------------------------------------

def test_compute_epistemic_fail_precedence():
    """VISION trigger present + engineering FAIL -> FAIL (precedence).

    FAIL > VISION > PASS (PLAN line 420).
    """
    findings = [_finding("G1.no_section", Severity.BLOCKER)]
    result = _compute_epistemic(findings, EngineeringVerdict.FAIL)
    assert result == EpistemicVerdict.FAIL


# ---------------------------------------------------------------------------
# test_compute_epistemic_g6_aggregate_fail
# ---------------------------------------------------------------------------

def test_compute_epistemic_g6_aggregate_fail():
    """G6.B.aggregate BLOCKER with engineering PASS -> FAIL.

    G6.B.aggregate is a G4/G6/G8 aggregate BLOCKER (fail trigger).
    """
    findings = [_finding("G6.B.aggregate", Severity.BLOCKER)]
    result = _compute_epistemic(findings, EngineeringVerdict.PASS)
    assert result == EpistemicVerdict.FAIL


# ---------------------------------------------------------------------------
# test_compute_epistemic_pass
# ---------------------------------------------------------------------------

def test_compute_epistemic_pass():
    """No VISION or FAIL triggers -> PASS."""
    findings = [
        _finding("F1.orphan_sc", Severity.MEDIUM),
        _finding("G4.calibration", Severity.LOW),
    ]
    result = _compute_epistemic(findings, EngineeringVerdict.PASS)
    assert result == EpistemicVerdict.PASS


# ---------------------------------------------------------------------------
# Additional edge cases
# ---------------------------------------------------------------------------

def test_compute_epistemic_g8_no_section_fail():
    """G8.A.no_section BLOCKER -> FAIL (G8 is a fail-gate prefix)."""
    findings = [_finding("G8.A.no_section", Severity.BLOCKER)]
    result = _compute_epistemic(findings, EngineeringVerdict.PASS)
    assert result == EpistemicVerdict.FAIL


def test_compute_epistemic_g4_aggregate_fail():
    """G4.A.aggregate BLOCKER -> FAIL."""
    findings = [_finding("G4.A.aggregate", Severity.BLOCKER)]
    result = _compute_epistemic(findings, EngineeringVerdict.PASS)
    assert result == EpistemicVerdict.FAIL


def test_compute_epistemic_vision_medium_not_trigger():
    """G1.no_section MEDIUM (not BLOCKER) does NOT trigger VISION."""
    findings = [_finding("G1.no_section", Severity.MEDIUM)]
    result = _compute_epistemic(findings, EngineeringVerdict.PASS)
    assert result == EpistemicVerdict.PASS


def test_compute_epistemic_g5_all_break_blocker_vision():
    """G5.all_break BLOCKER -> VISION (G5 is a vision-gate prefix)."""
    findings = [_finding("G5.all_break", Severity.BLOCKER)]
    result = _compute_epistemic(findings, EngineeringVerdict.PASS)
    assert result == EpistemicVerdict.VISION


def test_check_returns_verdict_instance():
    """check() returns a Verdict with all required fields."""
    from plan_forge.verdict import Verdict
    result = check(_MINIMAL_PLAN, llm_clients=[])
    assert isinstance(result, Verdict)
    assert isinstance(result.findings, list)
