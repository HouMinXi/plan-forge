"""Tests for G8 host-evidence injection logic."""
from __future__ import annotations

import json
import hashlib
import pytest

from plan_forge.checks.epistemic._evidence import _validate_evidence
from plan_forge.checks.epistemic.g8_source_diversity import check
from plan_forge.llm.client import LLMResponse
from plan_forge.llm.mocks import MockClient
from plan_forge.parser import parse
from plan_forge.verdict import Severity


def _resp(verdict: str, reasoning: str = "test") -> LLMResponse:
    """Build minimal LLMResponse."""
    return LLMResponse(
        verdict=verdict,
        reasoning=reasoning,
        cited_instances=[],
        search_evidence=[],
        cost_usd=0.0,
        raw_response={},
    )


def _plan_with_citations(citations: list[str]) -> str:
    """Build minimal plan with External Voices section."""
    cites_str = "\n".join(f"- {c}" for c in citations)
    return f"""# Test Plan

## External Voices

{cites_str}

We analyzed dissenting views from critics who disagree with our approach.
Historical failure cases like the 2016 incident taught us valuable lessons.

## Success Criteria
SC1. System works.
"""


class TestC1InjectedContradiction:
    """Test 1: injected C1 contradiction -> UNRESOLVABLE closes the hole."""

    def test_c1_without_evidence_false_passes(self):
        """C1 without evidence: model may false-pass as BY_KNOWLEDGE."""
        plan = _plan_with_citations([
            "Kahneman (2011). Thinking Fast and Slow."
        ])
        parsed = parse(plan)
        mock = MockClient(
            name="mock",
            responses={
                "Kahneman": _resp(
                    "RESOLVED_BY_KNOWLEDGE",
                    "Kahneman solo-authored this book"
                )
            }
        )
        with pytest.warns(UserWarning, match="single provider"):
            findings = check(parsed, [mock], host_evidence=None)
        non_arb = [f for f in findings if f.severity != Severity.ARBITRATION]
        assert len(non_arb) == 0

    def test_c1_with_evidence_unresolvable(self):
        """C1 with contradiction evidence -> UNRESOLVABLE (hole closed)."""
        plan = _plan_with_citations([
            "Turing (2020). Transformer Networks."
        ])
        parsed = parse(plan)
        evidence = {
            "Turing (2020). Transformer Networks.": [
                {
                    "tier": "T2_SILVER",
                    "domain": "en.wikipedia.org",
                    "title": "Alan Turing - Wikipedia",
                    "snippet": "Alan Turing died June 7, 1954",
                    "url": "https://en.wikipedia.org/wiki/Alan_Turing",
                },
            ]
        }
        mock = MockClient(
            name="mock",
            responses={
                "Turing": _resp(
                    "UNRESOLVABLE",
                    "Turing died 1954; cannot author 2020 paper"
                )
            }
        )
        with pytest.warns(UserWarning, match="single provider"):
            findings = check(parsed, [mock], host_evidence=evidence)
        blockers = [f for f in findings if f.severity == Severity.BLOCKER]
        assert any("unresolvable" in f.message.lower() for f in blockers)


class TestNonEmptyBackedSearchNotDowngraded:
    """Test 2: non-empty-backed VIA_SEARCH -> NOT downgraded."""

    def test_via_search_with_positive_evidence_guard_skipped(self):
        """Guard skips; VIA_SEARCH is not downgraded."""
        plan = _plan_with_citations([
            "Vaswani et al. (2017). Attention Is All You Need."
        ])
        parsed = parse(plan)
        evidence = {
            "Vaswani et al. (2017). Attention Is All You Need.": [
                {
                    "tier": "T1_GOLD",
                    "domain": "arxiv.org",
                    "title": "Attention Is All You Need",
                    "snippet": "Vaswani et al. 2017, Transformer, NeurIPS 31",
                    "url": "https://arxiv.org/abs/1706.03762",
                }
            ]
        }
        mock = MockClient(name="toolless", responses={"": _resp("RESOLVED_VIA_SEARCH", "matched from injected evidence")})
        with pytest.warns(UserWarning, match="single provider"):
            findings = check(parsed, [mock], host_evidence=evidence)
        non_arb = [f for f in findings if f.severity != Severity.ARBITRATION]
        assert len(non_arb) == 0


