# Phase 12: F3 Phase 10+ Subplan ID and Phase-Text Self-Reference - Context

**Gathered:** 2026-05-31
**Status:** Ready for planning

<domain>
## Phase Boundary

Two targeted changes to `f3_cross_plan_invariant.py` that eliminate two remaining
F3 false-positive (and false-negative) classes deferred from Phase 11:

1. **A. `_SUBPLAN_RE` extension**: The regex currently only matches `01-XX`
   through `09-XX`. Extending to cover Phase 10-99 fixes a false negative
   (cross-plan references to Phase 10+ plans were silently missed) and enables
   own-ID suppression for Phase 10+ plans that use heading-based ID format.

2. **B. Phase-text self-reference suppression**: A plan whose frontmatter
   declares `phase: 8` may mention "Phase 8" or "Phase-8" in its body
   (explaining its own phase context). These are self-references, not
   cross-plan references, and must not trigger F3. `_own_id_set()` needs to
   derive phase-text tokens from the frontmatter `phase:` field and add them
   to the verified set.

Zero changes outside `f3_cross_plan_invariant.py` and its unit tests + fixtures.

</domain>

<decisions>
## Implementation Decisions

### A. _SUBPLAN_RE Extension

- **D-01:** Change `_SUBPLAN_RE` from `r'(?<!\d-)\b0[1-9]-\d{2}\b'` to
  `r'(?<!\d-)\b(?:0[1-9]|[1-9]\d)-\d{2}\b'`. This covers Phase IDs `01-XX`
  through `99-XX`. The existing `(?<!\d-)` lookbehind protects against ISO
  date fragments (e.g. `10-02` in `2026-10-02`) for both one- and two-digit
  phase prefixes identically to the current Phase 1-9 protection.
- **D-02:** The same `_SUBPLAN_RE` constant is used in both `_extract_all_claims()`
  (body scan) and the heading scan inside `_own_id_set()`. A single constant
  change covers both sites automatically. No other references to `_SUBPLAN_RE`
  in the file.
- **D-03:** Effect of A on existing behavior: a plan that cross-references
  "10-02" without audit notes now correctly fires one F3 HIGH (was silently
  missed). This is a false-negative correction, not a new finding type.

### B. Phase-Text Token Suppression

- **D-04:** In `_own_id_set()`, when `phase_num` is successfully extracted from
  frontmatter, add all four phase-text token variants to `own`:
  - `f"phase {int(phase_num)}"` -- "phase 8" (unpadded, space)
  - `f"phase-{int(phase_num)}"` -- "phase-8" (unpadded, hyphen)
  - `f"phase {phase_num}"` -- "phase 08" (padded, space)
  - `f"phase-{phase_num}"` -- "phase-08" (padded, hyphen)
  This covers all four values that `_PHASE_RE.finditer(...).group(0).lower()`
  can return for the various ways "Phase 8" can appear in a document.
- **D-05:** Phase-text token construction requires only `phase_num`, NOT
  `plan_num`. Decouple from the `if phase_num and plan_num:` gate that guards
  subplan ID construction. A plan with `phase: 8` but no `plan:` field still
  gets phase-text suppression; the subplan ID `"08-XX"` is simply not added
  (unchanged behavior).
- **D-06:** Phase-text tokens are derived from frontmatter ONLY (not from
  headings). Heading scan continues to extract `_SUBPLAN_RE` matches as
  before. Reason: heading text is less structured and harder to interpret
  safely for phase-text extraction.

### Phase Structure

- **D-07:** 3 plans, same wave pattern as Phases 10 and 11:
  - Plan 12-01 (Wave 1): worktree setup + fixtures + RED test stubs
  - Plan 12-02 (Wave 2): `_SUBPLAN_RE` extension + phase-text tokens + bite test
  - Plan 12-03 (Wave 3): forge review (separate sub-session) + merge + cleanup

### Scope Boundary

- **D-08:** P1.orphan_identifier FPs, G2 heading-flex, and `_TASK_RE` self-
  reference suppression are NOT in scope. Phase 12 touches F3 only.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Implementation Target
- `src/plan_forge/checks/mechanical/f3_cross_plan_invariant.py` -- edit target;
  two changes: `_SUBPLAN_RE` constant (line 24) and `_own_id_set()` (lines 55-101)
- Line 24: `_SUBPLAN_RE` constant definition -- single change covers D-01/D-02
- Lines 55-101 (`_own_id_set`): insert D-04/D-05 phase-text block after frontmatter loop
- Lines 104-111 (`_extract_all_claims`): uses `_SUBPLAN_RE`; no direct edit needed
- Lines 93-99 (heading scan in `_own_id_set`): uses `_SUBPLAN_RE`; no direct edit needed

### Test and Fixture Targets
- `tests/unit/test_f3_cross_plan_invariant.py` -- existing test structure; add
  new test functions for Phase 10 cross-ref detection and phase-text suppression
