"""Unit tests for F10: noun-phrase duplicate detection."""
import pathlib

from plan_forge.parser import parse
from plan_forge.checks.mechanical import f10_noun_phrase_duplicate
from plan_forge.verdict import Severity

_FIXTURES = pathlib.Path(__file__).parent.parent / "fixtures"


def _load(name: str) -> str:
    return (_FIXTURES / name).read_text(encoding="utf-8")


def test_f10_pass_fixture():
    parsed = parse(_load("f10_fp.md"))
    findings = f10_noun_phrase_duplicate.check(parsed)
    assert findings == [], f"Expected no findings, got: {findings}"


def test_f10_fail_fixture():
    parsed = parse(_load("f10_tp.md"))
    findings = f10_noun_phrase_duplicate.check(parsed)
    ids = [f.check_id for f in findings]
    assert "F10.noun_phrase_duplicate" in ids, f"Expected F10.noun_phrase_duplicate, got: {ids}"


def test_f10_severity():
    parsed = parse(_load("f10_tp.md"))
    findings = f10_noun_phrase_duplicate.check(parsed)
    assert findings, "Need at least one finding to check severity"
    for f in findings:
        assert f.severity == Severity.LOW, (
            f"Expected LOW severity, got {f.severity}"
        )
