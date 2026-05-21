"""Unit tests for G3 Pre-mortem gate."""
import pathlib

from plan_forge.checks.epistemic.g3_premortem import check
from plan_forge.parser import parse
from plan_forge.verdict import Severity

FIXTURES = pathlib.Path(__file__).parent.parent / "fixtures"


def _load(name: str):
    return parse((FIXTURES / name).read_text())


def _make_causes(n: int, keyword: str = "early warning", extra: str = "counter") -> str:
    """Build a Pre-mortem section with n numbered causes containing keywords."""
    lines = ["## Pre-mortem\n"]
    for i in range(1, n + 1):
        lines.append(
            f"{i}. Cause {i}; {keyword}: signal{i}; {extra}: action{i}.\n"
        )
    return "\n".join(lines)


def test_pass():
    """g3_pass.md has >= 5 causes and both keywords -> no findings."""
    findings = check(_load("g3_pass.md"))
    assert findings == []


def test_absent_blocker():
    """Plan with no Pre-mortem section -> BLOCKER G3.no_section."""
    parsed = parse("# Plan\n\nNo premortem here.\n")
    findings = check(parsed)
    assert len(findings) == 1
    assert findings[0].check_id == "G3.no_section"
    assert findings[0].severity == Severity.BLOCKER


def test_insufficient_causes_blocker():
    """Section with < 5 causes -> BLOCKER G3.insufficient_causes."""
    findings = check(_load("g3_fail.md"))
    ids = [f.check_id for f in findings]
    assert "G3.insufficient_causes" in ids
    for f in findings:
        if f.check_id == "G3.insufficient_causes":
            assert f.severity == Severity.BLOCKER


def test_missing_early_warning_high():
    """Section with >= 5 causes but no 'early warning' keyword -> HIGH."""
    md = (
        "## Pre-mortem\n\n"
        "1. Cause 1; signal: A; counter: X.\n"
        "2. Cause 2; signal: B; counter: Y.\n"
        "3. Cause 3; signal: C; counter: Z.\n"
        "4. Cause 4; signal: D; counter: W.\n"
        "5. Cause 5; signal: E; counter: V.\n"
    )
    parsed = parse(md)
    findings = check(parsed)
    ids = [f.check_id for f in findings]
    assert "G3.no_early_warning" in ids
    for f in findings:
        if f.check_id == "G3.no_early_warning":
            assert f.severity == Severity.HIGH


def test_missing_counter_high():
    """Section with >= 5 causes and early warning but no 'counter' -> HIGH."""
    md = (
        "## Pre-mortem\n\n"
        "1. Cause 1; early warning: A; mitigation: X.\n"
        "2. Cause 2; early warning: B; mitigation: Y.\n"
        "3. Cause 3; early warning: C; mitigation: Z.\n"
        "4. Cause 4; early warning: D; mitigation: W.\n"
        "5. Cause 5; early warning: E; mitigation: V.\n"
    )
    parsed = parse(md)
    findings = check(parsed)
    ids = [f.check_id for f in findings]
    assert "G3.no_counter" in ids
    for f in findings:
        if f.check_id == "G3.no_counter":
            assert f.severity == Severity.HIGH


def test_premortem_no_hyphen_accepted():
    """'premortem' (no hyphen) is accepted as equivalent to 'pre-mortem'."""
    md = (
        "## Premortem\n\n"
        "1. Cause 1; early warning: A; counter: X.\n"
        "2. Cause 2; early warning: B; counter: Y.\n"
        "3. Cause 3; early warning: C; counter: Z.\n"
        "4. Cause 4; early warning: D; counter: W.\n"
        "5. Cause 5; early warning: E; counter: V.\n"
    )
    parsed = parse(md)
    findings = check(parsed)
    assert findings == []


def test_table_based_causes_pass():
    """Table rows are counted as cause entries (covers table-row branch)."""
    md = (
        "## Pre-mortem\n\n"
        "| Cause | Early Warning | Counter |\n"
        "|-------|---------------|---------|\n"
        "| Scope creep | Backlog grows | Scope freeze |\n"
        "| Staff churn | Absence pattern | Cross-train |\n"
        "| Budget cut | Forecast drift | Reserve fund |\n"
        "| Integration fail | CI failures | Continuous integration |\n"
        "| Vendor API break | Changelog alerts | Contract SLA |\n"
    )
    parsed = parse(md)
    findings = check(parsed)
    assert not any(f.check_id == "G3.insufficient_causes" for f in findings)


def test_bullet_based_causes_pass():
    """Bullet items are counted as cause entries (covers bullet fallback branch)."""
    md = (
        "## Pre-mortem\n\n"
        "- Scope creep; early warning: backlog grows; counter: scope freeze.\n"
        "- Staff churn; early warning: absence pattern; counter: cross-train.\n"
        "- Budget cut; early warning: forecast drift; counter: reserve fund.\n"
        "- Integration fail; early warning: CI alerts; counter: daily CI runs.\n"
        "- Vendor API break; early warning: changelog; counter: pin version.\n"
    )
    parsed = parse(md)
    findings = check(parsed)
    assert not any(f.check_id == "G3.insufficient_causes" for f in findings)
