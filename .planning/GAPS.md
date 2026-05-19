# Plan-Forge Known Gaps

This file tracks coverage gaps in plan-forge that are NOT (yet)
categorized as Out of Scope (we have not decided whether to do them)
and are NOT blocking Open Questions (they do not gate a v0.1 ship
decision).

Purpose: prevent "we know this dimension is missing" from getting
diluted into freeform notes scattered across PLAN.md.  When a SUBSPEC
or design discussion identifies a gap, record it here with the
four-field format below.  This keeps the gap discoverable without
requiring it to be promoted to Out of Scope (i.e., committed
non-feature) or Open Question (i.e., decision blocker) prematurely.

Format per entry:

- **What is missing**: concrete capability the tool does not have
- **Why it matters**: which failure mode it leaves uncaught
- **Why it is not in v0.1**: technical or scope reason for deferral
- **Promotion signal**: the empirical bar that would convert this
  Known Gap into a real roadmap item

The promotion signal is the most important field.  Without it, this
file degenerates into a wish list.  A gap should only sit here as
long as we do NOT yet have empirical evidence that it must be built;
once the promotion signal triggers, the entry is moved to PLAN
Implementation Tasks (for next-version scope) or to Out of Scope
(explicit decision not to build).

---

## Gap 1: Per-plan mechanical detection of review-loop trap

**What is missing**: a mechanical check that detects when a plan
under audit is degenerating into a review-trail rather than a spec.
Concrete signals would include: R-tag count growing over successive
runs of the same plan, Implementation Tasks completion ratio
stagnating across runs, polish-only edits dominating commits over a
defined window.

**Why it matters**: forge-code v2.0 Phase 2 took 50+ rounds of AI
panel review without producing code (recorded in feedback memory
`feedback_ai_review_strategic_limits.md`).  This exact anti-pattern
is the failure mode plan-forge is positioned to surface.  PM5 in
PLAN.md addresses this risk for plan-forge's OWN development as a
best-effort self-discipline pre-mortem, but plan-forge as a TOOL
has no mechanical detector for this pattern when auditing other
people's plans.  F5 R-tag pruner catches the cosmetic symptom (R-tag
overflow in a single SC), not the process-level pattern (review
rounds accumulating without code).

**Why it is not in v0.1**: detection requires either a corpus-db
history of the same plan across multiple runs (proper signal: review
rounds vs implementation progress over time) or out-of-band
integration with git / issue tracker (too invasive for v0.1).
v0.1 mechanical layer is stateless per-run; detecting this pattern
requires state that does not exist at v0.1 scope.

**Promotion signal**: 3+ documented cases in corpus_db (after v0.1
ships) where a plan passed plan-forge audit but in retrospect (T19 /
SC-3 retroactive audit) was identified as having been in a review-
loop trap that plan-forge failed to surface.  Threshold mirrors the
corpus-driven prompt-evolution gate pattern documented for G10
prompt v1 promotion (PLAN.md lines 2400-2407).  Until that signal
fires, the cost of building this detector (corpus schema changes +
cross-run state + heuristic tuning) exceeds the expected value.

---

Add new gaps below this line.  Keep the four-field format consistent
so the file does not drift.  If a gap belongs in Out of Scope (we
have decided not to build it) or in Open Questions (it blocks a
decision now), move it there instead -- this file is the holding
area for "we know it is missing AND we have not yet decided".
