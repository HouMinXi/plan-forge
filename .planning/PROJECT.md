# plan-forge v0.1.1 -- Precision Fixes

## What This Is

A patch milestone targeting three confirmed false-positive classes found during v0.1.0
self-dogfood. All three fixes are small, targeted, and have cross-model review consensus
(deepseek + mimo + kimi agreed on direction). No new gates. No architecture changes.

## Core Value

plan-forge's signal-to-noise ratio. A tool that cries wolf on low-severity noise or
blocks legitimate plans with a BLOCKER undermines trust faster than missing real defects.
v0.1.1 makes the three highest-impact precision corrections before any new capability work.

## Context

- v0.1.0 shipped 2026-05-26, tagged, Apache 2.0, on GitHub (HouMinXi/plan-forge)
- Self-dogfood: api.check on own master plan returns PASS (engineering + epistemic)
- GSD-format audit revealed format coupling: 36 BLOCKER no_section findings when run
  on forge planning docs (different heading names than plan-forge canonical)
- Three model review panel (deepseek/mimo/kimi) converged on fix directions

## Problems to Solve

1. G8.A.no_citation emits BLOCKER even when External Voices has prose citations
   (parser only matches APA bullet-list format; prose like "Nielsen (2022)..." invisible)
2. F2 emits LOW findings for plan-structural terms ("Implementation Tasks",
   "Success Criteria") that legitimately repeat in well-formed plans
3. plan-forge section keywords are hardcoded; GSD-format plans produce 36 no_section
   BLOCKERs because headings differ ("Architecture & Reference Class" vs "Reference Class")

## Requirements

### Active

- [ ] G8.A.no_citation severity: BLOCKER -> HIGH (1-line change, highest ROI)
- [ ] F2 false positives: heading-aware suppression or frozenset exemption for
      structural plan terms
- [ ] GSD compatibility: document the template fix path (zero plan-forge LOC);
      update forge GSD templates to embed canonical keywords

### Out of Scope

- New gates or checks -- v0.2
- Parser extension for prose citation detection -- v0.1.x backlog
- Section-alias system (150-300 LOC, 1 consumer, fails >=100 LOC/3 consumers rule) -- deferred
- F8.B contradiction detection -- deferred per circuit breaker
- Holdout corpus -- v0.1.x backlog

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| G8 downgrade not parser extension | Prose citation matching is NLP-hard; Part B LLM guard is the real anti-hallucination layer | Severity only |
| F2 heading-aware over frozenset | Heading-matching is self-maintaining; frozenset grows unbounded | ~5 LOC |
| GSD fix in forge templates, not plan-forge | Section-alias violates 100 LOC/3 consumers rule; one consumer (forge) fixes its own templates | 0 LOC in plan-forge |
| Q3 > Q2 > Q1 priority | G8 BLOCKER on legitimate plans is highest-severity UX breakage | Fix order |

## Evolution

After v0.1.1 ships, re-run GSD-format audit to confirm 36 BLOCKERs are gone
(template fix) and G8 no longer blocks prose-cited plans (severity fix).

---
*Last updated: 2026-05-27 after initialization*
