---
phase: 08-source-code-precision-fixes
plan: 01
subsystem: testing
tags: [pytest, fixtures, tdd, red-green, g8-source-diversity, f2-duplicate-fact]

requires: []
provides:
  - "Linked worktree fix/precision-v011 for Phase 8 code changes"
  - "3 new fixture .md files for G8 and F2 precision fix tests"
  - "4 new test functions establishing the RED state for GATE-01, GATE-03, GATE-04, GATE-05"
affects:
  - "08-02-source-code-g8-fix"
  - "08-03-source-code-f2-fix"

tech-stack:
  added: []
  patterns:
    - "TDD RED gate: new tests fail against unmodified source, proving fixtures are load-bearing"
    - "Fixture separation: empty-body vs non-empty-body cases use distinct files to test BLOCKER vs HIGH branches"

key-files:
  created:
    - "tests/fixtures/g8_prose_cited_fp.md"
    - "tests/fixtures/g8_empty_body_blocker.md"
    - "tests/fixtures/f2_heading_fp.md"
  modified:
    - "tests/unit/test_g8_source_diversity.py"
    - "tests/unit/test_f2_duplicate_fact.py"

key-decisions:
  - "All file edits committed to fix/precision-v011 branch inside .worktrees/fix-precision/"
  - "g8_prose_cited_fp.md uses inline prose so parsed.citations is empty while body.strip() is non-empty"
  - "g8_empty_body_blocker.md places External Voices section with no content between two headings so body.strip() is empty"
  - "f2_heading_fp.md uses 'Implementation Tasks' heading so heading_words contains both 'implementation' and 'tasks'"

patterns-established:
  - "Fixture design: verify parser behavior before writing tests to confirm fixture triggers the expected code path"
  - "RED confirmation: run new test in isolation before committing to verify FAIL on unmodified source"

requirements-completed:
  - GATE-01
  - GATE-02
  - GATE-03
  - GATE-04
  - GATE-05

duration: 25min
completed: 2026-05-28
---

# Phase 08 Plan 01: Wave 0 Test Scaffolding Summary

**Three fixture files and four test stubs establishing the RED state for G8.A.no_citation severity split and F2 heading-word suppression, all committed to fix/precision-v011 worktree branch**

## Performance

- **Duration:** ~25 min
- **Started:** 2026-05-28T02:30:00Z
- **Completed:** 2026-05-28T02:57:09Z
- **Tasks:** 3
- **Files modified:** 5 (3 fixtures created, 2 test files modified)

## Accomplishments

- Created worktree `.worktrees/fix-precision/` on branch `fix/precision-v011`; baseline confirmed at 17 tests passing
- Added two G8 fixtures (inline-prose citation FP, empty-body BLOCKER) plus two test stubs; RED confirmed (`test_prose_cited_emits_high` FAILS: BLOCKER != HIGH)
- Added F2 heading-fp fixture and two test stubs; RED confirmed (`test_f2_heading_fp_suppressed` FAILS: heading n-gram not suppressed against unmodified source)

## Task Commits

Each task was committed atomically to the `fix/precision-v011` branch:

1. **Task 1: Create worktree and verify baseline** - worktree created, 17 tests confirmed (no staged files; worktree creation leaves no tracked changes)
2. **Task 2: G8 fixtures and failing test stubs (RED)** - `194c556` (test)
3. **Task 3: F2 fixture and failing test stubs (RED)** - `94b4d56` (test)

## Files Created/Modified

- `tests/fixtures/g8_prose_cited_fp.md` - Inline prose citation fixture; body non-empty, parsed.citations empty; exercises G8.A.no_citation HIGH branch
- `tests/fixtures/g8_empty_body_blocker.md` - Empty External Voices body between two headings; exercises G8.A.no_citation BLOCKER branch
- `tests/fixtures/f2_heading_fp.md` - "implementation tasks" repeated in 4+ section bodies with "Implementation Tasks" heading; exercises F2 heading-word suppression
- `tests/unit/test_g8_source_diversity.py` - Added `test_prose_cited_emits_high` (RED) and `test_empty_body_emits_blocker` (passes on unmodified source)
- `tests/unit/test_f2_duplicate_fact.py` - Added `test_f2_heading_fp_suppressed` (RED) and `test_f2_genuine_phrase_not_suppressed` (passes on unmodified source)

## Decisions Made

- Task 1 required no commit: worktree creation does not modify any tracked files in the agent branch
- `g8_empty_body_blocker.md` uses two consecutive headings with no content between them; parser sets section.body to empty string
- `test_empty_body_emits_blocker` passes against unmodified source (current code always emits BLOCKER on empty citations); this is acceptable per plan
- `test_f2_genuine_phrase_not_suppressed` passes against unmodified source (the TP path is not broken by adding tests)

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Worktree `fix/precision-v011` is active and ready for Plan 02 (G8 source fix)
- RED state established: `test_prose_cited_emits_high` and `test_f2_heading_fp_suppressed` fail against unmodified source
- All 17 pre-existing G8 + F2 tests continue to pass (regression guard active)
- Plan 02 must turn `test_prose_cited_emits_high` GREEN by adding the body.strip() branch in g8_source_diversity.py
- Plan 03 must turn `test_f2_heading_fp_suppressed` GREEN by adding the heading_words guard in f2_duplicate_fact.py

---
*Phase: 08-source-code-precision-fixes*
*Completed: 2026-05-28*

## Self-Check: PASSED

| Item | Status |
|------|--------|
| `tests/fixtures/g8_prose_cited_fp.md` | FOUND |
| `tests/fixtures/g8_empty_body_blocker.md` | FOUND |
| `tests/fixtures/f2_heading_fp.md` | FOUND |
| Commit `194c556` (Task 2) | FOUND |
| Commit `94b4d56` (Task 3) | FOUND |
| `08-01-SUMMARY.md` | FOUND |
