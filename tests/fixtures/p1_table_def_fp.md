# P1 Table Definition FP Fixture

A Success Criteria table.  Each structured ID appears only as the first
cell of its row -- that is where it is defined.  P1 must not flag these.

## Success Criteria

| ID | Criterion | Fail Condition |
|----|-----------|----------------|
| phase-1 | Adapter registered and invocable | adapter fails to invoke |
| phase-2 | Coverage meets threshold | pytest reports below target |
| phase-3 | Documentation present | API docs missing |

## Design

The table above defines phase-1, phase-2, and phase-3 at their first
occurrence.  No other cross-reference is needed for these IDs.
