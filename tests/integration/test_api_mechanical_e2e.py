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

    Snapshot values (captured 2026-05-19, mechanical layer F1-F7 + P1/P2/P5):

    engineering = FAIL
      Reason: F3.unverified_cross_plan_ref (HIGH) and P1.orphan_identifier
      (HIGH) drive the FAIL.  F2.duplicate_fact also fires (the well-formed
      fixture reuses common phrases across sections, e.g. the Reference
      Class table values appear in multiple rows) but F2 is LOW and does not
      affect the engineering verdict.  P1 fires because section headings used
      as identifiers are not referenced elsewhere in the plan body.

    total findings = 26
      Breakdown: F2 x 20, F3 x 1, P1 x 5.

    check_id_counts = {
        'F2.duplicate_fact': 20,
        'F3.unverified_cross_plan_ref': 1,
        'P1.orphan_identifier': 5,
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
    assert len(result.findings) == 26, (
        f"{fixture}: finding count snapshot mismatch "
        f"(got {len(result.findings)}, expected 26). "
        "Update snapshot if a check was added or removed."
    )

    # Snapshot: per-check_id distribution
    expected_counts = {
        "F2.duplicate_fact": 20,
        "F3.unverified_cross_plan_ref": 1,
        "P1.orphan_identifier": 5,
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

    Snapshot values (captured 2026-05-19, mechanical layer F1-F7 + P1/P2/P5):

    engineering = FAIL
      Reason: same drivers as pass_well_formed -- F3.unverified_cross_plan_ref
      (HIGH) and P1.orphan_identifier (HIGH) cause the FAIL.  F2.duplicate_fact
      fires (LOW) on the shared table/prose structure but does not affect the
      verdict.  The missing Pre-mortem is an epistemic (G-layer) concern, not
      a mechanical one, so the F/PBR layer adds no finding for it here.

    total findings = 25
      Breakdown: F2 x 20, F3 x 1, P1 x 4.
      (One fewer P1 than pass_well_formed because the Pre-mortem section
      heading is absent, reducing the identifier count by 1.)

    check_id_counts = {
        'F2.duplicate_fact': 20,
        'F3.unverified_cross_plan_ref': 1,
        'P1.orphan_identifier': 4,
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
    assert len(result.findings) == 25, (
        f"{fixture}: finding count snapshot mismatch "
        f"(got {len(result.findings)}, expected 25). "
        "Update snapshot if a check was added or removed."
    )

    # Snapshot: per-check_id distribution
    expected_counts = {
        "F2.duplicate_fact": 20,
        "F3.unverified_cross_plan_ref": 1,
        "P1.orphan_identifier": 4,
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

    Snapshot values (captured 2026-05-19, mechanical layer F1-F7 + P1/P2/P5):

    engineering = FAIL
      Reason: P1.orphan_identifier (HIGH) drives the FAIL.  F2.duplicate_fact
      also fires (LOW, same repeated phrases in the Reference Class table) but
      does not affect the verdict.
      Neither F3 nor any anchor-specific mechanical check fires here because
      the G9 anchor check is a G-layer (epistemological) gate; the F-layer
      only flags structural issues.

    total findings = 23
      Breakdown: F2 x 20, P1 x 3.
      (F3 absent: this fixture has no explicit cross-plan references.
      P1 count is 3 because the fixture has fewer section identifiers.)

    check_id_counts = {
        'F2.duplicate_fact': 20,
        'P1.orphan_identifier': 3,
    }
    """
    fixture = "fail_no_g9_anchor.md"
    result = check_mechanical(_load(fixture))

    _assert_verdict_structure(result, fixture)

    # Snapshot: engineering verdict
    assert result.engineering == EngineeringVerdict.FAIL, (
        f"{fixture}: engineering snapshot mismatch. "
        "Update this snapshot with justification if severity logic changed."
    )

    # Snapshot: total finding count
    assert len(result.findings) == 23, (
        f"{fixture}: finding count snapshot mismatch "
        f"(got {len(result.findings)}, expected 23). "
        "Update snapshot if a check was added or removed."
    )

    # Snapshot: per-check_id distribution
    expected_counts = {
        "F2.duplicate_fact": 20,
        "P1.orphan_identifier": 3,
    }
    actual_counts = _check_id_counts(result.findings)
    assert actual_counts == expected_counts, (
        f"{fixture}: check_id count snapshot mismatch. "
        f"actual={actual_counts}, expected={expected_counts}. "
        "Update snapshot if a check's output changed."
    )
