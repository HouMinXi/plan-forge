# Phase 11: F3 Per-Mention Dedup and Own-ID Suppression - Context

**Gathered:** 2026-05-29
**Status:** Ready for planning

<domain>
## Phase Boundary

Two targeted changes to `f3_cross_plan_invariant.py` that eliminate two F3
false-positive classes in GSD-format PLAN.md files. Zero changes outside that
file and its tests.

</domain>

<decisions>
## Implementation Decisions

### F3-01: Per-Claim Dedup

- **D-01:** Change the `seen` set key from `(claim, lineno)` to `claim.lower()`.
  Current behavior: "Phase 8" on line 15 AND line 42 = 2 separate HIGH findings.
  Fixed behavior: first occurrence fires, subsequent occurrences are skipped.
- **D-02:** `location` for the deduplicated finding = `line:{first_lineno}` (the
  line number of the first occurrence). Consistent with how other gates report
  locations.

### F3-02: Own-ID Extraction from YAML Frontmatter

- **D-03:** Extend `_own_id_set()` to scan the YAML frontmatter block at the top
  of raw_text. Frontmatter detection: opening `---` must be on line 1 (strip
  leading BOM/blank before checking; accept line 2 only if line 1 is empty).
  The closing `---` must appear before the first `#` heading line -- any `---`
  after a heading is treated as a horizontal rule, not a frontmatter delimiter.
  If opening `---` not found on line 1, skip frontmatter scan entirely.
  Extract leading digits from `phase:` field AND digits from `plan:` field;
  BOTH must be zero-padded with `.zfill(2)` so the constructed ID matches
  `_SUBPLAN_RE` format (e.g., `phase: 8, plan: 2` -> `"08-02"`, not `"8-02"`).
  If EITHER field is absent, skip own-id construction entirely -- partial IDs
  like `"-02"` or `"08-"` are invalid and must not enter `own`.
- **D-04:** Frontmatter scan and heading scan are ADDITIVE (union), not exclusive
  fallback. Even when frontmatter yields an own ID, continue to scan the first
  ATX heading and add any IDs found there. This prevents silent failure when
  frontmatter and heading disagree. If frontmatter has no `phase:` or `plan:`
  fields, it contributes nothing and only the heading result is returned.
- **D-05:** `_own_id_set` returns `set[str]` of lowercase own-id strings, same
  contract as today. No return type or downstream usage change.
- **D-08 (known limitation):** `_SUBPLAN_RE = r'(?<!\d-)\b0[1-9]-\d{2}\b'`
  requires the first digit to be `0`, so Phase 10+ own IDs like `"10-02"` are
  never matched as claims in the document body. Frontmatter extraction correctly
  adds `"10-02"` to `verified`, but since `_SUBPLAN_RE` never extracts `"10-02"`
  as a claim, the suppression has no practical effect for Phase >= 10. Record in
  code comment; extending `_SUBPLAN_RE` is out of Phase 11 scope.

### Phase Structure

- **D-06:** 3 plans, same wave pattern as Phase 10:
  - Plan 11-01 (Wave 1): worktree + fixtures + RED test stubs
  - Plan 11-02 (Wave 2): dedup fix + frontmatter own-ID extension + bite test
  - Plan 11-03 (Wave 3): forge review (separate sub-session) + merge + cleanup

### Scope Boundary

- **D-07:** P1.orphan_identifier false positives are NOT in scope for Phase 11.
  That is a separate gate requiring separate analysis. Phase 11 touches F3 only.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Implementation Target
- `src/plan_forge/checks/mechanical/f3_cross_plan_invariant.py` -- edit target;
  two changes: `seen` key and `_own_id_set` frontmatter extension
- Lines 46-66 (`_own_id_set`): extend with frontmatter scan before heading fallback
- Lines 98-127 (`check()`): change `seen: set[tuple[str, int]]` to `seen: set[str]`
  and `key = (claim, lineno)` to `key = claim.lower()`

