# P1 Code-Symbol FP Fixture

This plan mentions code symbols once each.  None should trigger P1 because
code symbols are illustrative, not plan-structural identifiers.

## Overview

The SDK uses `anthropic` as the provider name when constructing the client.

To handle context expiry, override `__exit__` in the resource class.

Test scripts live in `foo.py` alongside `bar.md` for documentation.

The module path `checks.mechanical.run` is the entry point for linting.

The schema field `tool_use` carries the tool invocation payload.

An internal constant `plan_text` holds the raw document bytes.

A hash field `plan_hash` is stored for cache invalidation.

The orchestrator script is `g9_feasibility_anchor.py` in the checks dir.

The spec file `MANIFESTO.md` describes the overall project goals.

The `__init__` method sets up the instance state on construction.

A dotted accessor `result.verdict` reads the final gate output.

## Design

All of the above tokens are code symbols, not plan identifiers.  P1 must
remain silent on this document.
