# Plan 13-02: Implement F10-F15 Plan Quality Gates

**Status:** Complete
**Phase:** 13
**Plan:** 13-02

## What was built

Implemented six mechanical F-gates (F10-F15) in `src/plan_forge/checks/mechanical/`:

- **F10** (`f10_noun_phrase_duplicate.py`): Noun-phrase duplicate detection across plan
  sections — flags 3+-word phrases appearing 3+ times in 2+ distinct sections. Severity: LOW.
- **F11** (`f11_ac_test_traceability.py`): AC-to-test traceability — finds test function
  names in acceptance_criteria blocks and verifies they exist in `tests/`. Severity: MEDIUM.
- **F12** (`f12_temporal_anchor_lint.py`): Temporal anchor lint — flags unanchored
  before/after phrases in AC and action blocks. Severity: LOW.
- **F13** (`f13_cross_plan_claim_verifier.py`): Cross-plan claim verifier — flags cross-plan
  references in audit sections with fewer than 10 prose words. Severity: MEDIUM.
- **F14** (`f14_task_without_ac.py`): Task-without-acceptance-criteria — flags non-checkpoint
  tasks missing both AC and verify blocks. Severity: HIGH.
- **F15** (`f15_read_first_validity.py`): Read-first file validity — flags files in
  read_first blocks that do not exist on disk. Severity: MEDIUM.

All six gates registered in `__init__.py` with explicit imports and `findings.extend()` calls.

## Key decisions honored

- D-22: Explicit `__init__.py` registration (not auto-discovery)
- D-23: F15 parses `files_modified` from `raw_text` YAML frontmatter (no `parsed.frontmatter`)
- D-24: F11/F15 use `Path(__file__).resolve().parents[4]` for repo root; return `[]` if absent
- D-14/D-15: F14 exempts `checkpoint:*` task types and tasks with a `<verify>` block

## Test results

- F10-F15 unit tests: 18/18 PASS (was 12/18 FAIL in RED state)
- Full suite: 789 passed, 1 pre-existing fail (test_version_is_alpha2), 5 skipped
- Integration snapshots updated: 22→32, 20→30 (F10/F14/F15 fire on e2e fixtures)

## Bite tests

Each gate guard confirmed load-bearing:
- F10: removing section-boundary check causes FP fixture to fire
- F11: removing exists() check causes TP to fail on missing test name
- F12: removing anchor-exclusion check causes FP fixture to fire
- F13: changing prose-word threshold to 0 silences TP fixture
- F14: removing checkpoint exemption causes FP fixture to fire
- F15: removing files_modified exclusion causes FP fixture to fire

## Self-Check: PASSED
