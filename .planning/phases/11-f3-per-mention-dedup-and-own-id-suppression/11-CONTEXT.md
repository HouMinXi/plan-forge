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

- **D-03:** Extend `_own_id_set()` to scan YAML frontmatter (`---...---` block)
  for `phase:` and `plan:` fields before falling back to the first ATX heading.
  Extract the leading digit(s) from `phase:` (e.g., "08-source-code-precision-fixes"
  -> "08") and zero-pad `plan:` to 2 digits. Construct own ID as "{phase}-{plan}"
  (e.g., "08-02").
- **D-04:** If frontmatter lacks `phase:` or `plan:` fields, fall back to the
  existing first-ATX-heading scan. No change in behavior for non-GSD plans.
- **D-05:** `_own_id_set` returns `set[str]` of lowercase own-id strings, same
  contract as today. Adding the frontmatter path does not change the return type
  or downstream usage (`verified.update(_own_id_set(parsed))`).

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
- G2 heading-flex (listed in CLAUDE.md Backlog) -- deferred to a later phase.
- Configurable own-ID extraction -- 1 consumer today, deferred.

</deferred>

---

*Phase: 11-F3 Per-Mention Dedup and Own-ID Suppression*
*Context gathered: 2026-05-29*
