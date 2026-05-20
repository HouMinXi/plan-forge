"""Unit tests for plan_forge.verdict dataclasses and enums."""
from plan_forge.verdict import (
    EngineeringVerdict,
    EpistemicVerdict,
    EvidenceTier,
    Finding,
    LLMEvidence,
    Severity,
    Verdict,
)


# -------------------------------------------------------------------
# Severity enum
# -------------------------------------------------------------------

def test_severity_values():
    """Severity has exactly BLOCKER/HIGH/MEDIUM/LOW -- no INFO."""
    expected = {"BLOCKER", "HIGH", "MEDIUM", "LOW"}
    actual = {s.value for s in Severity}
    assert actual == expected


def test_severity_no_info():
    """INFO is deliberately absent from Severity."""
    names = {s.name for s in Severity}
    assert "INFO" not in names


def test_severity_is_str():
    """Severity members are also str instances (str, Enum)."""
    assert isinstance(Severity.BLOCKER, str)
    assert Severity.BLOCKER == "BLOCKER"


# -------------------------------------------------------------------
# EngineeringVerdict enum
# -------------------------------------------------------------------

def test_engineering_verdict_values():
    expected = {"PASS", "FAIL"}
    actual = {v.value for v in EngineeringVerdict}
    assert actual == expected


# -------------------------------------------------------------------
# EpistemicVerdict enum
# -------------------------------------------------------------------

def test_epistemic_verdict_values():
    expected = {"PASS", "FAIL", "VISION"}
    actual = {v.value for v in EpistemicVerdict}
    assert actual == expected


# -------------------------------------------------------------------
# EvidenceTier enum
# -------------------------------------------------------------------

def test_evidence_tier_values():
    expected = {"T1", "T2", "T3", "T4", "UNCLASSIFIED"}
    actual = {t.value for t in EvidenceTier}
    assert actual == expected


def test_evidence_tier_t4_is_suspect():
    """T4_SUSPECT (not T4_UNVERIFIABLE) -- the name reflects suspicion, not absence of data."""
    assert hasattr(EvidenceTier, "T4_SUSPECT")
    assert not hasattr(EvidenceTier, "T4_UNVERIFIABLE")
    assert EvidenceTier.T4_SUSPECT.value == "T4"


# -------------------------------------------------------------------
# LLMEvidence dataclass
# -------------------------------------------------------------------

def test_llm_evidence_required_fields():
    """LLMEvidence instantiates with required positional args."""
    ev = LLMEvidence(
        provider="anthropic",
        model="claude-opus-4-7",
        verdict="verified",
        reasoning="test reasoning",
        prompt_version="g6_v0",
        run_id=1,
    )
    assert ev.provider == "anthropic"
    assert ev.model == "claude-opus-4-7"
    assert ev.verdict == "verified"
    assert ev.reasoning == "test reasoning"
    assert ev.prompt_version == "g6_v0"
    assert ev.run_id == 1


def test_llm_evidence_tier_defaults_to_unclassified():
    """tier defaults to UNCLASSIFIED at construction time."""
    ev = LLMEvidence(
        provider="kimi",
        model="k2",
        verdict="unverified",
        reasoning="r",
        prompt_version="g8_v0",
        run_id=2,
    )
    assert ev.tier == EvidenceTier.UNCLASSIFIED


def test_llm_evidence_cited_instances_default():
    """cited_instances defaults to empty list."""
    ev = LLMEvidence(
        provider="deepseek",
        model="ds3",
        verdict="verified",
        reasoning="r",
        prompt_version="g6_v0",
        run_id=3,
    )
    assert ev.cited_instances == []
    assert isinstance(ev.cited_instances, list)


def test_llm_evidence_search_evidence_default():
    """search_evidence defaults to empty list."""
    ev = LLMEvidence(
        provider="mimo",
        model="m1",
        verdict="verified",
        reasoning="r",
        prompt_version="g9_v0",
        run_id=4,
    )
    assert ev.search_evidence == []
    assert isinstance(ev.search_evidence, list)


