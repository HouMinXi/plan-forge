"""Unit tests for checks/epistemic/_sections.py shared helper."""
from plan_forge.checks.epistemic._sections import find_section
from plan_forge.parser import parse


def _parse(md: str):
    return parse(md)


def test_find_section_single_keyword():
    """Helper finds a section matching one keyword."""
    md = "## Reference Class\n\nSome content.\n"
    parsed = _parse(md)
    sec = find_section(parsed, "reference class")
    assert sec is not None
    assert "Reference Class" in sec.heading


def test_find_section_multiple_keywords():
    """Helper requires ALL keywords to match."""
    md = "## Chaos Response Plan\n\nContent.\n"
    parsed = _parse(md)
    assert find_section(parsed, "chaos", "response") is not None
    assert find_section(parsed, "chaos", "missing") is None


def test_find_section_case_insensitive():
    """Keyword matching is case-insensitive."""
    md = "## Scope Challenge\n\nContent.\n"
    parsed = _parse(md)
    assert find_section(parsed, "SCOPE") is not None
    assert find_section(parsed, "Scope", "Challenge") is not None


def test_find_section_absent():
    """Returns None when no section matches."""
    md = "## Introduction\n\nIntro text.\n"
    parsed = _parse(md)
    assert find_section(parsed, "pre-mortem") is None


def test_find_section_partial_keyword_not_matched():
    """A keyword must appear as a substring of the heading."""
    md = "## Risk Register\n\nContent.\n"
    parsed = _parse(md)
    assert find_section(parsed, "risk") is not None
    assert find_section(parsed, "risk", "taxonomy") is None


def test_find_section_returns_first_match():
    """When multiple sections match, the first is returned."""
    md = "## Chaos Response A\n\nFirst.\n\n## Chaos Response B\n\nSecond.\n"
    parsed = _parse(md)
    sec = find_section(parsed, "chaos", "response")
    assert sec is not None
    assert "First" in sec.body  # must return the FIRST match, not the second
