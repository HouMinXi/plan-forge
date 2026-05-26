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


def test_risks_and_mitigations_heading_no_no_risks():
    """'## Risks & Mitigations' with a table -> G2.no_risks must not fire.

    The parser cannot extract bucket-structured risks from a flat table
    without Known/Gray/Black sub-sections, but the heading itself confirms
    the author provided a risks section.  Suppressing G2.no_risks avoids
    a false positive on this common heading variant.
    """
    parsed = _load("g2_risks_and_mitigations.md")
    findings = check(parsed)
    ids = [f.check_id for f in findings]
    assert "G2.no_risks" not in ids, (
        "G2.no_risks must not fire when '## Risks & Mitigations' is present;"
        f" got: {ids}"
    )


def test_risks_and_mitigations_fixture():
    """Fixture-based version: g2_risks_and_mitigations.md -> no G2.no_risks."""
    parsed = _load("g2_risks_and_mitigations.md")
    assert parsed.risks == [], (
        "fixture has no bucket sub-sections; risks should be empty"
    )
    # The section heading exists and must suppress no_risks
    section_headings = list(parsed.sections.keys())
    assert any('risk' in h.lower() for h in section_headings), (
        f"Expected a 'Risks' section heading; got {section_headings}"
    )
    findings = check(parsed)
    assert "G2.no_risks" not in [f.check_id for f in findings]


def test_no_risks_section_still_fires():
    """Teeth: a plan with no heading containing 'Risks' -> G2.no_risks still fires."""
    parsed = parse(
        "# Plan\n\n"
        "## Overview\n\n"
        "No risk discussion here.\n\n"
        "## Design\n\n"
        "Pure design notes without a risks section.\n"
    )
    findings = check(parsed)
    ids = [f.check_id for f in findings]
    assert "G2.no_risks" in ids, (
        f"G2.no_risks must fire when no Risks heading exists; got: {ids}"
    )


def test_prose_risks_word_does_not_count():
    """Scope guard: 'risk' in prose body must not suppress G2.no_risks.

    Only ATX headings are matched; a body paragraph mentioning 'risk' as
    a word does not constitute a Risks section.
    """
    parsed = parse(
        "# Plan\n\n"
        "## Overview\n\n"
        "There is a risk that the schedule slips.\n"
    )
    findings = check(parsed)
    ids = [f.check_id for f in findings]
    assert "G2.no_risks" in ids, (
        "Prose mention of 'risk' must not suppress G2.no_risks; "
        f"got: {ids}"
    )


def test_risks_and_mitigations_english_word_heading():
    """'## Risks and Mitigations' (English 'and') -> G2.no_risks must not fire.

    The substring match on 'risk' in the heading covers both the ampersand
    form ('Risks & Mitigations') and the English-word form ('Risks and
    Mitigations').  This locks the behavior so future regex changes cannot
    silently regress the English-word variant.
    """
    parsed = _load("g2_risks_and_word.md")
    findings = check(parsed)
    ids = [f.check_id for f in findings]
    assert "G2.no_risks" not in ids, (
        "G2.no_risks must not fire when '## Risks and Mitigations' "
        f"is present; got: {ids}"
    )


def test_h1_risk_title_no_h2_fires_no_risks():
    """H1 title containing 'risk' with no ## Risks section -> G2.no_risks fires.

    Before the level filter was added, an H1 like '# Risk Management Plan'
    would match the heading scan and suppress G2.no_risks even though the
    author never added a ## Risks section.  The level >= 2 guard closes
    this gap.
    """
    parsed = parse(
        "# Risk Management Plan\n\n"
        "## Overview\n\n"
        "This plan manages risks at a high level.\n\n"
        "## Timeline\n\n"
        "Q1: design, Q2: build, Q3: ship.\n"
    )
    findings = check(parsed)
    ids = [f.check_id for f in findings]
    assert "G2.no_risks" in ids, (
        "G2.no_risks must fire when only the H1 title contains 'risk' "
        f"and no ## Risks section exists; got: {ids}"
    )