- `tests/fixtures/f3_fail.md` -- existing TP fixture (must still fire post-fix)
- `tests/fixtures/f3_dedup_fp.md` -- Phase 11 dedup fixture (must still pass)
- `tests/fixtures/f3_own_id_fp.md` -- Phase 11 own-ID fixture (must still pass)

### Prior Phase Context
- `.planning/phases/11-f3-per-mention-dedup-and-own-id-suppression/11-CONTEXT.md`
  -- D-08 (deferred `_SUBPLAN_RE` extension) and deferred `_PHASE_RE`
  self-reference are the two items this phase resolves

</canonical_refs>

<code_context>
## Existing Code Insights

### Regex Architecture
- Three claim-detection patterns: `_PHASE_RE` (phase-N text), `_SUBPLAN_RE`
  (NN-MM subplan IDs), `_TASK_RE` (T-numbers). Only `_SUBPLAN_RE` is changed.
- `_PHASE_RE = re.compile(r'\bphase[-\s]\d+\b', re.IGNORECASE)`: matches
  both space ("Phase 8") and hyphen ("Phase-8") forms; claim `.lower()` produces
  "phase 8" or "phase-8". D-04 adds exactly these four forms to `own`.
- Negative lookbehind `(?<!\d-)` is fixed-length (2 chars) as required by
  Python's `re` engine. The extension `(?:0[1-9]|[1-9]\d)` does not change
  the lookbehind length or semantics.

### `_own_id_set()` Contract
- Returns `set[str]` of lowercase own-id strings. No return type change for D-04/D-05.
- Phase-text tokens are lowercase strings and feed into the same `verified`
  set in `check()` that compares against `claim.lower()`. Type contract unchanged.
- `_own_id_set()` is called once per `check()` call at line 134. No caching.

### `check()` Integration (no change needed)
- `verified.update(_own_id_set(parsed))` at line 134 already accepts any `set[str]`.
  Phase-text tokens returned by the extended `_own_id_set()` automatically flow into
  `verified` with zero changes to `check()`.
- Dedup via `seen: set[str]` (Phase 11 D-01) already in place.

### Existing Fixture Compatibility
- `f3_dedup_fp.md` and `f3_own_id_fp.md` use Phase 8-era IDs (`08-02`).
  Extending `_SUBPLAN_RE` to Phase 10+ does not change their matching behavior;
  both fixtures remain valid regression guards.

</code_context>

<specifics>
## Specific Ideas

### Fixture Design (three new fixtures)

1. **`tests/fixtures/f3_phase10_cross_ref.md`** (Change A -- RED state):
   A plan WITHOUT phase:10 frontmatter that references "10-02" in its body
   without any audit notes. Before fix: 0 findings (regex miss = false
   negative). After fix: 1 F3 HIGH finding. Test stub asserts
   `len(findings) == 1 and "10-02" in findings[0].message`.

2. **`tests/fixtures/f3_phase10_own_id_fp.md`** (Change A -- own-ID regression):
   A plan WITH `phase: 10` and `plan: 2` in frontmatter that references
   "10-02" in its body. After fix: 0 F3 findings (own-ID suppression via
   extended regex + frontmatter verified set). Regression guard confirming
   suppression works end-to-end for Phase 10+.

3. **`tests/fixtures/f3_phase_text_fp.md`** (Change B -- RED state):
   A plan with `phase: 8` in frontmatter (no `plan:` field required),
   body contains "Phase 8" and "Phase-8" without audit notes. Before fix:
   2 F3 HIGH findings. After fix: 0 findings. Test stub asserts
   `len(findings) == 0`.

Anti-gutting (can reuse or extend `f3_fail.md`):
   A plan with `phase: 8` in frontmatter, body references "Phase 9" without
   an audit note -- must still fire 1 F3 HIGH after fix. Confirms suppression
   is own-phase-only.

### Reference Implementation for D-04/D-05

Exact insertion inside `_own_id_set()`, between frontmatter loop and heading scan:

```python
    if phase_num:
        phase_int = int(phase_num)
        own.add(f"phase {phase_int}")    # "phase 8"
        own.add(f"phase-{phase_int}")   # "phase-8"
        own.add(f"phase {phase_num}")   # "phase 08"
        own.add(f"phase-{phase_num}")   # "phase-08"

    if phase_num and plan_num:
        own.add(f"{phase_num}-{plan_num}")
```

Phase-text block MUST precede the `if phase_num and plan_num:` guard so it
runs even when `plan_num` is absent.

</specifics>

<deferred>
## Deferred Ideas

- `_PHASE_RE` self-reference from heading-only plans (no frontmatter): a plan
  whose phase number comes only from its filename or heading still gets
  flagged for "Phase N" body text. Requires filename parsing or heading regex
  as an additional own-ID source. Out of Phase 12 scope.
- `_TASK_RE` self-reference suppression (T01, T02 references) -- separate class.
- P1.orphan_identifier FPs -- separate gate, separate phase.
- G2 heading-flex -- listed in CLAUDE.md Backlog.

</deferred>

---

*Phase: 12-F3 Phase 10+ Subplan ID and Phase-Text Self-Reference*
*Context gathered: 2026-05-31*
