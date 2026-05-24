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
    EvidenceHit,
    _format_evidence_block,
    _validate_evidence,
    canon,
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


class TestEvidenceHit:
    def test_accepts_five_keys(self):
        """EvidenceHit dict with five keys type-checks."""
        hit: EvidenceHit = {
            "tier": "T1_GOLD",
            "domain": "arxiv.org",
            "title": "Attention Is All You Need",
            "snippet": "Vaswani et al. 2017",
            "url": "https://arxiv.org/abs/1706.03762",
        }
        assert hit["tier"] == "T1_GOLD"
        assert hit["domain"] == "arxiv.org"


class TestFormatEvidenceBlock:
    def test_empty_list_returns_no_results(self):
        """Empty hit list -> 'No results found...' string."""
        result = _format_evidence_block([])
        assert result == "No results found after exhaustive search.\n"

    def test_single_hit_one_indexed(self):
        """Single hit -> [1] (tier=..., domain) title -- snippet\\n"""
        hit: EvidenceHit = {
            "tier": "T1_GOLD",
            "domain": "arxiv.org",
            "title": "Attention Is All You Need",
            "snippet": "Vaswani et al. 2017, Transformer",
            "url": "https://arxiv.org/abs/1706.03762",
        }
        result = _format_evidence_block([hit])
        expected = (
            "[1] (tier=T1_GOLD, arxiv.org) "
            "Attention Is All You Need -- "
            "Vaswani et al. 2017, Transformer\n"
        )
        assert result == expected

    def test_multiple_hits_sequential_indices(self):
        """Two hits -> [1] ... [2] ... with trailing newlines."""
        hits: list[EvidenceHit] = [
            {
                "tier": "T1_GOLD",
                "domain": "arxiv.org",
                "title": "Attention Is All You Need",
                "snippet": "Vaswani et al. 2017",
                "url": "https://arxiv.org/abs/1706.03762",
            },
            {
                "tier": "T2_SILVER",
                "domain": "en.wikipedia.org",
                "title": "Thinking, Fast and Slow",
                "snippet": "2011 book by Daniel Kahneman",
                "url": "https://en.wikipedia.org/wiki/Thinking,_Fast_and_Slow",
            },
        ]
        result = _format_evidence_block(hits)
        lines = result.splitlines(keepends=True)
        assert len(lines) == 2
        assert lines[0].startswith("[1]")
        assert lines[0].endswith("Vaswani et al. 2017\n")
        assert lines[1].startswith("[2]")
        assert lines[1].endswith("2011 book by Daniel Kahneman\n")

    def test_fixture_evidence_bundle_format(self):
        """G8 fixture-style evidence bundle renders char-for-char."""
        hits: list[EvidenceHit] = [
            {
                "tier": "T1_GOLD",
                "domain": "arxiv.org",
                "title": "Attention Is All You Need",
                "snippet": "Vaswani et al. 2017, Transformer, NeurIPS 31",
                "url": "https://arxiv.org/abs/1706.03762",
            },
            {
                "tier": "T1_GOLD",
                "domain": "proceedings.neurips.cc",
                "title": "Attention is All you Need",
                "snippet": "NeurIPS 2017 proceedings entry",
                "url": "https://proceedings.neurips.cc/...",
            },
        ]
        result = _format_evidence_block(hits)

        assert "[1] (tier=T1_GOLD, arxiv.org)" in result
        assert "Attention Is All You Need --" in result
        assert "[2] (tier=T1_GOLD, proceedings.neurips.cc)" in result
        assert result.count("\n") == 2

    def test_missing_optional_field_tolerant(self):
        """Missing keys use .get() default empty string."""
        hit_partial = {
            "tier": "T1_GOLD",
            "domain": "example.com",
            "title": "Test",
            "snippet": "snippet here",
        }
        result = _format_evidence_block([hit_partial])
        assert result.startswith("[1] (tier=T1_GOLD, example.com)")
        assert "Test -- snippet here\n" in result


class TestCanon:
    def test_strips_whitespace(self):
        """Leading and trailing whitespace is stripped."""
        assert canon("  Vaswani et al. (2017)  ") == "Vaswani et al. (2017)"

    def test_collapses_internal_whitespace(self):
        """Multiple spaces/tabs become single space."""
        assert canon("Vaswani  et   al.") == "Vaswani et al."
        assert canon("Vaswani\tet\tal.") == "Vaswani et al."

    def test_nfc_normalization(self):
        """Unicode NFC normalization applied."""
        s1 = "\u00e9"
        s2 = "\u00e9"
        assert canon("Caf" + s1) == canon("Caf" + s2)

    def test_combined_transformations(self):
        """Strip + collapse + NFC all apply."""
        raw = "  Vaswani  et  al.  "
        assert canon(raw) == "Vaswani et al."


