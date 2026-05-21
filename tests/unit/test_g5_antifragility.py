"""Unit tests for G5 Antifragility gate."""
import pathlib

from plan_forge.checks.epistemic.g5_antifragility import check
from plan_forge.parser import parse
from plan_forge.verdict import Severity

FIXTURES = pathlib.Path(__file__).parent.parent / "fixtures"


def _load(name: str):
    return parse((FIXTURES / name).read_text())


def test_pass():
    """g5_pass.md has 3 scenarios with mixed classifications -> no findings."""
    findings = check(_load("g5_pass.md"))
    assert findings == []


def test_absent_blocker():
    """Plan with no Chaos Response section -> BLOCKER G5.no_section."""
    parsed = parse("# Plan\n\nNo chaos response here.\n")
    findings = check(parsed)
    assert len(findings) == 1
    assert findings[0].check_id == "G5.no_section"
    assert findings[0].severity == Severity.BLOCKER


def test_insufficient_scenarios_blocker():
    """Section with < 3 classified scenarios -> BLOCKER G5.insufficient_scenarios."""
    md = (
        "## Chaos Response\n\n"
        "1. Load spike -- we survive via auto-scaling.\n"
        "2. Dependency API change -- will break the build.\n"
    )
    parsed = parse(md)
    findings = check(parsed)
    ids = [f.check_id for f in findings]
    assert "G5.insufficient_scenarios" in ids
    for f in findings:
        if f.check_id == "G5.insufficient_scenarios":
            assert f.severity == Severity.BLOCKER


def test_all_break_blocker():
    """g5_fail.md has 3 'break'-only scenarios -> BLOCKER G5.all_break."""
    findings = check(_load("g5_fail.md"))
    ids = [f.check_id for f in findings]
    assert "G5.all_break" in ids
    for f in findings:
        if f.check_id == "G5.all_break":
            assert f.severity == Severity.BLOCKER


def test_mixed_classification_passes():
    """Explicit mix of benefit + survive + degrade -> no findings."""
    md = (
        "## Chaos Response\n\n"
        "1. Stressor A -- we benefit from extra traffic.\n"
        "2. Stressor B -- the team will survive with reduced scope.\n"
        "3. Stressor C -- performance will degrade but not fail.\n"
    )
    parsed = parse(md)
    findings = check(parsed)
    assert findings == []


def test_break_with_other_class_not_all_break():
    """A scenario with both 'break' and 'survive' is not pure-break."""
    md = (
        "## Chaos Response\n\n"
        "1. Scenario A -- could break the build but we survive via fallback.\n"
        "2. Scenario B -- will break the timeline.\n"
        "3. Scenario C -- will break the cache but degrade gracefully.\n"
    )
    parsed = parse(md)
    findings = check(parsed)
    # G5.all_break must NOT fire because scenarios 1 and 3 have non-break words.
    ids = [f.check_id for f in findings]
    assert "G5.all_break" not in ids


def test_bullet_based_scenarios_pass():
    """Bullet entries are counted as scenarios (covers bullet branch)."""
    md = (
        "## Chaos Response\n\n"
        "- Load spike: we benefit from auto-scaling.\n"
        "- Staff absence: we survive with on-call rotation.\n"
        "- Dependency break: performance will degrade but core survives.\n"
    )
    parsed = parse(md)
    findings = check(parsed)
    assert findings == []


def test_table_based_scenarios_pass():
    """Table rows are counted as scenarios (covers table-row branch)."""
    md = (
        "## Chaos Response\n\n"
        "| Stressor | Response | Classification |\n"
        "|----------|----------|----------------|\n"
        "| Load spike | Auto-scale | benefit |\n"
        "| Staff absence | On-call | survive |\n"
        "| Dep change | Fallback | degrade |\n"
    )
    parsed = parse(md)
    findings = check(parsed)
    assert findings == []
