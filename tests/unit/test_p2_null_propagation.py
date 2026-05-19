"""Unit tests for P2: Null propagation check."""
import pathlib

from plan_forge.parser import parse
from plan_forge.checks.pbr import p2_null_propagation
from plan_forge.verdict import Severity

_FIXTURES = pathlib.Path(__file__).parent.parent / "fixtures"


def _load(name: str) -> str:
    return (_FIXTURES / name).read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Mandatory tests
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
# Edge case tests
# ---------------------------------------------------------------------------

def test_p2_non_null_invariant_comment():
    """Nullable with non-null invariant comment 5 lines before block -> NO finding."""
    md = (
        "# Plan\n\n"
        "## Design\n\n"
        "non-null invariant enforced by the caller validation layer.\n"
        "\n"
        "\n"
        "\n"
        "\n"
        "```python\n"
        "def process(data: dict | None) -> str:\n"
        "    return str(data)\n"
        "```\n"
    )
    parsed = parse(md)
    findings = p2_null_propagation.check(parsed)
    p2_findings = [f for f in findings if f.check_id == "P2.orphan_optional"]
    assert p2_findings == [], (
        f"non-null invariant comment should suppress finding, got: {p2_findings}"
    )


def test_p2_default_value_pattern():
    """Nullable with 'X or default' pattern in same block -> NO finding."""
    md = (
        "# Plan\n\n"
        "## Design\n\n"
        "```python\n"
        "def show(label: str | None) -> str:\n"
        "    display = label or 'unknown'\n"
        "    return display\n"
        "```\n"
    )
    parsed = parse(md)
    findings = p2_null_propagation.check(parsed)
    p2_findings = [f for f in findings if f.check_id == "P2.orphan_optional"]
    assert p2_findings == [], (
        f"'or default' pattern should suppress finding, got: {p2_findings}"
    )


def test_p2_optional_type():
    """Optional[int] with 'if name is None' in same block -> NO finding."""
    md = (
        "# Plan\n\n"
        "## Design\n\n"
        "```python\n"
        "def compute(value: Optional[int]) -> int:\n"
        "    if value is None:\n"
        "        return 0\n"
        "    return value * 2\n"
        "```\n"
    )
    parsed = parse(md)
    findings = p2_null_propagation.check(parsed)
    p2_findings = [f for f in findings if f.check_id == "P2.orphan_optional"]
    assert p2_findings == [], (
        f"Optional type with is None check should pass, got: {p2_findings}"
    )


def test_p2_prose_not_scanned():
    """Nullable patterns in prose (not in code block) do not trigger findings."""
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
        f"prose nullable patterns should not fire, got: {p2_findings}"
    )


def test_p2_assert_not_none():
    """assert X is not None in same block -> NO finding."""
    md = (
        "# Plan\n\n"
        "## Design\n\n"
        "```python\n"
        "def finalize(conn: object | None) -> str:\n"
        "    assert conn is not None\n"
        "    return conn.status\n"
        "```\n"
    )
    parsed = parse(md)
    findings = p2_null_propagation.check(parsed)
    p2_findings = [f for f in findings if f.check_id == "P2.orphan_optional"]
    assert p2_findings == [], (
        f"assert not None should suppress finding, got: {p2_findings}"
    )


def test_p2_p2_ok_marker():
    """p2-ok marker within 10 lines before block -> NO finding."""
    md = (
        "# Plan\n\n"
        "## Design\n\n"
        "<!-- plan-forge: p2-ok caller guarantees non-null -->\n"
        "```python\n"
        "def handler(event: dict | None) -> None:\n"
        "    process(event)\n"
        "```\n"
    )
    parsed = parse(md)
    findings = p2_null_propagation.check(parsed)
    p2_findings = [f for f in findings if f.check_id == "P2.orphan_optional"]
    assert p2_findings == [], (
        f"p2-ok marker should suppress finding, got: {p2_findings}"
    )
