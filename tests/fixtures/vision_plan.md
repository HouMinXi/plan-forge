<!-- fixture-contract:
  G8.A satisfied: External Voices section has citation (Flyvbjerg 2006),
    dissent keyword ("critics argue"), and failure case ("failure").
  G3 satisfied: Pre-mortem has 5 causes each with early_warning + counter.
  G1 absent (Reference Class) -> G1.no_section BLOCKER (VISION trigger).
  G7 absent (Scope Challenge)  -> G7.no_section BLOCKER (VISION trigger).
  Net: only vision-gate BLOCKERs fire -> epistemic VISION.
-->
# Vision Plan

## Overview

A plan about software.

## Risks

### Known Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| schedule slip | 50% | High | weekly review |

### Gray Rhinos

| Gray Rhino | Denial Reason | Counter |
|------------|---------------|---------|
| scope creep | Feels productive | weekly freeze |

### Black Swans

| Black Swan | Survival Plan |
|------------|---------------|
| key dep deprecated | fork internally |

## Pre-mortem

1. Ran out of time. early_warning: milestones missed. counter: re-scope.
2. API design breaks downstream. early_warning: complaints. counter: versioned API.
3. Tests too slow. early_warning: CI over 10 minutes. counter: parallelize.
4. Docs not maintained. early_warning: undocumented APIs. counter: doc linter.
5. Upstream breaks. early_warning: release notes. counter: pin version.

## Chaos Response

1. CI goes down -- the system will survive with local runs.
2. Key engineer unavailable -- throughput will degrade but core is protected.
3. Upstream API redesign -- the team will survive by pinning versions.

## External Voices

- Flyvbjerg (2006). From Nobel Prize to project management.

However, critics argue that forecasting anchors too conservatively.

The 2013 Healthcare.gov failure demonstrated integration testing gaps.
