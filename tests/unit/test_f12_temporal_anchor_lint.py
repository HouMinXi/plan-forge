"""Unit tests for F12: temporal anchor lint."""
import pathlib

from plan_forge.parser import parse
from plan_forge.checks.mechanical import f12_temporal_anchor_lint
from plan_forge.verdict import Severity

_FIXTURES = pathlib.Path(__file__).parent.parent / "fixtures"


def _load(name: str) -> str:
    return (_FIXTURES / name).read_text(encoding="utf-8")


def test_f12_pass_fixture():
    parsed = parse(_load("f12_fp.md"))
    findings = f12_temporal_anchor_lint.check(parsed)
    assert findings == [], f"Expected no findings, got: {findings}"


def test_f12_fail_fixture():
    parsed = parse(_load("f12_tp.md"))
    findings = f12_temporal_anchor_lint.check(parsed)
    ids = [f.check_id for f in findings]
    assert "F12.temporal_anchor_unanchored" in ids, (
        f"Expected F12.temporal_anchor_unanchored, got: {ids}"
    )


def test_f12_severity():
    parsed = parse(_load("f12_tp.md"))
    findings = f12_temporal_anchor_lint.check(parsed)
    assert findings, "Need at least one finding to check severity"
    for f in findings:
        assert f.severity == Severity.LOW, (
            f"Expected LOW severity, got {f.severity}"
        )
