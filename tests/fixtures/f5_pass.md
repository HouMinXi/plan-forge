# F5 Pass Fixture

SCs have at most 2 inline R-tags each.

## SC Table

| SC | Criterion | Body |
|----|-----------|------|
| SC-1 | Parsing | Must parse all headings. R1 H1 R2 M3 |
| SC-2 | Output | Must return list. R3 L1 |
| SC-3 | Edge case | Must handle empty input. |

## Summary

SC-1 has exactly 2 R-tags (the cap), SC-2 has 1, SC-3 has 0.
No SC exceeds the cap of 2, so F5 emits no findings.
