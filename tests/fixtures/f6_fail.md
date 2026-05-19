# F6 Fail Fixture

This fixture is paired with a preamble that contains a fact not
present in this plan body.

## Background

The plan covers mechanical check implementation.

## Design

Each check module exposes a check() function returning findings.

## Summary

The test passes a preamble containing a sentence about database
migration requirements that does not appear anywhere in this plan
body.  F6 should emit a finding for that preamble sentence.
