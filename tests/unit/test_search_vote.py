"""Tests for llm/search_vote.py (Phase 4).

All 7 mandated tests from SUBSPEC 7.2.
"""
from __future__ import annotations

import warnings


from plan_forge.llm.client import LLMResponse
from plan_forge.llm.mocks import MockClient
from plan_forge.llm.search_vote import search_vote


def _client(name: str, verdict: str) -> MockClient:
    resp = LLMResponse(verdict=verdict, reasoning="")
    return MockClient(name=name, responses={"": resp})


def _vote(*pairs, **kwargs):
    """Helper: search_vote over clients built from (name, verdict) pairs."""
    clients = [_client(name, verdict) for name, verdict in pairs]
    return search_vote(
        "test prompt",
        clients,
        cache_key_inputs={"plan": "test"},
        tool_use_schemas={name: None for name, _ in pairs},
        **kwargs,
    )


class TestSearchVoteN0:
    def test_returns_no_providers(self):
        result = _vote()
        assert result.status == "no_providers"
        assert result.verdict is None
        assert result.evidences == []
        assert result.active_providers == []


class TestSearchVoteN1:
    def test_returns_single_opinion(self):
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            result = _vote(("a", "PASS"))
        assert result.status == "single_opinion"
        assert result.verdict == "PASS"
        assert len(result.active_providers) == 1
        # Warning should be emitted
        assert any("single provider" in str(x.message) for x in w)


class TestSearchVoteN2:
    def test_agree_returns_consensus(self):
        result = _vote(("a", "PASS"), ("b", "PASS"))
        assert result.status == "consensus"
        assert result.verdict == "PASS"

    def test_disagree_returns_indeterminate(self):
        result = _vote(("a", "PASS"), ("b", "FAIL"))
        assert result.status == "indeterminate"
        assert result.verdict is None


class TestSearchVoteN3:
    def test_majority_2_of_3(self):
        """2/3 agree on PASS -> majority."""
        result = _vote(("a", "PASS"), ("b", "PASS"), ("c", "FAIL"))
        assert result.status == "majority"
        assert result.verdict == "PASS"
        assert result.threshold == 2

    def test_split_all_different_indeterminate(self):
        """All 3 different -> indeterminate (no majority possible)."""
        result = _vote(("a", "PASS"), ("b", "FAIL"), ("c", "VISION"))
        assert result.status == "indeterminate"
        assert result.verdict is None


class TestSearchVoteN4:
    def test_3_of_4_majority(self):
        """3/4 agree -> majority (threshold=3)."""
        result = _vote(("a", "PASS"), ("b", "PASS"), ("c", "PASS"), ("d", "FAIL"))
        assert result.status == "majority"
        assert result.verdict == "PASS"
        assert result.threshold == 3

    def test_2_2_split_indeterminate(self):
        """2-2 split -> indeterminate (threshold=3 not met)."""
        result = _vote(("a", "PASS"), ("b", "PASS"), ("c", "FAIL"), ("d", "FAIL"))
        assert result.status == "indeterminate"
        assert result.verdict is None
        assert result.threshold == 3


class TestVoteResultShape:
    def test_evidences_length_matches_providers(self):
        result = _vote(("x", "PASS"), ("y", "PASS"), ("z", "FAIL"))
        assert len(result.evidences) == 3
        assert len(result.active_providers) == 3

    def test_active_providers_names_match(self):
        result = _vote(("x", "PASS"), ("y", "FAIL"))
        assert set(result.active_providers) == {"x", "y"}
