# Phase 10: F2 Structural False-Positive Reduction - Context

**Gathered:** 2026-05-29
**Status:** Ready for planning

<domain>
## Phase Boundary

Add two new guards to `f2_duplicate_fact.check()` that suppress F2.duplicate_fact
LOW findings caused by structural template phrases and commit-signature tokens.
Zero changes outside `f2_duplicate_fact.py` and its tests.

</domain>

<decisions>
## Implementation Decisions

### Filter Logic

- **D-01:** Single union filter -- not two separate filters. Build
  `exclusion = _STRUCTURAL_WORDS | signoff_words`, then skip any n-gram
  where `all(w in exclusion for w in ng.split())`. Two separate filters
  fail on cross-category n-grams like "signed-off-by minxi" (one word in
  each set but neither set contains both).

### Structural Words Constant

- **D-02:** Module-level `frozenset` constant `_STRUCTURAL_WORDS` in
  `f2_duplicate_fact.py`, alongside the existing `_FINDING_CAP`. No new
  file, no new import. Creating a shared `_constants.py` fails the >=3
  consumers rule since only F2 uses it currently.
- **D-03:** Initial set (empirically derived from antishirk-m1-plan.md
  smoke test):
  `step, run, expected, pass, files, create, modify, append, commit, test,
  write, add, signed-off-by`
  -- 13 tokens. "signed-off-by" is included because it is a git commit
  metadata label, never a substantive plan fact.

### Signed-off-by Word Extraction

- **D-04:** Scan raw plan text (not `parsed.sections` body). Regex:
  `r'^\s*signed-off-by\s*:\s*(.*)'` on each line. Strip `<email@...>` with
  `re.sub(r'<[^>]+>', '', ...)`. Split and lowercase the remaining name
  tokens into `signoff_words`. Raw-text scan catches Signed-off-by lines
  inside XML/code blocks that the section parser may not include in body.

### Phase Structure

- **D-05:** 3 plans, same wave pattern as Phase 8:
  - Plan 10-01 (Wave 1): worktree + fixtures + RED test stubs
  - Plan 10-02 (Wave 2): implementation + bug-inject bite tests
  - Plan 10-03 (Wave 3): forge review (separate sub-session) + merge + cleanup

### Anti-Gutting

- **D-06:** The existing `tests/fixtures/f2_fail.md` TP fixture must
  continue to fire (confirmed: 4 LOW findings with the new code in the
  smoke test). Plan 10-02 must include a bug-inject cycle (same pattern
  as GATE-04T in Phase 8) proving the guard is load-bearing.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Implementation Target
- `src/plan_forge/checks/mechanical/f2_duplicate_fact.py` -- edit target;
  add `_STRUCTURAL_WORDS` constant and union filter inside `check()`
- `src/plan_forge/checks/mechanical/f2_duplicate_fact.py` lines 61-69 --
  existing `heading_words` guard that the new code sits adjacent to

### Test Fixtures
- `tests/fixtures/f2_fail.md` -- existing TP fixture; must still fire post-fix
- `tests/fixtures/f2_heading_fp.md` -- Phase 8 FP fixture; heading-word guard

### Phase 8 Precedent (same gate, same file)
- `.planning/phases/08-source-code-precision-fixes/08-03-PLAN.md` --
  F2 heading-words fix plan; new plan follows same task structure
- `.planning/phases/08-source-code-precision-fixes/08-CONTEXT.md` --
  Phase 8 F2 decisions for reference

### Smoke Test Evidence
- Empirical test on:
  `/home/houminxi/code/forge/.worktrees/p5-antishirk-spec/docs/plans/2026-05-28-antishirk-m1-plan.md`
  Baseline: 20 LOW. Post-fix: 0 LOW. TP f2_fail.md: 4 LOW (unchanged).

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Patterns
- `heading_words` build pattern (lines 61-63): iterate `parsed.sections`,
  call `.update(heading.lower().split())`. The new `signoff_words` loop
  mirrors this structure but scans raw text lines instead.
- Bug-inject pattern from Phase 8 (GATE-04T): comment out guard, confirm
  FP fixture fires, restore, confirm silence. Reuse exactly.

### Integration Points
- New code inserts after line 63 (end of `heading_words` build).
- The existing `if set(ng.split()) <= heading_words: continue` at line 67
  is REPLACED by the union filter (not a second separate guard).
- `_extract_ngrams()` is unchanged.

### Existing Test Structure
- `tests/unit/test_f2_duplicate_fact.py` -- extend with new tests for
  structural-word suppression and signed-off-by suppression.

</code_context>

<specifics>
## Specific Ideas

- Two new fixtures needed:
  1. `tests/fixtures/f2_structural_fp.md` -- plan with step/run/expected/pass
     phrases repeated across task sections; must produce 0 F2 LOW post-fix.
  2. `tests/fixtures/f2_signoff_fp.md` -- plan with repeated Signed-off-by
     examples across sections; must produce 0 F2 LOW post-fix.
- Real-world verification target:
  `/home/houminxi/code/forge/.worktrees/p5-antishirk-spec/docs/plans/2026-05-28-antishirk-m1-plan.md`
  Must verify 0 F2 LOW via `api.check(t, llm_clients=[])` post-merge.

</specifics>

<deferred>
## Deferred Ideas

- Configurable stopwords via user config file -- 1 consumer today, deferred.
- Frequency-based suppression -- plan-size-dependent threshold, not
  generalizable, deferred.
- Sub-heading extension of heading_words -- ineffective when "Step N:" is
  body text rather than markdown headings, deferred.

</deferred>

---

*Phase: 10-F2 Structural False-Positive Reduction*
*Context gathered: 2026-05-29*
