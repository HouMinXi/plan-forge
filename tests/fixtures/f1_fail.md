# Plan Document F1 Fail

An SC references a test that is not listed in the Verification section.

## SC Table

| SC | Criterion | Body |
|----|-----------|------|
| SC-1 | Parsing works | Verified by test_parse_sections |
| SC-2 | Coverage works | Verified by test_coverage_report |

## Verification

- test_parse_sections: checks section extraction

## Notes

SC-2 references a function that is absent from the verification list.
The orphan should be caught by the traceability check.
