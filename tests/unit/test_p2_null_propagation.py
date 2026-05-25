"""Unit tests for P2: Null propagation check."""
import pathlib

from plan_forge.parser import parse
from plan_forge.checks.pbr import p2_null_propagation
from plan_forge.verdict import Severity

_FIXTURES = pathlib.Path(__file__).parent.parent / "fixtures"


def _load(name: str) -> str:
    return (_FIXTURES / name).read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Mandatory fixture tests
# ---------------------------------------------------------------------------

def test_p2_pass_fixture():
    """Pass fixture: no P2 findings expected."""
    parsed = parse(_load("p2_pass.md"))
    findings = p2_null_propagation.check(parsed)
    p2_findings = [f for f in findings if f.check_id == "P2.orphan_optional"]
    assert p2_findings == [], f"Expected no P2 findings, got: {p2_findings}"


def test_p2_fail_fixture():
    """Fail fixture: at least one P2.orphan_optional finding expected."""
    parsed = parse(_load("p2_fail.md"))
    findings = p2_null_propagation.check(parsed)
    ids = [f.check_id for f in findings]
    assert "P2.orphan_optional" in ids, (
        f"Expected P2.orphan_optional, got: {ids}"
    )


def test_p2_severity():
    """All P2 findings must be HIGH severity."""
    parsed = parse(_load("p2_fail.md"))
    findings = p2_null_propagation.check(parsed)
    p2_findings = [f for f in findings if f.check_id == "P2.orphan_optional"]
    assert p2_findings, "Need at least one finding to check severity"
    for f in p2_findings:
        assert f.severity == Severity.HIGH, (
            f"Expected HIGH severity, got {f.severity}"
        )


# ---------------------------------------------------------------------------
# S5 narrowing: schema fields must not fire; function returns must still fire
# ---------------------------------------------------------------------------

def test_p2_fp_schema_field_fixture():
    """FP fixture: schema field declarations produce no P2 finding."""
    parsed = parse(_load("p2_fp_schema_field.md"))
    findings = p2_null_propagation.check(parsed)
    p2_findings = [f for f in findings if f.check_id == "P2.orphan_optional"]
    assert p2_findings == [], (
        "schema-field nullable declarations must not fire P2,"
        f" got: {p2_findings}"
    )


def test_p2_tp_func_return_fixture():
    """TP fixture: function returning optional with no handling fires P2."""
    parsed = parse(_load("p2_tp_func_return.md"))
    findings = p2_null_propagation.check(parsed)
    ids = [f.check_id for f in findings]
    assert "P2.orphan_optional" in ids, (
        "function returning optional without null-check must fire P2,"
        f" got: {ids}"
    )


def test_p2_class_field_no_finding():
    """Class field 'name: T | None' without null-check does not fire P2."""
    md = (
        "# Plan\n\n"
        "## Data Model\n\n"
        "```python\n"
        "class Record:\n"
        "    profile: dict | None\n"
        "    label: str | None\n"
        "```\n"
    )
    parsed = parse(md)
    findings = p2_null_propagation.check(parsed)
    p2_findings = [f for f in findings if f.check_id == "P2.orphan_optional"]
    assert p2_findings == [], (
        "class field declarations must not fire P2,"
        f" got: {p2_findings}"
    )


# ---------------------------------------------------------------------------
# Edge case tests
# ---------------------------------------------------------------------------

def test_p2_non_null_invariant_comment():
    """Non-null invariant comment 5 lines before block suppresses finding."""
    md = (
        "# Plan\n\n"
        "## Design\n\n"
        "non-null invariant enforced by the caller validation layer.\n"
        "\n"
        "\n"
        "\n"
        "\n"
        "```python\n"
        "def process() -> dict | None:\n"
        "    return _store.get('key')\n"
        "```\n"
    )
    parsed = parse(md)
    findings = p2_null_propagation.check(parsed)
    p2_findings = [f for f in findings if f.check_id == "P2.orphan_optional"]
    assert p2_findings == [], (
        "non-null invariant comment should suppress finding,"
        f" got: {p2_findings}"
    )


def test_p2_non_optional_return_no_finding():
    """Function with non-optional return type never fires P2."""
    md = (
        "# Plan\n\n"
        "## Design\n\n"
        "```python\n"
        "def compute(value: Optional[int]) -> int:\n"
        "    return value or 0\n"
        "```\n"
    )
    parsed = parse(md)
    findings = p2_null_propagation.check(parsed)
    p2_findings = [f for f in findings if f.check_id == "P2.orphan_optional"]
    assert p2_findings == [], (
        "non-optional return type must not fire P2,"
        f" got: {p2_findings}"
    )


def test_p2_optional_return_with_escape():
    """def func() -> Optional[T] with p2-ok escape -> NO finding."""
    md = (
        "# Plan\n\n"
        "## Design\n\n"
        "<!-- plan-forge: p2-ok callers check for None before use -->\n"
        "```python\n"
        "def compute() -> Optional[int]:\n"
        "    return _lookup()\n"
        "```\n"
    )
    parsed = parse(md)
    findings = p2_null_propagation.check(parsed)
    p2_findings = [f for f in findings if f.check_id == "P2.orphan_optional"]
    assert p2_findings == [], (
        "p2-ok escape on Optional return should suppress finding,"
        f" got: {p2_findings}"
    )


def test_p2_prose_not_scanned():
    """Nullable patterns in prose (not in code block) do not fire P2."""
    md = (
        "# Plan\n\n"
        "## Overview\n\n"
        "The result: str | None is documented here.\n"
        "No code block anywhere.\n"
    )
    parsed = parse(md)
    findings = p2_null_propagation.check(parsed)
    p2_findings = [f for f in findings if f.check_id == "P2.orphan_optional"]
    assert p2_findings == [], (
        "prose nullable patterns should not fire,"
        f" got: {p2_findings}"
    )


def test_p2_assert_not_none():
    """assert on return-value variable fires P2 (variable != func name)."""
    md = (
        "# Plan\n\n"
        "## Design\n\n"
        "```python\n"
        "def finalize() -> object | None:\n"
        "    return _connect()\n"
        "\n"
        "result = finalize()\n"
        "assert result is not None\n"
        "```\n"
    )
    parsed = parse(md)
    findings = p2_null_propagation.check(parsed)
    p2_findings = [f for f in findings if f.check_id == "P2.orphan_optional"]
    assert "P2.orphan_optional" in [f.check_id for f in findings], (
        "function with no null-check on its own name must fire P2,"
        f" got: {p2_findings}"
    )


def test_p2_p2_ok_marker():
    """p2-ok marker within 10 lines before block suppresses finding."""
    md = (
        "# Plan\n\n"
        "## Design\n\n"
        "<!-- plan-forge: p2-ok caller guarantees non-null -->\n"
        "```python\n"
        "def handler() -> dict | None:\n"
        "    return _store.get('event')\n"
        "```\n"
    )
    parsed = parse(md)
    findings = p2_null_propagation.check(parsed)
    p2_findings = [f for f in findings if f.check_id == "P2.orphan_optional"]
    assert p2_findings == [], (
        "p2-ok marker should suppress finding,"
        f" got: {p2_findings}"
    )


def test_p2_funcname_is_none_still_fires():
    """Checking the function object (not return value) does not suppress P2."""
    md = (
        "```python\n"
        "def load() -> Config | None:\n"
        "    pass\n"
        "\n"
        "if load is None:\n"
        "    return\n"
        "```"
    )
    plan = parse(md)
    findings = p2_null_propagation.check(plan)
    assert any(f.check_id == "P2.orphan_optional" for f in findings)
