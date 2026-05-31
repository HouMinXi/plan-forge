"""Integration tests: check_mechanical() end-to-end on existing fixtures.

Snapshot-style assertions: engineering verdict + total finding count +
check_id distribution are captured.  If a later commit changes any
value, the test fails loudly and forces the author to confirm intent
by updating the snapshot with a comment explaining the change.
"""
import pathlib

from plan_forge.api import check_mechanical
from plan_forge.verdict import (
    Verdict,
    EngineeringVerdict,
    EpistemicVerdict,
    Finding,
)

_FIXTURES = pathlib.Path(__file__).parent.parent / "fixtures"


def _load(name: str) -> str:
    return (_FIXTURES / name).read_text(encoding="utf-8")


def _check_id_counts(findings: list[Finding]) -> dict:
    """Return {check_id: count} mapping from a findings list."""
    counts: dict[str, int] = {}
    for f in findings:
        counts[f.check_id] = counts.get(f.check_id, 0) + 1
    return counts


# ---------------------------------------------------------------------------
# Helper: assert structural invariants common to every Verdict
# ---------------------------------------------------------------------------

def _assert_verdict_structure(result: Verdict, fixture_name: str) -> None:
    """Assert that result is a well-formed Verdict regardless of values."""
    assert isinstance(result, Verdict), (
        f"{fixture_name}: result must be a Verdict instance"
    )
    assert isinstance(result.findings, list), (
        f"{fixture_name}: Verdict.findings must be a list"
    )
    for item in result.findings:
        assert isinstance(item, Finding), (
            f"{fixture_name}: each findings element must be Finding, "
            f"got {type(item)}"
        )
    # epistemic is always VISION in mechanical-only mode (no G-gates run)
    assert result.epistemic == EpistemicVerdict.VISION, (
        f"{fixture_name}: epistemic must always be VISION in mechanical-only mode"
    )


# ---------------------------------------------------------------------------
# Test 1: pass_well_formed.md
# ---------------------------------------------------------------------------

def test_api_mechanical_on_pass_well_formed():
    """End-to-end on the well-formed pass fixture.

    Snapshot values (updated after P1 table-definition exemption):

    engineering = FAIL
      Reason: F3.unverified_cross_plan_ref (HIGH) drives the FAIL.
      F2.duplicate_fact fires (LOW, repeated Reference Class phrases) but
      does not affect the verdict.  P1 fires once ("phase 2" in the Goal
      anchor) but SC-N IDs are no longer orphans: they are defined as
      first-cell entries in the Success Criteria table.

    total findings = 22
      Breakdown: F2 x 20, F3 x 1, P1 x 1.

    check_id_counts = {
        'F2.duplicate_fact': 20,
        'F3.unverified_cross_plan_ref': 1,
        'P1.orphan_identifier': 1,
    }
    """
    fixture = "pass_well_formed.md"
    result = check_mechanical(_load(fixture))

    _assert_verdict_structure(result, fixture)

    # Snapshot: engineering verdict
    assert result.engineering == EngineeringVerdict.FAIL, (
        f"{fixture}: engineering snapshot mismatch. "
        "If F3/P1 severity changed, update this snapshot with justification."
    )

    # Snapshot: total finding count
    assert len(result.findings) == 32, (
        f"{fixture}: finding count snapshot mismatch "
        f"(got {len(result.findings)}, expected 32). "
        "Update snapshot if a check was added or removed."
    )

    # Snapshot: per-check_id distribution
    expected_counts = {
        "F2.duplicate_fact": 20,
        "F3.unverified_cross_plan_ref": 1,
        "F10.noun_phrase_duplicate": 10,
        "P1.orphan_identifier": 1,
    }
    actual_counts = _check_id_counts(result.findings)
    assert actual_counts == expected_counts, (
        f"{fixture}: check_id count snapshot mismatch. "
        f"actual={actual_counts}, expected={expected_counts}. "
        "Update snapshot if a check's output changed."
    )


