"""Unit tests for P5: Interface symmetry check."""
import pathlib

from plan_forge.parser import parse
from plan_forge.checks.pbr import p5_interface_symmetry
from plan_forge.verdict import Severity

_FIXTURES = pathlib.Path(__file__).parent.parent / "fixtures"


def _load(name: str) -> str:
    return (_FIXTURES / name).read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Mandatory tests
# ---------------------------------------------------------------------------

def test_p5_pass_fixture():
    """Pass fixture: no P5 findings expected."""
    parsed = parse(_load("p5_pass.md"))
    findings = p5_interface_symmetry.check(parsed)
    p5_findings = [
        f for f in findings
        if f.check_id in ("P5.module_design_orphan", "P5.t_row_orphan")
    ]
    assert p5_findings == [], f"Expected no P5 findings, got: {p5_findings}"


def test_p5_fail_fixture():
    """Fail fixture: at least one P5 finding expected (both check_ids)."""
    parsed = parse(_load("p5_fail.md"))
    findings = p5_interface_symmetry.check(parsed)
    ids = {f.check_id for f in findings}
    assert "P5.module_design_orphan" in ids, (
        f"Expected P5.module_design_orphan, got: {ids}"
    )
    assert "P5.t_row_orphan" in ids, (
        f"Expected P5.t_row_orphan, got: {ids}"
    )


def test_p5_severity():
    """All P5 findings must be HIGH severity."""
    parsed = parse(_load("p5_fail.md"))
    findings = p5_interface_symmetry.check(parsed)
    p5_findings = [
        f for f in findings
        if f.check_id in ("P5.module_design_orphan", "P5.t_row_orphan")
    ]
    assert p5_findings, "Need at least one finding to check severity"
    for f in p5_findings:
        assert f.severity == Severity.HIGH, (
            f"Expected HIGH severity, got {f.severity}"
        )


# ---------------------------------------------------------------------------
# Granularity + mode-string fixtures
# ---------------------------------------------------------------------------

def test_p5_fp_file_granularity_no_findings():
    """FP fixture: file-level T-row covers Module Designs APIs; no findings.

    record_outcome and query_results are covered by record.py and query.py
    at file granularity.  Mode strings `off` and `on_split_evidence_rich`
    are not APIs and must not trigger t_row_orphan.
    """
    parsed = parse(_load("p5_fp_file_granularity.md"))
    findings = p5_interface_symmetry.check(parsed)
    p5_findings = [
        f for f in findings
        if f.check_id in ("P5.module_design_orphan", "P5.t_row_orphan")
    ]
    assert p5_findings == [], (
        f"Expected no P5 findings on file-granularity fixture, "
        f"got: {p5_findings}"
    )


def test_p5_tp_missing_impl_fires():
    """TP fixture: frobnicate defined in Module Designs but absent from tasks.

    P5.module_design_orphan must fire for frobnicate even after the
    file-granularity relaxation.
    """
    parsed = parse(_load("p5_tp_missing_impl.md"))
    findings = p5_interface_symmetry.check(parsed)
    ids = {f.check_id for f in findings}
    assert "P5.module_design_orphan" in ids, (
        f"Expected P5.module_design_orphan for frobnicate, got: {ids}"
    )
    orphan_msgs = [
        f.message for f in findings
        if f.check_id == "P5.module_design_orphan"
    ]
    assert any("frobnicate" in m for m in orphan_msgs), (
        f"Expected frobnicate in orphan message, got: {orphan_msgs}"
    )


def test_p5_mode_string_not_t_row_orphan():
    """Bare mode strings in T-rows must not trigger t_row_orphan.

    `off` and `on_split_evidence_rich` are config values, not APIs.
    """
    md = (
        "# Plan\n\n"
        "## Module Designs\n\n"
        "```python\n"
        "def real_api(x: int) -> str:\n"
        "    pass\n"
        "```\n\n"
        "## Implementation Tasks\n\n"
        "| Task | Output |\n"
        "|------|--------|\n"
        "| T01  | `real_api` |\n"
        "| T02  | mode `off` or `on_split_evidence_rich` |\n"
    )
    parsed = parse(md)
    findings = p5_interface_symmetry.check(parsed)
    t_row_orphans = [
        f for f in findings if f.check_id == "P5.t_row_orphan"
    ]
    assert t_row_orphans == [], (
        f"Mode strings should not trigger t_row_orphan, got: {t_row_orphans}"
    )


# ---------------------------------------------------------------------------
# Edge case tests
# ---------------------------------------------------------------------------

def test_p5_bidirectional():
    """Missing both directions -> exactly 2 findings, one of each check_id."""
    md = (
        "# Plan\n\n"
        "## Module Designs\n\n"
        "```python\n"
        "def alpha_func(x: int) -> str:\n"
        "    pass\n"
        "```\n\n"
        "## Implementation Tasks\n\n"
        "| Task | Output |\n"
        "|------|--------|\n"
        "| T01  | `beta_func` |\n"
    )
    parsed = parse(md)
    findings = p5_interface_symmetry.check(parsed)
    p5_findings = [
        f for f in findings
        if f.check_id in ("P5.module_design_orphan", "P5.t_row_orphan")
    ]
    check_ids = [f.check_id for f in p5_findings]
    assert "P5.module_design_orphan" in check_ids, (
        f"Expected module_design_orphan: {check_ids}"
    )
    assert "P5.t_row_orphan" in check_ids, (
        f"Expected t_row_orphan: {check_ids}"
    )
    assert len(p5_findings) == 2, (
        f"Expected exactly 2 P5 findings, got {len(p5_findings)}: {p5_findings}"
    )


