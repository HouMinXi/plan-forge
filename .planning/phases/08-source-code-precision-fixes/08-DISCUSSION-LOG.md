# Phase 8 Discussion Log

**Date:** 2026-05-27
**Areas discussed:** F2 heading match, G8 body detection, Bug-inject form, Output detail

## Area: F2 Heading Match Precision

Q: How should "heading-aware" matching work?
Options: Exact match (n-gram == heading) / Word subset (each word in any heading)
Decision: Word subset

Follow-up Q: Match scope -- all words in ONE heading vs ANY heading?
Decision: All words in ANY heading (more permissive, handles composite headings)

## Area: G8 Body Emptiness Detection

Q: How to detect "has content but no parseable citations"?
Options: body.strip() non-empty / Minimum N characters
Decision: body.strip() non-empty

## Area: Bug-Inject Form

Q: Manual step in PLAN.md vs automated monkeypatch test?
Decision: Manual step in PLAN.md

## Area: Output Detail (raised by user, deferred)

Context: User ran skill runner against a real GSD spec doc, got 36-finding summary
with no per-finding detail. Could not act on individual findings.
Decision: Deferred to Phase 10 (new capability, out of Phase 8 scope)

## Deferred Ideas

- Phase 10: detailed findings output in skill runner and CLI