# ---------------------------------------------------------------------------
# Test 2: fail_missing_premortem.md
# ---------------------------------------------------------------------------

def test_api_mechanical_on_fail_missing_premortem():
    """End-to-end on the fixture that omits the Pre-mortem section.

    Snapshot values (updated after P1 table-definition exemption):

    engineering = FAIL
      Reason: F3.unverified_cross_plan_ref (HIGH) drives the FAIL.
      F2.duplicate_fact fires (LOW) on shared table/prose but does not
      affect the verdict.  P1 fires once ("phase 2" in the Goal anchor).
      SC-N IDs are no longer P1 orphans: they are defined as first-cell
      entries in the Success Criteria table.

    total findings = 22
      Breakdown: F2 x 20, F3 x 1, P1 x 1.

    check_id_counts = {
        'F2.duplicate_fact': 20,
        'F3.unverified_cross_plan_ref': 1,
        'P1.orphan_identifier': 1,
    }
    """
    fixture = "fail_missing_premortem.md"
    result = check_mechanical(_load(fixture))

    _assert_verdict_structure(result, fixture)

    # Snapshot: engineering verdict
    assert result.engineering == EngineeringVerdict.FAIL, (
        f"{fixture}: engineering snapshot mismatch. "
        "Update this snapshot with justification if severity logic changed."
    )

    # Snapshot: total finding count
    assert len(result.findings) == 32, (
        f"{fixture}: finding count snapshot mismatch "
        f"(got {len(result.findings)}, expected 32). "
        "Update snapshot if a check was added or removed."
    )

    # Snapshot: per-check_id distribution
    expected_counts = {
        "F2.duplicate_fact": 20,
        "F3.unverified_cross_plan_ref": 1,
        "F10.noun_phrase_duplicate": 10,
        "P1.orphan_identifier": 1,
    }
    actual_counts = _check_id_counts(result.findings)
    assert actual_counts == expected_counts, (
        f"{fixture}: check_id count snapshot mismatch. "
        f"actual={actual_counts}, expected={expected_counts}. "
        "Update snapshot if a check's output changed."
    )


# ---------------------------------------------------------------------------
# Test 3: fail_no_g9_anchor.md
# ---------------------------------------------------------------------------

def test_api_mechanical_on_fail_no_g9_anchor():
    """End-to-end on the fixture that omits G9 inline anchors on the Goal.

    Snapshot values (updated after P1 table-definition exemption):

    engineering = PASS
      SC-N IDs in the Success Criteria table are now treated as defined
      there (first-cell table definition), so P1 no longer fires on them.
      This fixture has no F3 cross-plan references and no other HIGH
      findings, so engineering reaches PASS.  The missing G9 anchor is
      an epistemic (G-layer) concern, not a mechanical one; the F/PBR
      layer correctly produces no finding for it.

    total findings = 20
      Breakdown: F2 x 20.
      (P1 absent: all former P1 findings were SC-N table-defined IDs.)

    check_id_counts = {
        'F2.duplicate_fact': 20,
    }
    """
    fixture = "fail_no_g9_anchor.md"
    result = check_mechanical(_load(fixture))

    _assert_verdict_structure(result, fixture)

    # Snapshot: engineering verdict
    assert result.engineering == EngineeringVerdict.PASS, (
        f"{fixture}: engineering snapshot mismatch. "
        "Update this snapshot with justification if severity logic changed."
    )

    # Snapshot: total finding count
    assert len(result.findings) == 30, (
        f"{fixture}: finding count snapshot mismatch "
        f"(got {len(result.findings)}, expected 30). "
        "Update snapshot if a check was added or removed."
    )

    # Snapshot: per-check_id distribution
    expected_counts = {
        "F2.duplicate_fact": 20,
        "F10.noun_phrase_duplicate": 10,
    }
    actual_counts = _check_id_counts(result.findings)
    assert actual_counts == expected_counts, (
        f"{fixture}: check_id count snapshot mismatch. "
        f"actual={actual_counts}, expected={expected_counts}. "
        "Update snapshot if a check's output changed."
    )
