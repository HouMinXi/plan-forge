"""Tests for checks/epistemic/_evidence.py and llm/prompts loader."""
from __future__ import annotations

import pytest

from plan_forge.checks.epistemic._evidence import (
    G6_VERIFIED,
    is_genuine_split,
    responses_to_evidence,
    schema_for,
    verdict_matches,
)
from plan_forge.llm.client import LLMResponse
from plan_forge.llm.mocks import MockClient
from plan_forge.llm.search_vote import VoteResult
from plan_forge.verdict import EvidenceTier


class TestVerdictMatches:
    def test_case_insensitive_match(self):
        assert verdict_matches("verified", G6_VERIFIED) is True
        assert verdict_matches("VERIFIED", G6_VERIFIED) is True
        assert verdict_matches("  Verified  ", G6_VERIFIED) is True

    def test_none_returns_false(self):
        assert verdict_matches(None, G6_VERIFIED) is False

    def test_mismatch(self):
        assert verdict_matches("UNVERIFIED", G6_VERIFIED) is False


class TestResponsesToEvidence:
    def test_maps_provider_model(self):
        client_a = MockClient(name="prov_a")
        client_a.model = "model-a"
        client_b = MockClient(name="prov_b")
        client_b.model = "model-b"

        resp_a = LLMResponse(
            verdict="VERIFIED", reasoning="good",
            cited_instances=[], search_evidence=[],
            cost_usd=0.0, raw_response={},
        )
        resp_b = LLMResponse(
            verdict="UNVERIFIED", reasoning="bad",
            cited_instances=[{"snippet": "x", "issue": "y"}],
            search_evidence=[],
            cost_usd=0.0, raw_response={},
        )

        vote = VoteResult(
            status="consensus",
            verdict="VERIFIED",
            evidences=[resp_a, resp_b],
            active_providers=["prov_a", "prov_b"],
            threshold=None,
        )

        result = responses_to_evidence(vote, [client_a, client_b], "test_v0")
        assert len(result) == 2
        assert result[0].provider == "prov_a"
        assert result[0].model == "model-a"
        assert result[0].run_id == 0
        assert result[0].tier == EvidenceTier.UNCLASSIFIED
        assert result[0].prompt_version == "test_v0"
        assert result[1].provider == "prov_b"
        assert result[1].model == "model-b"
        assert result[1].cited_instances == [{"snippet": "x", "issue": "y"}]


def _resp(verdict: str) -> LLMResponse:
    """Build a minimal LLMResponse with the given verdict."""
    return LLMResponse(
        verdict=verdict,
        reasoning="test",
        cited_instances=[],
        search_evidence=[],
        cost_usd=0.0,
        raw_response={},
    )


def _vote(evidences: list[LLMResponse]) -> VoteResult:
    """Build a VoteResult with indeterminate status."""
    return VoteResult(
        status="indeterminate",
        verdict=None,
        evidences=evidences,
        active_providers=[f"p{i}" for i in range(len(evidences))],
        threshold=None,
    )


class TestIsGenuineSplit:
    def test_verified_unverified_is_split(self):
        """Two distinct non-empty verdicts -> True."""
        vote = _vote([_resp("VERIFIED"), _resp("UNVERIFIED")])
        assert is_genuine_split(vote) is True

    def test_same_verdict_different_case_not_split(self):
        """'verified' vs 'VERIFIED' normalizes to same -> False."""
        vote = _vote([_resp("verified"), _resp("VERIFIED")])
        assert is_genuine_split(vote) is False

    def test_one_empty_not_split(self):
        """One non-empty + one empty verdict -> only one distinct -> False."""
        vote = _vote([_resp("VERIFIED"), _resp("")])
        assert is_genuine_split(vote) is False

    def test_both_empty_not_split(self):
        """Both empty verdicts -> zero distinct -> False."""
        vote = _vote([_resp(""), _resp("")])
        assert is_genuine_split(vote) is False

    def test_single_evidence_not_split(self):
        """Single provider -> one distinct verdict -> False."""
        vote = _vote([_resp("VERIFIED")])
        assert is_genuine_split(vote) is False


class TestSchemaFor:
    def test_known_provider(self):
        s = schema_for("anthropic")
        assert s is not None
        assert "type" in s

    def test_unknown_provider_returns_none(self):
        assert schema_for("nonexistent") is None

    def test_mimo_returns_none(self):
        # MIMO_WEB_SEARCH_TOOL is None
        assert schema_for("mimo") is None


class TestPromptLoader:
    def test_loads_existing(self, tmp_path):
        # Create a temp prompt file to test the loader mechanism
        prompt_file = tmp_path / "test_prompt_v0.txt"
        prompt_file.write_text("prompt content here", encoding="utf-8")

        from plan_forge.llm.prompts import load
        import plan_forge.llm.prompts as prompts_mod

        # Temporarily override _PROMPT_DIR
        original = prompts_mod._PROMPT_DIR
        prompts_mod._PROMPT_DIR = tmp_path
        try:
            text = load("test_prompt_v0")
            assert text == "prompt content here"
        finally:
            prompts_mod._PROMPT_DIR = original

    def test_missing_raises(self):
        from plan_forge.llm.prompts import load
        with pytest.raises(FileNotFoundError, match="prompt not found"):
            load("nonexistent_prompt_v99")