def test_llm_evidence_positional_order():
    """Positional arg order must match field declaration order (dataclass requirement).

    provider, model, verdict, reasoning, prompt_version, run_id
    (all required, in that order).
    """
    ev = LLMEvidence("anthropic", "opus", "pass", "reason", "v0", 42)
    assert ev.provider == "anthropic"
    assert ev.model == "opus"
    assert ev.verdict == "pass"
    assert ev.reasoning == "reason"
    assert ev.prompt_version == "v0"
    assert ev.run_id == 42


# -------------------------------------------------------------------
# Finding dataclass
# -------------------------------------------------------------------

def test_finding_required_fields():
    """Finding instantiates with required fields."""
    f = Finding(
        check_id="G3",
        severity=Severity.BLOCKER,
        location="plan",
        message="missing pre-mortem section",
    )
    assert f.check_id == "G3"
    assert f.severity == Severity.BLOCKER
    assert f.location == "plan"
    assert f.message == "missing pre-mortem section"


def test_finding_fix_hint_defaults_to_empty():
    """fix_hint defaults to empty string."""
    f = Finding(
        check_id="F1",
        severity=Severity.LOW,
        location="SC-1",
        message="orphan SC",
    )
    assert f.fix_hint == ""


def test_finding_llm_evidence_defaults_to_empty_list():
    f = Finding(
        check_id="G6.B",
        severity=Severity.HIGH,
        location="SC-5",
        message="not measurable",
    )
    assert f.llm_evidence == []


def test_finding_evidence_tier_summary_defaults_to_empty_dict():
    f = Finding(
        check_id="G10",
        severity=Severity.MEDIUM,
        location="g10",
        message="tier check",
    )
    assert f.evidence_tier_summary == {}


def test_finding_positional_order():
    """Positional arg order preserved after field addition."""
    f = Finding("G1", Severity.HIGH, "line 5", "missing ref class")
    assert f.check_id == "G1"
    assert f.severity == Severity.HIGH
    assert f.location == "line 5"
    assert f.message == "missing ref class"


# -------------------------------------------------------------------
# Verdict dataclass
# -------------------------------------------------------------------

def test_verdict_required_fields():
    """Verdict instantiates with two required fields."""
    v = Verdict(
        engineering=EngineeringVerdict.PASS,
        epistemic=EpistemicVerdict.PASS,
    )
    assert v.engineering == EngineeringVerdict.PASS
    assert v.epistemic == EpistemicVerdict.PASS


def test_verdict_findings_defaults_to_empty_list():
    v = Verdict(
        engineering=EngineeringVerdict.FAIL,
        epistemic=EpistemicVerdict.FAIL,
    )
    assert v.findings == []


def test_verdict_corpus_run_id_defaults_to_none():
    v = Verdict(
        engineering=EngineeringVerdict.PASS,
        epistemic=EpistemicVerdict.VISION,
    )
    assert v.corpus_run_id is None


def test_verdict_arbitration_triggered_defaults_to_false():
    v = Verdict(
        engineering=EngineeringVerdict.PASS,
        epistemic=EpistemicVerdict.PASS,
    )
    assert v.arbitration_triggered is False


def test_verdict_tier_summary_defaults_to_empty_dict():
    v = Verdict(
        engineering=EngineeringVerdict.PASS,
        epistemic=EpistemicVerdict.PASS,
    )
    assert v.tier_summary == {}


def test_verdict_arbitration_resolution_defaults_to_none():
    v = Verdict(
        engineering=EngineeringVerdict.PASS,
        epistemic=EpistemicVerdict.PASS,
    )
    assert v.arbitration_resolution is None


def test_verdict_positional_order():
    """Positional arg order preserved after field addition."""
    v = Verdict(EngineeringVerdict.FAIL, EpistemicVerdict.VISION)
    assert v.engineering == EngineeringVerdict.FAIL
    assert v.epistemic == EpistemicVerdict.VISION
