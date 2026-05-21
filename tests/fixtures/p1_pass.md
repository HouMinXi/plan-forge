# P1 Pass Fixture

Every identifier in this plan appears at least twice, ensuring P1
symbol closure is satisfied.

## Overview

The `parse_plan` function reads a markdown document and returns a
`ParsedPlan` object.  `parse_plan` is the main entry point.

The `ParsedPlan` dataclass holds extracted sections and SC rows.
`ParsedPlan` is used throughout the pipeline.

The `run_checks` function drives all mechanical checks.
Call `run_checks` with a parsed plan to get findings.

## References

The `verify_output` helper validates results.  Use `verify_output`
to confirm each check produces the correct finding list.

<!-- plan-forge: p1-ok external system -->
The `external_artifact_alpha` is an upstream dependency documented
in the external reference index.
