"""Integration tests for the five pure-mechanical epistemic gates via run()."""
from __future__ import annotations

from pathlib import Path

from plan_forge.checks.epistemic import run
from plan_forge.parser import parse

_FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"
_MECHANICAL_PREFIXES = ("G1.", "G2.", "G3.", "G5.", "G7.")


def _load(name: str) -> str:
    return (_FIXTURES / name).read_text(encoding="utf-8")


def _mechanical_findings(findings):
    """Filter to only the five mechanical gate findings."""
    return [
        f for f in findings
        if any(f.check_id.startswith(p) for p in _MECHANICAL_PREFIXES)
    ]


def test_run_on_well_formed_plan_no_mechanical_g_findings():
    """pass_well_formed.md satisfies G1/G2/G3/G5/G7 -> no mechanical findings."""
    parsed = parse(_load("pass_well_formed.md"))
    findings = run(parsed, llm_clients=[])
    mech = _mechanical_findings(findings)
    assert mech == [], (
        f"Expected no G1/G2/G3/G5/G7 findings; got: "
        f"{[(f.check_id, f.message) for f in mech]}"
    )


def test_run_on_empty_plan_all_sections_missing():
    """Minimal plan missing all sections -> one no_section BLOCKER per gate."""
    parsed = parse("# Minimal Plan\n\nNo epistemic sections here.\n")
    findings = run(parsed, llm_clients=[])
    mech = _mechanical_findings(findings)

    ids = [f.check_id for f in mech]
    expected = [
        "G1.no_section",
        "G2.no_risks",
        "G3.no_section",
        "G5.no_section",
        "G7.no_section",
    ]
    for expected_id in expected:
        assert expected_id in ids, (
            f"Expected {expected_id} in mechanical findings; got: {ids}"
        )

    from plan_forge.verdict import Severity
    for f in mech:
        if f.check_id in expected:
            assert f.severity == Severity.BLOCKER


def test_run_passes_empty_llm_clients():
    """Calling run() with empty llm_clients does not crash the mechanical gates."""
    parsed = parse("# Plan\n\nNo content.\n")
    findings = run(parsed, llm_clients=[])
    # Mechanical gates fire; no exception raised.
    mech = _mechanical_findings(findings)
    assert len(mech) >= 5
