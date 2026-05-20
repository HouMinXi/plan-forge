"""Tests for checks/epistemic/g6_sc_falsifiability.py."""
from __future__ import annotations

import json
from pathlib import Path

from plan_forge.checks.epistemic.g6_sc_falsifiability import check
from plan_forge.llm.client import LLMResponse
from plan_forge.llm.mocks import MockClient
from plan_forge.parser import parse
from plan_forge.verdict import Severity

_FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"


def _load_fixture(name: str) -> str:
    return (_FIXTURES / name).read_text(encoding="utf-8")


def _mock_client(name: str, verdict: str, reason: str = "test") -> MockClient:
    """Build a MockClient that returns a parsed verdict for any prompt.

    Mocks simulate the post-parse state: LLMResponse.verdict = the token
    (as a real provider would produce after JSON parsing).
    The raw_response preserves the full JSON for traceability.
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


class TestG6PartA:
    def test_missing_fail_condition_blocker(self):
        parsed = parse(_load_fixture("g6_fail.md"))
        findings = check(parsed, [])
        mech = [f for f in findings if f.check_id == "G6.A.mechanical"]
        # SC-2, SC-3, SC-4 have no fail_condition
        assert len(mech) == 3
        assert all(f.severity == Severity.BLOCKER for f in mech)

    def test_all_present_no_finding(self):
        parsed = parse(_load_fixture("g6_pass.md"))
        findings = check(parsed, [])
        mech = [f for f in findings if f.check_id == "G6.A.mechanical"]
        assert len(mech) == 0


class TestG6PartB:
    def test_unverified_emits_high(self):
        """MockClient votes UNVERIFIED -> HIGH finding."""
        parsed = parse(_load_fixture("g6_pass.md"))
        clients = [
            _mock_client("mock_a", "UNVERIFIED"),
            _mock_client("mock_b", "UNVERIFIED"),
        ]
        findings = check(parsed, clients)
        llm = [f for f in findings if f.check_id == "G6.B.llm"]
        assert len(llm) == 3  # all 3 SCs
        assert all(f.severity == Severity.HIGH for f in llm)

    def test_aggregate_over_30pct(self):
        """Enough UNVERIFIED to cross >30% threshold -> BLOCKER."""
        parsed = parse(_load_fixture("g6_pass.md"))
        clients = [
            _mock_client("mock_a", "UNVERIFIED"),
            _mock_client("mock_b", "UNVERIFIED"),
        ]
        findings = check(parsed, clients)
        agg = [f for f in findings if f.check_id == "G6.B.aggregate"]
        assert len(agg) == 1
        assert agg[0].severity == Severity.BLOCKER

    def test_no_providers_skips(self):
        """Empty llm_clients -> no Part B findings, no crash."""
        parsed = parse(_load_fixture("g6_pass.md"))
        findings = check(parsed, [])
        llm = [f for f in findings
               if f.check_id.startswith("G6.B")]
        assert len(llm) == 0

    def test_indeterminate_not_counted(self):
        """Split votes -> indeterminate -> verdict_matches False."""
        parsed = parse(_load_fixture("g6_pass.md"))
        # Two clients with different verdicts -> indeterminate
        clients = [
            _mock_client("mock_a", "VERIFIED"),
            _mock_client("mock_b", "UNVERIFIED"),
        ]
        findings = check(parsed, clients)
        llm = [f for f in findings if f.check_id == "G6.B.llm"]
        # indeterminate -> vote.verdict is None -> not counted
        assert len(llm) == 0

    def test_evidence_attached_to_finding(self):
        """Finding.llm_evidence populated with correct provider/model."""
        parsed = parse(_load_fixture("g6_pass.md"))
        clients = [
            _mock_client("mock_a", "UNVERIFIED"),
        ]
        findings = check(parsed, clients)
        llm = [f for f in findings if f.check_id == "G6.B.llm"]
        assert len(llm) > 0
        ev = llm[0].llm_evidence
        assert len(ev) == 1
        assert ev[0].provider == "mock_a"
        assert ev[0].run_id == 0
