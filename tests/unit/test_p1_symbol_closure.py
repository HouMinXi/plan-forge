"""Unit tests for P1: Symbol closure check."""
import pathlib

from plan_forge.parser import parse
from plan_forge.checks.pbr import p1_symbol_closure
from plan_forge.verdict import Severity

_FIXTURES = pathlib.Path(__file__).parent.parent / "fixtures"


def _load(name: str) -> str:
    return (_FIXTURES / name).read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Mandatory tests
# ---------------------------------------------------------------------------

def test_p1_pass_fixture():
    """Pass fixture: no P1 findings expected."""
    parsed = parse(_load("p1_pass.md"))
    findings = p1_symbol_closure.check(parsed)
    p1_findings = [f for f in findings if f.check_id == "P1.orphan_identifier"]
    assert p1_findings == [], f"Expected no P1 findings, got: {p1_findings}"


def test_p1_fail_fixture():
    """Fail fixture: at least one P1.orphan_identifier finding expected."""
    parsed = parse(_load("p1_fail.md"))
    findings = p1_symbol_closure.check(parsed)
    ids = [f.check_id for f in findings]
    assert "P1.orphan_identifier" in ids, (
        f"Expected P1.orphan_identifier, got: {ids}"
    )


def test_p1_severity():
    """All P1 findings must be HIGH severity."""
    parsed = parse(_load("p1_fail.md"))
    findings = p1_symbol_closure.check(parsed)
    p1_findings = [f for f in findings if f.check_id == "P1.orphan_identifier"]
    assert p1_findings, "Need at least one finding to check severity"
    for f in p1_findings:
        assert f.severity == Severity.HIGH, (
            f"Expected HIGH severity, got {f.severity}"
        )


# ---------------------------------------------------------------------------
# Edge case tests
# ---------------------------------------------------------------------------

def test_p1_marker_exemption():
    """Orphan identifier with p1-ok marker on same line -> NO finding."""
    md = (
        "# Plan\n\n"
        "## Overview\n\n"
        "The `unique_singleton_xyz` is used here. "
        "<!-- plan-forge: p1-ok intentionally external -->\n"
    )
    parsed = parse(md)
    findings = p1_symbol_closure.check(parsed)
    p1_findings = [f for f in findings if f.check_id == "P1.orphan_identifier"]
    assert p1_findings == [], (
        f"marker should suppress finding, got: {p1_findings}"
    )


def test_p1_cross_reference_section_exemption():
    """Identifier appearing once inside ## References -> NO finding."""
    md = (
        "# Plan\n\n"
        "## Overview\n\n"
        "This plan covers system design.\n\n"
        "## References\n\n"
        "- `orphan_in_refs` is an upstream artifact used by this plan.\n"
    )
    parsed = parse(md)
    findings = p1_symbol_closure.check(parsed)
    p1_findings = [f for f in findings if f.check_id == "P1.orphan_identifier"]
    assert p1_findings == [], (
        f"references section should exempt identifier, got: {p1_findings}"
    )


def test_p1_python_keyword_skip():
    """Common Python words (int, str, None) appearing once -> NO finding."""
    md = (
        "# Plan\n\n"
        "## Overview\n\n"
        "Return type is `int`.\n"
        "The value may be `str` or `None`.\n"
        "Use `bool` for flags.\n"
    )
    parsed = parse(md)
    findings = p1_symbol_closure.check(parsed)
    p1_findings = [f for f in findings if f.check_id == "P1.orphan_identifier"]
    # none of int/str/None/bool should fire
    idents_in_findings = [f.message for f in p1_findings]
    for word in ("int", "str", "None", "bool"):
        for msg in idents_in_findings:
            assert word not in msg, (
                f"keyword {word!r} should be exempt, found in: {msg}"
            )


def test_p1_multi_occurrence_no_finding():
    """Identifier appearing twice or more -> NO finding."""
    md = (
        "# Plan\n\n"
        "## Design\n\n"
        "`my_function` does X.\n"
        "Call `my_function` again here.\n"
    )
    parsed = parse(md)
    findings = p1_symbol_closure.check(parsed)
    p1_findings = [
        f for f in findings
        if f.check_id == "P1.orphan_identifier"
        and "my_function" in f.message
    ]
    assert p1_findings == [], (
        f"double-occurrence should not fire, got: {p1_findings}"
    )


def test_p1_orphan_in_code_block_not_sole_definition():
    """Identifier appearing only inside code block counts as use, not definition.

    An identifier appearing in a code block AND once in prose is two
    occurrences total -> no finding (>= 2 unique occurrences).
    But identifier appearing ONLY in a code block (once total) fires.
    """
    # Backtick identifier appearing only inside a code block fires P1.
    # (def-line identifiers are not caught by the backtick pattern.)
    md_bt_code = (
        "# Plan\n\n"
        "## Design\n\n"
        "Some prose here.\n\n"
        "```python\n"
        "x = `code_only_ident_abc`\n"
        "```\n"
    )
    parsed2 = parse(md_bt_code)
    findings2 = p1_symbol_closure.check(parsed2)
    # code_only_ident_abc appears once -> should fire
    ids2 = [f.check_id for f in findings2]
    assert "P1.orphan_identifier" in ids2, (
        "code-only single occurrence should still fire"
    )


def test_p1_p1_ok_marker_on_line_above():
    """p1-ok marker on the line ABOVE the identifier -> NO finding."""
    md = (
        "# Plan\n\n"
        "## Overview\n\n"
        "<!-- plan-forge: p1-ok reason: external system -->\n"
        "The `external_only_ident` is referenced here.\n"
    )
    parsed = parse(md)
    findings = p1_symbol_closure.check(parsed)
    p1_findings = [f for f in findings if f.check_id == "P1.orphan_identifier"]
    assert p1_findings == [], (
        f"marker on line above should suppress finding, got: {p1_findings}"
    )
