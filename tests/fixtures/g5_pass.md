# G5 Pass Fixture

## Chaos Response

Stressor scenarios and how the plan responds:

1. Server load doubles unexpectedly -- the system will benefit from pre-warmed auto-scaling.
2. A key library releases a breaking API change -- we survive by pinning versions and running integration tests.
3. Team bandwidth drops by 30% due to illness -- throughput will degrade but core deliverables are protected.
