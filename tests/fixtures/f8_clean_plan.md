# Clean Plan -- no capability claims

## Design

This module parses markdown and extracts sections.

## Tests

- `test_parse_empty.py`: verifies empty input returns empty ParsedPlan.
- `test_parse_headings.py`: verifies section extraction from a heading tree.

## Risks

- Parser misreads nested code fences.
