"""Unit tests for F5: R-tag pruner check."""
import pathlib

from plan_forge.parser import parse
from plan_forge.checks.mechanical import f5_r_tag_pruner
from plan_forge.verdict import Severity

_FIXTURES = pathlib.Path(__file__).parent.parent / "fixtures"


def _load(name: str) -> str:
    return (_FIXTURES / name).read_text(encoding="utf-8")


def test_f5_pass_fixture():
    """Pass fixture: no F5 findings (all SCs have <= 2 R-tags)."""
    parsed = parse(_load("f5_pass.md"))
    findings = f5_r_tag_pruner.check(parsed)
    assert findings == [], f"Expected no findings, got: {findings}"


def test_f5_fail_fixture():
    """Fail fixture: at least one F5.r_tag_overflow finding expected."""
    parsed = parse(_load("f5_fail.md"))
    findings = f5_r_tag_pruner.check(parsed)
    ids = [f.check_id for f in findings]
    assert "F5.r_tag_overflow" in ids, (
        f"Expected F5.r_tag_overflow, got: {ids}"
    )


def test_f5_severity():
    """All F5 findings must be LOW severity."""
    parsed = parse(_load("f5_fail.md"))
    findings = f5_r_tag_pruner.check(parsed)
    assert findings, "Need at least one finding to check severity"
    for f in findings:
        assert f.severity == Severity.LOW, (
            f"Expected LOW severity, got {f.severity} for {f.check_id}"
        )


def test_f5_edge_exactly_two_tags():
    """Edge case: SC with exactly 2 R-tags -> NO finding."""
    md = (
        "# Plan\n"
        "\n"
        "## SC Table\n"
        "\n"
        "| SC | Criterion | Body |\n"
        "|----|-----------|------|\n"
        "| SC-1 | Parsing | Must handle all inputs. R1 H1 R2 M3 |\n"
        "| SC-2 | Coverage | Must hit 90 percent. R3 L1 R4 B2 R5 H2 |\n"
    )
    parsed = parse(md)
    findings = f5_r_tag_pruner.check(parsed)
    # SC-1 has exactly 2 R-tags -> no finding
    sc1_findings = [f for f in findings if "SC-1" in f.location]
    assert not sc1_findings, (
        f"SC-1 with 2 tags should have no finding, got: {sc1_findings}"
    )
    # SC-2 has 3 R-tags -> finding
    sc2_findings = [f for f in findings if "SC-2" in f.location]
    assert sc2_findings, "SC-2 with 3 R-tags should produce a finding"
