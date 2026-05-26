"""Unit tests for F8: plan consistency check."""
import pathlib

from plan_forge.parser import parse
from plan_forge.checks.mechanical import f8_plan_consistency
from plan_forge.verdict import Severity

_FIXTURES = pathlib.Path(__file__).parent.parent / "fixtures"


def _load(name: str) -> str:
    return (_FIXTURES / name).read_text(encoding="utf-8")


# TP fixture: claim + mock-only evidence -> must fire

def test_tp_claim_mock_evidence_fires():
    """TP: plan with real-world claim and mock-only tests must fire."""
    parsed = parse(_load("f8_claim_mock_evidence.md"))
    findings = f8_plan_consistency.check(parsed)
    ids = [f.check_id for f in findings]
    assert "F8.A.unsupported_capability_claim" in ids, (
        f"Expected F8.A finding, got: {ids}"
    )


def test_tp_severity_is_high():
    """TP: F8.A findings must be HIGH severity."""
    parsed = parse(_load("f8_claim_mock_evidence.md"))
    findings = f8_plan_consistency.check(parsed)
    assert findings, "Need at least one finding to verify severity"
    for f in findings:
        assert f.severity == Severity.HIGH, (
            f"Expected HIGH, got {f.severity} in {f.check_id}"
        )


def test_tp_finding_contains_fix_hint():
    """TP: F8.A finding must carry a non-empty fix_hint."""
    parsed = parse(_load("f8_claim_mock_evidence.md"))
    findings = [
        f for f in f8_plan_consistency.check(parsed)
        if f.check_id == "F8.A.unsupported_capability_claim"
    ]
    assert findings, "Need at least one F8.A finding"
    for f in findings:
        assert f.fix_hint, f"fix_hint must not be empty, got: {f.fix_hint!r}"


# FP fixtures: must all produce ZERO F8 findings

def test_fp_clean_plan():
    """FP: plan with no capability claims -> no findings."""
    parsed = parse(_load("f8_clean_plan.md"))
    findings = f8_plan_consistency.check(parsed)
    assert findings == [], f"Expected no findings, got: {findings}"


def test_fp_claim_with_real_evidence():
    """FP: plan claims real-world effect but evidence section uses real data."""
    parsed = parse(_load("f8_claim_real_evidence.md"))
    findings = f8_plan_consistency.check(parsed)
    assert findings == [], (
        f"Claim + real evidence must NOT fire, got: {findings}"
    )


def test_fp_no_evidence_section():
    """FP: plan has claim but no evidence section -> no findings."""
    parsed = parse(_load("f8_no_evidence_section.md"))
    findings = f8_plan_consistency.check(parsed)
    assert findings == [], (
        f"Claim + no evidence section must NOT fire, got: {findings}"
    )


def test_fp_no_claim_mock_evidence():
    """FP: plan has mock evidence but no capability claim -> no findings."""
    parsed = parse(_load("f8_no_claim_mock_evidence.md"))
    findings = f8_plan_consistency.check(parsed)
    assert findings == [], (
        f"Mock evidence without claim must NOT fire, got: {findings}"
    )


def test_fp_claim_inside_code_block():
    """FP: claim keyword inside fenced code block must NOT trigger."""
    parsed = parse(_load("f8_claim_in_code_block.md"))
    findings = f8_plan_consistency.check(parsed)
    assert findings == [], (
        f"Claim in code block must NOT fire, got: {findings}"
    )


# Inline edge-case tests (no fixture files)

def test_empty_plan_no_findings():
    """Edge: empty plan -> no findings."""
    parsed = parse("")
    findings = f8_plan_consistency.check(parsed)
    assert findings == [], f"Empty plan must produce no findings, got: {findings}"


def test_for_example_exemption():
    """FP: 'for example' in evidence section must not count as a mock token."""
    md = (
        "# Plan\n\n"
        "## Overview\n\n"
        "This check catches real bugs in production code.\n\n"
        "## Tests\n\n"
        "Each assertion is against real data; for example, the\n"
        "corpus includes 50 actual plan documents.\n"
    )
    parsed = parse(md)
    findings = f8_plan_consistency.check(parsed)
    assert findings == [], (
        f"'for example' should be exempt, got: {findings}"
    )


def test_claim_in_both_claim_and_evidence():
    """TP: 'catches real bugs' in overview + mock in tests -> fires."""
    md = (
        "# Plan\n\n"
        "## Overview\n\n"
        "The tool catches real bugs by inspecting the AST.\n\n"
        "## Tests\n\n"
        "- Passes a stub ParsedPlan to the check.\n"
        "- Uses a mock parser that returns synthetic results.\n"
    )
    parsed = parse(md)
    findings = f8_plan_consistency.check(parsed)
    ids = [f.check_id for f in findings]
    assert "F8.A.unsupported_capability_claim" in ids, (
        f"Expected F8.A finding, got: {ids}"
    )


def test_guard_is_load_bearing():
    """Teeth: confirm the real-evidence guard is not a no-op.

    A plan with capability claims and ONLY mock/stub evidence must fire.
    A plan with capability claims and real/production evidence must NOT.
    If the guard were absent, both would fire -- only one should.
    """
    # This plan claims real-world effect and has ONLY mock evidence.
    # It MUST fire.
    tp_text = (
        "# Plan\n\n"
        "## Overview\n\n"
        "The tool catches real bugs by inspecting the AST.\n\n"
        "## Tests\n\n"
        "- Uses a mock parser returning stub results.\n"
        "- All inputs are synthetic strings constructed inline.\n"
    )
    parsed_tp = parse(tp_text)
    findings_tp = f8_plan_consistency.check(parsed_tp)
    ids_tp = [f.check_id for f in findings_tp]
    assert "F8.A.unsupported_capability_claim" in ids_tp, (
        "Claim + mock-only evidence must fire -- guard failure. "
        f"Got: {ids_tp}"
    )

    # This plan claims real-world effect but has real-data evidence.
    # It must NOT fire (the guard suppresses it).
    fp_text = (
        "# Plan\n\n"
        "## Overview\n\n"
        "The tool catches real bugs by inspecting the AST.\n\n"
        "## Tests\n\n"
        "- Runs against a live production codebase.\n"
        "- Results verified against actual output.\n"
    )
    parsed_fp = parse(fp_text)
    findings_fp = f8_plan_consistency.check(parsed_fp)
    assert findings_fp == [], (
        "Claim + real evidence must NOT fire -- guard is load-bearing. "
        f"Got: {findings_fp}"
    )
