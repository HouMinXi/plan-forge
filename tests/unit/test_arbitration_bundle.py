"""Tests for plan_forge.arbitration.bundle.build_evidence_bundle."""

from plan_forge.arbitration.bundle import build_evidence_bundle
from plan_forge.verdict import (
    EvidenceTier,
    Finding,
    LLMEvidence,
    Severity,
)


def _llm_ev(
    provider: str = "anthropic",
    verdict: str = "FAIL",
    reasoning: str = "test reasoning",
    cited_instances: list | None = None,
    search_evidence: list | None = None,
    tier: EvidenceTier = EvidenceTier.T2_SILVER,
) -> LLMEvidence:
    return LLMEvidence(
        provider=provider,
        model="test-model",
        verdict=verdict,
        reasoning=reasoning,
        prompt_version="v1",
        run_id=1,
        cited_instances=cited_instances if cited_instances is not None else [],
        search_evidence=search_evidence if search_evidence is not None else [],
        tier=tier,
    )


def _finding(
    check_id: str = "G6",
    severity: Severity = Severity.MEDIUM,
    location: str = "plan.md:10",
    message: str = "test message",
    fix_hint: str = "fix this",
    llm_evidence: list | None = None,
) -> Finding:
    return Finding(
        check_id=check_id,
        severity=severity,
        location=location,
        message=message,
        fix_hint=fix_hint,
        llm_evidence=llm_evidence if llm_evidence is not None else [],
    )


def test_header_present():
    f = _finding(check_id="G6", location="plan.md:10")
    out = build_evidence_bundle(f)
    assert "# Arbitration: G6 at plan.md:10" in out


def test_finding_section_lines():
    f = _finding(
        severity=Severity.HIGH,
        message="a message",
        fix_hint="fix it",
    )
    out = build_evidence_bundle(f)
    assert "- Severity: HIGH" in out
    assert "- Message: a message" in out
    assert "- Fix hint: fix it" in out


def test_severity_bare_value_not_enum_repr():
    f = _finding(severity=Severity.MEDIUM)
    out = build_evidence_bundle(f)
    assert "MEDIUM" in out
    assert "Severity.MEDIUM" not in out


def test_fix_hint_empty_renders_none():
    f = _finding(fix_hint="")
    out = build_evidence_bundle(f)
    assert "- Fix hint: (none)" in out


def test_provider_header_present():
    ev = _llm_ev(provider="kimi", verdict="PASS", tier=EvidenceTier.T2_SILVER)
    f = _finding(llm_evidence=[ev])
    out = build_evidence_bundle(f)
    assert "### Provider kimi: verdict = PASS (tier T2)" in out


def test_tier_bare_value_not_enum_repr():
    ev = _llm_ev(tier=EvidenceTier.T2_SILVER)
    f = _finding(llm_evidence=[ev])
    out = build_evidence_bundle(f)
    assert "T2" in out
    assert "EvidenceTier.T2_SILVER" not in out


def test_reasoning_line_present():
    ev = _llm_ev(reasoning="because reasons")
    f = _finding(llm_evidence=[ev])
    out = build_evidence_bundle(f)
    assert "- Reasoning: because reasons" in out


def test_cited_instances_multiple_items():
    cited = [
        {"snippet": "line1", "issue": "problem1"},
        {"snippet": "line2", "issue": "problem2"},
    ]
    ev = _llm_ev(cited_instances=cited)
    f = _finding(llm_evidence=[ev])
    out = build_evidence_bundle(f)
    assert "  - line1: problem1" in out
    assert "  - line2: problem2" in out


def test_cited_instances_empty_renders_none():
    ev = _llm_ev(cited_instances=[])
    f = _finding(llm_evidence=[ev])
    out = build_evidence_bundle(f)
    assert "- Cited instances:\n  - (none)" in out


def test_cited_instance_missing_keys_no_keyerror():
    cited_no_keys = [{}]
    ev_empty = _llm_ev(cited_instances=cited_no_keys)
    f_empty = _finding(llm_evidence=[ev_empty])
    out_empty = build_evidence_bundle(f_empty)
    assert "  - : " in out_empty

    cited_partial = [{"snippet": "x"}]
    ev_partial = _llm_ev(cited_instances=cited_partial)
    f_partial = _finding(llm_evidence=[ev_partial])
    out_partial = build_evidence_bundle(f_partial)
    assert "  - x: " in out_partial


def test_search_evidence_normal_shape():
    se = [{"query": "q", "result_summary": "summary", "url": "http://ex.com"}]
    ev = _llm_ev(search_evidence=se)
    f = _finding(llm_evidence=[ev])
    out = build_evidence_bundle(f)
    assert "  - Query: q -> summary (http://ex.com)" in out


def test_search_evidence_anthropic_shape_no_encrypted_text():
    se = [{"url": "https://example.com", "text": "ENCRYPTED_BLOB"}]
    ev = _llm_ev(search_evidence=se)
    f = _finding(llm_evidence=[ev])
    out = build_evidence_bundle(f)
    assert "ENCRYPTED_BLOB" not in out
    assert "https://example.com" in out


def test_search_evidence_empty_renders_none():
    ev = _llm_ev(search_evidence=[])
    f = _finding(llm_evidence=[ev])
    out = build_evidence_bundle(f)
    assert "- Search evidence:\n  - (none)" in out


def test_search_evidence_missing_keys_no_keyerror():
    se = [{}]
    ev = _llm_ev(search_evidence=se)
    f = _finding(llm_evidence=[ev])
    out = build_evidence_bundle(f)
    assert "  - Query:  ->  ()" in out


def test_no_llm_evidence_shows_placeholder():
    f = _finding(llm_evidence=[])
    out = build_evidence_bundle(f)
    assert "(no LLM evidence)" in out
    assert "### Provider" not in out


def test_multiple_providers_in_order():
    ev1 = _llm_ev(provider="anthropic", verdict="FAIL")
    ev2 = _llm_ev(provider="kimi", verdict="PASS")
    f = _finding(llm_evidence=[ev1, ev2])
    out = build_evidence_bundle(f)
    idx_a = out.index("### Provider anthropic")
    idx_k = out.index("### Provider kimi")
    assert idx_a < idx_k


def test_decision_block_canonical_vocab():
    f = _finding()
    out = build_evidence_bundle(f)
    assert "verified / unverified / deferred / abstain" in out


def test_return_type_and_trailing_newline():
    f = _finding()
    out = build_evidence_bundle(f)
    assert isinstance(out, str)
    assert out.endswith("\n")
