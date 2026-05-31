"""Unit tests for F11: acceptance-criteria to test-function traceability."""
import pathlib

from plan_forge.parser import parse
from plan_forge.checks.mechanical import f11_ac_test_traceability
from plan_forge.verdict import Severity

_FIXTURES = pathlib.Path(__file__).parent.parent / "fixtures"


def _load(name: str) -> str:
    return (_FIXTURES / name).read_text(encoding="utf-8")


def test_f11_pass_fixture():
    parsed = parse(_load("f11_fp.md"))
    findings = f11_ac_test_traceability.check(parsed)
    assert findings == [], f"Expected no findings, got: {findings}"


def test_f11_fail_fixture():
    parsed = parse(_load("f11_tp.md"))
    findings = f11_ac_test_traceability.check(parsed)
    ids = [f.check_id for f in findings]
    assert "F11.ac_test_missing" in ids, f"Expected F11.ac_test_missing, got: {ids}"


def test_f11_severity():
    parsed = parse(_load("f11_tp.md"))
    findings = f11_ac_test_traceability.check(parsed)
    assert findings, "Need at least one finding to check severity"
    for f in findings:
        assert f.severity == Severity.MEDIUM, (
            f"Expected MEDIUM severity, got {f.severity}"
        )
