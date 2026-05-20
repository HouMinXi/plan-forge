"""Tests for Verdict.active_providers field."""
from __future__ import annotations

from plan_forge.verdict import (
    EngineeringVerdict,
    EpistemicVerdict,
    Verdict,
)


class TestVerdictActiveProviders:
    def test_default_empty(self):
        """active_providers defaults to empty list."""
        v = Verdict(
            engineering=EngineeringVerdict.PASS,
            epistemic=EpistemicVerdict.VISION,
        )
        assert v.active_providers == []

    def test_round_trips(self):
        """Set active_providers; verify shape and content."""
        v = Verdict(
            engineering=EngineeringVerdict.PASS,
            epistemic=EpistemicVerdict.VISION,
            active_providers=["anthropic", "kimi"],
        )
        assert isinstance(v.active_providers, list)
        assert "anthropic" in v.active_providers
        assert len(v.active_providers) == 2

    def test_backward_compat_keyword_args(self):
        """Existing callers using keyword args still work after field addition."""
        v = Verdict(
            engineering=EngineeringVerdict.FAIL,
            epistemic=EpistemicVerdict.FAIL,
            findings=[],
            tier_summary={"G1": "PASS"},
        )
        assert v.active_providers == []
        assert v.tier_summary == {"G1": "PASS"}


class TestApiCheckMechanicalLeavesActiveProvidersEmpty:
    def test_check_mechanical_no_active_providers(self):
        """api.check_mechanical does not populate active_providers (no LLM ran)."""
        from plan_forge.api import check_mechanical

        plan_text = """## Title

## Objective
something

## Success Criteria

| ID | Name | Pass | Fail |
|----|------|------|------|
| SC-1 | X | pass | fail |

## Dependencies

none

## Timeline

2026-01 to 2026-03

## Risk Register

### Known Risks

none

## External Voices

none

## Reference Class

none
"""
        verdict = check_mechanical(plan_text)
        assert verdict.active_providers == []
