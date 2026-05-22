"""Unit tests for P6: Metadata currency check."""
import pathlib

from plan_forge.parser import parse
from plan_forge.checks.pbr import p6_metadata_currency
from plan_forge.checks import pbr
from plan_forge.verdict import Severity
from plan_forge import api

_FIXTURES = pathlib.Path(__file__).parent.parent / "fixtures"


def _load(name: str) -> str:
    return (_FIXTURES / name).read_text(encoding="utf-8")


def test_pass_current_metadata():
    """Pass fixture: frontmatter date covers in-body work -> 0 findings."""
    parsed = parse(_load("p6_pass.md"))
    findings = p6_metadata_currency.check(parsed)
    p6 = [f for f in findings if f.check_id == "P6.metadata_contradicts_body"]
    assert p6 == [], f"Expected no P6 findings, got: {p6}"


def test_fail_misstated_provenance():
    """Fail fixture: fm 2026-05-18, body 'integrated 2026-05-19' -> 1 HIGH finding."""
    parsed = parse(_load("p6_fail.md"))
    findings = p6_metadata_currency.check(parsed)
    p6 = [f for f in findings if f.check_id == "P6.metadata_contradicts_body"]
    assert len(p6) == 1, f"Expected exactly 1 P6 finding, got: {p6}"
    f = p6[0]
    assert f.severity == Severity.HIGH, f"Expected HIGH severity, got {f.severity}"
    # Location must point at the frontmatter date line, not the body line
    assert f.location.startswith("line:"), f"Expected line: location, got {f.location!r}"
    lineno = int(f.location.split(":")[1])
    # Frontmatter date line is line 3 in p6_fail.md (**Drafted**: 2026-05-18)
    assert lineno == 3, f"Expected location line 3 (fm date), got {lineno}"


def test_p6_severity_is_high():
    """All P6 findings must be HIGH severity."""
    parsed = parse(_load("p6_fail.md"))
    findings = p6_metadata_currency.check(parsed)
    p6 = [f for f in findings if f.check_id == "P6.metadata_contradicts_body"]
    assert p6, "Need at least one finding to check severity"
    for f in p6:
        assert f.severity == Severity.HIGH, (
            f"Expected HIGH severity, got {f.severity}"
        )


def test_pass_no_frontmatter():
    """Plan with no metadata keys -> 0 findings (scaffold case)."""
    md = (
        "# Plan\n\n"
        "## Overview\n\n"
        "R1 fixes integrated 2026-05-19.\n"
    )
    parsed = parse(md)
    findings = p6_metadata_currency.check(parsed)
    p6 = [f for f in findings if f.check_id == "P6.metadata_contradicts_body"]
    assert p6 == [], f"Expected no P6 findings for no-frontmatter plan, got: {p6}"


def test_pass_verbose_update_dates():
    """Frontmatter listing multiple dates: MAX clears the body claim.

    Verbose honest dating is never penalized: listing 2026-05-19 in
    frontmatter alongside 2026-05-18 means fm_latest = 05-19, which
    matches the body currency date -> no finding.
    """
    md = (
        "# Plan\n\n"
        "**Drafted**: 2026-05-18; R1 2026-05-19\n\n"
        "## Implementation\n\n"
        "R1 fixes integrated 2026-05-19.\n"
    )
    parsed = parse(md)
    findings = p6_metadata_currency.check(parsed)
    p6 = [f for f in findings if f.check_id == "P6.metadata_contradicts_body"]
    assert p6 == [], (
        f"Verbose update dates should be tolerated (MAX clears check), got: {p6}"
    )


def test_pass_imprecise_date():
    """Frontmatter with no exact YYYY-MM-DD (e.g. 'mid-May 2026') -> 0 findings."""
    md = (
        "# Plan\n\n"
        "**Drafted**: mid-May 2026\n\n"
        "## Implementation\n\n"
        "R1 fixes integrated 2026-05-19.\n"
    )
    parsed = parse(md)
    findings = p6_metadata_currency.check(parsed)
    p6 = [f for f in findings if f.check_id == "P6.metadata_contradicts_body"]
    assert p6 == [], (
        f"Imprecise date (no YYYY-MM-DD) should be tolerated, got: {p6}"
    )


