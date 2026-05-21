"""Unit tests for G2 Risk Taxonomy gate."""
import pathlib

from plan_forge.checks.epistemic.g2_risk_taxonomy import check
from plan_forge.parser import parse
from plan_forge.verdict import Severity

FIXTURES = pathlib.Path(__file__).parent.parent / "fixtures"


def _load(name: str):
    return parse((FIXTURES / name).read_text())


def test_pass_fixture_no_findings():
    """g2_pass.md has all three buckets, denial_reason, survival_plan -> no findings."""
    parsed = _load("g2_pass.md")
    # Verify the parser actually populated parsed.risks (G2 relies on this).
    assert len(parsed.risks) >= 3, (
        "parser did not populate risks from g2_pass.md; "
        "check fixture format matches parser expectations"
    )
    known = [r for r in parsed.risks if r.bucket == "known"]
    gray = [r for r in parsed.risks if r.bucket == "gray_rhino"]
    black = [r for r in parsed.risks if r.bucket == "black_swan"]
    assert len(known) >= 1
    assert len(gray) >= 1
    assert gray[0].denial_reason is not None
    assert len(black) >= 1
    assert black[0].survival_plan is not None

    findings = check(parsed)
    assert findings == []


def test_missing_bucket_blocker():
    """A plan missing a required bucket gets a BLOCKER per missing bucket."""
    md = (
        "## Risks\n\n"
        "### Known Risks\n\n"
        "| Risk | Probability | Impact | Mitigation |\n"
        "|------|-------------|--------|------------|\n"
        "| Schedule slip | High | Medium | Track weekly |\n\n"
        "### Black Swans\n\n"
        "| Black Swan | Survival Plan |\n"
        "|------------|---------------|\n"
        "| Vendor exits | Dual-source |\n"
    )
    parsed = parse(md)
    findings = check(parsed)
    ids = [f.check_id for f in findings]
    assert "G2.missing_gray_rhino" in ids
    for f in findings:
        if f.check_id == "G2.missing_gray_rhino":
            assert f.severity == Severity.BLOCKER


def test_gray_rhino_no_denial_high():
    """Gray Rhino without denial_reason -> HIGH finding."""
    parsed = _load("g2_fail.md")
    findings = check(parsed)
    ids = [f.check_id for f in findings]
    assert "G2.gray_rhino_no_denial" in ids
    for f in findings:
        if f.check_id == "G2.gray_rhino_no_denial":
            assert f.severity == Severity.HIGH


def test_black_swan_no_survival_high():
    """Black Swan without survival_plan -> HIGH finding."""
    md = (
        "## Risks\n\n"
        "### Known Risks\n\n"
        "| Risk | Probability | Impact | Mitigation |\n"
        "|------|-------------|--------|------------|\n"
        "| Scope creep | Medium | High | Scope control |\n\n"
        "### Gray Rhinos\n\n"
        "| Gray Rhino | Denial Reason | Counter |\n"
        "|------------|---------------|---------|\n"
        "| Regulatory shift | Team ignores it | Monitor regs |\n\n"
        "### Black Swans\n\n"
        "| Black Swan | Survival Plan |\n"
        "|------------|---------------|\n"
        "| Key vendor exits | -- |\n"
    )
    parsed = parse(md)
    findings = check(parsed)
    ids = [f.check_id for f in findings]
    assert "G2.black_swan_no_survival" in ids
    for f in findings:
        if f.check_id == "G2.black_swan_no_survival":
            assert f.severity == Severity.HIGH


def test_empty_risks_blocker():
    """Plan with no ## Risks section -> BLOCKER G2.no_risks."""
    parsed = parse("# Plan\n\nNo risks here.\n")
    findings = check(parsed)
    assert len(findings) == 1
    assert findings[0].check_id == "G2.no_risks"
    assert findings[0].severity == Severity.BLOCKER
