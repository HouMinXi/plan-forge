"""Unit tests for F1: SC-test traceability check."""
import pathlib

from plan_forge.parser import parse
from plan_forge.checks.mechanical import f1_sc_traceability
from plan_forge.verdict import Severity

_FIXTURES = pathlib.Path(__file__).parent.parent / "fixtures"


def _load(name: str) -> str:
    return (_FIXTURES / name).read_text(encoding="utf-8")


def test_f1_pass_fixture():
    """Pass fixture: no F1 findings expected."""
    parsed = parse(_load("f1_pass.md"))
    findings = f1_sc_traceability.check(parsed)
    assert findings == [], f"Expected no findings, got: {findings}"


def test_f1_fail_fixture():
    """Fail fixture: at least one F1.orphan_sc finding expected."""
    parsed = parse(_load("f1_fail.md"))
    findings = f1_sc_traceability.check(parsed)
    ids = [f.check_id for f in findings]
    assert "F1.orphan_sc" in ids, f"Expected F1.orphan_sc, got: {ids}"


def test_f1_severity():
    """All F1 findings must be HIGH severity."""
    parsed = parse(_load("f1_fail.md"))
    findings = f1_sc_traceability.check(parsed)
    assert findings, "Need at least one finding to check severity"
    for f in findings:
        assert f.severity == Severity.HIGH, (
            f"Expected HIGH severity, got {f.severity} for {f.check_id}"
        )


def test_f1_edge_single_side_only():
    """Edge case: only one side present -> NO findings (absence-of-test-section
    is G3/G7 territory, not F1; empty SC table is also out of F1 scope).
    """
    # SC table claims a test, but no test section exists
    md_no_test_section = (
        "# Plan\n"
        "\n"
        "## SC Table\n"
        "\n"
        "| SC | Criterion | Body |\n"
        "|----|-----------|------|\n"
        "| SC-1 | Check A | Verified by test_missing_func |\n"
    )
    parsed = parse(md_no_test_section)
    findings = f1_sc_traceability.check(parsed)
    assert findings == [], (
        f"No test section -> no F1 findings (G3/G7 territory), got: {findings}"
    )

    # Test section exists, but no SC table
    md_no_sc_table = (
        "# Plan\n"
        "\n"
        "## Test Plan\n"
        "\n"
        "- test_orphan_func: has no SC referencing it\n"
    )
    parsed2 = parse(md_no_sc_table)
    findings2 = f1_sc_traceability.check(parsed2)
    assert findings2 == [], (
        f"Empty SC table -> no F1 findings (G3/G7 territory), got: {findings2}"
    )


def test_f1_edge_orphan_both():
    """Edge case: plan with orphan SC and orphan test in same plan.

    Both F1.orphan_sc and F1.orphan_test should appear in one call.
    """
    md = (
        "# Edge Plan\n"
        "\n"
        "## SC Table\n"
        "\n"
        "| SC | Criterion | Body |\n"
        "|----|-----------|------|\n"
        "| SC-1 | Check A | Verified by test_undefined_func |\n"
        "\n"
        "## Test Plan\n"
        "\n"
        "- test_orphan_test_func: has no SC referencing it\n"
    )
    parsed = parse(md)
    findings = f1_sc_traceability.check(parsed)
    ids = [f.check_id for f in findings]
    assert "F1.orphan_sc" in ids, f"Expected F1.orphan_sc in {ids}"
    assert "F1.orphan_test" in ids, f"Expected F1.orphan_test in {ids}"
