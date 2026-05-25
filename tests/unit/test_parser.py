"""Unit tests for plan_forge.parser -- covers all 8 ParsedPlan fields."""
from pathlib import Path

from plan_forge.parser import parse

_FIXTURE_DIR = Path(__file__).parent.parent / "fixtures"


# -------------------------------------------------------------------
# test_parse_sections
# -------------------------------------------------------------------

def test_parse_sections():
    """Sections are extracted from ATX headings with correct body/level."""
    md = (
        "# Title\n"
        "\n"
        "Intro paragraph.\n"
        "\n"
        "## Reference Class\n"
        "\n"
        "Project A took 4 weeks.\n"
        "\n"
        "## Pre-mortem\n"
        "\n"
        "Failure mode 1.\n"
    )
    plan = parse(md)
    assert "Title" in plan.sections
    assert "Reference Class" in plan.sections
    assert "Pre-mortem" in plan.sections

    rc = plan.sections["Reference Class"]
    assert rc.level == 2
    assert "Project A" in rc.body

    pm = plan.sections["Pre-mortem"]
    assert pm.level == 2
    assert "Failure mode 1" in pm.body


def test_parse_sections_nested():
    """Subsections close correctly on same-level heading."""
    md = (
        "## Risks\n"
        "\n"
        "### Known Risks\n"
        "\n"
        "Risk A.\n"
        "\n"
        "### Gray Rhinos\n"
        "\n"
        "Rhino B.\n"
    )
    plan = parse(md)
    assert "Known Risks" in plan.sections
    assert "Gray Rhinos" in plan.sections
    # Known Risks body should NOT contain Gray Rhinos content
    assert "Rhino B" not in plan.sections["Known Risks"].body


# -------------------------------------------------------------------
# test_parse_sc_table
# -------------------------------------------------------------------

def test_parse_sc_table():
    """SC table parsing: SC-1, SC-2a, SC-2b with fail conditions."""
    md = (
        "## Success Criteria\n"
        "\n"
        "| SC | Criterion | Fail Condition |\n"
        "|-----|-----------|----------------|\n"
        "| SC-1 | Basic check | FAILS if no output |\n"
        "| SC-2a | Variant A | FAILS if A missing |\n"
        "| SC-2b | Variant B | FAILS if B missing |\n"
    )
    plan = parse(md)
    assert len(plan.sc_table) == 3

    sc1 = plan.sc_table[0]
    assert sc1.number == 1
    assert sc1.suffix == ''
    assert sc1.full_id == 'SC-1'
    assert sc1.name == 'Basic check'
    assert sc1.fail_condition == 'FAILS if no output'

    sc2a = plan.sc_table[1]
    assert sc2a.number == 2
    assert sc2a.suffix == 'a'
    assert sc2a.full_id == 'SC-2a'
    assert sc2a.name == 'Variant A'

    sc2b = plan.sc_table[2]
    assert sc2b.number == 2
    assert sc2b.suffix == 'b'
    assert sc2b.full_id == 'SC-2b'
    assert sc2b.name == 'Variant B'


def test_parse_sc_table_no_fail_condition_column():
    """SC table without Fail Condition column: fail_condition is None."""
    md = (
        "| SC | Name |\n"
        "|-----|------|\n"
        "| SC-3 | Third criterion |\n"
    )
    plan = parse(md)
    assert len(plan.sc_table) == 1
    assert plan.sc_table[0].fail_condition is None


# -------------------------------------------------------------------
# test_parse_risks
# -------------------------------------------------------------------

