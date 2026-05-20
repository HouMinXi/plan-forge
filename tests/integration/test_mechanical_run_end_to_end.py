"""Integration test: mechanical.run() on all existing check fixtures.

Smoke-tests that run() returns list[Finding] without raising for any
of the three plan fixtures.  Does NOT assert specific findings because
those fixtures were designed for G1-G10 validation.
"""
import pathlib

import pytest

from plan_forge.parser import parse
from plan_forge.checks import mechanical
from plan_forge.verdict import Finding

_FIXTURES = pathlib.Path(__file__).parent.parent / "fixtures"

_PLAN_FIXTURES = [
    "pass_well_formed.md",
    "fail_missing_premortem.md",
    "fail_no_g9_anchor.md",
]


@pytest.mark.parametrize("fixture_name", _PLAN_FIXTURES)
def test_mechanical_run_does_not_raise(fixture_name: str):
    """run() must return list[Finding] and not raise for any existing fixture."""
    text = (_FIXTURES / fixture_name).read_text(encoding="utf-8")
    parsed = parse(text)
    result = mechanical.run(parsed)
    assert isinstance(result, list), (
        f"run() must return list, got {type(result)}"
    )
    for item in result:
        assert isinstance(item, Finding), (
            f"Each element must be Finding, got {type(item)}: {item!r}"
        )


def test_mechanical_run_with_preamble_does_not_raise():
    """run() with preamble kwarg must not raise."""
    text = (_FIXTURES / "pass_well_formed.md").read_text(encoding="utf-8")
    parsed = parse(text)
    result = mechanical.run(parsed, preamble="Some context about the plan.")
    assert isinstance(result, list)
