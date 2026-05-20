"""End-to-end integration tests for api.check().

Three scenarios: golden path (well_formed.md -> PASS/PASS), a plan missing
structural sections (VISION/FAIL), and a plan with an orphan SC (FAIL).
"""
from __future__ import annotations

import json
from pathlib import Path

from plan_forge.api import check
from plan_forge.llm.client import LLMResponse
from plan_forge.llm.mocks import MockClient
from plan_forge.verdict import (
    EngineeringVerdict,
    EpistemicVerdict,
    Severity,
)

_FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"


def _load(name: str) -> str:
    return (_FIXTURES / name).read_text(encoding="utf-8")


def _mock_client(name: str, verdict: str) -> MockClient:
    """Build a MockClient returning the given verdict for any prompt.

    Uses empty string key so every prompt matches.
    """
    raw_json = json.dumps({
        "verdict": verdict,
        "reason": "integration test mock",
        "cited_instances": [],
        "search_evidence": [],
    })
    return MockClient(
        name=name,
        responses={"": LLMResponse(
            verdict=verdict,
            reasoning="integration test mock",
            cited_instances=[],
            search_evidence=[],
            cost_usd=0.0,
            raw_response={"original_json": raw_json},
        )},
    )


# ---------------------------------------------------------------------------
# Test 1: well_formed.md -> engineering PASS, epistemic PASS
# ---------------------------------------------------------------------------

def test_check_well_formed_plan_pass():
    """End-to-end: well_formed.md passes all gates -> engineering PASS / epistemic PASS.

    MockClients vote VERIFIED for all LLM checks (G6 SC falsifiability
    and G8 citation resolvability).  Findings may exist at MEDIUM/LOW
    but no BLOCKER/HIGH is allowed on the golden-path fixture.
    """
    plan_text = _load("well_formed.md")

    mock_clients = [
        _mock_client("mock_a", "VERIFIED"),
        _mock_client("mock_b", "VERIFIED"),
    ]

    verdict = check(plan_text, llm_clients=mock_clients, preamble=None)

    assert verdict.engineering == EngineeringVerdict.PASS
    assert verdict.epistemic == EpistemicVerdict.PASS
    # No BLOCKER or HIGH findings allowed in the golden-path fixture
    blocker_high = [
        f for f in verdict.findings
        if f.severity in {Severity.BLOCKER, Severity.HIGH}
    ]
    assert blocker_high == [], (
        f"well_formed.md produced unexpected BLOCKER/HIGH: "
        f"{[(f.check_id, f.severity, f.message[:60]) for f in blocker_high]}"
    )


# ---------------------------------------------------------------------------
# Test 2: vision plan (missing G1/G7 sections) -> epistemic VISION
# ---------------------------------------------------------------------------

def test_check_vision_plan():
    """A plan missing Reference Class and Scope Challenge -> epistemic VISION.

    G1.no_section and G7.no_section are BLOCKER findings on vision gates.
    External Voices is present (no G8.A.no_section), so no non-vision
    serious findings exist. Only vision-gate BLOCKERs fire, which
    resolve to VISION under the partition rule.
    """
    vision_plan = _load("vision_plan.md")
    verdict = check(vision_plan, llm_clients=[])

    assert verdict.epistemic == EpistemicVerdict.VISION
    vision_blockers = [
        f for f in verdict.findings
        if f.check_id.startswith(("G1.", "G7."))
        and f.severity == Severity.BLOCKER
    ]
    assert len(vision_blockers) > 0


# ---------------------------------------------------------------------------
# Test 3: fail plan (F1 BLOCKER from orphan SC) -> engineering FAIL
# ---------------------------------------------------------------------------

def test_check_fail_plan():
    """f1_fail.md: orphan SC (F1.orphan_sc HIGH) + no External Voices.

    F1.orphan_sc is HIGH severity and non-vision -> FAIL trigger.
    G8.A.no_section is BLOCKER (no External Voices section) and
    non-vision -> FAIL trigger.  G1/G3/G5/G7 absences are vision
    triggers; FAIL > VISION, so epistemic resolves to FAIL.
    """
    fail_plan = _load("f1_fail.md")
    verdict = check(fail_plan, llm_clients=[])

    assert verdict.engineering == EngineeringVerdict.FAIL
    # FAIL trigger: F1.orphan_sc (HIGH) + G8.A.no_section (BLOCKER);
    # VISION triggers also fire (G1/G3/G5/G7 absent) but FAIL wins.
    assert verdict.epistemic == EpistemicVerdict.FAIL
