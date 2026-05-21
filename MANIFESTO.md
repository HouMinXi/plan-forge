# plan-forge MANIFESTO

**Read this BEFORE writing any code, modifying any check, or proposing any
feature for plan-forge.**

This document is the philosophical anchor of the project. It exists to prevent
drift back to "linter" thinking. If you implement plan-forge as a markdown
linter, you have failed regardless of what tests pass.

---

## 1. The Problem plan-forge Exists to Solve

AI text generation has crossed a threshold. AI can now produce plans that look
like plans: well-structured, properly formatted, with appropriate jargon, full
of confident assertions, internally consistent, and superficially defensible.

These plans are often not plans. They are visions wearing the costume of plans.

A plan, in the Popperian sense, is a falsifiable proposition: it must state
what conditions would prove it wrong. A vision is an aspirational narrative:
it cannot be wrong because it makes no testable claim. AI excels at producing
visions because vision-production is what next-token prediction does well:
plausible continuation of preceding tokens. AI struggles to produce plans
because plan-production requires committing to falsifiable claims, and
committing to falsifiable claims means accepting that the model can be wrong.

The economic and social consequences of vision-as-plan are growing. Product
roadmaps that contain no failure conditions get funded. Research grants that
contain no reference class get awarded. Migration plans that contain no
pre-mortem get approved. Architecture decisions that contain no risk
taxonomy get committed.

Plan-forge is the gate at the idea-to-plan boundary.

## 2. The Family

plan-forge is part of an intended family of gates:

```
   raw idea                          plan                          code                          deploy
       |                              |                              |                              |
       +---> [forge-idea]      +--------------+              +-------------+              +------------+
              (future)         | plan-forge   |              | forge-code  |              |  future    |
                               | (this)       |              | (v1.0+)     |              +------------+
                               +--------------+              +-------------+
                                      |                              |
                                      v                              v
                              epistemic gate                 engineering gate
                              (falsifiability                (mechanical + LLM
                              + risk taxonomy                review for code
                              + reference class               quality)
                              + pre-mortem)
```

Each gate is an INDEPENDENT product. plan-forge does not depend on forge-code.
forge-code does not depend on plan-forge. Both are sibling defenses against
AI-generated artifact pollution in their respective domains.

plan-forge's customers are anyone authoring a plan, draft, proposal, RFC,
ADR, migration plan, research grant, pitch deck, policy proposal, or roadmap
in a context where AI assistance is present. This is a broader user set than
forge-code (which targets developers reviewing code).

## 3. The Ten Epistemic Concerns

plan-forge enforces ten distinct epistemological checks (G1-G10). Each
derives from a published research tradition. Each is mandatory; none is
opt-in. Plans that fail any check are blocked, not warned. G9 + G10
were added per R1 cross-AI review when narrowing the LLM role to per-
SC / per-citation questions revealed two additional gaps: feasibility
anchoring and recursive evidence provenance.

| ID | Concern | Source |
|----|---------|--------|
| G1 | Reference Class Forecasting | Flyvbjerg, 2002. Plans must compare against similar-scope historical projects. |
| G2 | Risk Taxonomy (3-class) | Wucker (gray rhino) + Taleb (black swan). Plans must classify risks. |
| G3 | Pre-mortem Section (mandatory) | Klein, HBR 2007. Plans must imagine and document their own failure. |
| G4 | Probability Calibration | Tetlock, 2015. Plans must use numeric probabilities, not hedge words. |
| G5 | Antifragility Audit | Taleb, 2007. Plans must specify how they respond to chaos. |
| G6 | SC Falsifiability (per-SC measurability) | Popper, 1934. Every success criterion must have an explicit fail condition with a measurable predicate. |
| G7 | Scope Challenge (barbell) | Taleb meta + project hygiene. Plans must justify their existence and avoid mediocre middle ground. |
| G8 | Source Diversity (per-citation resolvability) | Tetlock + observation that AI training corpora homogenize views. Plans must cite non-AI primary sources; each citation must resolve to a real publication. |
| G9 | Feasibility Anchor (per-anchor support) | Empirical-grounding commitment per Section 6 + replication-crisis literature (Open Science Collaboration 2015; Ioannidis 2005). Every quantitative claim must cite a real-world anchor (URL / project / prototype) whose data plausibly supports the claim magnitude. |
| G10 | Recursive Evidence Provenance | Section 6 + Section 12. Every LLM-cited evidence item must be classified into provenance tier T1-T4. Verdicts cannot stand on T3/T4-only chains. |

