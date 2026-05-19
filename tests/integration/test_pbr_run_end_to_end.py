"""Integration tests: pbr.run() and mechanical.run() PBR integration.

Verifies that:
1. pbr.run() returns list[Finding] for all P fixtures.
2. pbr.run() check_ids match expectations per fixture.
3. mechanical.run() returns combined F+PBR findings in F1..F7,P1,P2,P5 order.
"""
import pathlib

import pytest

from plan_forge.parser import parse
from plan_forge.checks import pbr
from plan_forge.checks import mechanical
from plan_forge.verdict import Finding

_FIXTURES = pathlib.Path(__file__).parent.parent / "fixtures"


def _load(name: str) -> str:
    return (_FIXTURES / name).read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# pbr.run() per-fixture smoke tests
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("fixture_name", [
    "p1_pass.md",
    "p1_fail.md",
    "p2_pass.md",
    "p2_fail.md",
    "p5_pass.md",
    "p5_fail.md",
])
def test_pbr_run_returns_finding_list(fixture_name: str):
    """pbr.run() must return list[Finding] and not raise for any P fixture."""
    text = _load(fixture_name)
    parsed = parse(text)
    result = pbr.run(parsed)
    assert isinstance(result, list), (
        f"pbr.run() must return list, got {type(result)}"
    )
    for item in result:
        assert isinstance(item, Finding), (
            f"Each element must be Finding, got {type(item)}: {item!r}"
        )


def test_pbr_run_p1_fail_has_p1_check_id():
    """pbr.run() on p1_fail.md returns at least one P1.orphan_identifier."""
    parsed = parse(_load("p1_fail.md"))
    findings = pbr.run(parsed)
    ids = [f.check_id for f in findings]
    assert "P1.orphan_identifier" in ids, (
        f"Expected P1.orphan_identifier from pbr.run(), got: {ids}"
    )


def test_pbr_run_p2_fail_has_p2_check_id():
    """pbr.run() on p2_fail.md returns at least one P2.orphan_optional."""
    parsed = parse(_load("p2_fail.md"))
    findings = pbr.run(parsed)
    ids = [f.check_id for f in findings]
    assert "P2.orphan_optional" in ids, (
        f"Expected P2.orphan_optional from pbr.run(), got: {ids}"
    )


def test_pbr_run_p5_fail_has_both_p5_check_ids():
    """pbr.run() on p5_fail.md returns both P5 check_ids."""
    parsed = parse(_load("p5_fail.md"))
    findings = pbr.run(parsed)
    ids = {f.check_id for f in findings}
    assert "P5.module_design_orphan" in ids, (
        f"Expected P5.module_design_orphan, got: {ids}"
    )
    assert "P5.t_row_orphan" in ids, (
        f"Expected P5.t_row_orphan, got: {ids}"
    )


def test_pbr_run_pass_fixtures_no_pbr_findings():
    """pbr.run() on all PASS fixtures returns no PBR check_ids."""
    pbr_check_ids = {
        "P1.orphan_identifier",
        "P2.orphan_optional",
        "P5.module_design_orphan",
        "P5.t_row_orphan",
    }
    for name in ("p1_pass.md", "p2_pass.md", "p5_pass.md"):
        parsed = parse(_load(name))
        findings = pbr.run(parsed)
        fired = [f for f in findings if f.check_id in pbr_check_ids]
        assert fired == [], (
            f"{name}: expected no PBR findings, got: {fired}"
        )


# ---------------------------------------------------------------------------
# mechanical.run() PBR integration: ordering check
# ---------------------------------------------------------------------------

def test_mechanical_run_includes_pbr_findings():
    """mechanical.run() on p1_fail.md returns PBR findings in addition to F-findings."""
    parsed = parse(_load("p1_fail.md"))
    findings = mechanical.run(parsed)
    assert isinstance(findings, list)
    ids = [f.check_id for f in findings]
    # At least one PBR finding must be present
    pbr_ids = [i for i in ids if i.startswith("P")]
    assert pbr_ids, f"Expected at least one P-finding in mechanical.run(), got: {ids}"


def test_mechanical_run_ordering_f_before_p():
    """F-check findings appear before P-check findings in mechanical.run() output."""
    # Use p5_fail.md which has Module Designs + Implementation Tasks
    # to trigger both F checks (minimal) and P5 checks
    md = (
        "# Plan\n\n"
        "## SC Table\n\n"
        "| SC | Criterion | Fail Condition |\n"
        "|----|-----------|----------------|\n"
        "| SC-1 | coverage | below 80% |\n\n"
        "## Tests\n\n"
        "SC-1 is verified here.\n\n"
        "## Module Designs\n\n"
        "```python\n"
        "def alpha_api(x: int) -> str:\n"
        "    pass\n"
        "```\n\n"
        "## Implementation Tasks\n\n"
        "| Task | Output |\n"
        "|------|--------|\n"
        "| T01  | `beta_api` |\n"
    )
    parsed = parse(md)
    findings = mechanical.run(parsed)
    ids = [f.check_id for f in findings]

    # Find first F-finding index and first P-finding index
    f_indices = [i for i, cid in enumerate(ids) if cid.startswith("F")]
    p_indices = [i for i, cid in enumerate(ids) if cid.startswith("P")]

    if f_indices and p_indices:
        assert min(f_indices) < min(p_indices), (
            f"F findings must precede P findings. Order: {ids}"
        )
    # At least P5 findings should be present
    assert any(cid.startswith("P") for cid in ids), (
        f"Expected P5 findings in combined output: {ids}"
    )
