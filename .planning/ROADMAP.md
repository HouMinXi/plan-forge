# Roadmap: plan-forge -- Active Development

## Overview

v0.1.0 shipped 2026-05-26. v0.1.1 shipped 2026-05-28 (G8 severity downgrade +
F2 heading-word suppression + GSD format compatibility). v0.1.2 targets the
remaining F2 false-positive class: structural template phrases and commit-signature
tokens that repeat across sections by design in implementation plans.

## Milestones

- **v0.1.0 MVP** - Phases 1-7 (shipped 2026-05-26)
- **v0.1.1 Precision Fixes** - Phases 8-9 (shipped 2026-05-28)
- **v0.1.2 F2 Structural FP Reduction** - Phase 10 (planned)

## Phases

<details>
<summary>v0.1.0 MVP (Phases 1-7) - SHIPPED 2026-05-26</summary>

Phases 1-7 covered parser, all mechanical F-gates (F1-F9), epistemic G-gates
(G1-G8), PBR gates, LLM layer (anthropic/deepseek/kimi/mimo/glm), host-search
G8 milestone, arbitration, corpus persistence, record-outcome intake, and the
T33 self-dogfood + T34 SC-3 audit. Full history in plan-forge-v0.1-PLAN.md.

</details>

<details>
<summary>v0.1.1 Precision Fixes (Phases 8-9) - SHIPPED 2026-05-28</summary>

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
- [x] 08-01-PLAN.md -- Worktree setup + fixture scaffolding + failing test stubs (RED)
- [x] 08-02-PLAN.md -- G8 severity fix: no_citation BLOCKER -> HIGH for non-empty body
- [x] 08-03-PLAN.md -- F2 heading-words suppression guard
- [x] 08-04-PLAN.md -- Forge review pipeline + merge + worktree cleanup

#### Phase 9: GSD Format Compatibility

**Goal**: Forge GSD planning docs produce zero G-gate no_section BLOCKERs when
checked with api.check (was 36)
**Depends on**: Phase 8
**Requirements**: GSD-01, GSD-02
**Success Criteria** (what must be TRUE):
  1. The documented fix path exists: forge GSD templates updated to embed
     plan-forge canonical section keywords in the appropriate heading positions
  2. Running api.check (mechanical-only, llm_clients=[]) on a forge GSD planning
     doc returns 0 G-gate no_section BLOCKERs (down from 36)
**Plans**: 2 plans

Plans:
- [x] 09-01-PLAN.md -- Add G-gate sections to both forge milestone ROADMAP files
- [x] 09-02-PLAN.md -- Add G-gate sections to 01-CONTEXT.md; fix citation in 03-CONTEXT.md; verify all 5 docs

</details>

### v0.1.2 F2 Structural FP Reduction

**Milestone Goal:** Eliminate F2.duplicate_fact false positives caused by
structural template phrases and commit-signature tokens in implementation plans.

#### Phase 10: F2 Structural False-Positive Reduction

**Goal**: F2.duplicate_fact no longer fires on structural template phrases
(step/run/expected/pass) or commit-signature tokens (author names in
Signed-off-by lines) in implementation plans
**Depends on**: Phase 9 (v0.1.1 shipped)
**Requirements**: F2-01, F2-02
**Success Criteria** (what must be TRUE):
  1. Running check_mechanical on a plan with structural template phrases
     (step write, step run, expected pass, etc. repeated across task sections)
     produces zero F2 LOW findings for those terms
  2. Running check_mechanical on a plan embedding commit message examples with
     repeated Signed-off-by lines produces zero F2 LOW findings for author-name
     phrases (e.g. "minxi hou", "signed-off-by minxi")
  3. Genuine duplicate-fact TP fixture still fires (anti-gutting verified)
  4. Bug-inject cycle confirms the guards are load-bearing
**Plans**: 3 plans

Plans:
- [x] 10-01-PLAN.md -- Worktree setup + fixture scaffolding + failing test stubs (RED)
- [x] 10-02-PLAN.md -- F2 union exclusion filter: structural words + signoff tokens + bug-inject
- [ ] 10-03-PLAN.md -- Forge review pipeline + merge + worktree cleanup

## Progress

**Execution Order:** 8 -> 9 -> 10

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 8. Source Code Precision Fixes | v0.1.1 | 4/4 | Complete | 2026-05-28 |
| 9. GSD Format Compatibility | v0.1.1 | 2/2 | Complete | 2026-05-28 |
| 10. F2 Structural FP Reduction | v0.1.2 | 2/3 | In Progress|  |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| GATE-01 | Phase 8 | Complete |
| GATE-02 | Phase 8 | Complete |
| GATE-03 | Phase 8 | Complete |
| GATE-04 | Phase 8 | Complete |
| GATE-05 | Phase 8 | Complete |
| GSD-01 | Phase 9 | Complete |
| GSD-02 | Phase 9 | Complete |
| F2-01 | Phase 10 | Pending |
| F2-02 | Phase 10 | Pending |
