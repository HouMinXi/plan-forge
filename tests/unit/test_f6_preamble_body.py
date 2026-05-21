"""Unit tests for F6: preamble-vs-body diff check."""
import pathlib

from plan_forge.parser import parse
from plan_forge.checks.mechanical import f6_preamble_body
from plan_forge.verdict import Severity

_FIXTURES = pathlib.Path(__file__).parent.parent / "fixtures"


def _load(name: str) -> str:
    return (_FIXTURES / name).read_text(encoding="utf-8")


def test_f6_pass_fixture():
    """Pass fixture (preamble=None): no F6 findings expected."""
    parsed = parse(_load("f6_pass.md"))
    # No preamble supplied -> F6 must return []
    findings = f6_preamble_body.check(parsed, preamble=None)
    assert findings == [], f"Expected no findings, got: {findings}"


def test_f6_fail_fixture():
    """Fail fixture: preamble contains a fact absent from plan body."""
    parsed = parse(_load("f6_fail.md"))
    # Preamble has a sentence about database migration not in the plan
    preamble = (
        "All database schema migrations must be reversible and"
        " idempotent to support rollback procedures."
    )
    findings = f6_preamble_body.check(parsed, preamble=preamble)
    ids = [f.check_id for f in findings]
    assert "F6.preamble_only_fact" in ids, (
        f"Expected F6.preamble_only_fact, got: {ids}"
    )


def test_f6_severity():
    """All F6 findings must be LOW severity."""
    parsed = parse(_load("f6_fail.md"))
    preamble = (
        "All database schema migrations must be reversible and"
        " idempotent to support rollback procedures."
    )
    findings = f6_preamble_body.check(parsed, preamble=preamble)
    assert findings, "Need at least one finding to check severity"
    for f in findings:
        assert f.severity == Severity.LOW, (
            f"Expected LOW severity, got {f.severity} for {f.check_id}"
        )


def test_f6_edge_none_and_empty_preamble():
    """Edge case: preamble is None or empty string -> NO findings."""
    parsed = parse(_load("f6_pass.md"))

    findings_none = f6_preamble_body.check(parsed, preamble=None)
    assert findings_none == [], "preamble=None must return []"

    findings_empty = f6_preamble_body.check(parsed, preamble="")
    assert findings_empty == [], "preamble='' must return []"

    findings_ws = f6_preamble_body.check(parsed, preamble="   ")
    assert findings_ws == [], "preamble='   ' must return []"
