"""Unit tests for F13: cross-plan claim verifier."""
import pathlib

from plan_forge.parser import parse
from plan_forge.checks.mechanical import f13_cross_plan_claim_verifier
from plan_forge.verdict import Severity

_FIXTURES = pathlib.Path(__file__).parent.parent / "fixtures"


def _load(name: str) -> str:
    return (_FIXTURES / name).read_text(encoding="utf-8")


def test_f13_pass_fixture():
    parsed = parse(_load("f13_fp.md"))
    findings = f13_cross_plan_claim_verifier.check(parsed)
    assert findings == [], f"Expected no findings, got: {findings}"


def test_f13_fail_fixture():
    parsed = parse(_load("f13_tp.md"))
    findings = f13_cross_plan_claim_verifier.check(parsed)
    ids = [f.check_id for f in findings]
    assert "F13.cross_plan_claim_thin" in ids, (
        f"Expected F13.cross_plan_claim_thin, got: {ids}"
    )


def test_f13_severity():
    parsed = parse(_load("f13_tp.md"))
    findings = f13_cross_plan_claim_verifier.check(parsed)
    assert findings, "Need at least one finding to check severity"
    for f in findings:
        assert f.severity == Severity.MEDIUM, (
            f"Expected MEDIUM severity, got {f.severity}"
        )
