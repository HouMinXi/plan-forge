"""Unit tests for F14: task-without-acceptance-criteria detection."""
import pathlib

from plan_forge.parser import parse
from plan_forge.checks.mechanical import f14_task_without_ac
from plan_forge.verdict import Severity

_FIXTURES = pathlib.Path(__file__).parent.parent / "fixtures"


def _load(name: str) -> str:
    return (_FIXTURES / name).read_text(encoding="utf-8")


def test_f14_pass_fixture():
    parsed = parse(_load("f14_fp.md"))
    findings = f14_task_without_ac.check(parsed)
    assert findings == [], f"Expected no findings, got: {findings}"


def test_f14_fail_fixture():
    parsed = parse(_load("f14_tp.md"))
    findings = f14_task_without_ac.check(parsed)
    ids = [f.check_id for f in findings]
    assert "F14.task_without_ac" in ids, (
        f"Expected F14.task_without_ac, got: {ids}"
    )


def test_f14_severity():
    parsed = parse(_load("f14_tp.md"))
    findings = f14_task_without_ac.check(parsed)
    assert findings, "Need at least one finding to check severity"
    for f in findings:
        assert f.severity == Severity.HIGH, (
            f"Expected HIGH severity, got {f.severity}"
        )