class TestEmptyBackedSearchDowngraded:
    """Test 3: empty [] + VIA_SEARCH -> downgraded (guard runs)."""

    def test_empty_evidence_list_still_runs_guard(self):
        """Empty list means search found nothing; guard must run."""
        plan = _plan_with_citations([
            "Smith (2020). Empty Evidence Test."
        ])
        parsed = parse(plan)
        evidence = {
            "Smith (2020). Empty Evidence Test.": []
        }
        mock = MockClient(name="toolless", responses={"Smith": _resp("RESOLVED_VIA_SEARCH", "test")})
        with pytest.warns(UserWarning, match="single provider"):
            findings = check(parsed, [mock], host_evidence=evidence)
        medium = [f for f in findings if f.severity == Severity.MEDIUM]
        assert len(medium) > 0


class TestSearchFailedSentinelDowngraded:
    """Test 4: search_failed + VIA_SEARCH -> downgraded (guard runs)."""

    def test_search_failed_sentinel_runs_guard(self):
        """search_failed sentinel means no evidence; guard must run."""
        plan = _plan_with_citations([
            "Jones (2019). Search Failed Test."
        ])
        parsed = parse(plan)
        evidence = {
            "Jones (2019). Search Failed Test.": {"search_failed": True}
        }
        mock = MockClient(name="toolless", responses={"Jones": _resp("RESOLVED_VIA_SEARCH", "test")})
        with pytest.warns(UserWarning, match="single provider"):
            findings = check(parsed, [mock], host_evidence=evidence)
        medium = [f for f in findings if f.severity == Severity.MEDIUM]
        assert len(medium) > 0


class TestAbsentKeyDowngraded:
    """Test 5: absent key + VIA_SEARCH -> downgraded (today's behavior)."""

    def test_citation_not_in_evidence_dict_runs_guard(self):
        """Citation absent from evidence -> guard runs; warning issued."""
        plan = _plan_with_citations([
            "Target (2020). Missing Evidence."
        ])
        parsed = parse(plan)
        evidence = {
            "Other (2019). Different Citation.": [
                {
                    "tier": "T1_GOLD",
                    "domain": "example.com",
                    "title": "Other Citation",
                    "snippet": "Other citation snippet",
                    "url": "http://example.com/other",
                }
            ]
        }
        mock = MockClient(name="toolless", responses={"Target": _resp("RESOLVED_VIA_SEARCH", "test")})
        with pytest.warns(UserWarning):
            findings = check(parsed, [mock], host_evidence=evidence)
        medium = [f for f in findings if f.severity == Severity.MEDIUM]
        missing = [
            f for f in findings
            if "missing" in f.message.lower() and f.check_id ==
 "G8.B.missing_evidence"
        ]
        assert len(missing) > 0
        assert len(medium) > 0


class TestDifferentEvidenceDifferentCacheKey:
    """Test 7: same citation, different evidence -> different cache keys."""

    def test_evidence_hash_in_cache_key(self):
        """Changing evidence changes the cache key."""
        citation = "Brown (2018). Cache Key Test."

        evidence1 = {citation: [{"tier": "T1_GOLD", "domain": "a.com",
 "title": "A", "snippet": "one", "url": "http://a.com"}]}
        evidence2 = {citation: [{"tier": "T1_GOLD", "domain": "b.com",
 "title": "B", "snippet": "two", "url": "http://b.com"}]}

        hash1 = hashlib.sha256(
            json.dumps(evidence1[citation], sort_keys=True).encode()
        ).hexdigest()
        hash2 = hashlib.sha256(
            json.dumps(evidence2[citation], sort_keys=True).encode()
        ).hexdigest()

        assert hash1 != hash2


class TestSelectiveBacking:
    """Test 9: 2 of 3 citations have evidence -> only those skip guard."""

    def test_partial_evidence_dict(self):
        """Citations with evidence skip guard; others run guard."""
        plan = _plan_with_citations([
            "Foo (2020). Paper A.",
            "Bar (2019). Paper B.",
            "Qux (2018). Paper C.",
        ])
        parsed = parse(plan)
        evidence = {
            "Foo (2020). Paper A.": [{"tier": "T1_GOLD", "domain": "a.com",
 "title": "A", "snippet": "A snippet", "url": "http://a.com"}],
            "Bar (2019). Paper B.": [{"tier": "T1_GOLD", "domain": "b.com",
 "title": "B", "snippet": "B snippet", "url": "http://b.com"}],
        }

        mock = MockClient(name="toolless", responses={
            "Foo": _resp("RESOLVED_VIA_SEARCH", "A backed"),
            "Bar": _resp("RESOLVED_VIA_SEARCH", "B backed"),
            "Qux": _resp("RESOLVED_VIA_SEARCH", "C hallucinated"),
        })

        with pytest.warns(UserWarning):
            findings = check(parsed, [mock], host_evidence=evidence)
        medium = [f for f in findings if f.severity == Severity.MEDIUM]
        missing = [f for f in findings if "missing" in f.message.lower()]

        assert len(missing) == 1
        assert any("Qux (2018). Paper C." in f.message for f in missing)
        assert len(medium) >= 1


