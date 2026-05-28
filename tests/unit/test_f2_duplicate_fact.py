"""Unit tests for F2: duplicate fact lint check."""
import pathlib

from plan_forge.parser import parse
from plan_forge.checks.mechanical import f2_duplicate_fact
from plan_forge.verdict import Severity

_FIXTURES = pathlib.Path(__file__).parent.parent / "fixtures"


def _load(name: str) -> str:
    return (_FIXTURES / name).read_text(encoding="utf-8")


def test_f2_pass_fixture():
    """Pass fixture: no F2 findings expected."""
    parsed = parse(_load("f2_pass.md"))
    findings = f2_duplicate_fact.check(parsed)
    assert findings == [], f"Expected no findings, got: {findings}"


def test_f2_fail_fixture():
    """Fail fixture: at least one F2.duplicate_fact finding expected."""
    parsed = parse(_load("f2_fail.md"))
    findings = f2_duplicate_fact.check(parsed)
    ids = [f.check_id for f in findings]
    assert "F2.duplicate_fact" in ids, f"Expected F2.duplicate_fact, got: {ids}"


def test_f2_severity():
    """All F2 findings must be LOW severity."""
    parsed = parse(_load("f2_fail.md"))
    findings = f2_duplicate_fact.check(parsed)
    assert findings, "Need at least one finding to check severity"
    for f in findings:
        assert f.severity == Severity.LOW, (
            f"Expected LOW severity, got {f.severity} for {f.check_id}"
        )


def test_f2_edge_exactly_two_sections():
    """Edge case: ngram in exactly 2 sections -> NO finding (boundary).

    Note: no h1 parent so sections are siblings; parser.py inclusive
    body accumulation only affects nested sections under a shared parent.
    """
    md = (
        "## Section One\n"
        "\n"
        "DatabaseConnection Pool is used here.\n"
        "\n"
        "## Section Two\n"
        "\n"
        "DatabaseConnection Pool is also used here.\n"
    )
    parsed = parse(md)
    findings = f2_duplicate_fact.check(parsed)
    # Exactly 2 sections is below the threshold of >= 3, so no F2 finding
    assert findings == [], (
        f"Expected no findings for ngram in 2 sections, got: {findings}"
    )


def test_f2_heading_fp_suppressed():
    parsed = parse(_load("f2_heading_fp.md"))
    findings = f2_duplicate_fact.check(parsed)
    assert findings == [], (
        f"Expected heading-derived n-gram suppressed, got: {findings}"
    )


def test_f2_genuine_phrase_not_suppressed():
    parsed = parse(_load("f2_fail.md"))
    findings = f2_duplicate_fact.check(parsed)
    ids = [f.check_id for f in findings]
    assert "F2.duplicate_fact" in ids, (
        f"Expected genuine repetition still fires, got: {ids}"
    )
