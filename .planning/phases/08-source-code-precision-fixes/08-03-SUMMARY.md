---
phase: 08-source-code-precision-fixes
plan: "03"
subsystem: checks/mechanical/f2_duplicate_fact
tags: [f2, false-positive, heading-suppression, bug-inject]
dependency_graph:
  requires: ["08-01", "08-02"]
  provides: ["F2-heading-guard", "GATE-04", "GATE-04T", "GATE-05"]
  affects: ["src/plan_forge/checks/mechanical/f2_duplicate_fact.py"]
tech_stack:
  added: []
  patterns: ["subset guard on flagged n-grams before findings loop"]
key_files:
  created: []
  modified:
    - src/plan_forge/checks/mechanical/f2_duplicate_fact.py
decisions:
  - "Word-level subset test (set <= heading_words) tolerates inflection and ordering differences without regex or stemming"
  - "Guard placed between sort and findings loop so _FINDING_CAP is applied before suppression"
  - "heading_words built from dict keys only (parsed.sections), not section body text"
metrics:
  duration: "~15 min"
  completed: "2026-05-28"
  tasks_completed: 3
  tasks_total: 3
  files_modified: 1
---

# Phase 08 Plan 03: F2 Heading-FP Suppression Summary

**One-liner:** Suppress F2 n-grams whose words are all present in section-heading vocabulary, eliminating structural-term false positives without affecting genuine duplicate-fact detection.

## What Was Built

`f2_duplicate_fact.py` now builds a `heading_words` set from all words in
`parsed.sections` keys (lowercased, split on whitespace) before the findings
loop. Any flagged n-gram whose word set is a subset of `heading_words` is
skipped via a `continue` guard.

This silences structural terms like "implementation tasks" and "success
criteria" that repeat across sections by design. Genuine content-level
repetitions (e.g., "DatabaseConnection Pool" against headings like
"Background", "Design", "Testing") are unaffected because those words do not
appear in any heading.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Apply F2 heading-words guard and verify GREEN | (part of 3c9618b) | f2_duplicate_fact.py |
| 2 | Bug-inject cycle GATE-04T | orchestrator-verified | -- |
| 3 | Full suite green and commit F2 fix | 3c9618b | f2_duplicate_fact.py |

## Verification Results

Full suite after fix:

```
765 passed, 5 skipped in 2.76s
```

F2-specific tests (6/6):

- test_f2_heading_fp_suppressed -- PASSED (heading-derived n-gram silenced)
- test_f2_genuine_phrase_not_suppressed -- PASSED (genuine phrase fires)
- test_f2_pass_fixture -- PASSED
- test_f2_fail_fixture -- PASSED
- test_f2_severity -- PASSED
- test_f2_edge_exactly_two_sections -- PASSED

## Bug-Inject Cycle (GATE-04T)

Performed by orchestrator before resuming Task 3:

- Guard removed (commented out): test_f2_heading_fp_suppressed FAILED (findings != []) -- confirms guard is load-bearing
- Guard restored: test_f2_heading_fp_suppressed PASSED (silence restored) -- confirms suppression is correct
- TP test (f2_fail.md): test_f2_genuine_phrase_not_suppressed PASSED after restore -- confirms no over-suppression

## Deviations from Plan

None -- plan executed exactly as written. The fix, step-0 checks, and
commit message structure all matched the plan specification.

## Known Stubs

None. The heading-words guard is fully wired; no placeholder paths remain.

## Threat Flags

None. The change touches only an in-process Python set computation over
already-parsed internal data structures. No new trust boundaries introduced.

## Self-Check: PASSED

- [x] src/plan_forge/checks/mechanical/f2_duplicate_fact.py -- modified and committed
- [x] commit 3c9618b exists
- [x] 765 passed, 0 new failures
- [x] Step 0 all clean (syntax, lint, non-ASCII, AI smell)
