"""Tests for checks/epistemic/g8_source_diversity.py."""
from __future__ import annotations

import json
import warnings
from pathlib import Path

from plan_forge.checks.epistemic.g8_source_diversity import check
from plan_forge.llm.client import LLMResponse
from plan_forge.llm.mocks import MockClient
from plan_forge.parser import parse
from plan_forge.verdict import EvidenceTier, Severity

_FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"


def _load_fixture(name: str) -> str:
    return (_FIXTURES / name).read_text(encoding="utf-8")


def _mock_client(name: str, verdict: str, reason: str = "test") -> MockClient:
    """Build a MockClient returning a parsed verdict for any prompt.

    Mocks simulate the post-parse state: LLMResponse.verdict = the token.
    raw_response preserves the JSON for traceability.
    """
    raw_json = json.dumps({
        "verdict": verdict,
        "reason": reason,
        "cited_instances": [],
        "search_evidence": [],
    })
    return MockClient(
        name=name,
        responses={"": LLMResponse(
            verdict=verdict,
            reasoning=reason,
            cited_instances=[],
            search_evidence=[],
            cost_usd=0.0,
            raw_response={"original_json": raw_json},
        )},
    )


class TestG8PartA:
    def test_no_external_voices_section_blocker(self):
        parsed = parse(_load_fixture("g8_fail.md"))
        findings = check(parsed, [])
        no_sect = [f for f in findings
                   if f.check_id == "G8.A.no_section"]
        assert len(no_sect) == 1
        assert no_sect[0].severity == Severity.BLOCKER

    def test_missing_dissent_blocker(self):
        text = (
            "# Plan\n\n"
            "## External Voices\n\n"
            "- Popper (1959). The Logic of Scientific Discovery. Routledge.\n\n"
            "The 2020 incident was a failure that taught a lesson.\n"
        )
        parsed = parse(text)
        findings = check(parsed, [])
        dissent = [f for f in findings
                   if f.check_id == "G8.A.no_dissent"]
        assert len(dissent) == 1
        assert dissent[0].severity == Severity.BLOCKER

    def test_missing_failure_case_blocker(self):
        text = (
            "# Plan\n\n"
            "## External Voices\n\n"
            "- Popper (1959). The Logic of Scientific Discovery. Routledge.\n\n"
            "However, critics disagree with this approach.\n"
        )
        parsed = parse(text)
        findings = check(parsed, [])
        fail_case = [f for f in findings
                     if f.check_id == "G8.A.no_failure_case"]
        assert len(fail_case) == 1
        assert fail_case[0].severity == Severity.BLOCKER

    def test_prose_cited_emits_high(self):
        parsed = parse(_load_fixture("g8_prose_cited_fp.md"))
        findings = check(parsed, [])
        no_cit = [f for f in findings
                  if f.check_id == "G8.A.no_citation"]
        assert len(no_cit) == 1
        assert no_cit[0].severity == Severity.HIGH

    def test_empty_body_emits_blocker(self):
        parsed = parse(_load_fixture("g8_empty_body_blocker.md"))
        findings = check(parsed, [])
        no_cit = [f for f in findings
                  if f.check_id == "G8.A.no_citation"]
        assert len(no_cit) == 1
        assert no_cit[0].severity == Severity.BLOCKER