class TestResolvableWithEvidenceStillResolve:
    """Test 10: R1-R4 WITH evidence -> still RESOLVE (no false injury)."""

    def test_resolvable_citation_with_evidence_passes(self):
        """Resolvable citation with supporting evidence still passes."""
        plan = _plan_with_citations([
            "Vaswani et al. (2017). Attention Is All You Need."
        ])
        parsed = parse(plan)
        evidence = {
            "Vaswani et al. (2017). Attention Is All You Need.": [
                {
                    "tier": "T1_GOLD",
                    "domain": "arxiv.org",
                    "title": "Attention Is All You Need",
                    "snippet": "Vaswani et al. 2017",
                    "url": "https://arxiv.org/abs/1706.03762",
                }
            ]
        }
        mock = MockClient(name="mock", responses={"": _resp("RESOLVED_VIA_SEARCH", "verified from evidence")})
        with pytest.warns(UserWarning, match="single provider"):
            findings = check(parsed, [mock], host_evidence=evidence)
        non_arb = [f for f in findings if f.severity != Severity.ARBITRATION]
        assert len(non_arb) == 0


class TestCanonWhitespaceVariant:
    """Test 11: whitespace-variant evidence key matches parsed citation."""

    def test_canon_normalizes_whitespace_for_lookup(self):
        """Evidence key with extra whitespace still matches citation."""
        plan = _plan_with_citations([
            "Vaswani et al. (2017). Title."
        ])
        parsed = parse(plan)
        evidence = {
            "  Vaswani  et   al. (2017).  Title.  ": [
                {
                    "tier": "T1_GOLD",
                    "domain": "example.com",
                    "title": "Title",
                    "snippet": "snippet",
                    "url": "http://example.com",
                }
            ]
        }
        mock = MockClient(
            name="mock",
            responses={
                "": _resp(
                    "RESOLVED_VIA_SEARCH",
                    "matched via canon",
                ),
            },
        )
        with pytest.warns(UserWarning, match="single provider"):
            findings = check(
                parsed, [mock], host_evidence=evidence,
            )
        non_arb = [
            f for f in findings
            if f.severity != Severity.ARBITRATION
        ]
        assert len(non_arb) == 0


class TestValidateThenCheckSearchFailed:
    """E2E: validate -> check proves sentinel stays dict.

    The search_failed sentinel must remain a dict after
    _validate_evidence so g8 isinstance(raw, list) is False,
    the guard runs, and VIA_SEARCH is downgraded to UNCERTAIN.
    This is the test that would have caught the list-wrapping bug.
    """

    def test_validated_search_failed_triggers_guard(self):
        """validate + check: search_failed -> guard runs -> MEDIUM."""
        plan = _plan_with_citations([
            "Doe (2021). Sentinel Integration Test."
        ])
        parsed = parse(plan)

        raw_evidence = {
            "Doe (2021). Sentinel Integration Test.": {
                "search_failed": True,
            }
        }
        validated = _validate_evidence(raw_evidence)

        assert isinstance(
            validated["Doe (2021). Sentinel Integration Test."],
            dict,
        ), "sentinel must stay a dict after validation"

        mock = MockClient(
            name="toolless",
            responses={
                "Doe": _resp(
                    "RESOLVED_VIA_SEARCH",
                    "hallucinated search claim",
                ),
            },
        )
        with pytest.warns(UserWarning, match="single provider"):
            findings = check(
                parsed, [mock], host_evidence=validated,
            )
        medium = [
            f for f in findings
            if f.severity == Severity.MEDIUM
        ]
        assert len(medium) > 0, (
            "VIA_SEARCH with search_failed must be downgraded"
        )
