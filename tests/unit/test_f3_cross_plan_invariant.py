"""Unit tests for F3: cross-plan invariant verification check."""
import pathlib

from plan_forge.parser import parse
from plan_forge.checks.mechanical import f3_cross_plan_invariant
from plan_forge.verdict import Severity

_FIXTURES = pathlib.Path(__file__).parent.parent / "fixtures"


def _load(name: str) -> str:
    return (_FIXTURES / name).read_text(encoding="utf-8")


def test_f3_pass_fixture():
    """Pass fixture: no F3 findings expected (refs in References section)."""
    parsed = parse(_load("f3_pass.md"))
    findings = f3_cross_plan_invariant.check(parsed)
    assert findings == [], f"Expected no findings, got: {findings}"


def test_f3_fail_fixture():
    """Fail fixture: at least one F3.unverified_cross_plan_ref expected."""
    parsed = parse(_load("f3_fail.md"))
    findings = f3_cross_plan_invariant.check(parsed)
    ids = [f.check_id for f in findings]
    assert "F3.unverified_cross_plan_ref" in ids, (
        f"Expected F3.unverified_cross_plan_ref, got: {ids}"
    )


def test_f3_severity():
    """All F3 findings must be HIGH severity."""
    parsed = parse(_load("f3_fail.md"))
    findings = f3_cross_plan_invariant.check(parsed)
    assert findings, "Need at least one finding to check severity"
    for f in findings:
        assert f.severity == Severity.HIGH, (
            f"Expected HIGH severity, got {f.severity} for {f.check_id}"
        )


def test_f3_edge_case_insensitive_exemption():
    """Edge case: claim in body uses different case than audit-notes entry -> NO finding.

    The regex is case-insensitive; verified set must normalize to lowercase so
    'Phase-1' in body is exempted by 'phase-1' in audit notes.
    """
    md = (
        "# Plan\n"
        "\n"
        "## Overview\n"
        "\n"
        "Phase-1 integration must be complete.\n"
        "\n"
        "## Audit Notes\n"
        "\n"
        "- phase-1: approved by the team.\n"
    )
    parsed = parse(md)
    findings = f3_cross_plan_invariant.check(parsed)
    assert findings == [], (
        f"Case mismatch should still be exempt, got: {findings}"
    )


def test_f3_edge_audit_notes_exemption():
    """Edge case: claim in body AND in audit notes -> NO finding."""
    md = (
        "# Plan\n"
        "\n"
        "## Overview\n"
        "\n"
        "This plan depends on T09 for API integration.\n"
        "\n"
        "## Audit Notes\n"
        "\n"
        "- T09: provides the check_mechanical() API surface.\n"
    )
    parsed = parse(md)
    findings = f3_cross_plan_invariant.check(parsed)
    # T09 is mentioned in Overview but also in Audit Notes -> exempted
    assert findings == [], (
        f"Expected no findings when claim is covered by audit notes,"
        f" got: {findings}"
    )


def test_f3_self_ref_silent():
    """Plan that mentions its own sub-plan id -> no F3 on the self-ref.

    A plan titled '02-01 ...' should not flag its own id as an unverified
    cross-plan reference; the id is derived from the first heading.
    """
    parsed = parse(_load("f3_self_ref.md"))
    findings = f3_cross_plan_invariant.check(parsed)
    self_ref_findings = [
        f for f in findings
        if "02-01" in f.message
    ]
    assert self_ref_findings == [], (
        f"Own id '02-01' should be exempt, got: {self_ref_findings}"
    )


def test_f3_date_fragment_silent():
    """Date fragments like '05-17' inside '2026-05-17' must not fire F3.

    The subplan pattern matched NN-NN which appears inside ISO dates.
    After the fix, a date-embedded fragment must be suppressed.
    """
    parsed = parse(_load("f3_date_nofire.md"))
    findings = f3_cross_plan_invariant.check(parsed)
    assert findings == [], (
        f"Date fragments should not fire F3, got: {findings}"
    )