def test_bare_body_date_ignored():
    """Body date with NO nearby currency keyword -> 0 findings (no FP)."""
    md = (
        "# Plan\n\n"
        "**Drafted**: 2026-05-18\n\n"
        "## Overview\n\n"
        "Target completion by 2030-01-01.\n"
    )
    parsed = parse(md)
    findings = p6_metadata_currency.check(parsed)
    p6 = [f for f in findings if f.check_id == "P6.metadata_contradicts_body"]
    assert p6 == [], (
        f"Bare body date without currency keyword should not fire, got: {p6}"
    )


def test_p6_ok_suppresses():
    """p6-ok marker in frontmatter region suppresses all P6 findings."""
    md = (
        "# Plan\n\n"
        "**Drafted**: 2026-05-18\n"
        "<!-- plan-forge: p6-ok body date is retrospective documentation -->\n\n"
        "## Implementation\n\n"
        "R1 fixes integrated 2026-05-19.\n"
    )
    parsed = parse(md)
    findings = p6_metadata_currency.check(parsed)
    p6 = [f for f in findings if f.check_id == "P6.metadata_contradicts_body"]
    assert p6 == [], f"p6-ok marker should suppress all findings, got: {p6}"


def test_multiple_contradicting_body_dates():
    """Multiple body currency-dates each > fm_latest -> one finding each."""
    md = (
        "# Plan\n\n"
        "**Drafted**: 2026-05-17\n\n"
        "## History\n\n"
        "R1 integrated 2026-05-18.\n"
        "R2 merged 2026-05-19.\n"
    )
    parsed = parse(md)
    findings = p6_metadata_currency.check(parsed)
    p6 = [f for f in findings if f.check_id == "P6.metadata_contradicts_body"]
    assert len(p6) == 2, f"Expected 2 findings (one per contradicting date), got: {p6}"
    dates_in_msgs = [f.message for f in p6]
    assert any("2026-05-18" in msg for msg in dates_in_msgs)
    assert any("2026-05-19" in msg for msg in dates_in_msgs)


def test_integration_via_pbr_run():
    """pbr.run() on p6_fail includes the P6 finding after P1/P2/P5 outputs."""
    parsed = parse(_load("p6_fail.md"))
    findings = pbr.run(parsed)
    p6 = [f for f in findings if f.check_id == "P6.metadata_contradicts_body"]
    assert len(p6) >= 1, "P6 finding must appear in pbr.run() output"

    all_ids = [f.check_id for f in findings]
    p6_positions = [i for i, fid in enumerate(all_ids)
                    if fid == "P6.metadata_contradicts_body"]
    non_p6_positions = [i for i, fid in enumerate(all_ids)
                        if fid.startswith(("P1.", "P2.", "P5."))]
    if non_p6_positions and p6_positions:
        assert max(non_p6_positions) < min(p6_positions), (
            "P6 findings must come after P1/P2/P5 findings"
        )


def test_p6_high_fails_engineering():
    """A plan whose ONLY finding is P6 -> engineering verdict is FAIL.

    This verifies P6 is an honesty check (HIGH -> FAIL), not a hygiene
    check (MEDIUM/LOW -> does not flip engineering).
    """
    # p6_fail.md is minimal enough that F1-F7 and P1/P2/P5 should not fire
    # on it; if they do, we filter for P6 specifically and verify the verdict
    # is still FAIL (because P6 is HIGH).
    verdict = api.check_mechanical(_load("p6_fail.md"))
    p6 = [f for f in verdict.findings
          if f.check_id == "P6.metadata_contradicts_body"]
    assert p6, "p6_fail.md must produce at least one P6 finding via check_mechanical"
    assert verdict.engineering.value == "FAIL", (
        f"P6 HIGH finding must flip engineering to FAIL, got {verdict.engineering}"
    )