The complementary mechanical layer (F1-F7) catches writing-style failures
empirically observed across 50+ rounds of cross-AI review on forge-code v2.0
Phase 2. These are necessary but not sufficient.

## 4. Architectural Commitments

### 4.1 Internalize, don't reference

Plan-forge implements its check logic directly. It does NOT subprocess-invoke
other tools or skills. It does NOT depend on Claude Code skill discovery. It
does NOT depend on a specific LLM provider being available.

Reason: a tool that depends on other tools inherits their failures. A
standalone tool with internalized logic has a clear contract and a single
chain of accountability.

Other tools may CALL plan-forge as a library. Plan-forge does not call them.

### 4.2 Library first, adapters second

The primary deliverable is a Python library exposing `check(plan_text) ->
Verdict`. The library has no IO, no subprocess calls, no skill dependencies.

Adapters wrap the library for specific contexts:
- Claude Code skill (for interactive review during writing)
- CLI (for CI and batch retroactive audits)
- Future: pre-commit hook, GitHub Action, editor LSP server, web UI

Reason: a tool with a clean library at its core can be embedded anywhere. A
tool that is CLI-first or skill-first or UI-first has artificial dependencies
on its delivery channel.

### 4.3 Multi-LLM provider

Where plan-forge uses LLM judgment (G6 plan-vs-vision, G8 AI-smell detection),
it calls multiple providers and votes. Default: Anthropic + Kimi + DeepSeek +
Mimo. Graceful degradation if some are unavailable. Mechanical-only fallback
if fewer than 2 providers respond.

Reason: single-provider judgment inherits that provider's training bias. The
specific failure plan-forge is designed to prevent (AI-generated plans
passing AI review) cannot be solved by adding more single-provider AI review.

### 4.4 Self-dogfood

Plan-forge's own plan must pass plan-forge before any code ships. The PLAN.md
file in `.planning/` is itself a plan-forge artifact subject to plan-forge
enforcement.

Recursive validation prevents the most basic failure mode: a tool for
enforcing plan discipline that was itself authored without discipline.

## 5. Anti-Goals

The following are explicitly NOT what plan-forge is or will become:

- **NOT a markdown linter.** prettier, markdownlint, vale exist. plan-forge
  is not in that category. If a feature request is "add rule for X
  formatting," it is out of scope.

- **NOT a writing-style helper.** Hemingway, Grammarly, ProseLint exist.
  plan-forge does not coach prose quality. Hedge-word detection (G4) is
  specifically about probability calibration, not stylistic preference.

- **NOT a productivity accelerator.** plan-forge intentionally makes plan
  authoring SLOWER. The point of a gate is to insert friction at a moment
  where friction prevents downstream cost.

- **NOT a substitute for human judgment.** plan-forge can detect structural
  patterns that correlate with vision-disguised-as-plan. It cannot replace a
  reviewer who deeply understands the domain.

- **NOT optional.** If a user can bypass plan-forge by adding a CLI flag or
  unchecking a box, plan-forge has failed. Opt-in falsification gates do not
  work; see the GSD skill suite for empirical evidence (gsd-list-phase-
  assumptions exists but is rarely used).

- **NOT scope-creeping.** plan-forge will not add features for code review,
  meeting notes, project tracking, time estimation, or any adjacent concern.
  The boundary is the plan document itself.

## 6. What plan-forge Refuses to Compromise On

Three commitments are non-negotiable. Any v0.x or v1.x that breaks them is
not plan-forge.

### Commitment 1: G1-G10 are gates, not suggestions

Every G is a hard fail. Plans that lack a Pre-mortem section do not get a
warning; they get FAIL. Plans that lack a Reference Class section do not
get a warning; they get FAIL.

The point is to make missing sections impossible to ship. A reviewer's job
is then narrow: read the sections that exist and judge their quality. A
reviewer should never need to ask "did you do a pre-mortem?"

### Commitment 2: Multi-source enforcement

G8 (Collective Bias / Source Diversity) requires at least one non-AI
primary source per plan. This is enforced. Plans that contain only AI-
generated reasoning will fail.

Rationale: AI training corpora homogenize views. The collective bias
externality is exactly the failure mode at the idea-stage that plan-forge
defends against at the plan-stage.

### Commitment 3: Empirical grounding