def test_f3_cross_ref_still_fires():
    """Teeth: a genuine cross-plan ref (02-03) in a 02-01 plan must still fire.

    The own-id exemption for 02-01 must not suppress a different id (02-03)
    that lacks an audit-notes entry.
    """
    parsed = parse(_load("f3_cross_ref_fires.md"))
    findings = f3_cross_plan_invariant.check(parsed)
    ids = [f.check_id for f in findings]
    assert "F3.unverified_cross_plan_ref" in ids, (
        f"Cross-plan ref '02-03' should still fire; got: {ids}"
    )
    ref_messages = [f.message for f in findings]
    assert any("02-03" in m for m in ref_messages), (
        f"Finding should mention '02-03'; messages: {ref_messages}"
    )
    # Own id 02-01 should still be silent
    own_findings = [f for f in findings if "02-01" in f.message]
    assert own_findings == [], (
        f"Own id '02-01' should remain silent; got: {own_findings}"
    )


def test_f3_dedup_fires_once():
    """Dedup: Phase 8 referenced 6 times must produce exactly 1 F3 finding."""
    parsed = parse(_load("f3_dedup_fp.md"))
    findings = f3_cross_plan_invariant.check(parsed)
    f3_findings = [f for f in findings if f.check_id == "F3.unverified_cross_plan_ref"]
    phase8_findings = [f for f in f3_findings if "Phase 8" in f.message or "phase 8" in f.message]
    assert len(phase8_findings) == 1, (
        f"Expected exactly 1 F3 finding for Phase 8, got {len(phase8_findings)}: "
        f"{[f.message for f in phase8_findings]}"
    )


def test_f3_own_id_suppressed_via_frontmatter():
    """Own-ID from YAML frontmatter must suppress self-references."""
    parsed = parse(_load("f3_own_id_fp.md"))
    findings = f3_cross_plan_invariant.check(parsed)
    own_id_findings = [
        f for f in findings
        if f.check_id == "F3.unverified_cross_plan_ref" and "08-02" in f.message
    ]
    assert own_id_findings == [], (
        f"Own id 08-02 from frontmatter should be exempt, got: {own_id_findings}"
    )

def test_f3_phase10_cross_ref_detected():
    """Phase 10+ subplan ID (10-02) in body must fire one F3 HIGH finding."""
    parsed = parse(_load("f3_phase10_cross_ref.md"))
    findings = f3_cross_plan_invariant.check(parsed)
    assert len(findings) == 1, (
        f"Expected 1 finding for 10-02, got {len(findings)}: {findings}"
    )
    assert "10-02" in findings[0].message, (
        f"Finding message should mention '10-02', got: {findings[0].message}"
    )


def test_f3_phase10_own_id_suppressed():
    """Phase 10 own-ID (10-02 from frontmatter) must suppress self-references."""
    parsed = parse(_load("f3_phase10_own_id_fp.md"))
    findings = f3_cross_plan_invariant.check(parsed)
    assert findings == [], (
        f"Own id '10-02' from frontmatter should be exempt, got: {findings}"
    )


def test_f3_phase_text_self_ref_suppressed():
    """Phase-text self-reference must not fire F3; different phase must fire.

    A plan with phase:8 frontmatter mentioning 'Phase 8' and 'Phase-8'
    must produce zero F3 findings for those phrases. A mention of 'Phase 9'
    (different phase, no audit note) must still produce one F3 finding.
    """
    parsed = parse(_load("f3_phase_text_fp.md"))
    findings = f3_cross_plan_invariant.check(parsed)
    f3_findings = [
        f for f in findings
        if f.check_id == "F3.unverified_cross_plan_ref"
    ]
    assert len(f3_findings) == 1, (
        f"Expected exactly 1 F3 finding (Phase 9 only), got {len(f3_findings)}: "
        f"{[f.message for f in f3_findings]}"
    )
    assert any("Phase 9" in f.message for f in f3_findings), (
        f"Remaining finding should mention 'Phase 9', got: "
        f"{[f.message for f in f3_findings]}"
    )
    assert all("Phase 8" not in f.message for f in f3_findings), (
        f"'Phase 8' should be suppressed as own-phase self-reference, got: "
        f"{[f.message for f in f3_findings]}"
    )