class TestG8PartB:
    def test_unresolvable_blocker(self):
        """MockClients vote UNRESOLVABLE -> BLOCKER."""
        parsed = parse(_load_fixture("g8_pass.md"))
        clients = [
            _mock_client("mock_a", "UNRESOLVABLE"),
            _mock_client("mock_b", "UNRESOLVABLE"),
        ]
        findings = check(parsed, clients)
        llm = [f for f in findings if f.check_id == "G8.B.llm"]
        assert len(llm) == 1
        assert llm[0].severity == Severity.BLOCKER
        assert "unresolvable" in llm[0].message

    def test_uncertain_medium(self):
        """MockClients vote UNCERTAIN -> MEDIUM."""
        parsed = parse(_load_fixture("g8_pass.md"))
        clients = [
            _mock_client("mock_a", "UNCERTAIN"),
            _mock_client("mock_b", "UNCERTAIN"),
        ]
        findings = check(parsed, clients)
        unc = [f for f in findings if f.check_id == "G8.B.uncertain"]
        assert len(unc) == 1
        assert unc[0].severity == Severity.MEDIUM

    def test_resolved_no_finding(self):
        """RESOLVED_BY_KNOWLEDGE -> no finding."""
        parsed = parse(_load_fixture("g8_pass.md"))
        clients = [
            _mock_client("mock_a", "RESOLVED_BY_KNOWLEDGE"),
            _mock_client("mock_b", "RESOLVED_BY_KNOWLEDGE"),
        ]
        findings = check(parsed, clients)
        llm = [f for f in findings
               if f.check_id.startswith("G8.B")]
        assert len(llm) == 0

    def test_no_providers_skips(self):
        """Empty llm_clients -> no Part B findings, no crash."""
        parsed = parse(_load_fixture("g8_pass.md"))
        findings = check(parsed, [])
        llm = [f for f in findings
               if f.check_id.startswith("G8.B")]
        assert len(llm) == 0

    def test_split_emits_arbitration(self):
        """Two clients split on citation -> ARBITRATION finding."""
        parsed = parse(_load_fixture("g8_pass.md"))
        clients = [
            _mock_client("mock_a", "RESOLVED_BY_KNOWLEDGE"),
            _mock_client("mock_b", "UNRESOLVABLE"),
        ]
        findings = check(parsed, clients)
        arb = [
            f for f in findings
            if f.check_id == "G8.B.llm"
            and f.severity == Severity.ARBITRATION
        ]
        assert len(arb) == 1
        assert arb[0].severity == Severity.ARBITRATION
        assert "arbitration" in arb[0].message

    def test_split_arbitration_evidence_has_two_entries(self):
        """Split finding carries evidence from both providers."""
        parsed = parse(_load_fixture("g8_pass.md"))
        clients = [
            _mock_client("mock_a", "RESOLVED_BY_KNOWLEDGE"),
            _mock_client("mock_b", "UNRESOLVABLE"),
        ]
        findings = check(parsed, clients)
        arb = [
            f for f in findings
            if f.check_id == "G8.B.llm"
            and f.severity == Severity.ARBITRATION
        ]
        assert len(arb) > 0
        ev = arb[0].llm_evidence
        assert len(ev) == 2
        verdicts = {e.verdict for e in ev}
        assert "RESOLVED_BY_KNOWLEDGE" in verdicts
        assert "UNRESOLVABLE" in verdicts

    def test_consensus_no_arbitration(self):
        """Both agree on RESOLVED -> no ARBITRATION finding."""
        parsed = parse(_load_fixture("g8_pass.md"))
        clients = [
            _mock_client("mock_a", "RESOLVED_BY_KNOWLEDGE"),
            _mock_client("mock_b", "RESOLVED_BY_KNOWLEDGE"),
        ]
        findings = check(parsed, clients)
        arb = [
            f for f in findings
            if f.severity == Severity.ARBITRATION
        ]
        assert arb == []


