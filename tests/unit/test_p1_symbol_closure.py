"""Unit tests for P1: Symbol closure check."""
import pathlib

from plan_forge.parser import parse
from plan_forge.checks.pbr import p1_symbol_closure
from plan_forge.verdict import Severity

_FIXTURES = pathlib.Path(__file__).parent.parent / "fixtures"


def _load(name: str) -> str:
    return (_FIXTURES / name).read_text(encoding="utf-8")


def _p1(findings: list) -> list:
    return [f for f in findings if f.check_id == "P1.orphan_identifier"]


# Mandatory fixture tests

def test_p1_pass_fixture():
    """Pass fixture: no P1 findings expected."""
    parsed = parse(_load("p1_pass.md"))
    assert _p1(p1_symbol_closure.check(parsed)) == []


def test_p1_fail_fixture():
    """Fail fixture: at least one P1.orphan_identifier finding expected."""
    parsed = parse(_load("p1_fail.md"))
    ids = [f.check_id for f in p1_symbol_closure.check(parsed)]
    assert "P1.orphan_identifier" in ids


def test_p1_severity():
    """All P1 findings must be HIGH severity."""
    parsed = parse(_load("p1_fail.md"))
    findings = _p1(p1_symbol_closure.check(parsed))
    assert findings, "Need at least one finding to check severity"
    for f in findings:
        assert f.severity == Severity.HIGH


# Code-symbol exemption: FP fixture must produce zero findings

def test_p1_codesymbol_fp_fixture():
    """Code symbols (dunders, dotted paths, filenames, lowercase) -> NO P1."""
    parsed = parse(_load("p1_codesymbol_fp.md"))
    findings = _p1(p1_symbol_closure.check(parsed))
    assert findings == [], (
        f"Code symbols must not fire P1, got: {findings}"
    )


# Plan identifier TP fixture: orphaned CapWords + SC-N must still fire

def test_p1_planid_tp_fixture():
    """CapWords term and SC-N used once with no cross-ref -> P1 fires."""
    parsed = parse(_load("p1_planid_tp.md"))
    findings = _p1(p1_symbol_closure.check(parsed))
    messages = " ".join(f.message for f in findings)
    assert "WidgetRegistry" in messages or "SC-91" in messages, (
        f"Expected WidgetRegistry or SC-91 orphan finding, got: {findings}"
    )


# Edge case: p1-ok marker suppresses a CapWords orphan

def test_p1_marker_exemption():
    """p1-ok marker on same line suppresses a CapWords orphan identifier."""
    md = (
        "# Plan\n\n"
        "## Overview\n\n"
        "The `ExternalRegistry` is an upstream component. "
        "<!-- plan-forge: p1-ok intentionally external -->\n"
    )
    parsed = parse(md)
    assert _p1(p1_symbol_closure.check(parsed)) == []


# References section exempts a CapWords identifier used once there

def test_p1_cross_reference_section_exemption():
    """CapWords identifier in ## References -> NO finding."""
    md = (
        "# Plan\n\n"
        "## Overview\n\n"
        "This plan covers system design.\n\n"
        "## References\n\n"
        "- `UpstreamArtifact` is defined in the parent plan.\n"
    )
    parsed = parse(md)
    assert _p1(p1_symbol_closure.check(parsed)) == []


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
    findings = _p1(p1_symbol_closure.check(parsed))
    msgs = " ".join(f.message for f in findings)
    for word in ("int", "str", "None", "bool"):
        assert word not in msgs, f"keyword {word!r} should be exempt"


def test_p1_multi_occurrence_no_finding():
    """CapWords identifier appearing twice -> NO finding."""
    md = (
        "# Plan\n\n"
        "## Design\n\n"
        "`MyComponent` does X.\n"
        "Call `MyComponent` again here.\n"
    )
    parsed = parse(md)
    findings = [
        f for f in p1_symbol_closure.check(parsed)
        if f.check_id == "P1.orphan_identifier"
        and "MyComponent" in f.message
    ]
    assert findings == []


def test_p1_orphan_capwords_in_code_block_fires():
    """CapWords identifier appearing only inside a code block -> P1 fires.

    Code blocks are illustrative (not definitions).  A CapWords plan term
    appearing once in a code block with no prose mention is still orphaned.
    """
    md = (
        "# Plan\n\n"
        "## Design\n\n"
        "Some prose here.\n\n"
        "```python\n"
        "x = `PlanRegistry`\n"
        "```\n"
    )
    parsed = parse(md)
    findings = p1_symbol_closure.check(parsed)
    ids = [f.check_id for f in findings]
    assert "P1.orphan_identifier" in ids, (
        "CapWords in code block only should still fire P1"
    )


def test_p1_lowercase_code_symbol_exempt():
    """All-lowercase backtick tokens are code symbols -> NO P1 finding."""
    md = (
        "# Plan\n\n"
        "## Overview\n\n"
        "The provider name `anthropic` is passed to the constructor.\n"
        "Override `tool_use` to customize the payload.\n"
        "The hash field `plan_hash` caches the document fingerprint.\n"
    )
    parsed = parse(md)
    assert _p1(p1_symbol_closure.check(parsed)) == []


def test_p1_dunder_exempt():
    """Dunder names are code symbols -> NO P1 finding."""
    md = (
        "# Plan\n\n"
        "## Overview\n\n"
        "Override `__exit__` to release the resource on scope exit.\n"
        "The `__init__` method initialises instance state.\n"
    )
    parsed = parse(md)
    assert _p1(p1_symbol_closure.check(parsed)) == []