Plan-forge's check thresholds and behaviors derive from observed data, not
theory alone. The corpus of forge-code v2.0 Phase 2 review (50+ rounds, 7
documented anti-patterns) anchors the mechanical layer. Future plans
audited through plan-forge feed back into corpus expansion.

If a check produces 0 catches across 10+ audits, it is removed. If a check
produces a pattern of catches consistent with a new anti-pattern, the new
pattern is documented and the check is strengthened.

## 7. Sources of Authority

Primary written sources cited (not AI-derived):

- Popper, *The Logic of Scientific Discovery* (1934)
- Klein, "Performing a Project Premortem", Harvard Business Review (2007)
- Kahneman & Tversky, "Intuitive Prediction: Biases and Corrective Procedures"
  (1979) -- planning fallacy origin
- Wucker, *The Gray Rhino* (2016)
- Taleb, *The Black Swan* (2007); *Antifragile* (2012)
- Tetlock & Gardner, *Superforecasting* (2015)
- Flyvbjerg et al., "Underestimating Costs in Public Works" (2002)
- Travassos et al., "Reading Techniques for OO Design Inspections" (2001)
- IEEE 830 (specifications quality attributes)
- Fagan, M., "Design and Code Inspections to Reduce Errors in Program
  Development", IBM Systems Journal (1976)

Corpus of empirical anti-patterns observed:

- 7 writing-style anti-patterns from forge-code v2.0 Phase 2 review (50+
  rounds across 6 sub-plans). Documented in
  `~/.claude/projects/-home-houminxi/memory/project_forge_plan_gate_corpus.md`
  and reproduced in `.planning/CORPUS.md` (TBD).
- 8 lessons documented in
  `~/code/forge/.planning/milestones/v2.0-phases/02-state-machine-rewrite/02-LEARNINGS.md`.

## 8. Maintenance Discipline

If you propose a new check (G9, G10, ...), you must:

1. Cite a primary written source (paper, book, standard). AI-derived
   justifications are not accepted (G8 self-application).
2. Show at least 3 empirical cases where the check would have prevented a
   real-world failure.
3. Demonstrate the check has measurable false-positive and false-negative
   rates on the existing corpus.
4. Convince two of three external LLM panels (Anthropic + Kimi + DeepSeek
   + Mimo, pick 3) that the check is non-redundant with existing G1-G10.

If you propose deleting an existing G, you must:

1. Show the G has produced fewer than 1 unique catch per 10 audits over 6
   months.
2. Confirm no production user depends on the G.
3. Migrate corresponding test fixtures to the deleted-checks archive.

If you propose making a G optional, the answer is no. See Commitment 1.

## 9. Failure Mode Acknowledgment

plan-forge can fail in specific ways. We acknowledge them publicly:

- **Ritualistic compliance**: users add the mandatory sections but fill them
  with empty boilerplate ("Pre-mortem: TBD"). G6 LLM judge partially defends
  by detecting empty sections. Long-term defense: A3 retroactive audit
  validates real bug catch; if 0 catches, plan-forge is theater and is
  abandoned.

- **False positives**: a real plan gets blocked because it has unconventional
  structure. Mitigation: inline `<!-- plan-forge: ack:G3 -->` marker to
  explicitly acknowledge a deviation with rationale. Use sparingly; counted
  in metrics.

- **LLM consensus on wrong verdict**: all four providers agree a vision is a
  plan. Mitigation: G7 scope-challenge mechanical check is independent of
  LLM. G1/G2/G3/G5/G7 are pure-Python. G6/G8 are the only LLM-dependent
  gates; if both fail simultaneously, mechanical layer still has 6/8
  coverage.

- **Tool obsolescence**: future LLM models natively perform G1-G10 reasoning,
  making plan-forge redundant. Mitigation: ship anyway. MANIFESTO + corpus
  + LEARNINGS are durable IP independent of tool layer.

## 10. The Test

If a future contributor reads this MANIFESTO and immediately begins
discussing markdown formatting rules, they have failed the test. The
correct first question is:

> What plan recently failed in a way G1-G10 would have caught? Was the
> failure real, or am I projecting?

Empirical evidence comes first. Theory follows.

## 11. Acknowledged Fundamental Limitation + Defense in Depth

plan-forge cannot fully solve the AI-detect-AI circularity. LLM-dependent
gates (G6 Part B, G8 Part B, G9 Part B, G10 Part B) inherit AI training
bias. Multi-provider vote reduces individual model bias but does not
eliminate collective AI training bias.

