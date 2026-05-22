"""Public API surface lock + version assertion for v0.1.0-alpha2."""
from __future__ import annotations

from pathlib import Path

import plan_forge
from plan_forge import Verdict


_FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"


class TestVersion:
    def test_version_is_alpha2(self):
        """Imported package version must equal 0.1.0a2."""
        assert plan_forge.__version__ == "0.1.0a2"


class TestPublicSurface:
    def test_public_surface_importable(self):
        """All five public symbols must be importable from plan_forge."""
        from plan_forge import check, scaffold, Verdict, Finding, Severity  # noqa: F401

    def test_all_list_exact(self):
        """__all__ must equal the expected 5-name list (no accidental additions)."""
        expected = ["check", "scaffold", "Verdict", "Finding", "Severity"]
        assert plan_forge.__all__ == expected

    def test_all_symbols_present_in_module(self):
        """Every name in __all__ must resolve as an attribute of the module."""
        for name in plan_forge.__all__:
            assert hasattr(plan_forge, name), f"plan_forge.{name} is missing"


class TestCheckReturnsVerdict:
    def test_check_returns_verdict_mechanical_only(self):
        """check() with llm_clients=[] returns a Verdict with required attributes.

        Using llm_clients=[] forces mechanical-only mode: no network, deterministic.
        """
        fixture = (_FIXTURES / "g1_pass.md").read_text()
        result = plan_forge.check(fixture, llm_clients=[])

        assert isinstance(result, Verdict)
        # Must have the three required attributes.
        assert hasattr(result, "engineering")
        assert hasattr(result, "epistemic")
        assert hasattr(result, "findings")
        # findings must be a list (may be empty for a passing fixture).
        assert isinstance(result.findings, list)