def test_p5_underscore_method_exemption():
    """Private method starting with underscore -> NO finding."""
    md = (
        "# Plan\n\n"
        "## Module Designs\n\n"
        "```python\n"
        "def public_api(x: int) -> str:\n"
        "    pass\n\n"
        "def _internal_helper(y: int) -> None:\n"
        "    pass\n"
        "```\n\n"
        "## Implementation Tasks\n\n"
        "| Task | Output |\n"
        "|------|--------|\n"
        "| T01  | `public_api` |\n"
    )
    parsed = parse(md)
    findings = p5_interface_symmetry.check(parsed)
    p5_findings = [
        f for f in findings
        if f.check_id in ("P5.module_design_orphan", "P5.t_row_orphan")
    ]
    assert p5_findings == [], (
        f"private method should be exempt, got: {p5_findings}"
    )


def test_p5_no_module_designs_no_finding():
    """Plan with no Module Designs section -> no P5 finding (skip silently)."""
    md = (
        "# Plan\n\n"
        "## Implementation Tasks\n\n"
        "| Task | Output |\n"
        "|------|--------|\n"
        "| T01  | `some_func` |\n"
    )
    parsed = parse(md)
    findings = p5_interface_symmetry.check(parsed)
    p5_findings = [
        f for f in findings
        if f.check_id in ("P5.module_design_orphan", "P5.t_row_orphan")
    ]
    assert p5_findings == [], (
        f"no Module Designs should produce no P5 findings, got: {p5_findings}"
    )


def test_p5_on_prefix_no_def_is_mode_string():
    """on_callback in T-rows with no def -> exempt as mode string.

    When an on_* token has no ``def token(`` definition anywhere in the
    plan, it is treated as a config/mode value and must not trigger
    t_row_orphan.
    """
    md = (
        "# Plan\n\n"
        "## Module Designs\n\n"
        "```python\n"
        "def real_api(x: int) -> str:\n"
        "    pass\n"
        "```\n\n"
        "## Implementation Tasks\n\n"
        "| Task | Output |\n"
        "|------|--------|\n"
        "| impl-1 | `real_api`, mode `on_callback` |\n"
    )
    parsed = parse(md)
    findings = p5_interface_symmetry.check(parsed)
    t_row_orphans = [
        f for f in findings if f.check_id == "P5.t_row_orphan"
    ]
    assert t_row_orphans == [], (
        f"on_callback with no def should be exempt, got: {t_row_orphans}"
    )


def test_p5_on_prefix_with_def_is_not_mode_string():
    """on_callback in T-rows WITH a def -> not exempt, fires t_row_orphan.

    When an on_* token has a ``def token(`` in the plan, it is a real
    function.  If it also appears in Module Designs it is fine; if absent
    from Module Designs, t_row_orphan fires.
    """
    md = (
        "# Plan\n\n"
        "## Module Designs\n\n"
        "```python\n"
        "def real_api(x: int) -> str:\n"
        "    pass\n"
        "```\n\n"
        "## Implementation Tasks\n\n"
        "| Task | Output |\n"
        "|------|--------|\n"
        "| impl-1 | `real_api`, `on_callback` |\n"
        "| impl-2 | def on_callback(evt): ... |\n"
    )
    parsed = parse(md)
    findings = p5_interface_symmetry.check(parsed)
    t_row_orphans = [
        f for f in findings if f.check_id == "P5.t_row_orphan"
    ]
    assert any("on_callback" in f.message for f in t_row_orphans), (
        f"on_callback with def but absent from Module Designs "
        f"should fire t_row_orphan, got: {t_row_orphans}"
    )


def test_p5_exempt_check_and_run_names():
    """'check' and 'run' are exempt convention names -> no finding."""
    md = (
        "# Plan\n\n"
        "## Module Designs\n\n"
        "```python\n"
        "def check(parsed: object) -> list:\n"
        "    pass\n\n"
        "def run(parsed: object) -> list:\n"
        "    pass\n\n"
        "def real_api(x: int) -> str:\n"
        "    pass\n"
        "```\n\n"
        "## Implementation Tasks\n\n"
        "| Task | Output |\n"
        "|------|--------|\n"
        "| T01  | `real_api` |\n"
    )
    parsed = parse(md)
    findings = p5_interface_symmetry.check(parsed)
    p5_findings = [
        f for f in findings
        if f.check_id in ("P5.module_design_orphan", "P5.t_row_orphan")
    ]
    assert p5_findings == [], (
        f"check/run should be exempt, got: {p5_findings}"
    )
