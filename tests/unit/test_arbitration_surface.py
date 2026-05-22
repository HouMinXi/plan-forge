"""Tests for plan_forge.arbitration.surface.decide_when_to_arbitrate."""

import pytest

from plan_forge.arbitration.surface import decide_when_to_arbitrate
from plan_forge.verdict import Finding, LLMEvidence, Severity


def _llm_ev(verdict: str, cited: int = 0) -> LLMEvidence:
    """Build a minimal LLMEvidence with the given verdict and citation count."""
    return LLMEvidence(
        provider="test-provider",
        model="test-model",
        verdict=verdict,
        reasoning="test reasoning",
        prompt_version="v1",
        run_id=1,
        cited_instances=[{"line": i} for i in range(cited)],
    )


def _finding(llm_evidences: list[LLMEvidence]) -> Finding:
    """Build a minimal Finding with the given LLM evidence list."""
    return Finding(
        check_id="G6",
        severity=Severity.MEDIUM,
        location="plan.md:1",
        message="test finding",
        llm_evidence=llm_evidences,
    )


def test_off_mode_never_surfaces():
    ev_a = _llm_ev("FAIL", cited=2)
    ev_b = _llm_ev("PASS", cited=2)
    f = _finding([ev_a, ev_b])
    should_surface, hits = decide_when_to_arbitrate([f], "off")
    assert should_surface is False
    assert hits == []


def test_unknown_mode_raises():
    with pytest.raises(ValueError, match="unknown arbitration mode"):
        decide_when_to_arbitrate([], "bad_mode")


@pytest.mark.parametrize("mode", ["off", "always", "on_split",
                                   "on_split_evidence_rich"])
def test_empty_findings_all_modes(mode):
    should_surface, hits = decide_when_to_arbitrate([], mode)
    assert should_surface is False
    assert hits == []


def test_empty_llm_evidence_not_surfaced_always():
    f = _finding([])
    should_surface, hits = decide_when_to_arbitrate([f], "always")
    assert should_surface is False
    assert hits == []


def test_empty_llm_evidence_not_surfaced_on_split_evidence_rich():
    f = _finding([])
    should_surface, hits = decide_when_to_arbitrate(
        [f], "on_split_evidence_rich"
    )
    assert should_surface is False
    assert hits == []


def test_always_non_split_surfaced():
    ev = _llm_ev("FAIL")
    f = _finding([ev])
    should_surface, hits = decide_when_to_arbitrate([f], "always")
    assert should_surface is True
    assert hits == [f]


def test_always_mixed_only_evidence_bearing():
    f_with = _finding([_llm_ev("FAIL")])
    f_without = _finding([])
    should_surface, hits = decide_when_to_arbitrate(
        [f_with, f_without], "always"
    )
    assert should_surface is True
    assert hits == [f_with]
    assert f_without not in hits


def test_on_split_non_split_not_surfaced():
    f = _finding([_llm_ev("FAIL"), _llm_ev("FAIL")])
    should_surface, hits = decide_when_to_arbitrate([f], "on_split")
    assert should_surface is False
    assert hits == []


def test_on_split_split_surfaced_no_citations():
    f = _finding([_llm_ev("FAIL", cited=0), _llm_ev("PASS", cited=0)])
    should_surface, hits = decide_when_to_arbitrate([f], "on_split")
    assert should_surface is True
    assert hits == [f]


def test_on_split_evidence_rich_split_all_cited():
    f = _finding([_llm_ev("FAIL", cited=1), _llm_ev("PASS", cited=2)])
    should_surface, hits = decide_when_to_arbitrate(
        [f], "on_split_evidence_rich"
    )
    assert should_surface is True
    assert hits == [f]


def test_on_split_evidence_rich_split_one_no_citation():
    f = _finding([_llm_ev("FAIL", cited=2), _llm_ev("PASS", cited=0)])
    should_surface, hits = decide_when_to_arbitrate(
        [f], "on_split_evidence_rich"
    )
    assert should_surface is False
    assert hits == []


def test_on_split_evidence_rich_non_split_not_surfaced():
    f = _finding([_llm_ev("FAIL", cited=3), _llm_ev("FAIL", cited=3)])
    should_surface, hits = decide_when_to_arbitrate(
        [f], "on_split_evidence_rich"
    )
    assert should_surface is False
    assert hits == []


@pytest.mark.parametrize("mode,evidences,expect_surface", [
    ("always", [_llm_ev("FAIL")], True),
    ("always", [], False),
    ("on_split", [_llm_ev("FAIL"), _llm_ev("PASS")], True),
    ("on_split", [_llm_ev("FAIL"), _llm_ev("FAIL")], False),
    ("on_split_evidence_rich",
     [_llm_ev("FAIL", cited=1), _llm_ev("PASS", cited=1)], True),
    ("off", [_llm_ev("FAIL"), _llm_ev("PASS")], False),
])
def test_return_contract_bool_matches_list(mode, evidences, expect_surface):
    f = _finding(evidences)
    findings = [f] if evidences else []
    should_surface, hits = decide_when_to_arbitrate(findings, mode)
    # bool must exactly mirror non-emptiness
    assert should_surface is bool(hits)
    assert should_surface is expect_surface
