"""Unit tests for Verdict.summary() -- output format and finding counts."""
from __future__ import annotations

from plan_forge.verdict import (
    EngineeringVerdict,
    EpistemicVerdict,
    Finding,
    Severity,
    Verdict,
)


def _finding(check_id: str, severity: Severity) -> Finding:
    """Build a minimal Finding for unit tests."""
    return Finding(
        check_id=check_id,
        severity=severity,
        location="test:1",
        message="unit test finding",
    )


def test_summary_format_pass_verdict():
    """summary() on PASS/PASS Verdict with no findings produces expected lines."""
    v = Verdict(
        engineering=EngineeringVerdict.PASS,
        epistemic=EpistemicVerdict.PASS,
    )
    result = v.summary()
    assert "Engineering: PASS" in result
    assert "Epistemic: PASS" in result
    assert "Findings: 0 total" in result
    assert "BLOCKER: 0" in result
    assert "HIGH: 0" in result
    assert "MEDIUM: 0" in result
    assert "LOW: 0" in result
    # No LLM providers line when active_providers is empty
    assert "LLM providers:" not in result


def test_summary_format_fail_verdict_with_findings():
    """summary() counts findings by severity correctly."""
    findings = [
        _finding("F1.orphan_sc", Severity.BLOCKER),
        _finding("G1.no_section", Severity.BLOCKER),
        _finding("F2.duplicate_fact", Severity.HIGH),
        _finding("G4.A.mechanical", Severity.MEDIUM),
        _finding("G4.A.mechanical", Severity.LOW),
        _finding("G4.A.mechanical", Severity.LOW),
    ]
    v = Verdict(
        engineering=EngineeringVerdict.FAIL,
        epistemic=EpistemicVerdict.FAIL,
        findings=findings,
    )
    result = v.summary()
    assert "Engineering: FAIL" in result
    assert "Epistemic: FAIL" in result
    assert "Findings: 6 total" in result
    assert "BLOCKER: 2" in result
    assert "HIGH: 1" in result
    assert "MEDIUM: 1" in result
    assert "LOW: 2" in result


def test_summary_includes_llm_providers_when_set():
    """summary() appends LLM providers line when active_providers is non-empty."""
    v = Verdict(
        engineering=EngineeringVerdict.PASS,
        epistemic=EpistemicVerdict.PASS,
        active_providers=["anthropic", "kimi"],
    )
    result = v.summary()
    assert "LLM providers: anthropic, kimi" in result


def test_summary_omits_llm_providers_when_empty():
    """summary() omits LLM providers line when active_providers is empty list."""
    v = Verdict(
        engineering=EngineeringVerdict.PASS,
        epistemic=EpistemicVerdict.PASS,
        active_providers=[],
    )
    result = v.summary()
    assert "LLM providers:" not in result


def test_summary_vision_verdict():
    """summary() handles VISION epistemic verdict correctly."""
    v = Verdict(
        engineering=EngineeringVerdict.PASS,
        epistemic=EpistemicVerdict.VISION,
        findings=[_finding("G1.no_section", Severity.BLOCKER)],
    )
    result = v.summary()
    assert "Epistemic: VISION" in result
    assert "BLOCKER: 1" in result


def test_summary_returns_string():
    """summary() return type is str."""
    v = Verdict(
        engineering=EngineeringVerdict.PASS,
        epistemic=EpistemicVerdict.PASS,
    )
    assert isinstance(v.summary(), str)


def test_summary_multiline():
    """summary() returns a multi-line string (newline-separated)."""
    v = Verdict(
        engineering=EngineeringVerdict.PASS,
        epistemic=EpistemicVerdict.PASS,
    )
    lines = v.summary().split("\n")
    # Minimum 7 lines: Engineering, Epistemic, Findings total, 4 severity lines
    assert len(lines) >= 7
