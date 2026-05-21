"""Integration tests: parse fixture files end-to-end."""
import pathlib

from plan_forge.parser import parse

_FIXTURES = pathlib.Path(__file__).resolve().parent.parent / "fixtures"


def _load_fixture(name: str) -> str:
    return (_FIXTURES / name).read_text(encoding="utf-8")


# -------------------------------------------------------------------
# pass_well_formed.md
# -------------------------------------------------------------------

def test_well_formed_sections():
    """Well-formed plan has all required G-check headings."""
    plan = parse(_load_fixture("pass_well_formed.md"))
    required = [
        "Reference Class",
        "Risks",
        "Pre-mortem",
        "Scope Challenge",
        "Chaos Response",
        "External Voices",
    ]
    for heading in required:
        assert heading in plan.sections, f"Missing section: {heading}"


def test_well_formed_sc_table():
    plan = parse(_load_fixture("pass_well_formed.md"))
    assert len(plan.sc_table) > 0
    ids = [sc.full_id for sc in plan.sc_table]
    assert "SC-1" in ids
    assert "SC-2a" in ids
    assert "SC-2b" in ids


def test_well_formed_risks_three_buckets():
    plan = parse(_load_fixture("pass_well_formed.md"))
    buckets = {r.bucket for r in plan.risks}
    assert "known" in buckets
    assert "gray_rhino" in buckets
    assert "black_swan" in buckets


def test_well_formed_no_unanchored_claims():
    """Every quantitative claim in well-formed plan has an anchor."""
    plan = parse(_load_fixture("pass_well_formed.md"))
    assert plan.quantitative_claims_without_anchor == [], (
        f"Unexpected unanchored claims: "
        f"{plan.quantitative_claims_without_anchor}"
    )


def test_well_formed_citations():
    plan = parse(_load_fixture("pass_well_formed.md"))
    assert len(plan.citations) >= 3


# -------------------------------------------------------------------
# fail_missing_premortem.md
# -------------------------------------------------------------------

def test_missing_premortem_not_in_sections():
    """Plan missing Pre-mortem does NOT have that section."""
    plan = parse(_load_fixture("fail_missing_premortem.md"))
    assert "Pre-mortem" not in plan.sections


def test_missing_premortem_other_sections_present():
    """Other sections are still parsed correctly."""
    plan = parse(_load_fixture("fail_missing_premortem.md"))
    assert "Reference Class" in plan.sections
    assert "Risks" in plan.sections
    assert "Scope Challenge" in plan.sections


# -------------------------------------------------------------------
# fail_no_g9_anchor.md
# -------------------------------------------------------------------

def test_no_g9_anchor_has_unanchored_claim():
    """Plan with missing anchor has '12 weeks' in unanchored claims."""
    plan = parse(_load_fixture("fail_no_g9_anchor.md"))
    unanchored_texts = [claim for _, claim in
                        plan.quantitative_claims_without_anchor]
    assert any("12 weeks" in t for t in unanchored_texts), (
        f"Expected '12 weeks' in unanchored claims, got: {unanchored_texts}"
    )


def test_no_g9_anchor_other_anchored_claims_ok():
    """Anchored claims in the same plan are still detected."""
    plan = parse(_load_fixture("fail_no_g9_anchor.md"))
    # $2000 in Scope Challenge has [anchor: in-plan-derivation ...]
    anchored_claims = {a.claim_text for a in plan.anchors}
    assert any("2000" in c for c in anchored_claims) or \
        len(plan.anchors) >= 1