Defense in depth (6 independent layers):

**Layer 1 -- Mechanical checks** (6 of 10 G-checks + F1-F7 + PBR):
  pure-Python, independent of any LLM. Structural falsifiability without
  AI inference. G1/G2/G3/G5/G7 mechanical parts + G6/G8/G9 mechanical
  parts + G10 mechanical part.

**Layer 2 -- Narrow LLM role**:
  G4/G6/G8/G9 Part B and G10 Part B restricted to narrow technical
  questions (per-SC measurability, per-citation resolvability, per-
  anchor feasibility, per-evidence tier), NOT grand "is this plan or
  vision" judgments. Grand judgments are made by Layer 1 mechanical
  checks (a plan without reference class / pre-mortem / 3-class risks /
  scope-challenge is by construction a vision, no LLM needed).

**Layer 3 -- Multi-provider vote**:
  4 LLM providers (Anthropic, Kimi, DeepSeek, Mimo); majority required;
  ties produce "indeterminate" (not silent default). Web search via
  tool_use enabled per provider capability.

**Layer 4 -- Human arbitration**:
  when LLM evidence is sufficient (per-provider cited instances) and
  verdict is split, decision elevates to human. LLM is evidence-
  gatherer, human is final arbiter. Mode configurable:
  `on_split_evidence_rich` (default), `on_split`, `always`, `off`.

**Layer 5 -- Independent ground truth corpus**:
  SC-3 retroactive audit validates against forge-code Phase 2
  LEARNINGS.md (documented pre-plan-forge by 50+ rounds of failure).
  corpus_db accumulates more independent ground truth over time.
  Outcomes table tracks predicted vs actual failure modes; plan-forge's
  own quality is measured by its prediction accuracy, not by its
  internal consistency.

**Layer 6 -- Empirical track record** (practice is the only test):
  each plan-forge run is recorded to corpus_db. Post-hoc, predicted
  failure modes are tracked against actual outcomes. If 6 months pass
  with no outcomes recorded, plan-forge has not been tested by practice
  and is abandoned per Section 6 (empirical grounding commitment).
  Self-falsifying clause: SC-19.

What plan-forge does NOT claim: it does not perfectly distinguish AI
plans from human plans. It detects plans that lack mechanical evidence
of falsifiability discipline, regardless of authorship. Some AI plans
pass; some human plans fail. plan-forge optimizes for plan QUALITY
using authorship-independent signals, then is empirically validated
by track record. Practice tests truth.

## 12. Recursive Epistemic Discipline

plan-forge applies its own epistemic standards to its own evidence.

When plan-forge's LLM gates (G4, G6, G8, G9) cite web evidence via
search, that evidence itself must meet G10 provenance tier criteria.
Without this recursion, plan-forge has a leak: structured plan ->
unstructured evidence -> contaminated conclusion.

The SCI replication crisis (Open Science Collaboration 2015; Ioannidis
2005) demonstrates that publication != truth. A paper is trustworthy
only after independent replication. plan-forge's LLM-fetched evidence
must clear the same bar.

Tiering applied:
- T1 GOLD: primary + 3+ replications -> VERIFIED inputs allowed
- T2 SILVER: primary + few replications -> VERIFIED with warn
- T3 BRONZE: unverified / aggregator -> WARN; insufficient sole basis
- T4 SUSPECT: AI-content / retracted / contradicted -> REJECT

A plan-forge verdict whose chain of evidence relies only on T3/T4
cannot stand. The verdict re-runs with stronger evidence or is
escalated to human arbitration (Layer 4 in Section 11).

This is NOT optional. Every LLM gate output is post-processed by G10
classification. corpus_db records tier per evidence cell.

Recursion depth cap: 2 (LLM evidence -> G10 classification -> G10's
own evidence classified once, no further). Beyond depth 2, escalate
to human. This bounds the infinite regress while preserving the
discipline for the most-cited evidence chains.

---

**Authoritative version**: this MANIFESTO is updated only when:
1. A new G-check is added (Section 8 process).
2. An architectural commitment is reviewed and explicitly modified.
3. A failure mode is upgraded from acknowledged to addressed.

All updates are git-traceable. Re-read this document at the start of any
major feature or refactor.

Author: Minxi Hou <houminxi@gmail.com>
Drafted: 2026-05-18
