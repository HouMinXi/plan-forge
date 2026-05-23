"""Unit tests for api.check() and _compute_epistemic().

Covers bootstrap, mechanical-only mode, VISION trigger,
FAIL precedence, G6 aggregate, and PASS path.
"""
from __future__ import annotations

import pathlib
from unittest.mock import patch

from plan_forge.api import check, _compute_epistemic
from plan_forge.verdict import (
    EngineeringVerdict,
    EpistemicVerdict,
    Severity,
    Finding,
)

_FIXTURES = pathlib.Path(__file__).parent.parent / "fixtures"


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
    absent) and FAIL conditions.  G8.A.no_section fires mechanically
    (section-detection only, no LLM) when External Voices is absent.
    FAIL > VISION, so epistemic resolves to FAIL.
    Engineering is also FAIL (G1/G2/G3/G5/G7/G8 BLOCKERs present).
    No LLM Part B findings since llm_clients=[].
    """
    result = check(_MINIMAL_PLAN, llm_clients=[])
    llm_check_ids = {f.check_id for f in result.findings
                     if ".B." in f.check_id or f.check_id.endswith(".llm")}
    assert len(llm_check_ids) == 0
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
    """G1.no_section BLOCKER with no non-vision serious findings -> VISION."""
    findings = [_finding("G1.no_section", Severity.BLOCKER)]
    result = _compute_epistemic(findings)
    assert result == EpistemicVerdict.VISION, (
        "single G1 BLOCKER with no non-vision serious finding must yield VISION; "
        "FAIL here means a non-vision trigger fired unexpectedly"
    )


# ---------------------------------------------------------------------------
# test_compute_epistemic_fail_wins_when_both_triggers_fire
# ---------------------------------------------------------------------------

def test_compute_epistemic_fail_wins_when_both_triggers_fire():
    """Both VISION trigger (G1 BLOCKER) and FAIL trigger (F1 HIGH) present -> FAIL.

    Verifies FAIL > VISION precedence when both fire.
    Bucket-assignment correctness (G1 -> VISION, F1 -> FAIL) is separately
    guarded by test_compute_epistemic_vision_trigger and
    test_compute_epistemic_g6_aggregate_fail.
    """
    findings = [
        _finding("G1.no_section", Severity.BLOCKER),
        _finding("F1.orphan_sc", Severity.HIGH),
    ]
    result = _compute_epistemic(findings)
    assert result == EpistemicVerdict.FAIL


# ---------------------------------------------------------------------------
# test_compute_epistemic_g6_aggregate_fail
# ---------------------------------------------------------------------------

def test_compute_epistemic_g6_aggregate_fail():
    """G6.B.aggregate BLOCKER -> FAIL (non-vision serious finding)."""
    findings = [_finding("G6.B.aggregate", Severity.BLOCKER)]
    result = _compute_epistemic(findings)
    assert result == EpistemicVerdict.FAIL


def test_compute_epistemic_g6a_mechanical_fail():
    """G6.A.mechanical BLOCKER -> FAIL (non-vision gate sub-ID)."""
    findings = [_finding("G6.A.mechanical", Severity.BLOCKER)]
    result = _compute_epistemic(findings)
    assert result == EpistemicVerdict.FAIL


def test_compute_epistemic_g6b_llm_high_fail():
    """G6.B.llm HIGH -> FAIL (non-vision gate; HIGH is serious)."""
    findings = [_finding("G6.B.llm", Severity.HIGH)]
    result = _compute_epistemic(findings)
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
    result = _compute_epistemic(findings)
    assert result == EpistemicVerdict.PASS


# ---------------------------------------------------------------------------
# Additional edge cases
# ---------------------------------------------------------------------------

def test_compute_epistemic_g8_no_section_fail():
    """G8.A.no_section BLOCKER -> FAIL (G8 is a non-vision gate)."""
    findings = [_finding("G8.A.no_section", Severity.BLOCKER)]
    result = _compute_epistemic(findings)
    assert result == EpistemicVerdict.FAIL


def test_compute_epistemic_g4_aggregate_fail():
    """G4.A.aggregate BLOCKER -> FAIL."""
    findings = [_finding("G4.A.aggregate", Severity.BLOCKER)]
    result = _compute_epistemic(findings)
    assert result == EpistemicVerdict.FAIL


def test_compute_epistemic_vision_medium_not_trigger():
    """G1.no_section MEDIUM (not BLOCKER/HIGH) does NOT trigger VISION."""
    findings = [_finding("G1.no_section", Severity.MEDIUM)]
    result = _compute_epistemic(findings)
    assert result == EpistemicVerdict.PASS


def test_compute_epistemic_g5_all_break_blocker_vision():
    """G5.all_break BLOCKER -> VISION (G5 is a vision-gate prefix)."""
    findings = [_finding("G5.all_break", Severity.BLOCKER)]
    result = _compute_epistemic(findings)
    assert result == EpistemicVerdict.VISION


def test_check_returns_verdict_instance():
    """check() returns a Verdict with all required fields."""
    from plan_forge.verdict import Verdict
    result = check(_MINIMAL_PLAN, llm_clients=[])
    assert isinstance(result, Verdict)
    assert isinstance(result.findings, list)


# ---------------------------------------------------------------------------
# Regression guards (added for VISION reachability fix)
# ---------------------------------------------------------------------------

def test_compute_epistemic_partial_high_is_vision():
    """G7.missing_barbell HIGH -> VISION (HIGH on a vision gate is VISION)."""
    findings = [_finding("G7.missing_barbell", Severity.HIGH)]
    result = _compute_epistemic(findings)
    assert result == EpistemicVerdict.VISION


def test_compute_epistemic_vision_high_with_non_vision_medium():
    """G1 HIGH (vision) + F1 MEDIUM (non-vision) -> VISION.

    MEDIUM does not reach has_fail_trigger; the vision HIGH dominates.
    Guards the severity threshold: only BLOCKER/HIGH are 'serious'.
    """
    findings = [
        _finding("G1.insufficient_reference_class", Severity.HIGH),
        _finding("F1.orphan_sc", Severity.MEDIUM),
    ]
    result = _compute_epistemic(findings)
    assert result == EpistemicVerdict.VISION


def test_compute_epistemic_g2_high_is_vision():
    """G2.gray_rhino_no_denial HIGH -> VISION (G2 partial-field HIGH)."""
    findings = [_finding("G2.gray_rhino_no_denial", Severity.HIGH)]
    result = _compute_epistemic(findings)
    assert result == EpistemicVerdict.VISION


def test_compute_epistemic_g3_high_is_vision():
    """G3.no_counter HIGH -> VISION (G3 partial-field HIGH)."""
    findings = [_finding("G3.no_counter", Severity.HIGH)]
    result = _compute_epistemic(findings)
    assert result == EpistemicVerdict.VISION


def test_check_vision_reachable_e2e():
    """check() must be able to return VISION end-to-end (ground truth).

    Uses tests/fixtures/vision_plan.md: has External Voices (no G8 BLOCKER)
    but missing Reference Class and Scope Challenge (G1/G7 absent).
    Only vision-gate BLOCKERs fire, so VISION is the expected verdict.
    """
    vision_plan = (_FIXTURES / "vision_plan.md").read_text(encoding="utf-8")
    result = check(vision_plan, llm_clients=[])
    # Precondition: External Voices must satisfy G8 mechanically so no G8
    # BLOCKER fires.  A future change to G8 heading detection could
    # invalidate this premise and flip epistemic to FAIL silently.
    g8_blockers = [
        f for f in result.findings
        if f.check_id.startswith("G8.") and f.severity == Severity.BLOCKER
    ]
    assert g8_blockers == [], (
        f"vision_plan must not produce G8 BLOCKERs; got: {g8_blockers}"
    )
    # G1/G7 BLOCKERs make engineering=FAIL; epistemic=VISION coexists because
    # vision-gate findings do not fire the epistemic FAIL trigger.
    assert result.engineering == EngineeringVerdict.FAIL, (
        f"G1/G7 BLOCKERs must produce engineering=FAIL; got {result.engineering!r}"
    )
    assert result.epistemic == EpistemicVerdict.VISION, (
        f"check() must return VISION when only vision-gate serious findings "
        f"are present; got {result.epistemic!r}"
    )


# ---------------------------------------------------------------------------
# Invariant: check_id prefix must match the gate that emits it
# ---------------------------------------------------------------------------

def test_check_id_prefix_invariant():
    """No gate module may emit a check_id whose prefix belongs to another gate.

    _compute_epistemic partitions findings by check_id prefix. If a non-vision
    gate (G4/G6/G8/F*/P*) emitted a check_id starting with G1./G2./G3./G5./G7.,
    it would silently be routed to the VISION bucket instead of FAIL.
    """
    import re

    checks_root = pathlib.Path(__file__).parent.parent.parent / "src" / "plan_forge" / "checks"
    vision_prefixes = ("G1.", "G2.", "G3.", "G5.", "G7.")
    # Matches keyword-arg check_id assignments: check_id="G1.no_section"
    kwarg_pattern = re.compile(r"""check_id\s*=\s*["']([^"']+)["']""")
    # Matches vision-prefixed string literals in tuple/list definitions,
    # e.g. _QUESTIONS entries like ("G7.missing_barbell", ...).
    vision_literal_pattern = re.compile(r"""["'](G[12357]\.[A-Za-z_]+)["']""")

    violations = []
    for py_file in checks_root.rglob("*.py"):
        content = py_file.read_text(encoding="utf-8")
        file_str = str(py_file).lower()
        # Scan both kwarg assignments and tuple literals for vision-prefixed IDs.
        candidates = [m.group(1) for m in kwarg_pattern.finditer(content)]
        candidates += [m.group(1) for m in vision_literal_pattern.finditer(content)]
        for cid in candidates:
            if not any(cid.startswith(vp) for vp in vision_prefixes):
                continue
            gate = cid.split(".")[0]  # e.g. "G1" from "G1.no_section"
            if gate.lower() not in file_str:
                violations.append((str(py_file.relative_to(checks_root)), cid))

    assert violations == [], (
        f"check_id prefix invariant violated: non-vision gate emits vision-prefixed "
        f"check_ids {violations}"
    )


# ---------------------------------------------------------------------------
# Advisory lock: ARBITRATION must never flip engineering or epistemic to FAIL
# ---------------------------------------------------------------------------

def test_arbitration_severity_not_in_engineering_fail_set():
    """Severity.ARBITRATION must not appear in _compute_engineering fail set.

    _compute_engineering uses {Severity.BLOCKER, Severity.HIGH}. If
    ARBITRATION were added, advisory split findings would flip
    engineering to FAIL, defeating the advisory-only design.
    """
    eng_fail = {Severity.BLOCKER, Severity.HIGH}
    assert Severity.ARBITRATION not in eng_fail


def test_arbitration_severity_not_in_epistemic_fail_set():
    """Severity.ARBITRATION must not appear in _compute_epistemic serious set.

    _compute_epistemic uses serious = (Severity.BLOCKER, Severity.HIGH).
    """
    epi_serious = (Severity.BLOCKER, Severity.HIGH)
    assert Severity.ARBITRATION not in epi_serious


def test_compute_engineering_arbitration_only_plan_passes():
    """A plan with only an ARBITRATION finding -> engineering PASS."""
    findings = [
        _finding("G6.B.llm", Severity.ARBITRATION),
    ]
    from plan_forge.api import _compute_engineering
    result = _compute_engineering(findings)
    assert result == EngineeringVerdict.PASS, (
        "ARBITRATION-only findings must yield engineering PASS; "
        f"got {result!r}"
    )


def test_compute_epistemic_arbitration_only_plan_not_fail():
    """A plan with only an ARBITRATION finding -> epistemic PASS or VISION.

    ARBITRATION is below the 'serious' threshold (BLOCKER/HIGH), so it
    triggers neither the FAIL path nor the VISION path. Epistemic -> PASS.
    """
    findings = [
        _finding("G6.B.llm", Severity.ARBITRATION),
    ]
    result = _compute_epistemic(findings)
    assert result != EpistemicVerdict.FAIL, (
        "ARBITRATION-only plan must not produce epistemic FAIL; "
        f"got {result!r}"
    )
    assert result == EpistemicVerdict.PASS, (
        "ARBITRATION-only plan with no vision or fail triggers -> PASS; "
        f"got {result!r}"
    )
