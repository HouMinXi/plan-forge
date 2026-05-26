# Claim + Mock Evidence (TP fixture)

## Overview

The new check catches real bugs in production codebases and validates
against production data.  It works on real code by inspecting the AST
and exercising the parser.

## Tests

- `test_with_mock.py`: uses a mock parser object.
- `test_stub_plan.py`: passes a stub ParsedPlan to the check function.
- Fixtures: synthetic plan strings generated inline.

## Risks

- Fixture coverage may not represent edge cases from real codebases.
