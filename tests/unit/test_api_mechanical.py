"""Unit tests for api.check_mechanical() and _compute_engineering()."""
import pathlib

from plan_forge.api import check_mechanical, _compute_engineering, check
from plan_forge.verdict import (
    Verdict,
    EngineeringVerdict,
    EpistemicVerdict,
    Severity,
    Finding,
)

_FIXTURES = pathlib.Path(__file__).parent.parent / "fixtures"


def _load(name: str) -> str:
    return (_FIXTURES / name).read_text(encoding="utf-8")


def _make_finding(severity: Severity) -> Finding:
    """Helper: construct a minimal Finding with the given severity."""
    return Finding(
        check_id="test.dummy",
        severity=severity,
        location="test:1",
        message="dummy finding for unit test",
    )


# ---------------------------------------------------------------------------
# Test 1: empty plan returns a valid Verdict
# ---------------------------------------------------------------------------

def test_check_mechanical_empty_plan():
    """Empty string input must return a Verdict (not raise).

    Engineering must be PASS (no HIGH/BLOCKER findings from empty input).
    Epistemic must be VISION (D3 contract).
    Findings may be empty or contain trivial F-layer findings; structure
    is asserted, not contents.
    """
    result = check_mechanical("")
    assert isinstance(result, Verdict)
    assert result.engineering == EngineeringVerdict.PASS
    assert result.epistemic == EpistemicVerdict.VISION
    assert isinstance(result.findings, list)


# ---------------------------------------------------------------------------
# Test 2: return type and finding element types
# ---------------------------------------------------------------------------

def test_check_mechanical_returns_verdict_type():
    """Non-empty plan: result is Verdict; findings is list of Finding."""
    result = check_mechanical("# My Plan\n\nSome prose.\n")
    assert isinstance(result, Verdict), "check_mechanical must return a Verdict"
    assert isinstance(result.findings, list), "Verdict.findings must be a list"
    for item in result.findings:
        assert isinstance(item, Finding), (
            f"each element in findings must be Finding, got {type(item)}"
        )


# ---------------------------------------------------------------------------
# Test 3: epistemic is always VISION regardless of input
# ---------------------------------------------------------------------------

def test_check_mechanical_epistemic_always_vision():
    """D3 contract: epistemic == VISION for all inputs in mechanical-only mode.

    Three inputs tested: empty / clean pass fixture / fail fixture with
    non-ASCII (f7_fail.md).  All must return VISION.
    """
    inputs = [
        "",
        _load("f5_pass.md"),
        _load("f7_fail.md"),
    ]
    for plan_text in inputs:
        result = check_mechanical(plan_text)
        assert result.epistemic == EpistemicVerdict.VISION, (
            f"epistemic must always be VISION; got {result.epistemic!r} "
            f"for input starting with {plan_text[:40]!r}"
        )


# ---------------------------------------------------------------------------
# Test 4: engineering PASS on clean input (f5_pass.md)
# ---------------------------------------------------------------------------

def test_check_mechanical_engineering_pass_on_clean_input():
    """f5_pass.md contains no F1-F7/PBR findings at HIGH/BLOCKER level.

    F5 pass fixture has valid SC rows with at most 2 R-tags each; it is
    the minimal clean fixture most likely to avoid triggering any HIGH
    finding.  Engineering must be PASS.
    """
    result = check_mechanical(_load("f5_pass.md"))
    assert result.engineering == EngineeringVerdict.PASS, (
        f"expected PASS on f5_pass.md; findings: {result.findings}"
    )


# ---------------------------------------------------------------------------
# Test 5: engineering FAIL on input with HIGH finding (f7_fail.md)
# ---------------------------------------------------------------------------

def test_check_mechanical_engineering_fail_on_high_finding():
    """f7_fail.md contains intentional non-ASCII characters.

    F7 emits HIGH severity findings for each non-ASCII byte found.
    D2 contract: any HIGH finding must flip engineering to FAIL.
    """
    result = check_mechanical(_load("f7_fail.md"))
    high_ids = [
        f.check_id for f in result.findings
        if f.severity in (Severity.HIGH, Severity.BLOCKER)
    ]
    assert high_ids, "f7_fail.md must produce at least one HIGH/BLOCKER finding"
    assert result.engineering == EngineeringVerdict.FAIL, (
        f"expected FAIL when HIGH findings present; engineering={result.engineering!r}"
    )


