---
plan: 10-02
phase: 10-f2-structural-false-positive-reduction
status: complete
completed: "2026-05-29"
---

# Plan 10-02 Summary: F2 Union Exclusion Filter

## What Was Built

Applied the three-way union exclusion filter to `f2_duplicate_fact.check()`:

  exclusion = _STRUCTURAL_WORDS | signoff_words | heading_words
  if set(ng.split()) <= exclusion:
      continue

Added two new constructs to `f2_duplicate_fact.py`:

1. _STRUCTURAL_WORDS -- module-level frozenset of 13 structural vocabulary tokens
   (step, run, expected, pass, files, create, modify, append, commit, test, write,
   add, signed-off-by) that repeat by design in task-formatted plans.

2. _SIGNOFF_RE + signoff_words -- per-document extraction of author-name tokens
   from Signed-off-by lines in parsed.raw_text.

The existing heading_words guard from Phase 8 is preserved as the third arm
of the union set.

## Test Results

- 8/8 F2 unit tests GREEN after fix (6 pre-existing + 2 new)
- Full suite: 766 passed, 1 failed (test_version_is_alpha2 -- pre-existing version
  mismatch, unrelated), 5 skipped
- Real-world plan (antishirk-m1-plan.md): F2 LOW 20 -> 0 after fix

## GATE-10T Bug-Inject Verification

Orchestrator performed the bug-inject cycle:
- Reduced exclusion to heading_words only (no structural or signoff words)
- test_f2_structural_fp_suppressed: FAILED (findings != []) -- guard confirmed load-bearing
- Restored three-way union
- test_f2_structural_fp_suppressed: PASSED
- test_f2_signoff_fp_suppressed: PASSED
- test_f2_fail_fixture: PASSED (genuine duplicate-fact detection unaffected)

## Commit

b1f3c1a on branch fix/f2-structural-fp-v012

## Self-Check: PASSED