class TestG8UnbackedSearchGuard:
    def test_n2_both_tool_less_search_claim_downgraded_to_uncertain(self):
        """N=2 both tool-less RESOLVED_VIA_SEARCH -> consensus UNCERTAIN."""

        class ToollessClient(MockClient):
            def __init__(self, name: str, verdict: str):
                raw_json = json.dumps({
                    "verdict": verdict,
                    "reason": "test",
                    "cited_instances": [],
                    "search_evidence": [],
                })
                super().__init__(
                    name=name,
                    responses={"": LLMResponse(
                        verdict=verdict,
                        reasoning="test",
                        cited_instances=[],
                        search_evidence=[],
                        cost_usd=0.0,
                        raw_response={"original_json": raw_json},
                    )},
                )

        parsed = parse(_load_fixture("g8_pass.md"))
        clients = [
            ToollessClient("toolless_a", "RESOLVED_VIA_SEARCH"),
            ToollessClient("toolless_b", "RESOLVED_VIA_SEARCH"),
        ]
        findings = check(parsed, clients)

        uncertain = [
            f for f in findings
            if f.check_id == "G8.B.uncertain"
        ]
        assert len(uncertain) == 1
        assert uncertain[0].severity == Severity.MEDIUM

        ev = uncertain[0].llm_evidence
        assert len(ev) == 2
        assert all(e.tier == EvidenceTier.T4_SUSPECT for e in ev)

    def test_n2_split_one_tool_one_tool_less_creates_arbitration(self):
        """N=2 one with tool (RESOLVED_VIA_SEARCH) + one tool-less
        (RESOLVED_VIA_SEARCH -> UNCERTAIN) -> split -> ARBITRATION."""

        class ClientWithSchema(MockClient):
            def __init__(self, name: str, verdict: str, has_tool: bool):
                raw_json = json.dumps({
                    "verdict": verdict,
                    "reason": "test",
                    "cited_instances": [],
                    "search_evidence": [],
                })
                super().__init__(
                    name=name,
                    responses={"": LLMResponse(
                        verdict=verdict,
                        reasoning="test",
                        cited_instances=[],
                        search_evidence=[],
                        cost_usd=0.0,
                        raw_response={"original_json": raw_json},
                    )},
                )
                self.has_tool = has_tool

        parsed = parse(_load_fixture("g8_pass.md"))
        clients = [
            ClientWithSchema("withtool", "RESOLVED_VIA_SEARCH", True),
            ClientWithSchema("toolless", "RESOLVED_VIA_SEARCH", False),
        ]

        from plan_forge.checks.epistemic._evidence import schema_for
        from unittest.mock import patch

        def patched_schema(name):
            for c in clients:
                if c.name == name:
                    return {"type": "web_search"} if c.has_tool else None
            return schema_for(name)

        with patch(
            "plan_forge.checks.epistemic.g8_source_diversity.schema_for",
            side_effect=patched_schema,
        ):
            findings = check(parsed, clients)

        arb = [
            f for f in findings
            if f.check_id == "G8.B.llm"
            and f.severity == Severity.ARBITRATION
        ]
        assert len(arb) == 1
        assert "arbitration" in arb[0].message

        ev = arb[0].llm_evidence
        assert len(ev) == 2
        verdicts = {e.verdict for e in ev}
        assert "RESOLVED_VIA_SEARCH" in verdicts
        assert "UNCERTAIN" in verdicts

        tiers = {e.provider: e.tier for e in ev}
        assert tiers["toolless"] == EvidenceTier.T4_SUSPECT
        assert tiers["withtool"] == EvidenceTier.UNCLASSIFIED


def test_g8_no_evidence_uses_valid_ttl_class(
    corpus_engine, clean_cache, monkeypatch
):
    """Without host evidence, Part B must hand cache.set a valid ttl_class.

    The no-evidence branch must resolve to 'canonical'. A non-TTL_SECONDS
    value makes cache.set raise ValueError, breaking every real-provider
    call that lacks host evidence. MockClient bypasses cache.set, so this
    needs a real client with a stubbed network call plus the real cache
    backend (wired to the test DB by corpus_engine).
    """
    import types

    from plan_forge.llm.deepseek_client import DeepSeekClient

    client = DeepSeekClient(api_key="unused-stub-key")

    def _fake_create(*args, **kwargs):
        message = types.SimpleNamespace(content="UNRESOLVABLE")
        return types.SimpleNamespace(
            choices=[types.SimpleNamespace(message=message)],
            usage=types.SimpleNamespace(prompt_tokens=1, completion_tokens=1),
            model_dump=lambda: {},
        )

    monkeypatch.setattr(
        client._client.chat.completions, "create", _fake_create
    )

    plan_text = (
        "# Plan\n\n## External Voices\n\n"
        "- Brooks (1975). The Mythical Man-Month.\n\n"
        "However, critics argue the estimate was optimistic. "
        "A historical failure case: the 2016 incident taught a lesson.\n"
    )
    parsed = parse(plan_text)
    assert parsed.citations

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        check(parsed, [client], host_evidence=None)