# ---------------------------------------------------------------------------
# Test 6: preamble kwarg is passed through to F6
# ---------------------------------------------------------------------------

def test_check_mechanical_preamble_kwarg_passed_through():
    """Preamble containing a sentence absent from the plan body triggers F6.

    The preamble must propagate from check_mechanical() through
    mechanical.run() to f6_preamble_body.check(); if the plumbing is
    broken, F6.preamble_only_fact will never appear.

    Plan body has no mention of the preamble sentence; F6 must flag it.
    F6 severity is LOW, so engineering may still be PASS here -- the
    test only verifies the plumbing, not the engineering verdict.
    """
    plan = "# Simple Plan\n\nThis plan does not mention the unique preamble fact.\n"
    preamble = (
        "The team has already completed a six-month discovery phase "
        "which produced 47 prototypes and three validated product hypotheses."
    )
    result = check_mechanical(plan, preamble=preamble)
    ids = [f.check_id for f in result.findings]
    # F6.preamble_only_fact: emitted by f6_preamble_body when a preamble
    # sentence has no match in the plan body.
    assert "F6.preamble_only_fact" in ids, (
        f"F6.preamble_only_fact expected when preamble has unique fact; got: {ids}"
    )


# ---------------------------------------------------------------------------
# Test 7: _compute_engineering rule (direct unit test)
# ---------------------------------------------------------------------------

def test_compute_engineering_rule():
    """Six sub-assertions for the D2 engineering verdict rule.

    FAIL iff any finding has severity BLOCKER or HIGH; MEDIUM and LOW do not trigger FAIL.
    MEDIUM and LOW are informational; they must NOT flip engineering.
    """
    # Sub-assertion 1: empty list -> PASS
    assert _compute_engineering([]) == EngineeringVerdict.PASS, (
        "empty findings list must yield PASS"
    )

    # Sub-assertion 2: one LOW -> PASS
    assert _compute_engineering([_make_finding(Severity.LOW)]) == EngineeringVerdict.PASS, (
        "single LOW finding must yield PASS"
    )

    # Sub-assertion 3: one HIGH -> FAIL
    assert _compute_engineering([_make_finding(Severity.HIGH)]) == EngineeringVerdict.FAIL, (
        "single HIGH finding must yield FAIL"
    )

    # Sub-assertion 4: one BLOCKER -> FAIL
    assert _compute_engineering([_make_finding(Severity.BLOCKER)]) == EngineeringVerdict.FAIL, (
        "single BLOCKER finding must yield FAIL"
    )

    # Sub-assertion 5: mix of LOW + HIGH -> FAIL (HIGH dominates)
    mixed_low_high = [_make_finding(Severity.LOW), _make_finding(Severity.HIGH)]
    assert _compute_engineering(mixed_low_high) == EngineeringVerdict.FAIL, (
        "LOW + HIGH mix must yield FAIL"
    )

    # Sub-assertion 6: mix of LOW + MEDIUM only -> PASS (MEDIUM does not trigger)
    mixed_low_medium = [_make_finding(Severity.LOW), _make_finding(Severity.MEDIUM)]
    assert _compute_engineering(mixed_low_medium) == EngineeringVerdict.PASS, (
        "LOW + MEDIUM mix must yield PASS; MEDIUM is informational per D2"
    )


# ---------------------------------------------------------------------------
# Verify check() and scaffold() are fully implemented (not stubs)
# ---------------------------------------------------------------------------

def test_check_returns_verdict():
    """check() must return a Verdict (not raise NotImplementedError).

    Mechanical-only mode (llm_clients=[]) avoids network calls in this test.
    """
    result = check("# Any plan", llm_clients=[])
    assert isinstance(result, Verdict)
    assert result.engineering in (EngineeringVerdict.PASS, EngineeringVerdict.FAIL)
    assert result.epistemic in (
        EpistemicVerdict.PASS, EpistemicVerdict.FAIL, EpistemicVerdict.VISION
    )


def test_scaffold_is_implemented(tmp_path):
    """scaffold() is fully implemented; calling it must not raise."""
    from plan_forge.api import scaffold as _scaffold
    result = _scaffold("impl-check", tmp_path)
    assert result.exists()
