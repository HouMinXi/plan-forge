# LESSONS-RETRO: Retroactive Audit of Forge Phase 2 Plans

Status: COMPLETE (v0.1.0, 2026-05-26).

---

## Purpose

SC-3 retroactive audit: measure how well plan-forge's deterministic mechanical
layer catches problems that actually occurred in archived forge Phase 2 plans,
against an independent problem list drafted before plan-forge existed.

---

## Method

- Audited plans: 02-01-PLAN.md through 02-06-PLAN.md (archived forge Phase 2).
- Independent ground truth: forge 02-LEARNINGS.md (pre-existing, not derived from
  plan-forge output): 6 Decisions, 8 Lessons, 6 Patterns, 7 Surprises.
- Layer measured: mechanical + PBR only (api.check with llm_clients=[], fully
  deterministic, no corpus DB, no alembic). The LLM gates (G6.B / G8.B) are
  non-deterministic and are not part of the ship gate.
- Run: api.check on each plan; findings aggregated by check_id.

---

## Per-Plan Results

| Plan  | lines | findings | over-length (F9) |
|-------|-------|----------|------------------|
| 02-01 | 478   | 69       | no (< 500)       |
| 02-02 | 912   | 87       | yes              |
| 02-03 | 896   | 71       | yes              |
| 02-04 | 1238  | 85       | yes              |
| 02-05 | 1156  | 122      | yes              |
| 02-06 | 743   | 77       | yes              |

All six FAIL both verdicts (expected: the archived plans carry the documented
defects). Aggregate by check_id: F2 120, F3 255, F4 2, F9 5, G1 6, G3 6,
G4.A 2, G5 6, G7 (four subchecks) 23, G8.A 6, P1 60, P2 4, P5 16.

---

## SC-3 Coverage

Denominator = 14 of 20 documented problems. Excluded because no plan-text gate
can detect them: L5 (subagent silent cleanup, impl-time), L6 (review-tool
worktree pollution, process), S2 and S3 (review-round dynamics, meta), S5
(per-plan cost, meta), S6 (extract-learnings tooling), and S4 (a positive
surprise, not a defect).

| Metric | Value |
|--------|-------|
| Plan-text-defect classes (denominator) | 14 |
| Caught by the deterministic mechanical layer | 12 |
| Coverage | 12/14 = 86% |

Target: >= 60% floor. Result: PASS (86%).

### Defect -> gate mapping

Caught (12):
- D1, D4, L7 -- scope / reference-class gaps -> G1 + G7 (no_section, missing_*)
- D2, L8 -- pre-mortem / falsification absence -> G3
- D6, L4, S7 -- cross-plan or invariant claims unverified -> F3
- L3 -- own-edit duplicate fact -> F2
- L1 -- AI panel converges to "consistent" not "correct" -> G7 (partial)
- L2, S1 -- plan over-length (> 700 lines) -> F9 (added this release)

Missed (2), both need the LLM advisory layer (deferred v0.1.x):
- D3 -- Phase 2 ships paper-review with zero real bug-catch. F8.A (capability
  claim vs mock-only evidence) did not fire: the forge plans do not phrase the
  claim with F8's keyword patterns. Needs LLM capability-claim nuance.
- D5 -- prose says the lock releases "inside" the block, pseudocode shows
  "outside". F8.B (contradiction) was deferred via its circuit breaker
  (false-positive-prone), so no deterministic gate covers it.

---

## Findings / Lessons

- 86% is a FLOOR on a single six-plan corpus, not independent validation. F9 was
  added after T34 named L2/S1 as the misses, so catching them is partly
  self-fulfilling; F9 is nonetheless a general over-500-line check, not tuned to
  these plans. Real validation needs an independent holdout corpus (another
  phase's plans plus its learnings), deferred to v0.1.x.
- Precision improved but is not yet good. The G2 false-positive class (no_risks
  firing despite a "## Risks" heading) is eliminated (6 -> 0). F3 dropped from
  290 to 255 after the own-id self-reference and ISO-date-fragment fixes. Still
  noisy and deferred to v0.1.x: F2 duplicate-fact (120), P1 orphan-identifier
  (60), and F3 per-mention inflation (one finding per mention, not per distinct
  id).
- The two misses are exactly the semantic cases a mechanical layer cannot reach
  cheaply (capability-claim nuance, prose-vs-code contradiction). They define the
  first job of the v0.1.x LLM advisory layer, not a gap to paper over by tuning
  the mechanical gates to this corpus.
- Separate parser blind spot (not part of this coverage number): F1
  (SC-traceability) and G6 (SC-falsifiability) are silent on GSD-format plans
  because the parser does not extract numbered-list success criteria into
  sc_table. Flagged for v0.1.x.