def test_parse_risks():
    """Risk extraction from 3 buckets: known, gray_rhino, black_swan."""
    md = (
        "## Risks\n"
        "\n"
        "### Known Risks\n"
        "\n"
        "| Risk | Probability | Impact |\n"
        "|------|-------------|--------|\n"
        "| Schedule slip | High | Medium |\n"
        "\n"
        "### Gray Rhinos\n"
        "\n"
        "| Gray Rhino | Denial Reason | Counter |\n"
        "|------------|---------------|---------|\n"
        "| Scope creep | Everyone ignores it | Weekly scope review |\n"
        "\n"
        "### Black Swans\n"
        "\n"
        "| Black Swan | Survival Plan |\n"
        "|------------|---------------|\n"
        "| Key person leaves | Cross-train team |\n"
    )
    plan = parse(md)

    known = [r for r in plan.risks if r.bucket == 'known']
    gray = [r for r in plan.risks if r.bucket == 'gray_rhino']
    black = [r for r in plan.risks if r.bucket == 'black_swan']

    assert len(known) == 1
    assert known[0].description == 'Schedule slip'

    assert len(gray) == 1
    assert gray[0].description == 'Scope creep'
    assert gray[0].denial_reason == 'Everyone ignores it'

    assert len(black) == 1
    assert black[0].description == 'Key person leaves'
    assert black[0].survival_plan == 'Cross-train team'


# -------------------------------------------------------------------
# test_parse_hedge_words
# -------------------------------------------------------------------

def test_parse_hedge_words():
    """All 11 canonical hedge words detected, case-insensitive."""
    words = [
        'maybe', 'likely', 'probably', 'perhaps', 'possibly',
        'seems', 'appears', 'should', 'could', 'might', 'may',
    ]
    md = '\n'.join(f"Line with {w} in it." for w in words)
    plan = parse(md)

    detected = {w for _, w in plan.hedge_word_locations}
    assert detected == set(words), f"Missing: {set(words) - detected}"
    assert len(plan.hedge_word_locations) == 11


def test_parse_hedge_words_meta_exemption():
    """Lines containing 'G4 Probability Calibration' are skipped."""
    md = (
        "This should be flagged.\n"
        "G4 Probability Calibration: maybe likely probably.\n"
        "Another should here.\n"
    )
    plan = parse(md)
    words = [w for _, w in plan.hedge_word_locations]
    assert words == ['should', 'should']


def test_parse_hedge_words_case_insensitive():
    """Hedge words matched case-insensitively, stored lowercase."""
    md = "SHOULD be detected. Maybe too."
    plan = parse(md)
    words = [w for _, w in plan.hedge_word_locations]
    assert 'should' in words
    assert 'maybe' in words


# -------------------------------------------------------------------
# test_parse_hedge_words_state_machine (REGRESSION)
# -------------------------------------------------------------------

def test_parse_hedge_words_state_machine():
    """REGRESSION: hedge words inside fenced code blocks NOT flagged.

    The fence-width state machine must track in_code_block across
    fence open/close, not just skip fence lines.
    """
    md = (
        "This should be flagged.\n"
        "```python\n"
        "# This should NOT be flagged\n"
        "if x might work:\n"
        "    pass\n"
        "```\n"
        "This could be flagged.\n"
    )
    plan = parse(md)

    lines_with_hedge = {line for line, _ in plan.hedge_word_locations}

    # "should" on line 1 and "could" on line 7 should be flagged
    assert 1 in lines_with_hedge, "should on line 1 not flagged"
    assert 7 in lines_with_hedge, "could on line 7 not flagged"

    # Lines 3, 4 (inside code block) should NOT be flagged
    assert 3 not in lines_with_hedge, "should inside code block flagged"
    assert 4 not in lines_with_hedge, "might inside code block flagged"

    assert len(plan.hedge_word_locations) == 2


def test_parse_hedge_words_multiple_code_blocks():
    """Multiple code block open/close cycles work correctly."""
    md = (
        "maybe here.\n"
        "```\n"
        "should not be here.\n"
        "```\n"
        "likely here.\n"
        "```\n"
        "could not be here.\n"
        "```\n"
        "possibly here.\n"
    )
    plan = parse(md)
    words = [w for _, w in plan.hedge_word_locations]
    assert words == ['maybe', 'likely', 'possibly']


