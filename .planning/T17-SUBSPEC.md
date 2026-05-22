# T17 SUBSPEC: PBR P6 metadata-currency check

Status: implemented (T17 complete; three-cycle review pending separately).
Depends on: T05 skeleton, T06 parser, T07 mechanical F1-F7, T08 PBR P1/P2/P5.
Scope: P6 only. Date-currency only (version-currency deferred, see GAPS.md Gap 3).

## 1. Severity philosophy
P6 is HIGH, and it is an HONESTY check, not a hygiene check. A frontmatter
currency date that contradicts in-body evidence means the plan misstates its
own provenance -- an honesty defect, not a formatting slip. Per T08 section 1,
HIGH is for findings whose resolution forces a true ownership action; here the
author must stop misstating the date (correct it, or honestly record the
update), which is exactly such an action. So P6 CAN drive an engineering FAIL.
Honest-but-imprecise dating is NOT penalized: P6 compares only exact YYYY-MM-DD
values, takes the MAX of all frontmatter dates (so listing every update -- even
verbosely -- clears the check), and emits nothing when the frontmatter carries
no exact date at all.

## 2. Architecture
src/plan_forge/checks/pbr/p6_metadata_currency.py exports exactly:
    def check(parsed: ParsedPlan) -> list[Finding]: ...
Imports mirror p2_null_propagation.py:
    from __future__ import annotations
    import re
    from plan_forge.parser import ParsedPlan
    from plan_forge.verdict import Finding, Severity

### 2.1 Integration
pbr/__init__.py run() appends P6 AFTER P5:
    findings.extend(p6_metadata_currency.check(parsed))
This is the ONLY wiring edit. api.check_mechanical -> mechanical.run ->
pbr.run already chains automatically, so P6 flows through with no api.py or
mechanical/__init__.py logic change. Final PBR order: P1, P2, P5, P6.
pbr/__init__.py module docstring updated: now says P6 is integrated (T17 done).

## 3. Finding contract
    Finding(
        check_id="P6.metadata_contradicts_body",
        severity=Severity.HIGH,
        location="line:<N>",          # line of the frontmatter date field
        message=<see 4.4>,
        fix_hint=<see 4.5>,
    )
llm_evidence / evidence_tier_summary left at default (pure mechanical).

## 4. Algorithm (date-currency)
4.1 Frontmatter region = from start of raw_text up to (but excluding) the first
    line that is an H2 heading ("## ..."). Concretely: scan lines until the
    first line matching r'^##\s'. Everything before that is the frontmatter
    region.
4.2 Frontmatter dates = all r'\b(\d{4})-(\d{2})-(\d{2})\b' matches found on
    lines in the frontmatter region that begin with a bold metadata key
    (r'^\*\*(Drafted|Status|Updated|Revised|Date|Last updated)\*\*\s*:'),
    case-insensitive on the key. fm_latest = max of those dates.
    If NO frontmatter date is found -> RETURN [] (no findings). This is the
    no-frontmatter PASS path that scaffold-generated plans rely on.
4.3 Body currency-dates = for each line AFTER the frontmatter region, find any
    YYYY-MM-DD whose date string is within 60 characters of a currency keyword
    on the same line. Currency keywords (case-insensitive):
      integrated, updated, revised, fixes, "as of", "current as of",
      completed, merged, shipped, released, "last updated".
    Record (date, line_number, frontmatter_date_line_number).
4.4 For each body currency-date strictly GREATER than fm_latest, emit ONE
    finding (dedupe by (date, body_line)). Point location at the frontmatter
    date field line (the line where fm_latest was found) so the fix is
    actionable. message example:
      "frontmatter currency date 2026-05-18 contradicts in-body evidence of
       work on 2026-05-19 (line 42); the plan misstates its own provenance"
4.5 fix_hint:
      "correct the frontmatter Drafted/Status/Updated date to honestly cover
       work through the latest in-body currency date (a date range or an
       appended update entry is fine -- verbose honest dating is not
       penalized), or add an inline <!-- plan-forge: p6-ok (reason) --> marker
       on the frontmatter date line if the in-body date genuinely predates
       drafting"
4.6 Escape hatch: if a line in the frontmatter region matches
    r'<!--\s*plan-forge:\s*p6-ok' -> RETURN [] (suppress all P6 for this plan).
    Mirror p2-ok semantics.

## 5. Edge cases (covered by tests)
- No frontmatter region / no dated metadata key -> [] (scaffold case).
- Body currency-date <= fm_latest -> [] (current metadata).
- Verbose frontmatter listing every update date -> fm_latest is the MAX -> [].
- Imprecise frontmatter date with no exact YYYY-MM-DD -> [] (uncertainty tolerated).
- Multiple contradicting body dates -> one finding each (deduped).
- p6-ok marker present -> [].
- A bare YYYY-MM-DD in the body NOT near a currency keyword -> ignored (no FP).

## 6. Test coverage (tests/unit/test_p6_metadata_currency.py)
- test_pass_current_metadata: p6_pass.md -> 0 findings.
- test_fail_misstated_provenance: p6_fail.md -> 1 P6.metadata_contradicts_body HIGH.
- test_p6_severity_is_high: all P6 findings must be HIGH.
- test_pass_no_frontmatter: no metadata keys -> 0 findings.
- test_pass_verbose_update_dates: verbose multi-date frontmatter -> MAX clears -> 0.
- test_pass_imprecise_date: no exact YYYY-MM-DD in frontmatter -> 0 findings.
- test_bare_body_date_ignored: body date with no currency keyword -> 0 findings.
- test_p6_ok_suppresses: misstated setup + p6-ok marker -> 0 findings.
- test_multiple_contradicting_body_dates: 2 body currency-dates > fm -> 2 findings.
- test_integration_via_pbr_run: pbr.run() includes P6 after P1/P2/P5.
- test_p6_high_fails_engineering: P6 finding -> check_mechanical engineering=FAIL.

## 7. Fixtures (tests/fixtures/)
- p6_pass.md: **Drafted**: 2026-05-19 + body "integrated 2026-05-19" (equal, clear).
- p6_fail.md: **Drafted**: 2026-05-18 + body "integrated 2026-05-19" (contradicts).
(Edge-case scenarios use inline strings in the test file, not separate fixtures.)

## 8. Non-goals (not in T17)
- Do NOT add frontmatter field to ParsedPlan / change parser.py (D2).
- Do NOT implement version-currency (D3; deferred to GAPS.md Gap 3).
- Do NOT modify F1-F7, P1/P2/P5, verdict.py, or their tests.
- Do NOT change api.py or mechanical logic (docstrings updated only).
