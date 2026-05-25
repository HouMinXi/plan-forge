"""Unit tests for G7 Scope Challenge gate."""
import pathlib

from plan_forge.checks.epistemic.g7_scope_challenge import check
from plan_forge.parser import parse
from plan_forge.verdict import Severity

FIXTURES = pathlib.Path(__file__).parent.parent / "fixtures"


def _load(name: str):
    return parse((FIXTURES / name).read_text())


def test_pass():
    """g7_pass.md answers all four questions -> no findings."""
    findings = check(_load("g7_pass.md"))
    assert findings == []


def test_absent_blocker():
    """Plan with no Scope Challenge section -> BLOCKER G7.no_section."""
    parsed = parse("# Plan\n\nNo scope challenge here.\n")
    findings = check(parsed)
    assert len(findings) == 1
    assert findings[0].check_id == "G7.no_section"
    assert findings[0].severity == Severity.BLOCKER


def test_missing_necessity_high():
    """Section missing necessity keywords -> HIGH G7.missing_necessity."""
    md = (
        "## Scope Challenge\n\n"
        "Consumer: data team.\n"
        "Do-nothing cost: 2 days per week.\n"
        "Barbell option: minimal vs full platform.\n"
    )
    parsed = parse(md)
    findings = check(parsed)
    ids = [f.check_id for f in findings]
    assert "G7.missing_necessity" in ids
    for f in findings:
        if f.check_id == "G7.missing_necessity":
            assert f.severity == Severity.HIGH


def test_missing_consumers_high():
    """Section missing consumers keywords -> HIGH G7.missing_consumers."""
    md = (
        "## Scope Challenge\n\n"
        "Why this exists: critical customer pain point.\n"
        "Do-nothing cost: 2 days per week.\n"
        "Barbell option: minimal vs full platform.\n"
    )
    parsed = parse(md)
    findings = check(parsed)
    ids = [f.check_id for f in findings]
    assert "G7.missing_consumers" in ids
    for f in findings:
        if f.check_id == "G7.missing_consumers":
            assert f.severity == Severity.HIGH


def test_missing_donothing_high():
    """Section missing do-nothing cost keywords -> HIGH G7.missing_donothing_cost."""
    md = (
        "## Scope Challenge\n\n"
        "Does this need to exist? Yes, critical need.\n"
        "Consumers: data team, reporting service, partner API.\n"
        "Barbell option: minimal vs full platform.\n"
    )
    parsed = parse(md)
    findings = check(parsed)
    ids = [f.check_id for f in findings]
    assert "G7.missing_donothing_cost" in ids
    for f in findings:
        if f.check_id == "G7.missing_donothing_cost":
            assert f.severity == Severity.HIGH


def test_missing_barbell_high():
    """g7_fail.md missing barbell discussion -> HIGH G7.missing_barbell."""
    findings = check(_load("g7_fail.md"))
    ids = [f.check_id for f in findings]
    assert "G7.missing_barbell" in ids
    for f in findings:
        if f.check_id == "G7.missing_barbell":
            assert f.severity == Severity.HIGH


def test_all_four_questions_answered():
    """All keyword groups present -> no findings."""
    md = (
        "## Scope Challenge\n\n"
        "Need to exist: yes, addresses critical pain.\n"
        "Consumer: data team, reporting service, partner API.\n"
        "Do-nothing cost: 2 engineer-days per week wasted.\n"
        "Barbell: either minimal (1 week) or full platform (6 months).\n"
    )
    parsed = parse(md)
    findings = check(parsed)
    assert findings == []


def test_fp_headings_only():
    """Q1 and Q2 answered only via subsection heading text -> no G7 findings.

    FP fixture: Q1 keyword ('does this need') and Q2 keyword ('consumer')
    appear only in '### Qn:' heading lines, not in body prose.  Before the
    fix the parser excluded heading lines from section.body, causing Q1 and
    Q2 to read as unaddressed even though the headings answered them.
    Q3 and Q4 also have body prose that satisfies their keywords.
    """
    findings = check(_load("g7_fp_headings_only.md"))
    assert findings == [], (
        f"unexpected findings on heading-only fixture: {findings}"
    )


def test_tp_missing_consumers():
    """Scope Challenge that omits consumers question -> G7.missing_consumers.

    TP fixture: Q2 heading and 'consumer'/'demand signal' are both absent;
    the fix must not suppress this real defect.
    """
    findings = check(_load("g7_tp_missing_consumers.md"))
    ids = [f.check_id for f in findings]
    assert "G7.missing_consumers" in ids
    for f in findings:
        if f.check_id == "G7.missing_consumers":
            assert f.severity == Severity.HIGH
