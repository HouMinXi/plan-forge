# Test Plan F1 Pass Fixture

A minimal plan where SC table tests match test list entries.

## SC Table

| SC | Criterion | Body |
|----|-----------|------|
| SC-1 | Parsing works | Verified by test_parse_sections |
| SC-2 | Verdict works | Verified by test_verdict_pass |

## Test Plan

- test_parse_sections: checks section extraction
- test_verdict_pass: checks verdict dataclass construction

## Summary

All SC references point to tests defined in the Test Plan section.
