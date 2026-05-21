"""Unit tests for F4: temporal anchor lint check."""
import pathlib

from plan_forge.parser import parse
from plan_forge.checks.mechanical import f4_temporal_anchor
from plan_forge.verdict import Severity

_FIXTURES = pathlib.Path(__file__).parent.parent / "fixtures"


def _load(name: str) -> str:
    return (_FIXTURES / name).read_text(encoding="utf-8")


def test_f4_pass_fixture():
    """Pass fixture: no F4 findings expected (all anchors are precise)."""
    parsed = parse(_load("f4_pass.md"))
    findings = f4_temporal_anchor.check(parsed)
    assert findings == [], f"Expected no findings, got: {findings}"


def test_f4_fail_fixture():
    """Fail fixture: at least one F4.imprecise_temporal_anchor expected."""
    parsed = parse(_load("f4_fail.md"))
    findings = f4_temporal_anchor.check(parsed)
    ids = [f.check_id for f in findings]
    assert "F4.imprecise_temporal_anchor" in ids, (
        f"Expected F4.imprecise_temporal_anchor, got: {ids}"
    )


def test_f4_severity():
    """All F4 findings must be LOW severity."""
    parsed = parse(_load("f4_fail.md"))
    findings = f4_temporal_anchor.check(parsed)
    assert findings, "Need at least one finding to check severity"
    for f in findings:
        assert f.severity == Severity.LOW, (
            f"Expected LOW severity, got {f.severity} for {f.check_id}"
        )


def test_f4_edge_dunder_no_finding():
    """Edge case: 'after __exit__' is a precise anchor -> NO finding."""
    md = (
        "# Plan\n"
        "\n"
        "## Design\n"
        "\n"
        "Resources are released after __exit__ is invoked.\n"
        "The session is closed after the function is complete.\n"
    )
    parsed = parse(md)
    findings = f4_temporal_anchor.check(parsed)
    # 'after __exit__' should NOT produce a finding (dunder = precise)
    # 'after the function is complete' SHOULD produce a finding
    after_exit_findings = [
        f for f in findings if "__exit__" in f.message
    ]
    assert not after_exit_findings, (
        f"'after __exit__' should not produce a finding, got: {after_exit_findings}"
    )
    # The imprecise one should be flagged
    imprecise = [f for f in findings if "complete" in f.message]
    assert imprecise, "Expected finding for 'after the function is complete'"