def test_p1_filename_exempt():
    """Filenames (known extensions) are code symbols -> NO P1 finding."""
    md = (
        "# Plan\n\n"
        "## Overview\n\n"
        "Test scripts live in `foo.py`.\n"
        "Documentation is in `MANIFESTO.md`.\n"
        "Schema in `schema.sql` and config in `settings.toml`.\n"
    )
    parsed = parse(md)
    assert _p1(p1_symbol_closure.check(parsed)) == []


def test_p1_dotted_path_exempt():
    """Dotted paths are code symbols -> NO P1 finding."""
    md = (
        "# Plan\n\n"
        "## Overview\n\n"
        "The entry point is `checks.mechanical.run`.\n"
        "Access results via `result.verdict` for the gate output.\n"
    )
    parsed = parse(md)
    assert _p1(p1_symbol_closure.check(parsed)) == []


def test_p1_p1_ok_marker_on_line_above():
    """p1-ok marker on the line ABOVE a CapWords identifier -> NO finding."""
    md = (
        "# Plan\n\n"
        "## Overview\n\n"
        "<!-- plan-forge: p1-ok reason: external system -->\n"
        "The `ExternalGateway` is referenced here.\n"
    )
    parsed = parse(md)
    assert _p1(p1_symbol_closure.check(parsed)) == []


# Table-definition exemption: FP fixture must produce zero findings

def test_p1_table_def_fp_fixture():
    """Structured IDs defined as first table cells -> NO P1 finding."""
    parsed = parse(_load("p1_table_def_fp.md"))
    findings = _p1(p1_symbol_closure.check(parsed))
    assert findings == [], (
        f"Table-defined structured IDs must not fire P1, got: {findings}"
    )


def test_p1_table_def_inline():
    """Structured ID defined only in a table first cell -> NO P1 finding.

    The ID appears exactly once, as the leading cell of a table row, with
    no prose mention anywhere else.  A single occurrence would normally be
    flagged as an orphan; the table row IS the definition, so P1 must stay
    silent.  This isolates the table-definition rule: the ID occurs once,
    so the duplicate-occurrence shortcut cannot mask a regression here.
    """
    md = (
        "# Plan\n\n"
        "## Success Criteria\n\n"
        "| ID | Criterion | Fail Condition |\n"
        "|----|-----------|----------------|\n"
        "| SC-7 | The widget loads correctly | widget absent |\n"
    )
    parsed = parse(md)
    findings = _p1(p1_symbol_closure.check(parsed))
    msgs = " ".join(f.message for f in findings)
    assert "SC-7" not in msgs, (
        "table-defined structured ID should be exempt from P1"
    )


# ALL_CAPS constant exemption: FP fixture must produce zero findings

def test_p1_allcaps_const_fp_fixture():
    """ALL_CAPS env-var constant in backticks -> NO P1 finding."""
    parsed = parse(_load("p1_allcaps_const_fp.md"))
    findings = _p1(p1_symbol_closure.check(parsed))
    assert findings == [], (
        f"ALL_CAPS constant must not fire P1, got: {findings}"
    )


def test_p1_allcaps_const_inline():
    """Backtick ALL_CAPS token is a constant -> NO P1 finding."""
    md = (
        "# Plan\n\n"
        "## Config\n\n"
        "Set `MY_API_KEY` to the credential from the vault.\n"
    )
    parsed = parse(md)
    findings = _p1(p1_symbol_closure.check(parsed))
    msgs = " ".join(f.message for f in findings)
    assert "MY_API_KEY" not in msgs, (
        "ALL_CAPS constant should be exempt from P1"
    )


# Code-type exemption: FP fixture must produce zero findings

def test_p1_code_type_fp_fixture():
    """CapWords token defined via return annotation in code block -> NO P1."""
    parsed = parse(_load("p1_code_type_fp.md"))
    findings = _p1(p1_symbol_closure.check(parsed))
    assert findings == [], (
        f"Code-block type annotation must not fire P1, got: {findings}"
    )


def test_p1_code_type_class_def_inline():
    """CapWords defined via 'class X' in a code block -> NO P1."""
    md = (
        "# Plan\n\n"
        "## Design\n\n"
        "The `DataRecord` holds each row.\n\n"
        "```python\n"
        "class DataRecord:\n"
        "    pass\n"
        "```\n"
    )
    parsed = parse(md)
    findings = _p1(p1_symbol_closure.check(parsed))
    msgs = " ".join(f.message for f in findings)
    assert "DataRecord" not in msgs, (
        "class-defined CapWords should be exempt from P1"
    )


def test_p1_orphan_capwords_value_assignment_still_fires():
    """CapWords in code block only as a backtick value, not a type -> fires.

    A backtick-wrapped CapWords token inside a code block that appears only
    as a value assignment (x = `PlanRegistry`) does NOT satisfy the type-
    annotation shape requirement.  It remains an orphan and P1 must fire.
    """
    md = (
        "# Plan\n\n"
        "## Design\n\n"
        "Some prose here.\n\n"
        "```python\n"
        "x = `PlanRegistry`\n"
        "```\n"
    )
    parsed = parse(md)
    findings = p1_symbol_closure.check(parsed)
    ids = [f.check_id for f in findings]
    assert "P1.orphan_identifier" in ids, (
        "CapWords value-assignment in code block should still fire P1"
    )
