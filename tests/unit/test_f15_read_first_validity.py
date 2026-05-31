"""Unit tests for F15: read-first file validity check."""
import pathlib

from plan_forge.parser import parse
from plan_forge.checks.mechanical import f15_read_first_validity
from plan_forge.verdict import Severity

_FIXTURES = pathlib.Path(__file__).parent.parent / "fixtures"


def _load(name: str) -> str:
    return (_FIXTURES / name).read_text(encoding="utf-8")


def test_f15_pass_fixture():
    parsed = parse(_load("f15_fp.md"))
    findings = f15_read_first_validity.check(parsed)
    assert findings == [], f"Expected no findings, got: {findings}"


def test_f15_fail_fixture():
    parsed = parse(_load("f15_tp.md"))
    findings = f15_read_first_validity.check(parsed)
    ids = [f.check_id for f in findings]
    assert "F15.read_first_missing" in ids, (
        f"Expected F15.read_first_missing, got: {ids}"
    )


def test_f15_severity():
    parsed = parse(_load("f15_tp.md"))
    findings = f15_read_first_validity.check(parsed)
    assert findings, "Need at least one finding to check severity"
    for f in findings:
        assert f.severity == Severity.MEDIUM, (
            f"Expected MEDIUM severity, got {f.severity}"
        )
