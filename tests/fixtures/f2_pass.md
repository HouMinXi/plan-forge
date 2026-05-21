# F2 Pass Fixture

A plan where no capitalized noun-phrase bigram/trigram appears in
three or more distinct sections.

## Background

ParsedPlan is the primary data structure for plan analysis.

## Design

The implementation uses ParsedSection objects to store heading and body.

## Implementation

Code resides in parser.py following the ParsedPlan schema.

## Summary

Each major phrase appears in at most two sections, so F2 finds nothing.
