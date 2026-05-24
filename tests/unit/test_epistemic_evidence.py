"""Tests for checks/epistemic/_evidence.py and llm/prompts loader."""
from __future__ import annotations

import pytest

from plan_forge.checks.epistemic._evidence import (
    G6_VERIFIED,
    G8_RESOLVED_BY_KNOWLEDGE,
    G8_RESOLVED_VIA_SEARCH,
    G8_UNCERTAIN,
    PROV_FABRICATED_SEARCH_EVIDENCE,
    PROV_UNBACKED_SEARCH_CLAIM,
    guard_unbacked_search,
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

    def test_deepseek_returns_none(self):
        # deepseek uses the openai SDK with no tool-call loop;
        # schema None makes it answer directly.
        assert schema_for("deepseek") is None

    def test_kimi_returns_none(self):
        # kimi uses the openai SDK with no tool-call loop;
        # schema None makes it answer directly.
        assert schema_for("kimi") is None

    def test_anthropic_not_none_regression(self):
        # anthropic's web_search is server-side; must stay non-None.
        assert schema_for("anthropic") is not None


class TestGuardUnbackedSearch:
    def test_tool_less_search_claim_downgraded(self):
        """Tool-less provider with search-claim verdict is downgraded."""
        resp = LLMResponse(
            verdict=G8_RESOLVED_VIA_SEARCH,
            reasoning="test",
            cited_instances=[],
            search_evidence=[],
            cost_usd=0.0,
            raw_response={},
        )
        prov = guard_unbacked_search(
            ["toolless"],
            [resp],
            {"toolless": None},
            search_claim_verdict=G8_RESOLVED_VIA_SEARCH,
            downgrade_verdict=G8_UNCERTAIN,
        )
        assert resp.verdict == G8_UNCERTAIN
        assert prov == {"toolless": PROV_UNBACKED_SEARCH_CLAIM}

    def test_tool_less_knowledge_verdict_fabricated_evidence_flagged(self):
        """Tool-less provider with non-search verdict but search_evidence."""
        resp = LLMResponse(
            verdict=G8_RESOLVED_BY_KNOWLEDGE,
            reasoning="test",
            cited_instances=[],
            search_evidence=[{"url": "http://fake.url"}],
            cost_usd=0.0,
            raw_response={},
        )
        prov = guard_unbacked_search(
            ["toolless"],
            [resp],
            {"toolless": None},
            search_claim_verdict=G8_RESOLVED_VIA_SEARCH,
            downgrade_verdict=G8_UNCERTAIN,
        )
        assert resp.verdict == G8_RESOLVED_BY_KNOWLEDGE
        assert prov == {"toolless": PROV_FABRICATED_SEARCH_EVIDENCE}

    def test_tool_less_knowledge_no_evidence_no_flag(self):
        """Tool-less provider with knowledge claim and no evidence is fine."""
        resp = LLMResponse(
            verdict=G8_RESOLVED_BY_KNOWLEDGE,
            reasoning="test",
            cited_instances=[],
            search_evidence=[],
            cost_usd=0.0,
            raw_response={},
        )
        prov = guard_unbacked_search(
            ["toolless"],
            [resp],
            {"toolless": None},
            search_claim_verdict=G8_RESOLVED_VIA_SEARCH,
            downgrade_verdict=G8_UNCERTAIN,
        )
        assert resp.verdict == G8_RESOLVED_BY_KNOWLEDGE
        assert prov == {}

    def test_provider_with_tool_not_downgraded(self):
        """Provider with a tool is not downgraded."""
        resp = LLMResponse(
            verdict=G8_RESOLVED_VIA_SEARCH,
            reasoning="test",
            cited_instances=[],
            search_evidence=[],
            cost_usd=0.0,
            raw_response={},
        )
        prov = guard_unbacked_search(
            ["withtool"],
            [resp],
            {"withtool": {"type": "web_search"}},
            search_claim_verdict=G8_RESOLVED_VIA_SEARCH,
            downgrade_verdict=G8_UNCERTAIN,
        )
        assert resp.verdict == G8_RESOLVED_VIA_SEARCH
        assert prov == {}

    def test_case_whitespace_caught(self):
        """Verdict matching is case-insensitive and strips whitespace."""
        resp = LLMResponse(
            verdict="  resolved_via_search  ",
            reasoning="test",
            cited_instances=[],
            search_evidence=[],
            cost_usd=0.0,
            raw_response={},
        )
        prov = guard_unbacked_search(
            ["toolless"],
            [resp],
            {"toolless": None},
            search_claim_verdict=G8_RESOLVED_VIA_SEARCH,
            downgrade_verdict=G8_UNCERTAIN,
        )
        assert resp.verdict == G8_UNCERTAIN
        assert prov == {"toolless": PROV_UNBACKED_SEARCH_CLAIM}

    def test_errored_verdict_none_no_downgrade(self):
        """Errored provider (verdict=None) is crash-safe."""
        resp = LLMResponse(
            verdict=None,
            reasoning="error",
            cited_instances=[],
            search_evidence=[],
            cost_usd=0.0,
            raw_response={},
        )
        prov = guard_unbacked_search(
            ["errored"],
            [resp],
            {"errored": None},
            search_claim_verdict=G8_RESOLVED_VIA_SEARCH,
            downgrade_verdict=G8_UNCERTAIN,
        )
        assert resp.verdict is None
        assert prov == {}

    def test_errored_verdict_empty_no_downgrade(self):
        """Errored provider (verdict="") is crash-safe."""
        resp = LLMResponse(
            verdict="",
            reasoning="error",
            cited_instances=[],
            search_evidence=[],
            cost_usd=0.0,
            raw_response={},
        )
        prov = guard_unbacked_search(
            ["errored"],
            [resp],
            {"errored": None},
            search_claim_verdict=G8_RESOLVED_VIA_SEARCH,
            downgrade_verdict=G8_UNCERTAIN,
        )
        assert resp.verdict == ""
        assert prov == {}

    def test_flag_only_mode_no_tokens(self):
        """Guard with no tokens only flags fabricated evidence."""
        resp = LLMResponse(
            verdict=G8_RESOLVED_VIA_SEARCH,
            reasoning="test",
            cited_instances=[],
            search_evidence=[{"url": "http://fake.url"}],
            cost_usd=0.0,
            raw_response={},
        )
        prov = guard_unbacked_search(
            ["toolless"],
            [resp],
            {"toolless": None},
        )
        assert resp.verdict == G8_RESOLVED_VIA_SEARCH
        assert prov == {"toolless": PROV_FABRICATED_SEARCH_EVIDENCE}

    def test_both_tokens_or_neither(self):
        """Fail-loud if exactly one token is set."""
        resp = LLMResponse(
            verdict=G8_RESOLVED_VIA_SEARCH,
            reasoning="test",
            cited_instances=[],
            search_evidence=[],
            cost_usd=0.0,
            raw_response={},
        )
        with pytest.raises(ValueError, match="must be set together"):
            guard_unbacked_search(
                ["toolless"],
                [resp],
                {"toolless": None},
                search_claim_verdict=G8_RESOLVED_VIA_SEARCH,
            )
        with pytest.raises(ValueError, match="must be set together"):
            guard_unbacked_search(
                ["toolless"],
                [resp],
                {"toolless": None},
                downgrade_verdict=G8_UNCERTAIN,
            )

    def test_length_precondition(self):
        """Guard fails if active_providers and evidences lengths mismatch."""
        resp = LLMResponse(
            verdict=G8_RESOLVED_VIA_SEARCH,
            reasoning="test",
            cited_instances=[],
            search_evidence=[],
            cost_usd=0.0,
            raw_response={},
        )
        with pytest.raises(AssertionError, match="length mismatch"):
            guard_unbacked_search(
                ["a", "b"],
                [resp],
                {"a": None, "b": None},
                search_claim_verdict=G8_RESOLVED_VIA_SEARCH,
                downgrade_verdict=G8_UNCERTAIN,
            )


class TestResponsesToEvidenceProvenance:
    def test_provenance_maps_to_t4_suspect(self):
        """Provider in vote.provenance gets tier T4_SUSPECT."""
        client_a = MockClient(name="prov_a")
        client_a.model = "model-a"

        resp_a = LLMResponse(
            verdict="VERIFIED",
            reasoning="good",
            cited_instances=[],
            search_evidence=[{"url": "http://fake.url"}],
            cost_usd=0.0,
            raw_response={},
        )

        vote = VoteResult(
            status="single_opinion",
            verdict="VERIFIED",
            evidences=[resp_a],
            active_providers=["prov_a"],
            threshold=None,
            provenance={"prov_a": PROV_FABRICATED_SEARCH_EVIDENCE},
        )

        result = responses_to_evidence(vote, [client_a], "test_v0")
        assert len(result) == 1
        assert result[0].tier == EvidenceTier.T4_SUSPECT

    def test_no_provenance_unclassified(self):
        """Provider NOT in vote.provenance gets tier UNCLASSIFIED."""
        client_a = MockClient(name="prov_a")
        client_a.model = "model-a"

        resp_a = LLMResponse(
            verdict="VERIFIED",
            reasoning="good",
            cited_instances=[],
            search_evidence=[],
            cost_usd=0.0,
            raw_response={},
        )

        vote = VoteResult(
            status="single_opinion",
            verdict="VERIFIED",
            evidences=[resp_a],
            active_providers=["prov_a"],
            threshold=None,
            provenance={},
        )

        result = responses_to_evidence(vote, [client_a], "test_v0")
        assert len(result) == 1
        assert result[0].tier == EvidenceTier.UNCLASSIFIED


class TestPromptLoader:
    def test_loads_existing(self, tmp_path):
        prompt_file = tmp_path / "test_prompt_v0.txt"
        prompt_file.write_text("prompt content here", encoding="utf-8")

        from plan_forge.llm.prompts import load
        import plan_forge.llm.prompts as prompts_mod

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
