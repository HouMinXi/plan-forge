# Roadmap: plan-forge v0.1.1 -- Precision Fixes

## Overview

v0.1.0 shipped 2026-05-26. Self-dogfood revealed three confirmed false-positive
classes. This milestone makes the two highest-ROI src/ corrections (G8 severity
downgrade + F2 heading-aware suppression) and fixes the GSD format coupling
(36 BLOCKER no_section findings) by updating forge templates -- zero LOC in
plan-forge itself.

## Milestones

- **v0.1.0 MVP** - Phases 1-7 (shipped 2026-05-26)
- **v0.1.1 Precision Fixes** - Phases 8-9 (in progress)

## Phases

<details>
<summary>v0.1.0 MVP (Phases 1-7) - SHIPPED 2026-05-26</summary>

Phases 1-7 covered parser, all mechanical F-gates (F1-F9), epistemic G-gates
(G1-G8), PBR gates, LLM layer (anthropic/deepseek/kimi/mimo/glm), host-search
G8 milestone, arbitration, corpus persistence, record-outcome intake, and the
T33 self-dogfood + T34 SC-3 audit. Full history in plan-forge-v0.1-PLAN.md.

</details>

### v0.1.1 Precision Fixes

**Milestone Goal:** Eliminate the three confirmed false-positive classes from
v0.1.0 self-dogfood without introducing new gates or architecture changes.

#### Phase 8: Source Code Precision Fixes

**Goal**: G8.A.no_citation no longer blocks prose-cited plans, and F2 no longer
fires on capitalized plan section headings
**Depends on**: Phase 7 (v0.1.0 shipped)
**Requirements**: GATE-01, GATE-02, GATE-03, GATE-04, GATE-05
**Success Criteria** (what must be TRUE):
  1. Running api.check on a plan whose External Voices section contains prose
     citations ("Nielsen (2022) showed...") returns HIGH, not BLOCKER, for
     G8.A.no_citation
  2. Running api.check on a well-formed plan that uses "Implementation Tasks"
     and "Success Criteria" as section headings produces zero F2 LOW findings
     for those terms
  3. Existing G8 true-positive fixture still fires (anti-gutting verified) and
     F2 genuine-repetition fixture still fires
**Plans**: 4 plans

Plans:
- [ ] 08-01-PLAN.md -- Worktree setup + fixture scaffolding + failing test stubs (RED)
- [ ] 08-02-PLAN.md -- G8 severity fix: no_citation BLOCKER -> HIGH for non-empty body
- [ ] 08-03-PLAN.md -- F2 heading-words suppression guard
- [ ] 08-04-PLAN.md -- Forge review pipeline + merge + worktree cleanup

#### Phase 9: GSD Format Compatibility

**Goal**: Forge GSD planning docs produce zero G-gate no_section BLOCKERs when
checked with api.check (was 36)
**Depends on**: Phase 8
**Requirements**: GSD-01, GSD-02
**Success Criteria** (what must be TRUE):
  1. The documented fix path exists: forge GSD templates updated to embed
     plan-forge canonical section keywords (e.g. "## Architecture & Reference
     Class") in the appropriate heading positions
  2. Running api.check (mechanical-only, llm_clients=[]) on a forge GSD planning
     doc returns 0 G-gate no_section BLOCKERs (down from 36)
**Plans**: TBD

## Progress

**Execution Order:** 8 -> 9

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 8. Source Code Precision Fixes | v0.1.1 | 0/TBD | Not started | - |
| 9. GSD Format Compatibility | v0.1.1 | 0/TBD | Not started | - |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| GATE-01 | Phase 8 | Pending |
| GATE-02 | Phase 8 | Pending |
| GATE-03 | Phase 8 | Pending |
| GATE-04 | Phase 8 | Pending |
| GATE-05 | Phase 8 | Pending |
| GSD-01 | Phase 9 | Pending |
| GSD-02 | Phase 9 | Pending |