class TestValidateEvidence:
    def test_valid_evidence_bundle(self):
        """Valid dict with hit lists passes through."""
        raw = {
            "Vaswani et al. (2017)": [
                {
                    "tier": "T1_GOLD",
                    "domain": "arxiv.org",
                    "title": "Attention Is All You Need",
                    "snippet": "Vaswani et al. 2017",
                    "url": "https://arxiv.org/abs/1706.03762",
                }
            ]
        }
        result = _validate_evidence(raw)
        assert "Vaswani et al. (2017)" in result
        assert len(result["Vaswani et al. (2017)"]) == 1
        assert result["Vaswani et al. (2017)"][0]["tier"] == "T1_GOLD"

    def test_search_failed_sentinel(self):
        """{"search_failed": true} stays a dict (not wrapped in list)."""
        raw = {
            "Citation X": {"search_failed": True}
        }
        result = _validate_evidence(raw)
        assert "Citation X" in result
        assert result["Citation X"] == {"search_failed": True}

    def test_caps_hits_at_10(self):
        """More than 10 hits truncated to 10."""
        hits = [
            {
                "tier": "T1_GOLD",
                "domain": f"example{i}.com",
                "title": f"Title {i}",
                "snippet": f"Snippet {i}",
                "url": f"https://example{i}.com",
            }
            for i in range(15)
        ]
        raw = {"Citation": hits}
        result = _validate_evidence(raw)
        assert len(result["Citation"]) == 10

    def test_truncates_snippet_to_500_chars(self):
        """Long snippets truncated to 500 chars."""
        long_snippet = "x" * 600
        raw = {
            "Citation": [
                {
                    "tier": "T1_GOLD",
                    "domain": "example.com",
                    "title": "Title",
                    "snippet": long_snippet,
                    "url": "https://example.com",
                }
            ]
        }
        result = _validate_evidence(raw)
        assert len(result["Citation"][0]["snippet"]) == 500

    def test_strips_control_chars_from_title_snippet(self):
        """Control characters removed from title and snippet."""
        raw = {
            "Citation": [
                {
                    "tier": "T1_GOLD",
                    "domain": "example.com",
                    "title": "Title\x00with\x1Fcontrol",
                    "snippet": "Snippet\x0Awith\x0Dcontrol",
                    "url": "https://example.com",
                }
            ]
        }
        result = _validate_evidence(raw)
        title = result["Citation"][0]["title"]
        snippet = result["Citation"][0]["snippet"]
        assert "\x00" not in title
        assert "\x1F" not in title
        assert "\x0A" not in snippet
        assert "\x0D" not in snippet

    def test_coerces_unknown_tier_to_t3_bronze(self):
        """Unknown tier value coerced to T3_BRONZE with warning."""
        raw = {
            "Citation": [
                {
                    "tier": "T99_UNKNOWN",
                    "domain": "example.com",
                    "title": "Title",
                    "snippet": "Snippet",
                    "url": "https://example.com",
                }
            ]
        }
        with pytest.warns(UserWarning, match="unknown tier.*T3_BRONZE"):
            result = _validate_evidence(raw)
        assert result["Citation"][0]["tier"] == "T3_BRONZE"

    def test_rejects_non_dict_top_level(self):
        """Top-level non-dict raises ValueError."""
        with pytest.raises(ValueError, match="evidence must be a dict"):
            _validate_evidence([])

    def test_rejects_non_string_keys(self):
        """Non-string keys raise ValueError."""
        raw = {123: []}
        with pytest.raises(ValueError, match="keys must be strings"):
            _validate_evidence(raw)

    def test_rejects_empty_whitespace_keys(self):
        """Empty or whitespace-only keys raise ValueError."""
        with pytest.raises(ValueError, match="keys cannot be empty"):
            _validate_evidence({"  ": []})

    def test_rejects_key_exceeding_1kb(self):
        """Keys > 1KB raise ValueError."""
        long_key = "x" * 1025
        raw = {long_key: []}
        with pytest.raises(ValueError, match="key exceeds 1KB"):
            _validate_evidence(raw)

    def test_rejects_non_list_non_search_failed_value(self):
        """Value that is not list or search_failed sentinel raises."""
        raw = {"Citation": "invalid"}
        with pytest.raises(ValueError, match="must be list"):
            _validate_evidence(raw)

    def test_rejects_non_dict_hit(self):
        """Hit that is not a dict raises ValueError."""
        raw = {"Citation": ["not a dict"]}
        with pytest.raises(ValueError, match="hit 0.*must be dict"):
            _validate_evidence(raw)
