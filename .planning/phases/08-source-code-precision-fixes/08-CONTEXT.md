# Phase 8 Context: Source Code Precision Fixes

**Phase:** 8 -- Source Code Precision Fixes
**Date:** 2026-05-27
**Status:** Context gathered, ready to plan

## Domain

Two surgical src/ fixes to eliminate confirmed false positives from v0.1.0
self-dogfood. No new gates. No new architecture. Both fixes have crossed
the cross-model review panel (deepseek + mimo + kimi) and have a clear
implementation path.

## Decisions

### G8.A.no_citation Severity (GATE-01, GATE-02, GATE-03)

**Decision:** Change G8.A.no_citation from Severity.BLOCKER to Severity.HIGH.
Additionally, distinguish between a truly empty External Voices body and a body
with content but no parseable citations:

- body is None (no section) -> existing G8.A.no_section BLOCKER unchanged
- body.strip() == "" (section exists but empty) -> G8.A.no_citation BLOCKER
- body.strip() != "" and len(parsed.citations) == 0 -> G8.A.no_citation HIGH

**File:** src/plan_forge/checks/epistemic/g8_source_diversity.py, lines 98-107.
**Change size:** ~5 lines (add body.strip() check before emitting the finding).

**Bug-inject teeth (GATE-01T):** Manual step before commit -- temporarily revert
severity to BLOCKER, confirm prose-cited FP fixture fires as BLOCKER, restore to HIGH,
confirm fixture returns HIGH. Record result in commit message body.

### F2 Heading-Aware Suppression (GATE-04, GATE-05)

**Decision:** Word-subset match across ALL headings. A bigram/trigram is suppressed
if EVERY word in the n-gram appears as a word in at least one section heading
(case-insensitive, any heading -- not required to be the same heading).

**Implementation:** In the flagging step of f2_duplicate_fact.py, build a
heading_words set from parsed.sections keys (tokenize each heading into words,
lowercase). For each flagged n-gram, check if all its words appear in heading_words.
If yes, skip.

**File:** src/plan_forge/checks/mechanical/f2_duplicate_fact.py.
**Change size:** ~8-12 lines.

**Bug-inject teeth (GATE-04T):** Manual step before commit -- temporarily remove
the heading-word check, confirm the structural-term FP fixture fires F2 findings,
restore, confirm silence. Record result.

### Bug-Inject Form

Both GATE-01T and GATE-04T are manual steps documented in PLAN.md, not automated
test cases. The implementer performs the flip-confirm-restore cycle before committing
and records the result (fixture name, before/after finding count) in the commit message.

### Findings Detail Output

Deferred to Phase 10. The skill runner currently outputs summary only (counts by
severity); full per-finding detail (check_id, message, location, fix_hint) is needed
for usability. This is a new output capability -- out of scope for Phase 8.

## Canonical Refs

- src/plan_forge/checks/epistemic/g8_source_diversity.py (G8 Part A, lines 75-130)
- src/plan_forge/checks/mechanical/f2_duplicate_fact.py (F2 check, full file)
- tests/unit/test_g8_source_diversity.py (G8 tests, anti-gutting fixtures)
- tests/unit/test_f2_duplicate_fact.py (F2 tests)
- .planning/REQUIREMENTS.md (GATE-01 through GATE-05, GATE-01T, GATE-04T)

## Code Context

- parsed.sections is dict[str, ParsedSection] where keys are heading strings
- parsed.citations is a list of citation strings extracted by _extract_citations()
- _find_external_voices_body() returns str | None (None = section absent)
- F2 _extract_ngrams(text) returns a set of lowercase bigram/trigram strings

## Deferred Ideas

- Phase 10: skill runner + CLI detailed findings output -- show full list with
  check_id, message, location, fix_hint per finding (blocked user from reading
  36-finding report on a real GSD spec doc)
