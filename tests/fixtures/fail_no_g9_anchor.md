# Plan With Missing G9 Anchor

## Goal

Ship v0.1 of the widget library in 12 weeks.

## Success Criteria

| SC | Criterion | Fail Condition |
|----|-----------|----------------|
| SC-1 | Library compiles | FAILS if build errors on CI |
| SC-2a | Unit test coverage | FAILS if coverage below 80% |
| SC-2b | Integration tests | FAILS if any integration test fails |

## Reference Class

| Project | Scope | Actual Duration | Plan-vs-Actual |
|---------|-------|-----------------|----------------|
| forge-code v1 | lint tool | 10 weeks | 1.4x |
| ruff v0.1 | lint tool | 8 weeks | 1.1x |

Outside-view estimate: 9 weeks median.
[anchor: in-plan-derivation from Reference Class table above]

## Risks

### Known Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Schedule slip | 60% | High | Weekly milestones |

### Gray Rhinos

| Gray Rhino | Denial Reason | Counter |
|------------|---------------|---------|
| Scope creep | Feels productive | Weekly scope freeze review |

### Black Swans

| Black Swan | Survival Plan |
|------------|---------------|
| Key dependency deprecated | Fork and maintain internally |

## Pre-mortem

1. Ran out of time due to underestimation.
   - early_warning: 2 milestones missed consecutively
   - counter: re-scope to MVP
2. API design causes downstream breakage.
   - early_warning: 3+ consumer complaints in first week
   - counter: versioned API from day 1
3. Test infrastructure too slow.
   - early_warning: CI takes more than 10 minutes
   - counter: parallelize test execution
4. Documentation not maintained.
   - early_warning: 5+ undocumented public APIs
   - counter: doc linter in CI
5. Integration with upstream breaks.
   - early_warning: upstream release notes mention breaking changes
   - counter: pin upstream version, test against nightly

## Scope Challenge

Q1: Does this need to exist? Yes -- no existing tool covers G1-G10.
Q2: 3 consumers: forge-code CI, plan-forge self-audit, team RFC process.
Q3: Do-nothing cost: $2000 in review labor per quarter.
[anchor: in-plan-derivation from team time tracking]
Q4: Barbell: minimal mechanical checks (safe) + optional LLM (upside).

## Chaos Response

| Stressor | Classification |
|----------|---------------|
| CI goes down for 2 days | survive |
| Key engineer unavailable 1 week | survive |
| Upstream API redesign | degrade |

## External Voices

- Flyvbjerg et al. (2002). Underestimating Costs in Public Works Projects.
- Klein (2007). Performing a Project Premortem.
- Taleb (2007). The Black Swan.