def test_parse_hedge_words_wide_fence():
    """REGRESSION: 4-backtick fences close only on matching 4-backtick fence.

    A 3-backtick fence INSIDE a 4-backtick block must not close the block.
    """
    md = (
        "should be flagged.\n"
        "````\n"
        "# content inside 4-backtick block\n"
        "might NOT be flagged.\n"
        "```\n"
        "still inside 4-backtick block -- could NOT be flagged.\n"
        "```\n"
        "still inside 4-backtick block -- may NOT be flagged.\n"
        "````\n"
        "possibly flagged again.\n"
    )
    plan = parse(md)
    lines_with_hedge = {line for line, _ in plan.hedge_word_locations}
    assert 1 in lines_with_hedge, "should on line 1 not flagged"
    assert 10 in lines_with_hedge, "possibly on line 10 not flagged"
    for inside_line in (3, 4, 6, 8):
        assert inside_line not in lines_with_hedge, (
            f"line {inside_line} inside 4-backtick block was flagged"
        )


# -------------------------------------------------------------------
# test_parse_citations
# -------------------------------------------------------------------

def test_parse_citations():
    """Citations extracted from External Voices section."""
    md = (
        "## External Voices\n"
        "\n"
        "- Flyvbjerg et al. (2002). Underestimating Costs in Public Works.\n"
        "- Klein (2007). Performing a Project Premortem.\n"
        "- Not a citation line\n"
        "- Taleb (2007). The Black Swan.\n"
    )
    plan = parse(md)
    assert len(plan.citations) == 3
    assert any('Flyvbjerg' in c for c in plan.citations)
    assert any('Klein' in c for c in plan.citations)
    assert any('Taleb' in c for c in plan.citations)


def test_parse_citations_only_in_external_voices():
    """Citations outside External Voices section are NOT extracted."""
    md = (
        "## References\n"
        "\n"
        "- Popper (1934). The Logic of Scientific Discovery.\n"
        "\n"
        "## External Voices\n"
        "\n"
        "- Tetlock (2015). Superforecasting.\n"
    )
    plan = parse(md)
    assert len(plan.citations) == 1
    assert 'Tetlock' in plan.citations[0]


def test_parse_citations_author_initials_single():
    """Author initials after surname are now accepted.

    "Kahneman, D. (2011). Title." and "Brooks, F. P. (1975). Title."
    were previously dropped because the regex had no initials group.
    """
    md = (
        "## External Voices\n"
        "\n"
        "- Kahneman, D. (2011). Thinking, Fast and Slow.\n"
        "- Brooks, F. P. (1975). The Mythical Man-Month.\n"
        "- Dijkstra, E. (2020). Go To Statement Considered Harmful.\n"
    )
    plan = parse(md)
    assert len(plan.citations) == 3, (
        f"expected 3 citations, got {len(plan.citations)}: "
        f"{plan.citations}"
    )
    assert any('Kahneman' in c for c in plan.citations)
    assert any('Brooks' in c for c in plan.citations)
    assert any('Dijkstra' in c for c in plan.citations)


def test_parse_citations_author_initials_coauthor():
    """Coauthor with initials after ampersand is now accepted.

    "Zhang, L. & Kumar, R. (2019). Title." was previously dropped.
    """
    md = (
        "## External Voices\n"
        "\n"
        "- Zhang, L. & Kumar, R. (2019). Theory of X.\n"
    )
    plan = parse(md)
    assert len(plan.citations) == 1, (
        f"expected 1 citation, got {len(plan.citations)}: "
        f"{plan.citations}"
    )
    assert any('Zhang' in c for c in plan.citations)


