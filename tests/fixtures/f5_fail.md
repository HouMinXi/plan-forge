# F5 Fail Fixture

One SC has more than 2 inline R-tags.

## SC Table

| SC | Criterion | Body |
|----|-----------|------|
| SC-1 | Parsing | Must parse all headings. R1 H1 R2 M3 R3 L2 |
| SC-2 | Output | Must return list. R4 B1 |

## Summary

SC-1 has 3 inline R-tags (R1 H1, R2 M3, R3 L2), which exceeds the
cap of 2.  F5 should emit one finding for SC-1.