### Test Fixtures
- `tests/fixtures/f3_fail.md` -- existing TP fixture (if present; verify)
- `tests/unit/test_f3_cross_plan_invariant.py` -- existing test structure

### Phase 10 Precedent (same gate family, same file pattern)
- `.planning/phases/10-f2-structural-false-positive-reduction/10-CONTEXT.md`
- `.planning/phases/10-f2-structural-false-positive-reduction/10-02-PLAN.md`

### Evidence
- Empirical: `check_mechanical` on `10-02-PLAN.md` -> 6 HIGH all F3 for "Phase 8"
- Root cause confirmed: `seen` key is `(claim, lineno)` not `claim.lower()`
- Own-ID: `_own_id_set` returns empty for GSD PLAN.md (frontmatter before first heading)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Patterns
- Phase 10's three-way union pattern (two independent guards in one step) informed
  the design here: similarly, frontmatter scan + heading fallback are sequential
  checks in `_own_id_set`, not two separate functions.
- Bite-test pattern (GATE-10T / GATE-04T): same approach for Phase 11 bug-inject.

### Integration Points
- `_own_id_set(parsed)` is called in `check()` at line 100; return value feeds into
  `verified` set. No signature change needed.

### GSD PLAN.md ATX Headings (current known behavior, not a format guarantee)
- Observed: 10-01, 10-02, 09-02 PLAN.md files start with `<objective>` XML, no
  `#` headings. Heading scan currently returns empty set for these GSD plans.
  Frontmatter is the primary effective own-ID path for current GSD plans.
  D-04's union design means future plans with ATX headings work correctly too.

### Existing Test Compatibility (D-01 regression risk: NONE -- empirically confirmed)
- Unit tests (`test_f3_cross_plan_invariant.py`): assert existence/severity only
  (`check_id in ids`), NOT count. D-01 safe.
- Integration tests (`test_api_mechanical_e2e.py`): assert `len(result.findings)`
  and `check_id_counts` snapshots. HOWEVER empirically verified by cross-AI review:
  the two integration fixtures (`pass_well_formed.md`, `fail_missing_premortem.md`)
  each contain only 1 unique F3 claim, so D-01 does not change their F3 count.
  Executor must confirm this still holds after adding new Phase 11 F3 fixtures.
- `seen` set is local to `check()`. Key change is self-contained.

### ParsedPlan.raw_text
- Confirmed available (used in Phase 10 for signoff_words extraction).
- YAML frontmatter appears at the start of raw_text before the closing `---`.

</code_context>

<specifics>
## Specific Ideas

- Two new fixtures:
  1. `tests/fixtures/f3_dedup_fp.md` -- plan referencing "Phase 8" six times;
     must produce exactly 1 F3 finding post-fix (not 6).
  2. `tests/fixtures/f3_own_id_fp.md` -- GSD PLAN.md with `phase: "08"` and
     `plan: "02"` in frontmatter, references "08-02" in body; must produce
     0 F3 findings for "08-02" post-fix.
- Real-world verification: run `check_mechanical` on
  `.planning/phases/10-f2-structural-false-positive-reduction/10-02-PLAN.md`
  before and after fix; HIGH count should drop from 6 to 1 (one for "Phase 8"
  on first occurrence, none for repeated mentions).

</specifics>

<deferred>
## Deferred Ideas

- P1.orphan_identifier false positives -- separate gate, separate phase.
- `_PHASE_RE` self-reference (e.g., "Phase 8" in a Phase 8 plan) is not suppressed
  by subplan-format own-IDs ("08-02"). This is a pre-existing gap; fixing it would
  require `_own_id_set` to also construct `"phase 8"` / `"phase-8"` tokens, which
  is out of Phase 11 scope.
- G2 heading-flex (listed in CLAUDE.md Backlog) -- deferred to a later phase.
- Configurable own-ID extraction -- 1 consumer today, deferred.

</deferred>

---

*Phase: 11-F3 Per-Mention Dedup and Own-ID Suppression*
*Context gathered: 2026-05-29*
