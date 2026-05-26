"""Unit tests for F9: plan length gate."""
import pathlib

from plan_forge.checks.mechanical import f9_plan_length
from plan_forge.checks.mechanical.f9_plan_length import _LENGTH_THRESHOLD
from plan_forge.parser import parse
from plan_forge.verdict import Severity

_FIXTURES = pathlib.Path(__file__).parent.parent / "fixtures"


def _load(name: str) -> str:
    return (_FIXTURES / name).read_text(encoding="utf-8")


def test_long_plan_fires():
    """A plan exceeding the threshold produces exactly one F9 finding."""
    parsed = parse(_load("f9_long.md"))
    findings = f9_plan_length.check(parsed)
    assert len(findings) == 1
    assert findings[0].check_id == "F9.plan_too_long"
    assert findings[0].severity == Severity.MEDIUM


def test_short_plan_silent():
    """A plan within the threshold produces no F9 findings."""
    parsed = parse(_load("f9_short.md"))
    findings = f9_plan_length.check(parsed)
    assert findings == []


def test_exactly_at_threshold_silent():
    """A plan of exactly _LENGTH_THRESHOLD lines does not fire."""
    text = "\n".join(f"line {i}" for i in range(1, _LENGTH_THRESHOLD + 1))
    parsed = parse(text)
    findings = f9_plan_length.check(parsed)
    assert findings == [], (
        f"Plan of exactly {_LENGTH_THRESHOLD} lines should not fire"
    )


def test_one_over_threshold_fires():
    """A plan of _LENGTH_THRESHOLD + 1 lines fires."""
    text = "\n".join(
        f"line {i}" for i in range(1, _LENGTH_THRESHOLD + 2)
    )
    parsed = parse(text)
    findings = f9_plan_length.check(parsed)
    assert len(findings) == 1
    assert findings[0].check_id == "F9.plan_too_long"


def test_finding_message_contains_line_count():
    """The finding message reports the actual line count."""
    text = "\n".join(
        f"line {i}" for i in range(1, _LENGTH_THRESHOLD + 50)
    )
    parsed = parse(text)
    findings = f9_plan_length.check(parsed)
    assert findings
    assert str(_LENGTH_THRESHOLD + 49) in findings[0].message


def test_teeth_threshold_comparison():
    """Bidirectional teeth: dropping the threshold comparison causes the
    short fixture to fire; restoring it silences it.

    This test verifies the comparison is the operative gate by setting
    a threshold below the short fixture's line count via monkeypatching.
    """
    parsed = parse(_load("f9_short.md"))
    line_count = len(parsed.raw_text.splitlines())

    # Temporarily lower the threshold below the short fixture's length
    original = f9_plan_length._LENGTH_THRESHOLD
    try:
        f9_plan_length._LENGTH_THRESHOLD = line_count - 1
        findings = f9_plan_length.check(parsed)
        assert len(findings) == 1, (
            "short fixture should fire when threshold is lowered below it"
        )
    finally:
        f9_plan_length._LENGTH_THRESHOLD = original

    # Restored: short fixture is silent again
    findings = f9_plan_length.check(parsed)
    assert findings == [], (
        "short fixture should be silent after threshold is restored"
    )
