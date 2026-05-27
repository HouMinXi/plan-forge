# Phase 9 Context: GSD Format Compatibility

**Phase:** 9 -- GSD Format Compatibility
**Date:** 2026-05-27
**Status:** Context gathered, ready to plan

## Domain

Zero-LOC change to plan-forge. Update forge GSD planning documents (ROADMAP.md
and CONTEXT.md files) to embed plan-forge canonical section keywords in headings,
so api.check(llm_clients=[]) returns 0 G-gate no_section BLOCKERs (down from 36).
The plan-forge codebase is not modified.

## Decisions

### Target Documents (GSD-01, GSD-02)

Update only ROADMAP.md and CONTEXT.md files in the active (non-archived) forge
planning directory. PLAN.md files are excluded -- implementation plans do not
naturally contain epistemic sections like External Voices or Pre-Mortem.

Active files to update (5 total):
- /home/houminxi/code/forge/.planning/ROADMAP.md
- /home/houminxi/code/forge/.planning/milestones/v2.1-dynamic-gate/ROADMAP.md
- /home/houminxi/code/forge/.planning/phases/01-r1-commit-gate-r4-docs/01-CONTEXT.md
- /home/houminxi/code/forge/.planning/phases/02-r2-mutation-pipeline-step/02-CONTEXT.md
- /home/houminxi/code/forge/.planning/phases/03-r3-e2e-coverage/03-CONTEXT.md

### G-gate Keyword Requirements

Each document needs at least one heading containing the required substring:

G1 -- heading contains "reference class" (e.g. "## Prior Work and Reference Class")
G2 -- level>=2 heading contains "risk" (e.g. "## Risks and Mitigations")
G3 -- heading contains "pre-mortem" or "premortem" (e.g. "## Pre-Mortem Analysis")
G5 -- heading contains "chaos response" or "chaos" (e.g. "## Chaos Response")
G7 -- heading contains "scope challenge" or "scope" (e.g. "## Scope Challenge")
G8 -- heading contains "external voices" (e.g. "## External Voices")

Each added section must have real content, not just a heading. Empty sections
are detectable by G-gate content checks beyond the no_section gate.

### Verification (GSD-02)

After updating all 5 documents, run api.check(llm_clients=[]) on each from
the plan-forge worktree. Target: 0 G-gate no_section BLOCKERs per document
(BLOCKER = check_id contains 'no_section').

Run command (from plan-forge install):
  uv run python -c "
from plan_forge.parser import parse; from plan_forge import api
t = open('/path/to/doc.md').read()
r = api.check(t, llm_clients=[])
ns = [f for f in r.findings if 'no_section' in f.check_id]
print('no_section BLOCKERs:', len(ns))
"

## Canonical Refs

- /home/houminxi/code/forge/.planning/ (forge planning root)
- /home/houminxi/code/plan-forge/src/plan_forge/checks/epistemic/_sections.py
  (find_section: all(kw in heading.lower() for kw in keywords))
- G1: g1_reference_class.py -- looks for "reference class"
- G2: g2_risk_taxonomy.py -- level>=2 AND 'risk' in heading.lower()
- G3: g3_premortem.py -- "pre-mortem" or "premortem"
- G5: g5_antifragility.py -- "chaos response" or "chaos"
- G7: g7_scope_challenge.py -- "scope challenge" or "scope"
- G8: g8_source_diversity.py -- "external voices" in heading.lower()

## Code Context

- find_section(parsed, *keywords): first section where
  all(kw in section.heading.lower() for kw in keywords)
- G2 differs: uses direct loop with section.level >= 2 check
- G8 differs: uses _find_external_voices_body() checking heading.lower()

## Deferred Ideas

- Section-alias system in plan-forge (~150-300 LOC, 1 consumer) -- deferred
- Format-declaration mechanism -- v0.2+
