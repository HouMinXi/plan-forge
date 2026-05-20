"""Integration tests for checks/epistemic.run() aggregator."""
from __future__ import annotations

import json
from pathlib import Path

from plan_forge.checks.epistemic import run
from plan_forge.llm.client import LLMResponse
from plan_forge.llm.mocks import MockClient
from plan_forge.parser import parse
from plan_forge.verdict import Finding

_FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"


def _load_fixture(name: str) -> str:
    return (_FIXTURES / name).read_text(encoding="utf-8")


def _mock_client(name: str, verdict: str, reason: str = "test") -> MockClient:
    """Build a MockClient returning a parsed verdict for any prompt."""
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


class TestEpistemicRunOnG6FailFixture:
    def test_combined_findings_include_g6(self):
        """run() on g6_fail fixture includes G6.A.mechanical findings."""
        parsed = parse(_load_fixture("g6_fail.md"))
        clients = [
            _mock_client("mock_a", "VERIFIED"),
            _mock_client("mock_b", "VERIFIED"),
        ]
        findings = run(parsed, clients)
        g6_ids = [f.check_id for f in findings
                  if f.check_id.startswith("G6")]
        assert len(g6_ids) > 0
        assert "G6.A.mechanical" in g6_ids


class TestEpistemicRunNoProviders:
    def test_only_mechanical_findings_no_crash(self):
        """With empty llm_clients, only Part A findings are present."""
        parsed = parse(_load_fixture("g6_fail.md"))
        findings = run(parsed, [])
        # Only mechanical findings (no LLM part)
        for f in findings:
            assert not f.check_id.endswith(".llm")
            assert f.check_id != "G6.B.aggregate"
        # Should have G6.A.mechanical + G8.A.no_section (g6_fail has no
        # External Voices section)
        check_ids = {f.check_id for f in findings}
        assert "G6.A.mechanical" in check_ids


class TestEpistemicRunReturnsFindings:
    def test_returns_finding_list(self):
        """run() returns a list of Finding instances."""
        parsed = parse(_load_fixture("g4_pass.md"))
        findings = run(parsed, [])
        assert isinstance(findings, list)
        for f in findings:
            assert isinstance(f, Finding)
