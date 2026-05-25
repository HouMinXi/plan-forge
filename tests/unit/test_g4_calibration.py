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
        """Fail fixture: >10 strong probability hedges -> aggregate BLOCKER."""
        parsed = parse(_load_fixture("g4_fail.md"))
        findings = check(parsed, [])
        agg = [f for f in findings if f.check_id == "G4.A.aggregate"]
        assert len(agg) == 1
        assert agg[0].severity == Severity.BLOCKER
        per_hedge = [f for f in findings if f.check_id == "G4.A.mechanical"]
        assert len(per_hedge) > 10
        assert all(f.severity == Severity.MEDIUM for f in per_hedge)


class TestG4FPVocabAndModals:
    def test_no_findings_on_vocab_list_and_prose_modals(self):
        """FP fixture: hedge vocabulary definition plus prose bare modals.

        The vocabulary list at lines containing the canonical hedge words
        is a definitional enumeration; prose modals (may/should/could/
        might) in planning sentences are out of scope.  Neither should
        produce any G4 finding.
        """
        parsed = parse(_load_fixture("g4_fp_vocab_and_modals.md"))
        findings = check(parsed, [])
        assert len(findings) == 0, (
            f"Expected 0 findings on FP fixture, got {len(findings)}: "
            + str([f.message for f in findings])
        )


class TestG4TPSinglePrediction:
    def test_single_uncalibrated_prediction_fires(self):
        """TP fixture: one strong hedge fires G4.A.mechanical."""
        parsed = parse(_load_fixture("g4_tp_single_prediction.md"))
        findings = check(parsed, [])
        mech = [f for f in findings if f.check_id == "G4.A.mechanical"]
        assert len(mech) >= 1, (
            "Expected at least one G4.A.mechanical finding on TP fixture"
        )
        assert all(f.severity == Severity.MEDIUM for f in mech)

    def test_no_aggregate_on_single_prediction(self):
        """A single uncalibrated claim does not produce an aggregate BLOCKER."""
        parsed = parse(_load_fixture("g4_tp_single_prediction.md"))
        findings = check(parsed, [])
        agg = [f for f in findings if f.check_id == "G4.A.aggregate"]
        assert len(agg) == 0


class TestG4Exemptions:
    def test_numeric_probability_exempts(self):
        text = "This will likely succeed with 85% confidence.\n"
        parsed = parse(text)
        findings = check(parsed, [])
        assert len(findings) == 0

    def test_hedge_ok_marker_exempts_strong_hedge(self):
        """Marker exempts a strong probability hedge."""
        text = (
            "This will probably fail. "
            "<!-- plan-forge: hedge-ok -->\n"
        )
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

    def test_bare_modals_not_flagged_without_numeric_context(self):
        """Generic modals in ordinary prose are out of scope for G4."""
        text = (
            "The service should restart after deployment.\n"
            "Users might need to re-authenticate.\n"
            "The cache could require tuning.\n"
            "Migration may take longer than planned.\n"
        )
        parsed = parse(text)
        findings = check(parsed, [])
        assert len(findings) == 0

    def test_strong_hedge_without_calibration_fires(self):
        """A strong probability hedge with no % or marker fires."""
        text = "This approach will probably succeed.\n"
        parsed = parse(text)
        findings = check(parsed, [])
        mech = [f for f in findings if f.check_id == "G4.A.mechanical"]
        assert len(mech) == 1
        assert mech[0].severity == Severity.MEDIUM

    def test_g4_section_definition_region_exempt(self):
        """Hedges inside a G4 Calibration section heading are exempt."""
        text = (
            "### G4 Probability Calibration -- PASS\n"
            "\n"
            "- Most likely failure is a dependency version mismatch.\n"
            "- Probably resolved in the next iteration.\n"
        )
        parsed = parse(text)
        findings = check(parsed, [])
        assert len(findings) == 0, (
            "Expected 0 in G4 section, got: "
            + str([f.message for f in findings])
        )

    def test_hedge_enumeration_line_exempt(self):
        """A line listing >= 5 canonical hedge words is not flagged."""
        text = (
            "- hedge words: maybe / likely / probably / perhaps / "
            "possibly / seems / appears / should\n"
        )
        parsed = parse(text)
        findings = check(parsed, [])
        assert len(findings) == 0


class TestG4HedgeSync:
    def test_all_hedges_matched_by_parser_re(self):
        """Every word in _ALL_HEDGES must be matched by parser._HEDGE_RE."""
        from plan_forge.parser import _HEDGE_RE
        from plan_forge.checks.epistemic.g4_calibration import _ALL_HEDGES
        for word in _ALL_HEDGES:
            assert _HEDGE_RE.search(word), (
                f"{word!r} in _ALL_HEDGES not matched by parser._HEDGE_RE"
            )

    def test_hedge_enumeration_line_prose_not_exempt(self):
        """Prose with 5+ hedge words but no delimiter is not exempted."""
        text = (
            "We should probably maybe possibly likely consider this "
            "approach.\n"
        )
        parsed = parse(text)
        findings = check(parsed, [])
        mech = [f for f in findings if f.check_id == "G4.A.mechanical"]
        assert len(mech) >= 1, (
            "Prose with many hedge words must not be exempted by "
            "hedge-enumeration guard"
        )


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
        text = "This approach probably needs more work.\n"
        parsed = parse(text)
        findings = check(parsed, [client])
        mech = [f for f in findings if f.check_id == "G4.A.mechanical"]
        assert len(mech) == 1
        assert all(len(f.llm_evidence) == 0 for f in findings)
