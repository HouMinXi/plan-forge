# Claim + No Evidence Section (FP fixture -- should NOT fire)

## Overview

The check catches real bugs in production codebases.

## Design

We scan the AST and compare with known bad patterns.

## Risks

- May miss obscure bug patterns not covered by the AST scan.
