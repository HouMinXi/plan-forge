"""Unit tests for plan_forge.scaffold.render().

Phase 1 tests: rendering basics and required section presence.
"""
from __future__ import annotations

from plan_forge.scaffold import render

_REQUIRED_SECTIONS = [
    "## Success Criteria",
    "## Test Plan",
    "## Overview",
    "## Deliverables",
    "## Module Designs",
    "## Implementation Tasks",
    "## Reference Class",
    "## Risks",
    "## Pre-mortem",
    "## Scope Challenge",
    "## Chaos Response",
    "## External Voices",
]


def test_render_contains_title() -> None:
    """render() places the plan name in the H1 heading."""
    result = render("my-plan")
    assert "# my-plan" in result


def test_render_title_in_h1_not_just_anywhere() -> None:
    """The plan name appears as an H1 (single #) heading."""
    result = render("test-title")
    lines = result.splitlines()
    h1_lines = [ln for ln in lines if ln.startswith("# ") and not ln.startswith("## ")]
    assert any("test-title" in ln for ln in h1_lines)


def test_render_has_all_sections() -> None:
    """All required ## section headings are present in the skeleton."""
    result = render("any-name")
    for section in _REQUIRED_SECTIONS:
        assert section in result, f"missing section: {section!r}"


def test_render_is_deterministic() -> None:
    """Two render() calls with the same name produce identical output."""
    first = render("alpha")
    second = render("alpha")
    assert first == second


def test_render_name_substitution() -> None:
    """Different names produce different output (title is not hardcoded)."""
    result_a = render("project-a")
    result_b = render("project-b")
    assert result_a != result_b
    assert "# project-a" in result_a
    assert "# project-b" in result_b


def test_render_returns_str() -> None:
    """render() returns a plain string."""
    assert isinstance(render("x"), str)


def test_render_ends_with_newline() -> None:
    """render() output ends with a newline (keep_trailing_newline=True)."""
    result = render("n")
    assert result.endswith("\n")