def test_parse_citations_no_regression_existing_forms():
    """Existing citation forms without initials are still extracted."""
    md = (
        "## External Voices\n"
        "\n"
        "- Klein (2007). Performing a Project Premortem.\n"
        "- Flyvbjerg et al. (2002). Underestimating Costs.\n"
        "- Popper (1934). The Logic of Scientific Discovery.\n"
    )
    plan = parse(md)
    assert len(plan.citations) == 3, (
        f"expected 3 citations, got {len(plan.citations)}: "
        f"{plan.citations}"
    )
    assert any('Klein' in c for c in plan.citations)
    assert any('Flyvbjerg' in c for c in plan.citations)
    assert any('Popper' in c for c in plan.citations)


def test_parse_citations_non_citation_bullet_rejected():
    """Non-citation bullets in External Voices are NOT extracted.

    A plain prose bullet like "See the appendix for the full list."
    must not be treated as a citation.
    """
    md = (
        "## External Voices\n"
        "\n"
        "- See the appendix for the full list.\n"
        "- Klein (2007). Performing a Project Premortem.\n"
    )
    plan = parse(md)
    assert len(plan.citations) == 1, (
        f"expected 1 citation (Klein only), got {len(plan.citations)}: "
        f"{plan.citations}"
    )
    assert any('Klein' in c for c in plan.citations)
    assert not any('appendix' in c for c in plan.citations)


def test_parse_citations_bibliography_order_italic_title():
    """Bibliography-order with italic title is extracted.

    "Popper, *The Logic of Scientific Discovery* (1934)." uses the
    bibliography order (title before year) rather than APA inline
    (year after author).  The parser must recognize both.
    """
    md = (
        "## External Voices\n"
        "\n"
        "- Popper, *The Logic of Scientific Discovery* (1934). Falsifia"
        "bility doctrine.\n"
        "- Wucker, *The Gray Rhino* (2016). Gray rhino taxonomy.\n"
        "- Tetlock & Gardner, *Superforecasting* (2015). Calibration.\n"
    )
    plan = parse(md)
    assert len(plan.citations) == 3, (
        f"expected 3 bibliography-order citations, got "
        f"{len(plan.citations)}: {plan.citations}"
    )
    assert any('Popper' in c for c in plan.citations)
    assert any('Wucker' in c for c in plan.citations)
    assert any('Tetlock' in c for c in plan.citations)


def test_parse_citations_bibliography_order_quoted_title():
    """Bibliography-order with quoted title and et al. is extracted.

    "Flyvbjerg et al., \"Underestimating Costs\" (2002)." and
    "Kahneman & Tversky, \"Intuitive Prediction\" (1979)." must match.
    """
    md = (
        "## External Voices\n"
        "\n"
        '- Flyvbjerg et al., "Underestimating Costs in Public Works"'
        " (2002). Reference class.\n"
        '- Kahneman & Tversky, "Intuitive Prediction" (1979).'
        " Planning fallacy.\n"
    )
    plan = parse(md)
    assert len(plan.citations) == 2, (
        f"expected 2 citations, got {len(plan.citations)}: "
        f"{plan.citations}"
    )
    assert any('Flyvbjerg' in c for c in plan.citations)
    assert any('Kahneman' in c for c in plan.citations)


def test_parse_citations_bibliography_prose_bullets_rejected():
    """FP guard: ordinary prose bullets in External Voices yield 0.

    Bullets without a (YYYY) year pattern must never be extracted,
    even when they start with a capitalized word.  This ensures G8
    still fires when citations are genuinely absent.
    """
    md = (
        "## External Voices\n"
        "\n"
        "- See the literature review appendix for relevant prior work.\n"
        "- The project team reviewed internal retrospectives.\n"
        "- Best practices from industry experience informed this plan.\n"
        "- Industry norms and team judgment were consulted.\n"
    )
    plan = parse(md)
    assert len(plan.citations) == 0, (
        f"expected 0 citations (prose only), got "
        f"{len(plan.citations)}: {plan.citations}"
    )


def test_parse_citations_bibliography_fp_fixture():
    """FP fixture: bibliography-order citations produce >= 1 citation."""
    with open(
        _FIXTURE_DIR / "g8_biblio_citation_fp.md", encoding="utf-8"
    ) as fh:
        md = fh.read()
    plan = parse(md)
    assert len(plan.citations) >= 1, (
        f"FP fixture must yield >= 1 citation; got {len(plan.citations)}"
    )


