# F6 Pass Fixture

This fixture is used without a preamble argument.
When preamble is None, F6 returns no findings.

## Background

The plan covers mechanical check implementation for F1 through F7.

## Design

Each check module exposes a check() function that returns findings.

## Summary

No preamble is supplied in the test, so F6 is a no-op.
