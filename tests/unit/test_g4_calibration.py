"""Tests for checks/epistemic/g4_calibration.py (Part A only)."""
from __future__ import annotations

from pathlib import Path

from plan_forge.checks.epistemic.g4_calibration import check
from plan_forge.llm.client import LLMResponse
from plan_forge.llm.mocks import MockClient
from plan_forge.parser import parse
from plan_forge.verdict import Severity

_FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"


def _load_fixture(name: str) -> str:
    return (_FIXTURES / name).read_text(encoding="utf-8")


class TestG4PassFixture:
    def test_no_aggregate(self):
        """Pass fixture: <=10 uncalibrated hedges -> no aggregate BLOCKER."""
        parsed = parse(_load_fixture("g4_pass.md"))
        findings = check(parsed, [])
        agg = [f for f in findings if f.check_id == "G4.A.aggregate"]
        assert len(agg) == 0


class TestG4FailFixture:
    def test_triggers_aggregate_blocker(self):
        """Fail fixture: >10 uncalibrated hedges -> aggregate BLOCKER."""
        parsed = parse(_load_fixture("g4_fail.md"))
        findings = check(parsed, [])
        agg = [f for f in findings if f.check_id == "G4.A.aggregate"]
        assert len(agg) == 1
        assert agg[0].severity == Severity.BLOCKER
        # Verify per-hedge findings are MEDIUM
        per_hedge = [f for f in findings if f.check_id == "G4.A.mechanical"]
        assert len(per_hedge) > 10
        assert all(f.severity == Severity.MEDIUM for f in per_hedge)


class TestG4Exemptions:
    def test_numeric_probability_exempts(self):
        text = "This will likely succeed with 85% confidence.\n"
        parsed = parse(text)
        findings = check(parsed, [])
        assert len(findings) == 0

    def test_hedge_ok_marker_exempts(self):
        text = "The service should work. <!-- plan-forge: hedge-ok -->\n"
        parsed = parse(text)
        findings = check(parsed, [])
        assert len(findings) == 0

    def test_code_block_hedges_skipped(self):
        """Hedge words inside fenced code blocks are not flagged."""
        text = (
            "# Plan\n"
            "\n"
            "```python\n"
            "if should_retry:\n"
            "    might_fail = True\n"
            "    could_timeout = True\n"
            "    maybe_null = True\n"
            "```\n"
            "\n"
            "No hedge words outside code.\n"
        )
        parsed = parse(text)
        findings = check(parsed, [])
        assert len(findings) == 0


class TestG4IgnoresLLMClients:
    def test_ignores_llm_clients(self):
        """MockClients passed but never called (Part B deferred)."""
        client = MockClient(
            name="mock",
            responses={"always": LLMResponse(
                verdict="VERIFIED", reasoning="ok",
                cited_instances=[], search_evidence=[],
                cost_usd=0.0, raw_response={},
            )},
        )
        text = "The system might need scaling.\n"
        parsed = parse(text)
        findings = check(parsed, [client])
        # Should produce 1 MEDIUM finding but no LLM interaction
        mech = [f for f in findings if f.check_id == "G4.A.mechanical"]
        assert len(mech) == 1
        # LLM evidence should be empty (no Part B)
        assert all(len(f.llm_evidence) == 0 for f in findings)