def test_parse_citations_bibliography_tp_fixture():
    """TP fixture: prose-only External Voices yields 0 citations."""
    with open(
        _FIXTURE_DIR / "g8_biblio_citation_tp.md", encoding="utf-8"
    ) as fh:
        md = fh.read()
    plan = parse(md)
    assert len(plan.citations) == 0, (
        f"TP fixture must yield 0 citations; got "
        f"{len(plan.citations)}: {plan.citations}"
    )


def test_parse_citations_biblio_prose_bullet_rejected():
    """Prose bullets with quoted phrases and a year are NOT extracted.

    A bullet like 'Consider "structured data" (2024) for the design.'
    starts with a capitalized word and contains (YYYY), but lacks the
    mandatory comma before the quoted title.  The bibliography regex
    must require the comma so such prose does not suppress G8.
    """
    md = (
        "## External Voices\n"
        "\n"
        '- Consider "structured data" (2024) for the design.\n'
        '- Research "best practices" (2023) methodology.\n'
        "- Klein (2007). Performing a Project Premortem.\n"
    )
    plan = parse(md)
    assert len(plan.citations) == 1
    assert any("Klein" in c for c in plan.citations)


def test_parse_citations_biblio_known_boundary_capitalized_noun():
    """Known boundary: capitalized noun + comma + quoted phrase + year matches.

    The bibliography regex cannot distinguish a plan noun like Strategy
    from a surname without a dictionary.  This documents the behavior so
    future regex changes do not silently widen it.
    """
    md = (
        "## External Voices\n"
        "\n"
        '- Strategy, "Phase Two" (2024) is complete.\n'
    )
    plan = parse(md)
    # This matches because the regex cannot tell a noun from a surname.
    # It is an acceptable limitation: External Voices in practice contains
    # only citations, not plan-noun bullets.
    assert len(plan.citations) == 1


# -------------------------------------------------------------------
# test_parse_anchors
# -------------------------------------------------------------------

def test_parse_anchors():
    """G9 anchor extraction with type classification."""
    md = (
        "The project takes 12 weeks.\n"
        "[anchor: https://example.com/timeline]\n"
        "\n"
        "Cost is $500K.\n"
        "[anchor: prototype, measured throughput]\n"
        "\n"
        "Performance improved 3x.\n"
        "[anchor: ref: Smith et al. 2020]\n"
        "\n"
        "Duration is 6 months.\n"
        "[anchor: see table in section 3]\n"
        "\n"
        "Takes 4 weeks as estimated.\n"
        "[anchor: forge-code project]\n"
    )
    plan = parse(md)
    assert len(plan.anchors) == 5

    types = {a.anchor_type for a in plan.anchors}
    assert 'url' in types
    assert 'prototype' in types
    assert 'publication' in types
    assert 'in_plan_derivation' in types
    assert 'project_name' in types


def test_parse_anchor_url_type():
    """Anchor starting with http classified as url."""
    md = (
        "Takes 8 weeks.\n"
        "[anchor: https://example.com/data]\n"
    )
    plan = parse(md)
    assert len(plan.anchors) >= 1
    url_anchors = [a for a in plan.anchors if a.anchor_type == 'url']
    assert len(url_anchors) >= 1


def test_parse_anchor_publication_et_al():
    """Anchor containing 'et al' classified as publication."""
    md = (
        "Improvement of 2x observed.\n"
        "[anchor: Flyvbjerg et al. cost overrun study]\n"
    )
    plan = parse(md)
    pub_anchors = [a for a in plan.anchors if a.anchor_type == 'publication']
    assert len(pub_anchors) >= 1


