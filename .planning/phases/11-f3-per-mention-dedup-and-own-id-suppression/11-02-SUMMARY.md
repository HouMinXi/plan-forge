---
phase: 11-f3-per-mention-dedup-and-own-id-suppression
plan: "02"
subsystem: checks/mechanical
tags: [f3, dedup, own-id, false-positive-reduction]
requirements: [F3-01, F3-02]

dependency_graph:
  requires: [11-01]
  provides: [f3-dedup-fix-committed]
  affects: [src/plan_forge/checks/mechanical/f3_cross_plan_invariant.py]

tech_stack:
  added: []
  patterns:
    - "seen-set keyed on normalized claim text (claim.lower()) to collapse per-line duplicates"
    - "frontmatter scanning with BOM tolerance for own-ID extraction in GSD-format plans"
    - "union of frontmatter and heading sources in _own_id_set"

key_files:
  created: []
  modified:
    - src/plan_forge/checks/mechanical/f3_cross_plan_invariant.py

decisions:
  - "Dedup key is claim.lower() (not (claim, lineno)) -- one finding per unique cross-plan reference"
  - "frontmatter scan runs before heading scan; results are unioned, not exclusive"
  - "Phase 10+ own-ID suppression deferred: _SUBPLAN_RE only matches 01-09 phase numbers in body text"

metrics:
  duration: "~15 minutes"
  completed: "2026-05-30"
  tasks_completed: 3
  tasks_total: 3
  files_changed: 1
---

# Phase 11 Plan 02: F3 dedup key fix and frontmatter own-ID extraction

One-liner: change F3 dedup key from (claim, lineno) to claim.lower(), and add YAML frontmatter scanning to _own_id_set so GSD-format plans no longer self-flag.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Apply dedup key change and frontmatter own-ID extension | b548cd4 | f3_cross_plan_invariant.py |
| 2 | Bug-inject cycle GATE-11T (human checkpoint) | confirmed by orchestrator | -- |
| 3 | Full suite green and commit F3 fix | b548cd4 | f3_cross_plan_invariant.py |

## What Was Built

Two false-positive classes eliminated in `f3_cross_plan_invariant.py`:

**F3-01 (dedup):** The `check()` function now uses `claim.lower()` as the key in the `seen` set instead of the previous `(claim, lineno)` tuple. The old key made every line occurrence of the same reference unique, so "Phase 8" on six lines produced six identical HIGH findings. The new key collapses all occurrences to one finding (at the first line number seen).

**F3-02 (own-ID):** `_own_id_set()` now scans YAML frontmatter for `phase:` and `plan:` fields before falling back to the ATX heading scan. Both sources contribute to the own-ID set via union. GSD plans carry structured frontmatter instead of headings; the old heading-only approach returned an empty set for every GSD plan, causing the plan's own sub-plan ID to fire as an unverified cross-plan reference. A `_BOM` constant (U+FEFF) was added to handle files with BOM prefixes before the `---` delimiter check.

## Test Results

Full suite: **768 passed, 1 pre-existing failure (test_version_is_alpha2 -- version string mismatch, unrelated), 5 skipped**.

All 10 F3 tests pass:

- test_f3_dedup_fires_once: PASSED (exactly 1 finding for "Phase 8" x6)
- test_f3_own_id_suppressed_via_frontmatter: PASSED (08-02 from frontmatter exempted)
- test_f3_self_ref_silent: PASSED (heading-based own-ID preserved)
- test_f3_cross_ref_still_fires: PASSED (02-03 genuine cross-ref still fires)
- test_f3_fail_fixture: PASSED (TP still fires)
- test_f3_pass_fixture: PASSED
- test_f3_severity: PASSED
- test_f3_date_fragment_silent: PASSED
- test_f3_edge_case_insensitive_exemption: PASSED
- test_f3_edge_audit_notes_exemption: PASSED

## Bug-Inject Cycle (GATE-11T)

Confirmed by orchestrator before this continuation agent was spawned:

- Dedup key reverted to `(claim, lineno)`: `f3_dedup_fp.md` fixture produced **6 findings** for Phase 8.
- Fix restored (`claim.lower()`): fixture produced **1 finding**.
- TP fixture `f3_fail.md`: unaffected, continued to fire after restore.

The guard is load-bearing. Over-suppression is not occurring.

## Step 0 Results

All checks clean on the diff:

- 0a syntax: `python3 -m py_compile` -- OK
- 0b ruff: `All checks passed!`
- 0c non-ASCII: OK (no non-ASCII characters in new lines)
- 0d AI smell: OK (no task IDs, no model names, no plan-ref labels)

## Deviations from Plan

**1. Commit staged only f3_cross_plan_invariant.py**

Plan Task 3 instructed staging four files including test fixtures and the test module. Those three files (`tests/fixtures/f3_dedup_fp.md`, `tests/fixtures/f3_own_id_fp.md`, `tests/unit/test_f3_cross_plan_invariant.py`) were already committed in Plan 11-01 (commit 62e13f2). Re-staging already-committed unmodified files is a no-op in git; only the one file with working-tree changes was staged and committed. This is correct behavior.

**2. Commit subject wording differs slightly from plan template**

Plan suggested "checks/f3: deduplicate per-claim findings and extract own-ID from frontmatter". Actual subject: "checks/f3: deduplicate findings per claim and extract own-ID from frontmatter". Semantically equivalent; human-voice phrasing retained.

## Known Stubs

None. All test fixtures are wired to real check() behavior.

## Threat Flags

None. No new network endpoints, auth paths, file access patterns, or schema changes introduced.

## Self-Check: PASSED

- [x] `src/plan_forge/checks/mechanical/f3_cross_plan_invariant.py` -- confirmed modified
- [x] commit b548cd4 -- confirmed in git log
- [x] SUMMARY.md written before final docs commit
