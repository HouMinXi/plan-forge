# Well-Formed Plan: plan-forge v0.1

Ship plan-forge v0.1, a Python library that enforces G1-G10 and F1-F7
gates on plan documents.

## Success Criteria

| SC | Criterion | Fail Condition |
|----|-----------|----------------|
| SC-1 | Library parses plan documents | FAILS if parse() raises on valid input |
| SC-2 | Mechanical checks run | FAILS if check_mechanical() returns no findings on a known-bad plan |
| SC-3 | Epistemic checks run | FAILS if check() raises with llm_clients=[] |
| SC-4 | Verdict aggregation correct | FAILS if FAIL verdict returned when no BLOCKER or HIGH finding present |

## Test Plan

- test_parse_plan_sections: covers SC-1; verifies section extraction from markdown
- test_check_mechanical_returns_verdict: covers SC-2; verifies check_mechanical() returns Verdict
- test_check_epistemic_runs: covers SC-3; verifies check() with llm_clients=[] does not raise
- test_verdict_aggregation: covers SC-4; verifies PASS verdict when no BLOCKER or HIGH

## Overview

The `check` function is the primary entry point for the library.
`check` accepts a plan document as text and returns a `Verdict` object.

The `Verdict` dataclass holds engineering and epistemic verdicts plus findings.
`Verdict` is constructed by aggregating findings from all three check layers.

The `parse` function converts raw markdown into a `ParsedPlan` object.
`parse` is called internally by `check` before any gate runs.
The `ParsedPlan` dataclass is the intermediate representation used by all gates.

## Deliverables

| Item | Description |
|------|-------------|
| `check` | Public API entry point accepting plan text |
| `Verdict` | Dataclass returned by check() with verdicts and findings |
| `parse` | Internal parser converting markdown to ParsedPlan |

## Module Designs

```python
def check(plan_text: str, llm_clients=None, preamble=None):
    pass

class Verdict:
    pass

def parse(plan_text: str):
    pass
```

## Implementation Tasks

| Task | Description | Output |
|------|-------------|--------|
| T01 | Implement parser | `parse` |
| T02 | Implement check API | `check` |
| T03 | Implement Verdict dataclass | Verdict dataclass |

## Reference Class

Historical projects with similar scope and plan-vs-actual ratios:

| Project | Scope | Actual Duration | Plan-vs-Actual |
|---------|-------|-----------------|----------------|
| ruff v0.1 | lint tool Python | 10 weeks | 1.3x |
| mypy v0.9 | type checker Python | 14 weeks | 1.7x |

Both projects ran over plan due to edge-case discovery during implementation.
Outside-view estimate: apply 1.5x multiplier to the current eight-week estimate.

## Risks

### Known Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| LLM API instability | 40% | Medium | Graceful fallback to mechanical-only mode |
| Scope creep in gate design | 60% | High | Strict spec-first development process |

### Gray Rhinos

| Gray Rhino | Denial Reason | Counter |
|------------|---------------|---------|
| Corpus recording becomes load-bearing | Teams ignore it until reports are needed | Define corpus interface in v0.1 spec |
| Third-party LLM costs spike | Teams assume current pricing holds | Implement mock clients for CI from day one |

### Black Swans

| Black Swan | Survival Plan |
|------------|---------------|
| LLM provider shuts down | Provider registry allows new providers to be added without API changes |
| Python ABI breaks extension dependencies | Pin Python version in CI; test on fallback version |

## Pre-mortem

Imagine the project has failed. What went wrong?

1. Gate implementation diverged from spec without versioned update. early_warning: interpretation comments missing in code. counter: mandatory interpretation comments at every decision point.
2. LLM clients returned non-deterministic verdicts causing flaky tests. early_warning: test suite failure rate above five percent. counter: use MockClient exclusively in unit tests.
3. Fixture coverage was insufficient to catch gate regressions. early_warning: new gate added without corresponding pass fixture. counter: require pass and fail fixture for every gate before merging.
4. Corpus recording introduced tight coupling to the database layer. early_warning: check() signature changes to accept a DB session object. counter: corpus recording is optional and delegated to later tasks.
5. Performance degraded as gate count grew from eight to ten checks. early_warning: check() call time exceeds two seconds at p50 on a typical plan. counter: benchmark in CI; defer expensive gates behind explicit flags.

## Scope Challenge

Q1: Does this need to exist? Yes -- no existing tool enforces G1-G10
structural gates on plan documents. Plans are reviewed manually today,
which misses systematic epistemic failures and justifies this work.

Q2: Who are the consumers? Three concrete consumers have been
identified: the plan-forge CI pipeline itself for self-audit,
the forge-code review tool which calls check() on embedded plans,
and the team RFC process as a pre-submission gate. These are internal
consumers with confirmed demand signals from weekly engineering reviews.

Q3: What is the do-nothing cost? The status quo cost is estimated at
three engineer-hours per plan review for manual epistemic checking,
multiplied by twelve plans per quarter, totaling thirty-six hours per
quarter in direct labor. The do-nothing path compounds with team growth.

Q4: Barbell analysis: either build the minimal mechanical gates only
(two weeks, no LLM cost) or build the full G1-G10 plus LLM pipeline
(eight weeks, higher upside). There is no middle ground that delivers
proportional value. We choose the full pipeline because mechanical-only
catches less than forty percent of epistemic failures.

## Chaos Response

1. LLM provider outage during CI run -- the system will survive by falling back to mechanical-only mode when llm_clients=[] is passed.
2. New gate added mid-milestone that changes check() output schema -- old callers degrade gracefully; they receive additional findings but no breaking API change.
3. Corpus database unavailable for recording -- throughput will degrade to in-memory only; check() still returns correct verdicts.

## External Voices

- Flyvbjerg (2006). From Nobel Prize to project management: getting risks right.
- Klein (2007). Performing a project premortem.
- Taleb (2007). The Black Swan: The Impact of the Highly Improbable.

However, critics note that reference-class forecasting can anchor plans
too conservatively when the project is genuinely novel in scope.

The 2013 Healthcare.gov launch failure demonstrated that structural
review processes alone cannot substitute for integration testing.
