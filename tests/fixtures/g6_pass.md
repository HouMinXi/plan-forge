# G6 Pass Fixture -- all SCs have concrete measurable fail_conditions

## Success Criteria

| SC | Criterion | Fail Condition |
|----|-----------|----------------|
| SC-1 | API latency | FAILS if curl /health median > 100ms over 5 samples at 1Hz |
| SC-2 | Test coverage | FAILS if pytest --cov reports < 80% line coverage |
| SC-3 | Build time | FAILS if make all takes > 60 seconds on CI runner |
