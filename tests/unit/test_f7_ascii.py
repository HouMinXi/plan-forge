"""Unit tests for F7: ASCII / non-ASCII grep check.

Note: f7_fail.md is intentionally non-ASCII; do not include in ASCII sweep.
"""
import pathlib

from plan_forge.parser import parse
from plan_forge.checks.mechanical import f7_ascii
from plan_forge.verdict import Severity

_FIXTURES = pathlib.Path(__file__).parent.parent / "fixtures"


def _load(name: str) -> str:
    # F7 fail fixture is intentionally non-ASCII; do not include in ASCII sweep.
    return (_FIXTURES / name).read_text(encoding="utf-8")


def test_f7_pass_fixture():
    """Pass fixture: all ASCII content -> no F7 findings."""
    parsed = parse(_load("f7_pass.md"))
    findings = f7_ascii.check(parsed)
    assert findings == [], f"Expected no findings, got: {findings}"


def test_f7_fail_fixture():
    """Fail fixture: non-ASCII chars -> at least one F7.non_ascii_char."""
    # F7 fail fixture is intentionally non-ASCII; do not include in ASCII sweep.
    parsed = parse(_load("f7_fail.md"))
    findings = f7_ascii.check(parsed)
    ids = [f.check_id for f in findings]
    assert "F7.non_ascii_char" in ids, (
        f"Expected F7.non_ascii_char, got: {ids}"
    )


def test_f7_severity():
    """All F7 findings must be HIGH severity."""
    # F7 fail fixture is intentionally non-ASCII; do not include in ASCII sweep.
    parsed = parse(_load("f7_fail.md"))
    findings = f7_ascii.check(parsed)
    assert findings, "Need at least one finding to check severity"
    for f in findings:
        assert f.severity == Severity.HIGH, (
            f"Expected HIGH severity, got {f.severity} for {f.check_id}"
        )


def test_f7_edge_empty_and_em_dash():
    """Edge case: empty plan -> no findings; em dash -> correct fix_hint."""
    # Empty plan
    parsed_empty = parse("")
    findings_empty = f7_ascii.check(parsed_empty)
    assert findings_empty == [], "Empty plan must produce no findings"

    # Plan with em dash U+2014 via chr() so this source file stays ASCII
    em_dash = chr(0x2014)
    plan_text = "# Title\n\nThis is an em dash: " + em_dash + " used incorrectly.\n"
    parsed_dash = parse(plan_text)
    findings_dash = f7_ascii.check(parsed_dash)
    assert len(findings_dash) == 1, (
        f"Expected exactly 1 finding for em dash, got {len(findings_dash)}"
    )
    f = findings_dash[0]
    assert f.check_id == "F7.non_ascii_char"
    assert "2014" in f.message, f"Expected U+2014 in message, got: {f.message!r}"
    assert "--" in f.fix_hint, (
        f'Expected "--" in fix_hint for em dash, got: {f.fix_hint!r}'
    )