def test_parse_anchor_in_plan_derivation():
    """Anchor with 'in-plan-derivation' classified correctly."""
    md = (
        "Estimated at 16 weeks total.\n"
        "[anchor: in-plan-derivation from Reference Class table]\n"
    )
    plan = parse(md)
    ipd = [a for a in plan.anchors if a.anchor_type == 'in_plan_derivation']
    assert len(ipd) >= 1


# -------------------------------------------------------------------
# test_parse_quantitative_claims_without_anchor
# -------------------------------------------------------------------

def test_parse_quantitative_claims_without_anchor():
    """Unanchored quantitative claims are captured."""
    md = (
        "This takes 12 weeks to complete.\n"
        "No anchor provided above.\n"
        "\n"
        "This takes 4 weeks.\n"
        "[anchor: forge-code project]\n"
    )
    plan = parse(md)
    unanchored = plan.quantitative_claims_without_anchor
    # "12 weeks" has no anchor; "4 weeks" does
    assert any('12 weeks' in claim for _, claim in unanchored)
    anchored_claims = {a.claim_text for a in plan.anchors}
    assert any('4 weeks' in c for c in anchored_claims)


# -------------------------------------------------------------------
# test_parse_anchor_back_reference_exempted
# -------------------------------------------------------------------

def test_parse_anchor_back_reference_exempted():
    """Back-references to canonical anchors are NOT flagged as unanchored.

    Under the canonical-declaration convention: claims whose surrounding
    text contains back-reference phrases are skipped.
    """
    md = (
        "The project takes 16 weeks.\n"
        "[anchor: reference class derivation]\n"
        "\n"
        "As discussed, the 16 weeks estimate is conservative.\n"
        "\n"
        "Per Reference Class data, 16 weeks is the median.\n"
        "\n"
        "See L100 for the 16 weeks breakdown.\n"
        "\n"
        "The downstream 16 weeks figure is well-supported.\n"
    )
    plan = parse(md)

    # The first "16 weeks" is anchored.
    # Lines 4, 6, 8, 10 all contain back-reference phrases and
    # should NOT appear in quantitative_claims_without_anchor.
    unanchored_texts = [claim for _, claim in
                        plan.quantitative_claims_without_anchor]
    # None of the back-referenced "16 weeks" should be in unanchored
    for text in unanchored_texts:
        if '16 weeks' in text:
            # If it appears, it must NOT be from a back-reference line
            assert False, (
                f"Back-referenced claim should be exempted: {text!r}"
            )


def test_parse_anchor_table_cells_skipped():
    """Quantitative claims inside table cells are skipped entirely.

    G9 checks prose only; tables are the anchor source (Reference Class
    table itself IS the anchor).
    """
    md = (
        "| Project | Duration | Ratio |\n"
        "|---------|----------|-------|\n"
        "| Project A | 8 weeks | 1.2x |\n"
        "| Project B | 12 weeks | 0.9x |\n"
        "\n"
        "This project will take 10 weeks.\n"
    )
    plan = parse(md)
    # "8 weeks" and "12 weeks" in table should NOT appear in unanchored
    unanchored_texts = [claim for _, claim in
                        plan.quantitative_claims_without_anchor]
    for text in unanchored_texts:
        assert '8 weeks' not in text, "table cell claim should be skipped"
        assert '12 weeks' not in text, "table cell claim should be skipped"
    # "10 weeks" in prose IS unanchored (no anchor provided)
    assert any('10 weeks' in t for t in unanchored_texts)


def test_parse_g9_code_block_skipped():
    """Quantitative claims inside fenced code blocks are skipped."""
    md = (
        "```\n"
        "timeout = 30 days\n"
        "```\n"
        "\n"
        "This takes 5 weeks.\n"
    )
    plan = parse(md)
    unanchored_texts = [claim for _, claim in
                        plan.quantitative_claims_without_anchor]
    # "30 days" inside code block should be skipped
    assert not any('30 days' in t for t in unanchored_texts)
    # "5 weeks" in prose should be captured
    assert any('5 weeks' in t for t in unanchored_texts)
