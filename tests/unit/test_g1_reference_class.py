"""Unit tests for G1 Reference Class gate."""
import pathlib

from plan_forge.checks.epistemic.g1_reference_class import check
from plan_forge.parser import parse
from plan_forge.verdict import Severity

FIXTURES = pathlib.Path(__file__).parent.parent / "fixtures"


def _load(name: str):
    return parse((FIXTURES / name).read_text())


def test_pass():
    """g1_pass.md has >= 2 ratio lines -> no findings."""
    findings = check(_load("g1_pass.md"))
    assert findings == []


def test_absent_section_blocker():
    """Plan with no ## Reference Class section -> BLOCKER G1.no_section."""
    parsed = parse("# Plan\n\nIntroduction text.\n")
    findings = check(parsed)
    assert len(findings) == 1
    assert findings[0].check_id == "G1.no_section"
    assert findings[0].severity == Severity.BLOCKER


def test_insufficient_projects_blocker():
    """g1_fail.md has only 1 ratio line -> BLOCKER G1.insufficient_reference_class."""
    findings = check(_load("g1_fail.md"))
    ids = [f.check_id for f in findings]
    assert "G1.insufficient_reference_class" in ids
    for f in findings:
        if f.check_id == "G1.insufficient_reference_class":
            assert f.severity == Severity.BLOCKER
            assert "1 project" in f.message


def test_ratio_regex_variants():
    """Ratio detection handles 1.5x, 3X, 'ratio 2.0' variants."""
    md = (
        "## Reference Class\n\n"
        "- Project Alpha: ran 1.5x over plan.\n"
        "- Project Beta: ratio 2.0 vs original estimate.\n"
        "- Project Gamma: overran by 3X.\n"
    )
    parsed = parse(md)
    findings = check(parsed)
    assert findings == []


def test_zero_ratio_lines_blocker():
    """Section present but no ratio lines -> insufficient (0 projects)."""
    md = (
        "## Reference Class\n\n"
        "We looked at several projects but did not record ratios.\n"
    )
    parsed = parse(md)
    findings = check(parsed)
    assert any(f.check_id == "G1.insufficient_reference_class"
               for f in findings)
