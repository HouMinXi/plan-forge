"""Tests for checks/epistemic/g8_source_diversity.py."""
from __future__ import annotations

import json
from pathlib import Path

from plan_forge.checks.epistemic.g8_source_diversity import check
from plan_forge.llm.client import LLMResponse
from plan_forge.llm.mocks import MockClient
from plan_forge.parser import parse
from plan_forge.verdict import Severity

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
