# plan-forge v0.1 PLAN

**Phase**: 0 (greenfield)
**Status**: Draft post-R3-fixes; ready for R4 cross-AI review OR T05 implementation start (per descope decision at week-5 checkpoint)
**Drafted**: 2026-05-18; R1-fixes 2026-05-19; R2-fixes 2026-05-19; R3-fixes 2026-05-19
**Author**: Minxi Hou <houminxi@gmail.com>
**Repository**: ~/code/plan-forge (git init complete)
**Depends on**:
- Python 3.11+
- Anthropic SDK (`anthropic`), Kimi/DeepSeek/Mimo SDKs (with `tool_use` /
  function-calling support for LLM web search per E1)
- SQLAlchemy 2.0 + Alembic (corpus_db event-sourcing layer per H2)
- pytest for tests
- jinja2 for scaffold templates
- httpx (LLM HTTP transport; tool_use web search)
- No internal dependencies; no other Claude Code skills called as subprocess

**Required reading before review**:
- `MANIFESTO.md` (this repo) -- philosophical anchor; non-negotiable
  principles; includes Section 11 (Acknowledged Fundamental Limitation +
  Defense-in-Depth) and Section 12 (Recursive Epistemic Discipline) added
  per R1 review
- `/tmp/plan_falsification_synthesis.md` -- epistemological framework
  (Popper / Klein / Wucker / Taleb / Tetlock / Flyvbjerg) the G1-G10
  checks derive from
- `~/.claude/projects/-home-houminxi/memory/project_forge_plan_gate_corpus.md`
  -- 7 writing-style anti-patterns observed across 50+ rounds of forge-code
  v2.0 Phase 2 review (informs F1-F7 mechanical checks)
- `~/code/forge/.planning/milestones/v2.0-phases/02-state-machine-rewrite/02-LEARNINGS.md`
  -- empirical lessons that motivate G1-G10 mandate; serves as INDEPENDENT
  ground-truth corpus for SC-3 retroactive audit (this file pre-dates
  plan-forge)
- `.planning/R1-REVIEW-SUMMARY.md` (to be written T03b) -- summary of
  R1 cross-AI review BLOCKER consensus and applied fixes

## Goal

Ship plan-forge v0.1 as a standalone Python library + Claude Code skill +
CLI that enforces TEN epistemological gates (G1-G10) and seven mechanical
writing-style checks (F1-F7) on plan documents, backed by an append-only
corpus_db audit ledger, multi-provider LLM with web search, human
arbitration on LLM-split-with-evidence, and a self-falsifying abandonment
clause.

Primary deliverable: `from plan_forge import check; verdict =
check(plan_text)` returns a `Verdict` dataclass with two sub-verdicts:
`engineering_verdict` (PASS / FAIL) and `epistemic_verdict` (PASS / FAIL /
VISION). Either FAIL or VISION blocks the plan from "READY" state. Every
run is persisted to corpus_db. Outcomes (predicted vs actual failure
modes) are recorded post-hoc to validate plan-forge's own track record
per MANIFESTO Section 6 (empirical-grounding commitment).

Acceptance (SC-3, revised per R1 B5 fix): plan-forge v0.1 mechanical +
LLM gates run retroactively on 02-01..02-06 forge-code Phase 2 archived
plans, with detection coverage against the INDEPENDENT documented-problem
list in `02-LEARNINGS.md` (drafted pre-plan-forge by 50+ rounds of AI
panel + manual extraction). Coverage = (problems_caught_by_plan_forge /
total_problems_in_02-LEARNINGS.md) >= 60%. Failure of this criterion
(< 60%) indicates plan-forge's epistemic foundation insufficient;
trigger redesign or abandon per MANIFESTO Section 6.

## Requirements

### Mechanical layer (F1-F7, pure Python, no LLM)

- **F1 SC-test traceability**: parse SC table + test list from plan; cross-
  reference. Orphan SC (claims test but no matching test entry) or orphan
  test (test exists but no SC references it) reported.
- **F2 Duplicate-fact lint**: tokenize plan into noun phrases; count
  occurrences. Phrases appearing in 3+ sections flagged with single-source-
  of-truth recommendation.
- **F3 Cross-plan invariant verification**: regex extract claims about
  other plans/modules (patterns: `phase-\d+`, named upstream symbols,
  `02-\d+`). Each claim must have grep evidence in plan body or audit-
  notes section.
- **F4 Temporal anchor lint**: regex finds `before|after` adjacent to
  `return|exit|complete`. Require precise anchor specification
  (`__exit__`, `return statement executed`, `caller assignment`).
- **F5 R-tag pruner**: count inline `R\d+ [BHM]\d+` style tags per SC
  entry. Cap at 2; excess must move to CHANGELOG section.
- **F6 Preamble-vs-body diff**: when an orchestrator preamble
  (conversation context) is provided alongside plan, compare for facts
  present in preamble but absent from plan body.
- **F7 ASCII / non-ASCII grep**: detect non-ASCII characters added in
  plan (em dash, smart quotes, arrows). Equivalent to forge CLAUDE.md
  Step 0c.

### PBR layer (P1/P2/P5/P6, pure Python, no LLM)

Perspective-Based Reading checks derived from Travassos OO inspection
taxonomy and IEEE 830 quality attributes. Internalized per MANIFESTO
Architectural Commitment 1; no subprocess calls to `plan-review` skill.

- **P1 Symbol closure**: every identifier introduced in plan body
  (module names, function names, table names, SC IDs, T-task IDs) must
  be either defined in plan OR explicitly cross-referenced to upstream
  artifact. Orphan identifier (used but neither defined nor cross-
  referenced) reported. Detection: build identifier graph; flag nodes
  with no defining edge.
- **P2 Null propagation**: optional fields and nullable returns in
  module designs must have explicit null-handling semantics. Detection:
  regex `: \w+ \| None` in code blocks; require corresponding "if X is
  None" branch in caller's pseudocode OR explicit "non-null invariant
  enforced by ..." comment. Orphan optional (declared but never
  null-checked) reported.
- **P5 Interface symmetry**: every public API method introduced in
  Module Designs must appear in either Implementation Tasks (T-row
  output column) or Architecture data-flow diagram. Symmetric: every
  T-row output method must trace back to Module Designs. Asymmetry
  reported.
- **P6 Metadata currency**: PLAN's frontmatter fields (Drafted, Phase,
  Status, Depends on) cross-checked against in-body claims. E.g., if
  body says "R1 fixes integrated 2026-05-19" but frontmatter still
  says "Drafted 2026-05-18", metadata-stale finding raised. Detection:
  regex extract dates/versions from frontmatter and body; diff.

PBR checks run as part of `checks.mechanical.run`; same Finding
schema; same severity grading.

### Epistemological layer (G1-G10, mechanical + narrow LLM)

Per R1 B3 fix: LLM role is restricted to narrow technical questions
(per-SC measurability, per-citation resolvability, per-anchor
feasibility, per-evidence tier), NOT grand "is this plan or vision"
judgment. Grand judgments are made by mechanical G7 + G3 + G2 + G1 (a
plan without reference class / pre-mortem / 3-class risks / scope-
challenge is by construction a vision, no LLM needed).

- **G1 Reference Class Forecasting** (mechanical): plan must contain
  `## Reference Class` section with 2+ historical similar-scope projects,
  each with (name, scope, actual duration, plan-vs-actual ratio).
  Outside-view estimate computed. Inside-view-only estimate flagged.

- **G2 Risk Taxonomy 3-class** (mechanical): plan must contain `## Risks`
  section with three subsections: `### Known Risks`, `### Gray Rhinos`,
  `### Black Swans`. Gray Rhinos must have `denial_reason` field. Black
  Swans must have `survival_plan` field. All-in-one bucket or empty Gray
  Rhinos = FAIL.

- **G3 Pre-mortem MANDATORY** (mechanical): plan must contain `## Pre-
  mortem` section with at least 5 ranked failure causes, each with
  `early_warning` field and `counter` field.

- **G4 Probability Calibration** (mechanical + narrow LLM):
  - Part A (mechanical, primary): hedge words (English canonical set:
    `maybe / likely / probably / perhaps / possibly / seems /
    appears / should / could / might / may`; Chinese hedge regex via
    Unicode) flagged. Each hedge instance must have either adjacent
    numeric probability (0-100%) OR explicit `<!-- plan-forge:
    hedge-ok -->` marker (with optional reason inside parens, e.g.,
    `<!-- plan-forge: hedge-ok (reviewer-question) -->`). Implementation
    note (Module Designs g4_calibration.py): regex SOURCE-OF-TRUTH is
    the 11-word list above; code regex MUST match this list exactly to
    avoid Requirements / code drift (P5 interface symmetry).
  - Part B (LLM, narrow with web search): for hedge instances WITHOUT
    numeric probability, LLM looks up domain reference data via web
    search and asks "is there empirical anchor for the implicit
    probability claimed by this hedge?" If LLM returns
    RESOLVED_VIA_SEARCH (T1/T2 tier per G10) with measurable anchor,
    finding downgraded from BLOCKER to MEDIUM warning.

- **G5 Antifragility Audit** (mechanical): plan must contain `## Chaos
  Response` section with 3 stressor scenarios. Per-scenario
  classification: benefit / survive / degrade / break. All scenarios
  "break" = FAIL.

- **G6 SC Falsifiability** (mechanical + narrow LLM):
  - Part A (mechanical, primary): every SC entry must have explicit
    fail-condition column. Plans without per-SC fail-conditions FAIL.
  - Part B (LLM, narrow with web search): per SC, multi-LLM majority
    vote on the narrow technical question "does this SC's fail-
    condition specify a measurable predicate (concrete observable
    state + detection procedure)?" Per-SC VERIFIED or UNVERIFIED. If
    > 30% of SCs UNVERIFIED, finding raised. Web search permitted so
    LLM can verify whether the claimed threshold (e.g., "p99 latency
    < 50ms") is plausible vs absurd given domain reference data.
  - The broad "plan vs vision" judgment is enforced PRIMARILY by G7 +
    G3 + G2 + G1 mechanical, not by G6 LLM.

- **G7 Scope Challenge / Barbell** (mechanical): plan must contain
  `## Scope Challenge` section answering Q1-Q4: (does this need to
  exist? + 3 real consumers OR public-artifact alternative + do-nothing
  cost quantified + barbell vs middle-ground check).

- **G8 Source Diversity** (mechanical + narrow LLM with web search):
  - Part A (mechanical, primary): `## External Voices` section + 1
    non-AI primary source + 1 dissenting view addressed + 1 historical
    failure case + citation regex.
  - Part B (LLM, narrow with web search): per citation, LLM verifies
    via web search "does this citation resolve to a real publication
    (author + title + year + venue consistent and findable)?" Tiers per
    G10 + E3: RESOLVED_VIA_SEARCH / RESOLVED_BY_KNOWLEDGE / UNCERTAIN
    (surface to human per H1) / UNRESOLVABLE (FAIL). Fabricated
    citations (verified false via search) trigger BLOCKER finding.

- **G9 Feasibility Anchor** (mechanical + narrow LLM with web search,
  NEW per R1 E2):
  - Part A (mechanical, primary): every quantitative claim or timeline
    projection in plan must cite a real-world anchor (URL,
    publication, comparable project name, or empirical prototype
    reference). Plans with quantitative claims lacking anchor = FAIL.
    Acceptable anchor formats: `[anchor: <url>]`, `[anchor: <project-
    name>, <duration>]`, `[anchor: prototype, <result-summary>]`,
    `[anchor: <in-plan-derivation-pointer>]` (for claims whose anchor
    is a derivation table or formula elsewhere in the same plan).
  - Canonical-declaration convention (per R4 S1 fix): each unique
    quantitative claim has ONE canonical declaration carrying the
    full inline `[anchor: ...]`. Downstream references to the same
    number (e.g., "as discussed earlier the 16-week estimate")
    do NOT require their own anchor as long as they are
    grammatically clear back-references to the canonical. Parser
    deduplicates by claim-value + adjacency to noun phrase
    referencing the canonical section. The mechanical implementation
    in `g9_feasibility_anchor.py` builds the canonical-anchor set
    in pass 1 and silences downstream-reference findings in pass 2.
  - Part B (LLM, narrow with web search): per anchor, LLM verifies via
    web search that the cited anchor (a) URL resolves OR project named
    is real AND (b) anchor data plausibly supports the claim
    (magnitude / units / context). E.g., a "Phase 2 takes 2 weeks"
    claim anchored to "ruff scaling phase took 8 weeks" is plausible
    (both phases of similar lint-tool maturation); same claim anchored
    to "Twitter rewrite took 6 months" is NOT plausible (different
    category). LLM verdict per anchor: SUPPORTS / WEAK_SUPPORT /
    CONTRADICTS / UNVERIFIABLE.
  - G9 mechanical = "anchor section/citation exists per claim"; G9 LLM
    = "anchor actually supports the magnitude claimed".
  - Rationale: forge-code v2.0 Phase 2 was estimated "~2 weeks" without
    any reference-class anchor; actual was 1 week + 50 rounds of AI
    panel + 5 strategic interventions. G9 would have FAIL'd the Phase
    2 plan pre-execution.

- **G10 Recursive Evidence Provenance** (mechanical + narrow LLM with
  web search, NEW per R1; addresses B3 leak):

  All LLM-fetched evidence (used by G4/G6/G8/G9 Part B and G10 itself)
  must be classified by provenance tier. Tier criteria:

  | Tier | Criteria |
  |------|----------|
  | T1 GOLD | Primary source verified + 3+ independent replications/citations from non-co-authors + no retraction + no major dissent |
  | T2 SILVER | Primary source verified + 1-2 replications OR widely cited but not yet replicated + no retraction + minor dissent OK |
  | T3 BRONZE | Secondary aggregator (blog/news summary) OR primary verified but no replications OR cannot find replications |
  | T4 SUSPECT | AI-generated content suspected (per anti-ai-audit heuristic) OR retracted / formally contradicted OR primary URL fails to resolve OR replicators contradict |

  - Part A (mechanical, primary): for every LLM evidence cell in
    corpus_db, schema column `tier` must be filled (T1-T4) by post-
    processing. Empty tier = invalid evidence; finding raised.
  - Part B (LLM, narrow with web search): tier classifier prompt
    inputs each evidence item and outputs tier + replication_urls +
    verifiability per E3.
  - Hard fail: any plan-forge verdict (FAIL or VISION) whose
    underlying evidence chain relies SOLELY on T3/T4 evidence (without
    T1/T2 corroboration). Such verdicts re-run with stronger evidence
    requirement OR escalate to human arbitration per H1.
  - Recursive application: G10 evaluates evidence used by G4/G6/G8/G9
    AND evidence used by G10 itself in the next tier-classification
    round. Recursion depth cap: 2 (LLM evidence -> G10 classification
    -> G10's own evidence classified once, no further). Beyond depth
    2, escalate to human.
  - **Descope coupling** (R3 LOW-3): G10 is a no-op when ALL of
    G4/G6/G8/G9 Part B are descoped (e.g., week-5 descope path
    drops LLM web search entirely). In that case, the code path
    short-circuits: `g10_evidence_tier.run(empty_evidence_rows)`
    returns no findings; tier_summary shows `{"UNCLASSIFIED": 0}`
    rather than empty dict. Documented in g10_evidence_tier.py
    docstring; not a v0.1 bug.

### Corpus / Audit layer (NEW per R1 H2)

- **corpus_db**: append-only SQLite event-sourcing ledger. Every
  plan-forge run is recorded. Schema (6 tables) defined in Module
  Designs section. Privacy: opt-in `--corpus-private` redacts
  `plan_text` but preserves `plan_hash` for traceability. Scope of
  flag: applies ONLY to `plan-forge check` and `plan-forge audit-
  retroactive` subcommands (the two that ingest plan content);
  `plan-forge scaffold`, `record-outcome`, and `abandonment-check`
  ignore the flag (they do not write plan_text). Adapter A (library)
  passes equivalent kwarg `corpus_private=True`. Default OFF (plan_text
  stored verbatim for full audit replay).

### Arbitration layer (NEW per R1 H1)

- **Human arbitration**: when LLM gate outputs split (e.g., 2-2 tie or
  3-1 with the minority providing strong per-instance evidence) AND
  evidence is "rich" (every provider cited >= 1 concrete instance per
  finding), arbitration is triggered. Adapter B (skill) surfaces the
  evidence bundle to the human user in Claude Code chat; user provides
  verdict + rationale; result persisted to `arbitrations` table.
- Modes: `always` / `on_split` / `on_split_evidence_rich` (DEFAULT) /
  `off`. User-configurable per `check(..., arbitration_mode=...)`
  call or CLI flag `--arbitration-mode`.

### Outcomes layer (NEW per R1 H3)

- **outcomes table**: tracks post-hoc validation. After a plan-forge
  verdict, the user records (manually or via tooling) whether
  predicted failure modes actually manifested. Outcome types:
  `predicted_manifested` / `predicted_did_not_manifest` /
  `unpredicted_occurred` / `plan_succeeded`. Empirical track record
  drives plan-forge's own quality metric per MANIFESTO Section 6.
- **Self-falsifying abandonment clause** (SC-19): if 6 calendar months
  pass with 0 outcomes recorded, `tools/abandon.py` generates
  `ABANDONMENT.md` tombstone with revival criteria. plan-forge tagged
  `v0.x.y-abandoned`. Tool not maintained until revival criteria met.
  corpus_db preserved for future revival.

### LLM web search layer (NEW per R1 E1)

- All LLM gate calls (G4/G6/G8/G9 Part B + G10 Part B) MAY use the
  provider's tool_use / function-calling web search capability.
  Anthropic, Kimi, DeepSeek support tool_use; Mimo support verified at
  T10 implementation (if not supported, Mimo runs in
  `no_search_judgment` degraded tier per E3 verdict tag).
- Each LLM call's prompt is allowed up to N (default 3) search calls.
  Search queries + results + URLs are persisted to corpus_db
  `llm_evidence.search_evidence` JSON column.
- Cost cap per plan (revised per R3 RN-6 honest recalibration):
  - **Plan-size-aware cost projection**: cost scales with SC count,
    citation count, anchor count. Formula:
    ```
    projected = base + (sc_count * 0.020) + (citation_count * 0.015)
              + (anchor_count * 0.020)
    base = 0.20  # G1-G3 + G5 + G7 mechanical overhead (cached LLM
                 # for hedge anchor verification)
    ```
    For typical 10-SC plan with 8 citations + 5 anchors: projected
    = 0.20 + 0.20 + 0.12 + 0.10 = $0.62 -> median $0.75 envelope
    plausible.
    For 28-SC plan-forge PLAN itself with ~25 citations + ~15
    anchors: projected = 0.20 + 0.56 + 0.375 + 0.30 = $1.44 ->
    sits between soft and hard cap; expected to often trigger
    fallback on G10 recursive layer for the largest plans.
  - **Soft cap (median target)**: $0.75/plan [anchor: plan-size-aware
    cost projection formula above evaluated at typical 10-SC plan +
    8 citations + 5 anchors = $0.62; soft envelope = projected + 20%
    headroom] for typical plans (<= 10 SC). SC-14 measures median
    across 10 SAMPLE plans which are intentionally typical-sized;
    large plans are NOT expected to hit soft cap.
  - **Hard cap (per-run abort)**: $2.00/plan [anchor: plan-size-aware
    formula at 28-SC + 25 citations + 15 anchors = $1.44; hard ceiling
    = projected + 40% headroom = $2.00 absolute; ref: large-plan
    operating budget per R3 RN-6 derivation] ABSOLUTE CEILING.
    Triggers mechanical-only fallback with explicit warning and
    corpus_db `actual_cost_usd` recorded. For large plans (~28 SC),
    $2.00 IS the expected operating budget, NOT an emergency cap.
  - **Override**: env var `PLAN_FORGE_COST_CAP_USD` and CLI flag
    `--cost-cap <usd>` permit raising up to $5.00. Beyond $5.00
    requires `--allow-runaway-cost` explicit confirmation.
  - **Rationale (R3 history)**: original $0.50 (R1) -> $0.75 soft
    (R2) -> $0.75 soft + $2.00 hard with size-aware projection (R3).
    DS R3 NI-6 correctly noted that 28-SC plan-forge self-audit
    cannot fit in $0.75 even with cache. Honest: large plans use
    $2.00 hard cap as operating budget; soft cap applies to typical
    plans only.

### Verdict layer

- Output: `Verdict(engineering_verdict, epistemic_verdict, findings,
  corpus_run_id, arbitration_triggered, tier_summary,
  arbitration_resolution)`.
- `engineering_verdict`: PASS / FAIL (from F1-F7 + G6/G8/G9 mechanical
  parts + G10 mechanical part).
- `epistemic_verdict`: PASS / FAIL / VISION (aggregate of G1-G10 per
  rules below).
- Findings: list with severity (BLOCKER / HIGH / MEDIUM / LOW),
  location, message, fix_hint, llm_evidence_per_provider (if applicable),
  evidence_tier (T1-T4 if LLM-derived).
- `corpus_run_id`: PK from corpus_db `plan_runs` table; allows post-
  hoc inspection.
- `arbitration_triggered`: bool; if True, surface to user before
  returning verdict.
- `tier_summary`: dict counting evidence by tier (e.g.,
  `{"T1": 5, "T2": 12, "T3": 2, "T4": 0}`) for audit visibility.
- `arbitration_resolution`: str | None; human verdict if arbitration
  occurred.

#### Epistemic verdict aggregation rules (PASS / FAIL / VISION)

Per R2 H-A fix: G6 LLM role narrowed to per-SC measurability (not
grand plan-vs-vision judgment). VISION verdict now derives from
mechanical G1-G7 structural absence, not LLM opinion.

**VISION triggers** (any one sufficient):
1. G1 mechanical FAIL: `## Reference Class` section absent OR < 2
   projects listed OR no outside-view estimate computed.
2. G2 mechanical FAIL: `## Risks` section missing any of 3 subsections
   (Known / Gray Rhinos / Black Swans) OR Gray Rhinos lack
   denial_reason OR Black Swans lack survival_plan.
3. G3 mechanical FAIL: `## Pre-mortem` section absent OR < 5 failure
   causes OR any cause lacks early_warning or counter field.
4. G7 mechanical FAIL: `## Scope Challenge` section absent OR Q1-Q4
   any unanswered OR Q3 (do-nothing cost) not quantified.
5. G5 mechanical FAIL: `## Chaos Response` section absent OR < 3
   scenarios OR all 3 scenarios classified "break".

Rationale: a plan without reference class, pre-mortem, 3-class risk
taxonomy, scope challenge, or chaos response is by construction a
vision (lacks falsifiability structure), regardless of whether SCs
have fail-conditions. G6 LLM checks SC-level measurability; G1/G2/G3/
G5/G7 mechanical checks plan-level structure.

**FAIL triggers** (any one sufficient, takes precedence over VISION):
1. Any BLOCKER-severity finding from F1-F7 or PBR checks.
2. G6 mechanical FAIL: > 30% of SCs lack fail_condition column.
3. G6 LLM aggregate FAIL: > 30% of SCs flagged UNVERIFIED by LLM
   majority (per-SC measurability check).
4. G8 mechanical FAIL: `## External Voices` section absent OR missing
   non-AI source OR missing dissenting view OR missing failure case.
5. G8 LLM FAIL: > 1 fabricated citation confirmed via search (tier
   T4 UNRESOLVABLE with "search confirmed false").
6. G9 mechanical FAIL: quantitative claim without anchor citation.
7. G9 LLM FAIL: > 30% of anchors flagged CONTRADICTS by LLM majority.
8. G10 FAIL: any FAIL or VISION verdict whose evidence chain is
   solely T3/T4 (no T1/T2 corroboration).
9. G4 mechanical FAIL: > 10 hedge instances without numeric
   probability or explicit `<!-- plan-forge: hedge-ok -->` marker.

**PASS**: neither FAIL nor VISION triggered.

**Precedence**: FAIL > VISION > PASS. A plan that triggers both FAIL
and VISION conditions returns epistemic_verdict = FAIL (more specific
diagnosis).

### Adapters

- **Adapter A** (Python library): `from plan_forge import check`. Primary.
- **Adapter B** (Claude Code skill): `/plan-forge <path>` slash command.
  Primary for Minxi's daily workflow. Handles arbitration UI surface +
  human verdict capture.
- **Adapter C** (CLI): `plan-forge check <plan>`,
  `plan-forge audit-retroactive <dir>`, `plan-forge scaffold <name>`,
  `plan-forge record-outcome <run-id>`, `plan-forge abandonment-check`.
  Secondary; for CI and batch retroactive audits.
- Deferred to v0.2+: pre-commit hook, GitHub Action, LSP server, web UI.

## Architecture

### Six-layer defense (per MANIFESTO Section 11)

Aligned with MANIFESTO Section 11's enumerated 6 layers. Multi-provider
LLM vote is a distinct layer (L3) from narrow LLM role (L2) because
voting is the disagreement-detection mechanism that triggers L4 human
arbitration; without L3, L2 reduces to single-provider judgment and
L4 has no trigger condition.

| Layer | Component | LLM-dependent? | Function |
|-------|-----------|---------------|----------|
| L1 Mechanical | F1-F7 + G1/G2/G3/G5/G7 mechanical parts + G6/G8/G9 mechanical parts + G10 mechanical | NO | Structural falsifiability without AI inference (6 of 10 G-checks fully independent of LLM) |
| L2 Narrow LLM role | G4/G6/G8/G9 Part B + G10 Part B | YES | Narrow technical questions only (per-SC measurability, per-citation resolvability, per-anchor feasibility, per-evidence tier); NOT grand "plan or vision" judgment |
| L3 Multi-provider vote | search_vote across Anthropic/Kimi/DeepSeek/Mimo | YES (4 providers + tool_use web search) | Majority required; ties produce indeterminate; degraded providers excluded from denominator per M3-DS rule |
| L4 Human arbitration | arbitration/ subpackage + Adapter B UI | NO (human decides) | When LLM evidence rich and L3 vote split, decision elevates to human; mode configurable (default on_split_evidence_rich) |
| L5 Independent ground truth corpus | 02-LEARNINGS.md (forge Phase 2, pre-plan-forge) + corpus_db append-only ledger | NO | SC-3 retroactive audit validates against pre-existing failure record; corpus accumulates more independent ground truth over time |
| L6 Empirical track record + abandonment | outcomes table + ABANDONMENT.md generator + SC-19 self-falsifying clause | NO | Each run recorded; predicted vs actual outcomes tracked; 6 months without outcomes triggers ABANDONMENT.md tombstone with revival criteria |

### Top-level data flow

```
plan_forge.api.check(plan_text, llm_clients=None,
                     arbitration_mode="on_split_evidence_rich",
                     corpus_db_path=None)
  |
  +-> parser.parse(plan_text) -> ParsedPlan
  |       (sections, SC table, risk register, hedge words, citations,
  |        anchors per G9)
  |
  +-> corpus.start_run(parsed_plan, llm_clients) -> run_id
  |       (creates plan_runs row, returns PK for evidence linking)
  |
  +-> checks.mechanical.run(ParsedPlan) -> List[Finding]
  |       F1-F7 + PBR P1/P2/P5/P6 + L1 portions of G1-G10
  |
  +-> checks.epistemic_llm.run(ParsedPlan, llm_clients, run_id)
  |        -> List[Finding]
  |       G4/G6/G8/G9 Part B (LLM with web search via llm.search_vote)
  |       Each LLM call: result + evidence + search_evidence persisted
  |       to llm_evidence table (with prompt_version column)
  |
  +-> checks.g10_evidence_tier.run(llm_evidence_rows, llm_clients)
  |        -> List[Finding]
  |       G10 Part B: tier-classify every evidence cell. Recursion
  |       depth 2 cap. Updates llm_evidence.tier column.
  |
  +-> arbitration.maybe_surface(findings, mode) -> bool
  |       If split + evidence_rich (and mode allows): surface bundle
  |       to user via Adapter B; capture verdict to arbitrations table
  |
  +-> verdict.compute(findings, run_id) -> Verdict
          engineering_verdict = max severity in (F + PBR + G mechanical)
          epistemic_verdict = aggregate(G1-G10 considering tier filter)
            -> PASS / FAIL / VISION
          (FAIL/VISION rejected if evidence chain is solely T3/T4)
          tier_summary computed; arbitration_triggered set
```

### Repository layout

```
~/code/plan-forge/
  MANIFESTO.md
  README.md
  ABANDONMENT.md             # generated by tools/abandon.py when SC-19 triggers
  pyproject.toml
  alembic.ini                # corpus_db migration config
  migrations/                # Alembic migration scripts
    env.py
    versions/
      0001_initial_schema.py
  src/plan_forge/
    __init__.py              # exports check, scaffold, Verdict, Severity
    api.py                   # public api impl
    parser.py                # markdown plan parser
    verdict.py               # Verdict + Finding + Severity dataclasses
    checks/
      mechanical/
        f1_sc_traceability.py
        f2_duplicate_fact.py
        f3_cross_plan_invariant.py
        f4_temporal_anchor.py
        f5_r_tag_pruner.py
        f6_preamble_body.py
        f7_ascii.py
      pbr/
        p1_symbol_closure.py
        p2_null_propagation.py
        p5_interface_symmetry.py
        p6_metadata_currency.py
      epistemic/
        g1_reference_class.py     # mechanical only
        g2_risk_taxonomy.py       # mechanical only
        g3_premortem.py           # mechanical only
        g4_calibration.py         # mechanical + narrow LLM Part B
        g5_antifragility.py       # mechanical only
        g6_sc_falsifiability.py   # mechanical + narrow LLM Part B
        g7_scope_challenge.py     # mechanical only
        g8_source_diversity.py    # mechanical + narrow LLM Part B
        g9_feasibility_anchor.py  # NEW: mechanical + narrow LLM Part B
        g10_evidence_tier.py      # NEW: mechanical + recursive LLM Part B
    llm/
      client.py                   # LLMClient Protocol (with tool_use)
      anthropic_client.py
      kimi_client.py
      deepseek_client.py
      mimo_client.py              # may degrade to no_search_judgment
      search_vote.py              # majority vote with web search + degradation
      tool_use.py                 # web search tool_use schema per provider
      prompts/
        g4_calibration_anchor_v0.txt
        g6_sc_measurability_v0.txt    # per R1 B4
        g8_citation_resolvability_v0.txt
        g9_feasibility_anchor_v0.txt  # NEW
        g10_evidence_tier_v0.txt      # NEW
      cache.py                    # SHA-256 (plan_hash, prompt_hash, model)
    corpus/                       # NEW: H2 corpus_db layer
      __init__.py
      db.py                       # SQLAlchemy engine + session
      schema.sql                  # raw DDL (also as Alembic migration)
      models.py                   # SQLAlchemy ORM models (6 tables)
      record.py                   # record_plan_run / record_finding /
                                  # record_evidence / record_arbitration /
                                  # record_outcome APIs
      query.py                    # corpus query helpers (by tier, by gate)
      redact.py                   # --corpus-private plan_text redaction
    arbitration/                  # NEW: H1 human arbitration layer
      __init__.py
      surface.py                  # decide_when_to_arbitrate(findings,
                                  #   llm_evidence, mode) -> bool
                                  # evidence_richness threshold algorithm
      bundle.py                   # build human-readable evidence bundle
      capture.py                  # capture human verdict ->
                                  # record_arbitration
    scaffold/
      __init__.py
      templates/
        default.md.j2             # plan skeleton with all G1-G10 sections
        roadmap.md.j2             # v0.1.5 candidate (per Open Q)
  adapters/
    skill/
      SKILL.md                    # /plan-forge slash command
      runner.py                   # invokes api.check + arbitration surface
    cli/
      __init__.py
      main.py                     # argparse + dispatch (5 subcommands)
  tools/                          # NEW: helper scripts
    abandon.py                    # generates ABANDONMENT.md when SC-19
                                  # triggers (6 months no outcomes)
    outcomes_cli.py               # `plan-forge record-outcome` impl
    retroactive_audit.py          # T19 driver
  tests/
    unit/
      test_f1.py through test_f7.py
      test_g1.py through test_g10.py
      test_pbr.py
      test_corpus_db.py
      test_arbitration.py
      test_g10_recursion_cap.py
    fixtures/
      pass_well_formed.md
      fail_missing_premortem.md
      fail_vision_disguised.md
      fail_all_known_risks.md
      fail_no_g9_anchor.md         # NEW
      fail_g10_t4_only_evidence.md # NEW
      prompts/
        g6_v0_pass.json            # expected LLM output for known PASS SC
        g6_v0_fail.json            # expected LLM output for known FAIL SC
        g8_v0_resolvable.json
        g8_v0_unresolvable.json
        g9_v0_supports.json
        g9_v0_contradicts.json
        g10_v0_t1.json
        g10_v0_t4.json
    integration/
      test_check_end_to_end.py
      test_corpus_persistence.py   # NEW
      test_arbitration_flow.py     # NEW
    dogfood/
      test_plan_forge_own_plan.py
  .planning/
    plan-forge-v0.1-PLAN.md        (this file)
    R1-REVIEW-SUMMARY.md           (R1 BLOCKER consensus + fixes; T03b)
    CORPUS.md                      (anti-pattern catalog, to be written)
    LESSONS-RETRO.md               (forge-code Phase 2 retroactive audit, T19)
```

### corpus_db location

Default: `~/.local/share/plan-forge/corpus.db` (XDG-compliant).
Override: `--corpus-db <path>` CLI or `corpus_db_path` API param.
Multi-user: each install has own DB; opt-in `--corpus-shared <path>`
points at shared SQLite over NFS for team aggregation (v0.2 candidate;
v0.1 single-user assumed).

## Module Designs

### parser.py

```python
from dataclasses import dataclass

@dataclass
class ParsedSection:
    heading: str
    level: int
    body: str
    line_start: int
    line_end: int

@dataclass
class ParsedSC:
    number: int
    name: str
    body: str
    fail_condition: str | None
    line: int

@dataclass
class ParsedRisk:
    bucket: str  # "known" / "gray_rhino" / "black_swan"
    description: str
    denial_reason: str | None
    survival_plan: str | None

@dataclass
class ParsedAnchor:
    # G9: per-claim anchor citation
    claim_text: str       # the quantitative claim
    anchor_text: str      # the cited anchor (URL / project name / prototype ref)
    anchor_type: str      # "url" / "project_name" / "prototype" / "publication"
    line: int

@dataclass
class ParsedPlan:
    raw_text: str
    sections: dict[str, ParsedSection]
    sc_table: list[ParsedSC]
    risks: list[ParsedRisk]
    hedge_word_locations: list[tuple[int, str]]  # (line, word)
    citations: list[str]
    ai_smell_phrases: list[tuple[int, str]]
    anchors: list[ParsedAnchor]                  # NEW per G9
    quantitative_claims_without_anchor: list[tuple[int, str]]  # G9 mechanical
```

### verdict.py

```python
from enum import Enum
from dataclasses import dataclass, field

class Severity(Enum):
    BLOCKER = "BLOCKER"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"

class EngineeringVerdict(Enum):
    PASS = "PASS"
    FAIL = "FAIL"

class EpistemicVerdict(Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    VISION = "VISION"

class EvidenceTier(Enum):
    T1_GOLD = "T1"
    T2_SILVER = "T2"
    T3_BRONZE = "T3"
    T4_SUSPECT = "T4"
    UNCLASSIFIED = "U"   # G10 has not yet run

@dataclass
class LLMEvidence:
    provider: str         # "anthropic" / "kimi" / "deepseek" / "mimo"
    model: str            # e.g., "claude-opus-4-7"
    verdict: str          # provider's individual verdict
    reasoning: str
    cited_instances: list[dict]   # [{"snippet": ..., "issue": ...}]
    search_evidence: list[dict]   # [{"query": ..., "result": ..., "url": ...}]
    prompt_version: str           # filename of prompt used
    run_id: int                   # FK to plan_runs; set by corpus recorder
    # tier filled by G10 post-processing; defaults to UNCLASSIFIED at
    # construction time so G4/G6/G8/G9 callers do not need to know G10
    # output schema. G10 may upgrade U -> T1/T2/T3/T4 (monotonic).
    tier: EvidenceTier = EvidenceTier.UNCLASSIFIED

@dataclass
class Finding:
    check_id: str         # "F1" / "G3" / "G6.mechanical" / "G6.llm" / etc.
    severity: Severity
    location: str
    message: str
    fix_hint: str
    llm_evidence: list[LLMEvidence] = field(default_factory=list)
    evidence_tier_summary: dict = field(default_factory=dict)

@dataclass
class Verdict:
    engineering: EngineeringVerdict
    epistemic: EpistemicVerdict
    findings: list[Finding]
    corpus_run_id: int | None             # PK in plan_runs table
    arbitration_triggered: bool
    tier_summary: dict                    # {"T1": N, "T2": N, "T3": N, "T4": N}
    arbitration_resolution: str | None = None  # "verified" / "unverified" / "deferred" / "abstain" (canonical 4-value vocab; matches arbitrations.human_verdict in corpus schema and bundle.py prompt)
```

### llm/search_vote.py

```python
def search_vote(
    clients: list[LLMClient],
    prompt: str,
    input_payload: dict,
    *,
    min_responders: int = 2,
    max_searches_per_call: int = 3,
    cost_cap_usd: float = 0.75,
) -> tuple[str, list[LLMEvidence], float]:
    """Multi-LLM majority vote with web search via tool_use.

    Each client runs prompt with tool_use enabled. Web search calls are
    capped at max_searches_per_call per client. Total cost is
    accumulated; if projected cost exceeds cost_cap_usd, remaining
    providers are skipped (graceful degradation).

    Returns:
        verdict: aggregated verdict ("verified" / "unverified" /
                 "split" / "indeterminate")
        evidence: list of LLMEvidence (one per responding provider)
        cost_usd: total cost of LLM + search calls

    Special verdict "split" indicates 2-2 tie or 3-1 with strong
    evidence on minority side; arbitration.surface() decides whether
    to escalate to human.

    Voting rules with degraded providers (R2 M3-DS fix):
    Providers that return "no_search_judgment" (e.g., Mimo without
    tool_use support; or any provider whose search call failed) DO
    NOT count toward the majority denominator. Concrete:

      - 3 providers vote "verified", 1 returns "no_search_judgment":
        majority is 3/3 = verified (degraded provider excluded).
      - 2 providers vote "verified", 1 votes "unverified", 1 returns
        "no_search_judgment": 3 effective voters; 2/3 majority for
        verified.
      - 2 providers degraded + 2 vote different: only 2 effective
        voters; verdict = "indeterminate" because min_responders=2 met
        but they disagree and no tiebreaker available.
      - All 4 degraded: verdict = "indeterminate" with cost = 0;
        triggers mechanical-only path for this gate.

    Degraded evidence rows ARE persisted to corpus_db with
    tier=UNCLASSIFIED for audit; they just do not vote. The Verdict's
    `tier_summary` includes a "degraded" count for visibility.
    """
```

### checks/epistemic/g4_calibration.py

```python
def check(
    parsed: ParsedPlan,
    llm_clients: list[LLMClient],
    run_id: int,
    corpus: CorpusRecorder,
) -> list[Finding]:
    findings: list[Finding] = []

    # G4 Part A (mechanical): hedge words must have numeric probability
    # or explicit <!-- plan-forge: hedge-ok --> marker
    hedge_regex = re.compile(
        r'\b(maybe|likely|probably|perhaps|possibly|seems|appears|'
        r'should|could|might|may)\b',
        re.IGNORECASE
    )
    marker_regex = re.compile(r'<!--\s*plan-forge:\s*hedge-ok\s*-->')
    numeric_prob_regex = re.compile(r'\b\d{1,3}%\b')

    # State machine: skip ENTIRE fenced code blocks, not just fence
    # lines. Per R3 RN-5: G4 false-positives on should/might/could
    # inside Module Designs pseudo-code Python blocks.
    in_code_block = False
    for line_num, line_text in enumerate(parsed.raw_text.splitlines(), 1):
        stripped = line_text.strip()
        # Toggle on any fence marker (```, ```python, ```sql, etc.)
        if stripped.startswith("```"):
            in_code_block = not in_code_block
            continue
        if in_code_block:
            continue
        # Skip G4 definition meta-context (self-reference exemption)
        if "G4 Probability Calibration" in line_text:
            continue

        hedges = hedge_regex.findall(line_text)
        if not hedges:
            continue
        
        # Check for exemption marker or adjacent numeric probability
        has_marker = marker_regex.search(line_text)
        has_numeric = numeric_prob_regex.search(line_text)
        
        if not has_marker and not has_numeric:
            findings.append(Finding(
                check_id="G4.A.mechanical",
                severity=Severity.MEDIUM,
                location=f"line {line_num}",
                message=f"hedge word(s) {hedges} without numeric probability or exemption marker",
                fix_hint="add adjacent numeric probability (e.g., '70%') or "
                         "<!-- plan-forge: hedge-ok --> if uncertainty is intentional",
            ))

    # Threshold: > 10 unexempted hedges = aggregate BLOCKER
    if len(findings) > 10:
        findings.append(Finding(
            check_id="G4.A.aggregate",
            severity=Severity.BLOCKER,
            location="plan",
            message=f"{len(findings)} hedge instances without calibration (>10 threshold)",
            fix_hint="calibrate probabilities or add exemption markers",
        ))

    # G4 Part B (narrow LLM with web search): for hedges WITHOUT numeric
    # probability, LLM searches for domain reference data and asks "is
    # there empirical anchor for the implicit probability?"
    # (Implementation deferred to v0.1.1 per descope; Part A sufficient for v0.1)

    return findings
```

### checks/epistemic/g6_sc_falsifiability.py

```python
def check(
    parsed: ParsedPlan,
    llm_clients: list[LLMClient],
    run_id: int,
    corpus: CorpusRecorder,
) -> list[Finding]:
    findings: list[Finding] = []

    # G6 Part A (mechanical): every SC must have fail_condition
    for sc in parsed.sc_table:
        if not sc.fail_condition:
            findings.append(Finding(
                check_id="G6.A.mechanical",
                severity=Severity.BLOCKER,
                location=f"SC-{sc.number}",
                message="missing fail_condition column",
                fix_hint="add 'FAILS if ...' clause to SC body",
            ))

    # G6 Part B (narrow LLM with web search): per-SC measurability
    prompt_template = load_prompt("g6_sc_measurability_v0.txt")
    prompt_version = "g6_sc_measurability_v0"
    unverified_count = 0

    for sc in parsed.sc_table:
        if not sc.fail_condition:
            continue  # already failed Part A; skip Part B
        payload = {
            "sc_id": sc.number,
            "sc_text": sc.name,
            "fail_condition_text": sc.fail_condition,
        }
        verdict, evidence, cost = search_vote(
            llm_clients,
            prompt_template,
            payload,
        )
        for ev in evidence:
            ev.prompt_version = prompt_version
            corpus.record_evidence(run_id, "G6.B", sc.number, ev)
        if verdict == "unverified":
            unverified_count += 1
            findings.append(Finding(
                check_id="G6.B.llm",
                severity=Severity.HIGH,
                location=f"SC-{sc.number}",
                message="LLM majority: fail-condition not measurable",
                fix_hint="strengthen with concrete state + procedure",
                llm_evidence=evidence,
            ))

    # Threshold: > 30% UNVERIFIED -> aggregate BLOCKER
    if parsed.sc_table and unverified_count / len(parsed.sc_table) > 0.30:
        findings.append(Finding(
            check_id="G6.B.aggregate",
            severity=Severity.BLOCKER,
            location="plan.sc_table",
            message=f"{unverified_count}/{len(parsed.sc_table)} SCs "
                    f"flagged as not measurable (>30% threshold)",
            fix_hint="rewrite SCs with concrete fail-conditions",
        ))

    return findings
```

### checks/epistemic/g9_feasibility_anchor.py

```python
def check(
    parsed: ParsedPlan,
    llm_clients: list[LLMClient],
    run_id: int,
    corpus: CorpusRecorder,
) -> list[Finding]:
    findings: list[Finding] = []

    # G9 Part A (mechanical): every quantitative claim must cite anchor
    for line, claim in parsed.quantitative_claims_without_anchor:
        findings.append(Finding(
            check_id="G9.A.mechanical",
            severity=Severity.BLOCKER,
            location=f"line {line}",
            message=f"quantitative claim without anchor: {claim!r}",
            fix_hint="add [anchor: <url|project|prototype>] citation",
        ))

    # G9 Part B (narrow LLM with web search): per-anchor feasibility
    prompt_template = load_prompt("g9_feasibility_anchor_v0.txt")
    prompt_version = "g9_feasibility_anchor_v0"

    for anchor in parsed.anchors:
        payload = {
            "claim_text": anchor.claim_text,
            "anchor_text": anchor.anchor_text,
            "anchor_type": anchor.anchor_type,
        }
        verdict, evidence, cost = search_vote(
            llm_clients,
            prompt_template,
            payload,
        )
        for ev in evidence:
            ev.prompt_version = prompt_version
            corpus.record_evidence(run_id, "G9.B", anchor.line, ev)
        if verdict in ("contradicts", "unverifiable"):
            findings.append(Finding(
                check_id="G9.B.llm",
                severity=Severity.HIGH if verdict == "contradicts"
                         else Severity.MEDIUM,
                location=f"line {anchor.line}",
                message=f"anchor {verdict}: {anchor.anchor_text!r}",
                fix_hint=("anchor data does not support claim magnitude"
                          if verdict == "contradicts"
                          else "anchor not verifiable via search; "
                               "provide stronger anchor"),
                llm_evidence=evidence,
            ))

    return findings
```

### checks/epistemic/g10_evidence_tier.py

```python
def run(
    llm_evidence_rows: list[LLMEvidence],
    llm_clients: list[LLMClient],
    corpus: CorpusRecorder,
    *,
    recursion_depth: int = 0,
    max_depth: int = 2,
) -> list[Finding]:
    """Recursive evidence provenance classifier.

    For each piece of LLM evidence used by G4/G6/G8/G9 (Part B), runs
    the G10 prompt to assign tier T1-T4. Recursively classifies the
    evidence used by G10 itself, up to max_depth=2. Beyond depth 2,
    escalates to human arbitration.
    """
    if recursion_depth >= max_depth:
        return [Finding(
            check_id="G10.recursion_cap",
            severity=Severity.MEDIUM,
            location="g10",
            message="recursion depth cap reached; escalate to human",
            fix_hint="arbitrate manually",
        )]

    findings: list[Finding] = []
    prompt_template = load_prompt("g10_evidence_tier_v0.txt")
    prompt_version = "g10_evidence_tier_v0"

    for ev in llm_evidence_rows:
        if ev.tier != EvidenceTier.UNCLASSIFIED:
            continue
        payload = {
            "evidence_text": ev.reasoning + " " + str(ev.cited_instances),
            "citing_gate": ev.provider,
            "context": ev.prompt_version,
        }
        # R4 T1 fix: Guard degraded providers BEFORE LLM call + tier
        # coercion to avoid spurious G10.tier_coercion Finding emission.
        # Degraded provider evidence (no_search_judgment) has no content
        # for G10 to classify; skip the entire classification path.
        if ev.verdict == "no_search_judgment":
            ev.tier = EvidenceTier.UNCLASSIFIED
            corpus.update_evidence_tier(ev)
            continue

        verdict, g10_evidence, cost = search_vote(
            llm_clients,
            prompt_template,
            payload,
        )
        # Safe tier assignment with fallback (R3 M-3 fix):
        # LLM may return malformed verdict despite prompt constraints.
        # Coerce to EvidenceTier; on failure default to T3 (BRONZE) and
        # emit a Finding for audit. Never crash on LLM string drift.
        try:
            ev.tier = EvidenceTier(verdict)
        except ValueError:
            ev.tier = EvidenceTier.T3_BRONZE
            findings.append(Finding(
                check_id="G10.tier_coercion",
                severity=Severity.LOW,
                location=f"evidence run_id={ev.run_id} provider={ev.provider}",
                message=f"LLM returned non-enum tier {verdict!r}; "
                        f"coerced to T3_BRONZE",
                fix_hint="check LLM prompt + provider's structured "
                         "output support; consider prompt v1",
            ))
        corpus.update_evidence_tier(ev)

        for sub_ev in g10_evidence:
            sub_ev.prompt_version = prompt_version
            corpus.record_evidence(ev.run_id, "G10.B", -1, sub_ev)

        # Recursively classify G10's own evidence
        sub_findings = run(
            g10_evidence,
            llm_clients,
            corpus,
            recursion_depth=recursion_depth + 1,
            max_depth=max_depth,
        )
        findings.extend(sub_findings)

    # T3/T4-only verdict check (hard fail per G10 requirement)
    t3_t4_only_findings = _detect_t3_t4_only_chains(llm_evidence_rows)
    findings.extend(t3_t4_only_findings)

    return findings
```

### corpus/schema.sql (event-sourcing, 6 tables)

```sql
-- Append-only event ledger per H2
-- All tables use TEXT primary keys for portable hashing where applicable

CREATE TABLE schema_version (
    version TEXT PRIMARY KEY,
    applied_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE plan_runs (
    run_id INTEGER PRIMARY KEY AUTOINCREMENT,
    plan_hash TEXT NOT NULL,                  -- sha256(plan_text)[:16]
    plan_text TEXT,                            -- nullable if --corpus-private
    plan_path TEXT,                            -- source path (may be /tmp)
    plan_forge_version TEXT NOT NULL,          -- e.g., "0.1.0"
    arbitration_mode TEXT NOT NULL,
    cost_cap_usd REAL NOT NULL,
    actual_cost_usd REAL,
    started_at TIMESTAMP NOT NULL,
    completed_at TIMESTAMP,
    engineering_verdict TEXT,                  -- "PASS" / "FAIL"
    epistemic_verdict TEXT                     -- "PASS" / "FAIL" / "VISION"
);

CREATE INDEX idx_plan_runs_plan_hash ON plan_runs(plan_hash);

CREATE TABLE findings (
    finding_id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id INTEGER NOT NULL REFERENCES plan_runs(run_id),
    check_id TEXT NOT NULL,                    -- "F1" / "G6.A.mechanical"
    severity TEXT NOT NULL,
    location TEXT NOT NULL,
    message TEXT NOT NULL,
    fix_hint TEXT
);

CREATE INDEX idx_findings_run_id ON findings(run_id);
CREATE INDEX idx_findings_check_id ON findings(check_id);

CREATE TABLE llm_evidence (
    evidence_id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id INTEGER NOT NULL REFERENCES plan_runs(run_id),
    gate_id TEXT NOT NULL,                     -- "G6.B" / "G8.B" / "G10.B"
    target_id TEXT,                            -- SC number / anchor line / etc.
    provider TEXT NOT NULL,
    model TEXT NOT NULL,
    prompt_version TEXT NOT NULL,
    verdict TEXT NOT NULL,                     -- provider's verdict
    reasoning TEXT,
    cited_instances TEXT,                      -- JSON array
    search_evidence TEXT,                      -- JSON array
    tier TEXT,                                  -- T1 / T2 / T3 / T4 (G10 output)
    g10_run BOOLEAN NOT NULL DEFAULT FALSE,
    cost_usd REAL,
    recorded_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_llm_evidence_run_id ON llm_evidence(run_id);
CREATE INDEX idx_llm_evidence_tier ON llm_evidence(tier);

CREATE TABLE arbitrations (
    arbitration_id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id INTEGER NOT NULL REFERENCES plan_runs(run_id),
    finding_id INTEGER REFERENCES findings(finding_id),
    triggered_at TIMESTAMP NOT NULL,
    bundle_text TEXT NOT NULL,                 -- the evidence bundle shown
    human_verdict TEXT CHECK(human_verdict IS NULL OR human_verdict IN (
        'verified', 'unverified', 'deferred', 'abstain'
    )),                                        -- R4 T5 fix: CHECK constraint
                                               -- enforces canonical 4-value
                                               -- vocab matching M-1 alignment
                                               -- (bundle.py, Verdict comment,
                                               -- SC-17 spec all use same set)
    human_rationale TEXT,
    overrode_llm BOOLEAN,                      -- true if user disagreed
    captured_at TIMESTAMP
);

CREATE INDEX idx_arbitrations_run_id ON arbitrations(run_id);

CREATE TABLE outcomes (
    outcome_id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id INTEGER NOT NULL REFERENCES plan_runs(run_id),
    finding_id INTEGER REFERENCES findings(finding_id),
    outcome_type TEXT NOT NULL CHECK(outcome_type IN (
        'predicted_manifested',
        'predicted_did_not_manifest',
        'unpredicted_occurred',
        'plan_succeeded'
    )),
    outcome_date TIMESTAMP NOT NULL,
    evidence TEXT,                             -- post-hoc evidence (commit/incident)
    recorder TEXT NOT NULL,                    -- who recorded ("Minxi" / CI)
    notes TEXT,
    recorded_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_outcomes_run_id ON outcomes(run_id);
CREATE INDEX idx_outcomes_type ON outcomes(outcome_type);
```

### corpus/record.py API

```python
class CorpusRecorder:
    def __init__(self, db_path: Path, redact: bool = False) -> None:
        ...

    def start_run(
        self,
        plan: ParsedPlan,
        plan_forge_version: str,
        arbitration_mode: str,
        cost_cap_usd: float,
    ) -> int:
        """Insert plan_runs row; return run_id."""

    def record_finding(self, run_id: int, finding: Finding) -> int:
        """Append-only insert into findings."""

    def record_evidence(
        self,
        run_id: int,
        gate_id: str,
        target_id: str | int,
        evidence: LLMEvidence,
    ) -> int:
        """Append-only insert into llm_evidence."""

    def update_evidence_tier(self, evidence: LLMEvidence) -> None:
        """Sole UPDATE allowed: setting tier after G10 classifies.
        This is the ONLY mutation in corpus_db; all other ops are
        append-only. Tier transition U -> T1/T2/T3/T4 is monotonic."""

    def record_arbitration(
        self,
        run_id: int,
        finding_id: int | None,
        bundle_text: str,
        human_verdict: str,
        human_rationale: str,
        overrode_llm: bool,
    ) -> int:
        """Append-only insert into arbitrations."""

    def record_outcome(
        self,
        run_id: int,
        finding_id: int | None,
        outcome_type: str,
        outcome_date: datetime,
        evidence: str | None,
        recorder: str,
        notes: str | None = None,
    ) -> int:
        """Append-only insert into outcomes."""

    def finalize_run(
        self,
        run_id: int,
        engineering_verdict: str,
        epistemic_verdict: str,
        actual_cost_usd: float,
    ) -> None:
        """Closes the plan_run row (sets completed_at + verdicts +
        actual cost). This is a CONTROLLED update on plan_runs row's
        completion fields only; other columns immutable post-insert."""
```

### corpus/redact.py

```python
def redact_plan_text(plan_text: str) -> tuple[str | None, str]:
    """For --corpus-private flag.

    Returns (plan_text_to_store, plan_hash). plan_text_to_store is
    None when redacted; plan_hash is always preserved for traceability.
    """
    plan_hash = hashlib.sha256(plan_text.encode("utf-8")).hexdigest()[:16]
    return None, plan_hash
```

### arbitration/surface.py

```python
def decide_when_to_arbitrate(
    findings: list[Finding],
    mode: str,
) -> tuple[bool, list[Finding]]:
    """Returns (should_surface, findings_to_arbitrate).

    Modes:
      - "always": surface all LLM-derived findings
      - "on_split": surface when any LLM finding has split votes
      - "on_split_evidence_rich" (DEFAULT): surface when split AND
        every provider in the split cited >= 1 concrete instance with
        per-instance reasoning
      - "off": never surface
    """
    if mode == "off":
        return False, []
    to_arbitrate = []
    for f in findings:
        if not f.llm_evidence:
            continue
        verdicts = [ev.verdict for ev in f.llm_evidence]
        unique_verdicts = set(verdicts)
        is_split = len(unique_verdicts) > 1
        if mode == "always":
            to_arbitrate.append(f)
        elif is_split:
            if mode == "on_split":
                to_arbitrate.append(f)
            elif mode == "on_split_evidence_rich":
                if all(len(ev.cited_instances) >= 1 for ev in f.llm_evidence):
                    to_arbitrate.append(f)
    return bool(to_arbitrate), to_arbitrate
```

### arbitration/bundle.py

```python
def build_evidence_bundle(finding: Finding) -> str:
    """Format finding + per-provider evidence + cited instances + search
    evidence into a human-readable markdown block.

    Output structure:
        # Arbitration: {finding.check_id} at {finding.location}

        ## Finding
        - Severity: {severity}
        - Message: {message}
        - Fix hint: {fix_hint}

        ## LLM evidence

        ### Provider {p}: verdict = {verdict} (tier {tier})
        - Reasoning: {reasoning}
        - Cited instances:
          - {snippet1}: {issue1}
          - ...
        - Search evidence:
          - Query: {q1} -> {result1} ({url1})
          - ...

        ## Decision
        Please respond with one of: verified / unverified / deferred / abstain
        and a rationale.
    """
```

### tools/abandon.py

```python
def check_abandonment(db_path: Path, plan_forge_version: str) -> Path | None:
    """Per SC-19: if corpus_db's plan_runs has >= 1 entry older than 6
    months AND outcomes table has 0 rows, generate ABANDONMENT.md
    tombstone.

    Returns: path to generated tombstone, or None if not triggered.

    Tombstone content (templated):
      # plan-forge ABANDONED

      Date: {today}
      Version at abandonment: {plan_forge_version}
      First-run date: {oldest_plan_run_date}

      Reason: 6+ months elapsed since first plan-forge run with 0
      outcomes recorded; tool has not been empirically validated by
      practice per MANIFESTO Section 6.

      ## Revival criteria (any one):
      - 3+ post-implementation failures within 6 months that fit
        G1-G10 patterns (recorded as outcomes after abandonment)
      - New domain emerges where plan rollback cost is irreversibly
        high (per MANIFESTO scope)
      - Independent third-party LEARNINGS-style failure corpus reaches
        N >= 20 entries, providing ground truth absent at abandonment

      ## Revival process:
      1. `git tag v{plan_forge_version}-revived`
      2. Update MANIFESTO Section 6 empirical-grounding statement with
         new evidence
      3. Run retroactive audit on the new failure cases (corpus_db
         preserved at {db_path})
      4. If catches >= 60% of independent failure patterns per SC-3
         pattern, revive is justified
      5. Resume work on next v0.x or v0.x+1

      corpus_db preserved at: {db_path}
    """
```

### Prompt Versioning Policy

Per R1 B4: prompts are CONTRACT, not just code. Specifically:

1. **Filename = version**: `<gate>_<purpose>_v<N>.txt` where N is an
   integer starting at 0. Never edit a v0 file in place; create v1 for
   any behavior-affecting change. Whitespace-only edits permitted in
   place.
2. **corpus_db records prompt_version**: every LLM call persists the
   exact `prompt_version` (filename without extension). Verdict
   traceability requires this column.
3. **Fixture coverage per version**: every prompt vN requires at least
   2 fixtures in `tests/fixtures/prompts/<gate>_v<N>_*.json` (one
   expected PASS LLM output, one expected FAIL). Tests run prompt vN
   against fixtures; deviations from expected output indicate either
   prompt regression or LLM behavior drift (both auditable).
4. **A/B retroactive validation**: when promoting vN+1, retroactively
   run corpus_db's last-30-day plan_runs against both vN and vN+1.
   Disagreement rate > 20% blocks promotion until human review of
   each diff.
5. **PR review**: prompt diffs reviewed with same rigor as code (3
   cycles + adversarial) per MANIFESTO Section 8. Reasoning: a prompt
   change is a behavior change.
6. **Self-application**: this PLAN.md uses placeholder prompt
   filenames (g6_sc_measurability_v0.txt etc.); actual prompts are
   shown next in this section. Subsequent versions follow above
   policy.

### LLM Prompt Bodies (v0)

All prompts are ASCII-only. Each must produce single-line JSON output;
no markdown fences. Web search permitted per E1. Prompts are
intentionally narrow per R1 B3 (LLM bias mitigation).

#### llm/prompts/g6_sc_measurability_v0.txt

```
You are reviewing a single success criterion (SC) entry from a project
plan. Determine whether the SC's stated fail-condition specifies a
MEASURABLE PREDICATE.

A measurable predicate has BOTH:
1. A concrete observable state (output value, metric, file
   presence/absence, exit code, log entry, etc.) that, if observed,
   proves the SC failed.
2. A detection procedure (how an evaluator would observe state 1).

You MAY use the web_search tool (up to 3 calls) to check whether the
claimed threshold value is plausible vs absurd given domain reference
data. Example: "build time < 30s" -- search for typical build times of
similar projects to judge plausibility.

VERIFIED requires BOTH parts present AND threshold value plausible.
UNVERIFIED if either part is missing, ambiguous, or threshold is
absurd given domain data.

Engineering reference: how do practitioners replicate published
research? They check that (a) the claim has a measurable predicate,
(b) the threshold is consistent with prior literature, (c) the
detection procedure is reproducible. Apply the same lens here.

Acceptable example (VERIFIED):
  SC: "API responds to /health within 50ms"
  Fail-condition: "curl <host>/health takes > 100ms median over 5
    consecutive samples at 1Hz"
  -> {"verdict": "VERIFIED", "reason": "concrete state (>100ms median)
       + clear procedure (5 samples at 1Hz); 100ms is plausible for
       /health endpoints per domain reference",
      "cited_instances": [], "search_evidence": []}

Unacceptable example A (no fail-condition):
  SC: "System should be performant"
  Fail-condition: (absent)
  -> {"verdict": "UNVERIFIED", "reason": "no fail-condition specified",
      "cited_instances": [{"snippet": "System should be performant",
       "issue": "vague success criterion; no concrete state"}],
      "search_evidence": []}

Unacceptable example B (state not concrete):
  SC: "Code is maintainable"
  Fail-condition: "Maintainers complain"
  -> {"verdict": "UNVERIFIED", "reason": "complaint is subjective",
      "cited_instances": [{"snippet": "Maintainers complain",
       "issue": "no objective threshold"}],
      "search_evidence": []}

Unacceptable example C (procedure absent):
  SC: "Build time < 30s"
  Fail-condition: "Build is slow"
  -> {"verdict": "UNVERIFIED", "reason": "state exists but procedure
       absent",
      "cited_instances": [{"snippet": "Build is slow",
       "issue": "no detection procedure"}],
      "search_evidence": []}

Unacceptable example D (threshold absurd, found via search):
  SC: "ML model trains in 1 hour on CPU"
  Fail-condition: "Training > 1 hour on CPU for ResNet-50 on ImageNet"
  -> {"verdict": "UNVERIFIED", "reason": "search reveals ResNet-50
       ImageNet training takes ~24h on 8x V100, 'CPU 1 hour' contradicts
       domain reference",
      "cited_instances": [{"snippet": "trains in 1 hour on CPU",
       "issue": "infeasible threshold"}],
      "search_evidence": [{"query": "ResNet-50 ImageNet training time CPU",
       "result_summary": "single-CPU training infeasible; ~24h on GPU
        cluster", "url": "<retrieved-url>"}]}

INPUT (single-line JSON payload):
{"sc_id": ..., "sc_text": ..., "fail_condition_text": ...}

OUTPUT (single-line JSON, no markdown):
{"verdict": "VERIFIED" | "UNVERIFIED",
 "reason": "<one sentence>",
 "cited_instances": [{"snippet": "<text>", "issue": "<what's missing>"}],
 "search_evidence": [{"query": "...", "result_summary": "...",
                      "url": "..."}]}

Constraints:
- Do not judge the SC's domain importance or business value.
- Do not judge the plan as a whole. Only this single SC.
- If fail-condition uses hedge words (probably/likely/should), that
  is UNVERIFIED (hedges are not measurable predicates).
- Empty cited_instances if VERIFIED.
- Empty search_evidence if no search was needed (commonly-known domain).
```

#### llm/prompts/g8_citation_resolvability_v0.txt

```
You are verifying a single citation from a project plan's External
Voices section. Determine whether the citation is RESOLVABLE -- i.e.,
whether the cited work plausibly exists as a real, identifiable
publication or source.

You SHOULD use the web_search tool (up to 3 calls) to attempt
resolution. Engineering reference: just as researchers check whether
prior work cited in a paper actually exists and supports the claimed
proposition, verify these citations.

Tiered verdict (per E3):
  RESOLVED_VIA_SEARCH:  search returned matching record
  RESOLVED_BY_KNOWLEDGE: training-corpus confirms (no search needed
                        because work is well-known canonical)
  UNCERTAIN:            need human verification (surfaces to H1)
  UNRESOLVABLE:         internal contradiction OR search confirmed
                        false OR fabricated

A citation has internal contradictions if:
  - author lifespan inconsistent with publication year
    (e.g., "Turing 2010")
  - work title mentions technology not yet existing at year
  - publisher / venue did not exist at year

Acceptable example (RESOLVED_BY_KNOWLEDGE):
  "Popper, K. (1959). The Logic of Scientific Discovery. Routledge."
  -> {"verdict": "RESOLVED_BY_KNOWLEDGE", "reason": "well-known
       philosophical canonical work; author + title + year + publisher
       consistent",
      "cited_instances": [], "search_evidence": []}

Acceptable example (RESOLVED_VIA_SEARCH):
  "Pineau et al. (2020). Improving Reproducibility in Machine Learning
   Research. JMLR."
  -> {"verdict": "RESOLVED_VIA_SEARCH",
      "reason": "Pineau et al 2020 paper on ML reproducibility verified
       in JMLR per search",
      "cited_instances": [],
      "search_evidence": [{"query": "Pineau 2020 reproducibility JMLR",
       "result_summary": "paper found at jmlr.org",
       "url": "<retrieved-url>"}]}

UNCERTAIN example (generic author, plausible but not findable):
  "Smith, J. (2024). Towards a Theory of Plan Robustness. AI Methods."
  -> {"verdict": "UNCERTAIN",
      "reason": "generic author name 'Smith, J.' and generic journal
       'AI Methods'; search returned no match; plausible but not
       verifiable",
      "cited_instances": [{"snippet": "Smith, J.",
       "issue": "generic author without first-name initial"}],
      "search_evidence": [{"query": "Smith Theory of Plan Robustness
       2024", "result_summary": "no matching record",
       "url": "<retrieved-url>"}]}

UNRESOLVABLE example (internal contradiction):
  "Turing, A. (2010). On Capabilities of Transformer Networks. Mind."
  -> {"verdict": "UNRESOLVABLE",
      "reason": "Turing died 1954; cannot author 2010 transformer paper",
      "cited_instances": [{"snippet": "Turing, A. (2010)",
       "issue": "temporal impossibility"}],
      "search_evidence": []}

INPUT:
{"citation_text": "...", "context": "<where cited>"}

OUTPUT:
{"verdict": "RESOLVED_VIA_SEARCH" | "RESOLVED_BY_KNOWLEDGE"
            | "UNCERTAIN" | "UNRESOLVABLE",
 "reason": "<one sentence>",
 "cited_instances": [{"snippet": "<text>", "issue": "<what's wrong>"}],
 "search_evidence": [{"query": "...", "result_summary": "...",
                      "url": "..."}]}

Constraints:
- Generic author names (Smith / Brown / Lee) without first-name
  initial default to UNCERTAIN unless search resolves.
- Do not fabricate URLs in search_evidence; use actual retrieved
  URLs or omit the entry.
- UNCERTAIN is NOT a failure -- surfaces to human arbitration.
- UNRESOLVABLE requires concrete contradiction or confirmed-false
  search result.
```

#### llm/prompts/g9_feasibility_anchor_v0.txt

```
You are evaluating whether a quantitative claim in a project plan is
supported by its cited anchor.

The plan author has provided an anchor (URL / project name / prototype
reference / publication) intended to ground a quantitative claim.
Your task: judge whether the anchor's actual data plausibly supports
the magnitude / units / timeline / cost claimed.

Engineering reference: a researcher claiming "method X achieves Y%
accuracy on dataset Z" must cite a prior benchmark establishing
realistic accuracy ranges. You apply the same scrutiny here.

You SHOULD use the web_search tool (up to 3 calls) to:
1. Verify the anchor (URL resolves; project named is real)
2. Retrieve the anchor's actual data (numbers, durations, costs)
3. Compare to the claim

Verdict:
  SUPPORTS:      anchor confirms claim magnitude / direction
  WEAK_SUPPORT:  anchor exists but data partially differs (e.g.,
                 different scale; needs interpolation)
  CONTRADICTS:   anchor exists but data shows claim is unrealistic
  UNVERIFIABLE:  anchor not found or data not retrievable

Acceptable example (SUPPORTS):
  Claim: "Migrating a 50M-row Postgres table with NOT NULL backfill
   takes ~3 hours."
  Anchor: "GitLab.com blog post Sept 2022: 100M-row backfill 6 hours."
  -> {"verdict": "SUPPORTS",
      "reason": "GitLab anchor: 100M rows in 6h => 16.7M/h; claim
       50M in 3h => 16.7M/h; consistent throughput",
      "search_evidence": [{"query": "GitLab Postgres NOT NULL
       backfill 100M rows", "result_summary": "blog post confirms 6h",
       "url": "<retrieved-url>"}]}

Acceptable example (CONTRADICTS):
  Claim: "plan-forge v0.1 ships in 4 weeks."
  Anchor: "ruff (Python lint): 6 months plan, 12 months actual."
  -> {"verdict": "CONTRADICTS",
      "reason": "ruff (pure-lint, simpler than plan-forge) took 12mo;
       plan-forge with G1-G10 + LLM layer extrapolates well beyond
       4wk",
      "search_evidence": [{"query": "ruff Python linter project
       timeline", "result_summary": "ruff project history confirms
       12mo actual", "url": "<retrieved-url>"}]}

UNVERIFIABLE example:
  Claim: "Algorithm runs in O(n log n)."
  Anchor: "Internal benchmark, see ~/notebook/2024-Q3.ipynb"
  -> {"verdict": "UNVERIFIABLE",
      "reason": "anchor refers to private internal artifact; cannot
       verify without access",
      "search_evidence": []}

INPUT:
{"claim_text": "...", "anchor_text": "...", "anchor_type": "..."}

OUTPUT:
{"verdict": "SUPPORTS" | "WEAK_SUPPORT" | "CONTRADICTS" | "UNVERIFIABLE",
 "reason": "<one sentence with the numerical comparison>",
 "cited_instances": [{"snippet": "<text>", "issue": "<discrepancy>"}],
 "search_evidence": [{"query": "...", "result_summary": "...",
                      "url": "..."}]}

Constraints:
- Always compute the actual magnitude comparison; do not abstract.
  E.g., "50M / 3h = 16.7M/h; reference is 16.7M/h; consistent".
- WEAK_SUPPORT requires partial-but-non-contradictory data, not just
  "could be true".
- UNVERIFIABLE for private artifacts only; if anchor refers to a
  public-but-not-found artifact, return CONTRADICTS (with reason
  "search returned no public record").
```

#### llm/prompts/g10_evidence_tier_v0.txt

```
You are classifying the provenance tier of a piece of evidence cited
by another check in plan-forge. The evidence is a claim, citation, or
search result used by G4/G6/G8/G9 (or by G10 itself in a prior round).

Engineering reference: how does the scientific community judge the
reliability of a finding? By replication, independent citation, and
absence of retraction. T1 GOLD evidence has cleared replication; T4
SUSPECT has not.

You SHOULD use the web_search tool (up to 4 calls) to verify:
1. Primary source URL resolves (or work title found in scholar DB)
2. Replication / reproduction studies exist (by non-co-authors)
3. Dissenting views OR retractions exist
4. AI-generated content suspected (per anti-ai-audit heuristics:
   generic phrasing, no concrete author, suspicious citation density)

Tier criteria:

  T1 GOLD:
    - Primary source verified (URL resolves OR title in scholar DB)
    - 3+ independent replications/citations from non-co-authors
    - No retraction; no major dissent

  T2 SILVER:
    - Primary source verified
    - 1-2 replications OR widely cited but not yet replicated
    - No retraction; minor dissent acceptable

  T3 BRONZE:
    - Secondary aggregator (blog summary, news article)
    - OR primary verified but 0 replications found
    - OR cannot find replications (search inconclusive)

  T4 SUSPECT:
    - AI-generated content suspected (anti-ai-audit heuristic flag)
    - OR formally retracted / contradicted
    - OR primary URL fails to resolve
    - OR replicators contradict each other systematically

Acceptable example (T1):
  Evidence: "Open Science Collaboration (2015) found 39% of psychology
   replication attempts succeeded."
  -> {"tier": "T1", "primary_url": "<retrieved-url>",
      "replication_evidence": [{"url": "<url1>", "type": "citation"},
       {"url": "<url2>", "type": "replication"},
       {"url": "<url3>", "type": "citation"}],
      "reasoning": "OSC 2015 Science paper widely cited and replicated
       across psych field; >> 3 non-co-author citations",
      "verifiability": "high"}

Acceptable example (T3):
  Evidence: "A Medium blog post by @user123 claims their startup
   shipped in 2 weeks using AI."
  -> {"tier": "T3", "primary_url": "<retrieved-url>",
      "replication_evidence": [],
      "reasoning": "single blog post; no replication; aggregator-tier",
      "verifiability": "low"}

Acceptable example (T4):
  Evidence: "Per Smith 2024, plan-forge methodology is best practice."
  -> {"tier": "T4", "primary_url": null,
      "replication_evidence": [],
      "reasoning": "search returned no record of Smith 2024 cited
       work; possibly AI-fabricated citation",
      "verifiability": "low"}

INPUT:
{"evidence_text": "...", "citing_gate": "G6.B" | "G8.B" | "G9.B"
                                       | "G10.B",
 "context": "<prompt_version that produced this evidence>"}

OUTPUT:
{"tier": "T1" | "T2" | "T3" | "T4",
 "primary_url": "<url-or-null>",
 "replication_evidence": [{"url": "...", "type": "replication"
                                              | "citation"
                                              | "dissent"
                                              | "retraction"}],
 "reasoning": "<one sentence>",
 "verifiability": "high" | "medium" | "low"}

Constraints:
- Do NOT use the web_search tool to look up plan-forge itself or
  this plan's content; you are evaluating the evidence's external
  provenance, not the plan.
- T2 requires AT LEAST 1 verified replication or wide citation; do
  not collapse T3 into T2.
- AI-generated suspicion (T4) requires concrete heuristic trigger
  (e.g., citation does not resolve + generic phrasing); do not
  classify T4 on aesthetic judgment alone.
- Output `tier` MUST be one of T1/T2/T3/T4. Never emit UNCERTAIN or
  other values; if torn between two tiers, choose the lower (more
  cautious) tier and explain in `reasoning`. Recursion-cap deferral
  to human is handled by plan-forge code (`g10_evidence_tier.run`
  returns Finding with check_id="G10.recursion_cap" when depth >=
  max_depth), NOT by the LLM. The LLM always classifies T1-T4.
- If primary source cannot be located AND no replication evidence
  exists AND no contradiction found: tier = T3 (with reasoning
  "search inconclusive; treat as aggregator-tier"). Do NOT invent
  citations or URLs to justify T1/T2.
```

### Tool_use schema (E1 web search across providers)

```python
# llm/tool_use.py
ANTHROPIC_WEB_SEARCH_TOOL = {
    "name": "web_search",
    "description": "Search the web and return top-3 results with "
                   "title, snippet, and URL.",
    "input_schema": {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "search query"},
        },
        "required": ["query"],
    },
}

# Kimi / DeepSeek follow OpenAI tool_use schema (functions field)
OPENAI_COMPAT_TOOL = {
    "type": "function",
    "function": {
        "name": "web_search",
        "description": "Search the web; returns top-3 snippets + URLs.",
        "parameters": {
            "type": "object",
            "properties": {"query": {"type": "string"}},
            "required": ["query"],
        },
    },
}

# Mimo support verified at T10. If absent, MimoClient returns
# verdict tagged "no_search_judgment" tier UNCLASSIFIED per E3.
```

## Implementation Tasks

Phase numbering: T01-T04 = setup (mostly DONE); T05-T13 = core
mechanical + library; T14-T21 = LLM gates + scaffolding + adapters;
T22-T28 = corpus_db + arbitration + outcomes (R1 H1/H2/H3); T29-T31 =
G9/G10 (R1 E2/G10) + LLM web search (R1 E1); T32-T35 = self-dogfood +
retroactive audit + review + ship.

| # | Task | Output | Done when |
|---|------|--------|-----------|
| T01 | git init (DONE) | ~/code/plan-forge/.git | repo exists |
| T02 | MANIFESTO.md (DONE; needs R1 update T02b) | MANIFESTO.md | 294 lines initial; R1 update adds Sections 11 + 12 |
| T02b | MANIFESTO Section 11 + 12 (Defense-in-Depth + Recursive Epistemic Discipline) | MANIFESTO.md revised | ASCII clean, sections present, anti-bypass language strengthened |
| T03 | this PLAN.md (R2 post-R1-fixes) | plan-forge-v0.1-PLAN.md | ASCII clean, all G1-G10 sections present, R1 fix mapping in Appendix B |
| T03b | R1-REVIEW-SUMMARY.md (consensus + fixes summary) | .planning/R1-REVIEW-SUMMARY.md | BLOCKER B1-B5 + HIGH items documented with applied fix per item |
| T04 | self-dogfood walkthrough on R2 PLAN | Appendix A updated | each G1-G10 has PASS/FAIL judgment with evidence |
| T05 | pyproject.toml + skeleton + Alembic setup | pyproject.toml + src/plan_forge/ skeleton + alembic.ini + migrations/env.py | `pip install -e .` works; `alembic upgrade head` runs on empty DB |
| T06 | verdict.py + parser.py (incl. anchor extractor for G9) | both modules + unit tests | parser handles fixtures; verdict computes from finding list; anchors extracted |
| T07 | F1-F7 mechanical checks | 7 modules + 7 test files | each F has PASS fixture + FAIL fixture; tests pass |
| T08 | PBR P1/P2/P5 mechanical (3 modules; P6 split to T17 per R4 T4 fix avoiding overlap) | 3 modules + 3 tests | each PBR pass (P1, P2, P5) has PASS + FAIL fixture |
| T09 | api.check_mechanical() | api.py partial | runs F + PBR; returns findings (no LLM yet) |
| T10 | LLM client + multi-provider + tool_use web search | llm/ subpackage | Anthropic + Kimi + DeepSeek + Mimo clients + search_vote.py; Mimo tool_use support verified or fallback documented |
| T11 | G4 + G6 + G8 (mechanical + narrow LLM Part B) + v0 prompts + fixtures | 3 modules + 3 prompts + 6 fixtures (2 per gate) | mechanical part standalone; Part B uses search_vote; prompt_version recorded |
| T12 | G1-G3 + G5 + G7 (pure mechanical G's) | 5 modules + tests | each G has PASS + FAIL fixture |
| T13 | api.check() core + verdict aggregation (G1-G8 + F1-F7 + PBR; NO G9/G10 yet) | api.py core complete | end-to-end PASS on well-formed fixture; CHECKPOINT 1 (week 5) |
| T14 | scaffold/ + templates | default.md.j2 | `scaffold("test-plan")` produces template with all G1-G10 sections |
| T15 | Adapter A (library) v0.1.0-alpha1 | __init__.py exports | `from plan_forge import check` works with G1-G8 |
| T16 | Adapter C (CLI) basic 3 commands | adapters/cli/main.py | check + scaffold + audit-retroactive functional with help |
| T17 | PBR P6 metadata-currency check (T08 covers P1/P2/P5; P6 added in R2 M2-Mimo as separate task to avoid T08 overload) | 1 module + tests | P6 has PASS + FAIL fixture; integrated into api.check_mechanical with T08 outputs |
| T18 | Buffer slot 1 (wk 6-7 catch-up) | absorb T10/T11/T12 overrun OR start T22 corpus early if on schedule | If schedule on track: begin T22 (corpus schema). If T10/T11/T12 overrunning: dedicate to catch-up. Decision recorded at week-5 checkpoint review. |
| T19 | Buffer slot 2 (wk 7-8 catch-up) | continue T18 absorption OR start T23 corpus.db | same gating logic as T18; cumulative slip > 1 week triggers descope checkpoint 2 |
| T20 | LESSONS-RETRO.md scaffold (pre-audit infrastructure) | empty LESSONS-RETRO.md template + retroactive_audit.py runner skeleton | template ready to receive T34 audit data; runner can iterate phases/02-*/ paths |
| T21 | Adapter A v0.1.0-alpha2 (pre-corpus integration) | __init__.py exports + minimal check() with G1-G8 + F1-F7 + PBR | `from plan_forge import check` returns Verdict on G1-G8 fixtures; sets stage for T22 corpus integration |
| T22 | corpus/schema.sql + Alembic migration 0001 | migrations/versions/0001_initial_schema.py | `alembic upgrade head` creates 6 tables on fresh DB |
| T23 | corpus/db.py + models.py + record.py | 3 modules + unit tests | record_plan_run / record_finding / record_evidence / record_arbitration / record_outcome / finalize_run all functional with append-only contracts; UPDATE allowed only on llm_evidence.tier monotonic transition |
| T24 | corpus/redact.py + --corpus-private flag | privacy module + CLI flag | redacted plan_text stored as NULL with plan_hash preserved |
| T25 | arbitration/surface.py with 4 modes | module + tests | `on_split_evidence_rich` default; correctly identifies split-with-evidence findings; `off` mode skips all |
| T26 | arbitration/bundle.py | module + tests | human-readable markdown bundle includes per-provider verdict + cited instances + search evidence + tier |
| T27 | arbitration/capture.py + record_arbitration integration | module + tests | captured verdict + rationale appended to arbitrations table; overrode_llm flag set correctly |
| T28 | Adapter B (Claude Code skill) with human-in-loop UI | adapters/skill/SKILL.md + runner.py | `/plan-forge <path>` invocable; arbitration_mode=on_split_evidence_rich triggers surface in Claude Code chat; user verdict captured to corpus_db; CHECKPOINT 2 (week 8) |
| T29 | G9 module + v0 prompt + fixtures + LLM Part B | g9_feasibility_anchor.py + prompt + 2 fixtures | mechanical anchor-citation check + LLM feasibility check; integrated to api.check() |
| T30 | G10 module + v0 prompt + fixtures + recursion cap | g10_evidence_tier.py + prompt + 2 fixtures | tier classifier with depth-2 recursion cap; T3/T4-only chain detection; integrated as post-processing on G4/G6/G8/G9 evidence; CHECKPOINT 3 (week 12) |
| T31 | LLM web search integration across providers (E1) | llm/tool_use.py + per-provider adapters | Anthropic + Kimi + DeepSeek tool_use confirmed; Mimo confirmed or no_search_judgment fallback documented; cost cap honored |
| T32 | tools/abandon.py + tools/outcomes_cli.py | 2 tool scripts + tests | `plan-forge record-outcome` works; `plan-forge abandonment-check` checks SC-19 trigger and generates ABANDONMENT.md template if conditions met |
| T33 | Self-dogfood: api.check() on this PLAN (T18 equivalent) | dogfood test | PLAN passes plan-forge with PASS both verdicts AND all evidence T1/T2; engineering + epistemic verdicts persisted to corpus_db |
| T34 | Retroactive audit on forge-code Phase 2 archived plans (T19 equivalent) | LESSONS-RETRO.md | 02-01..02-06 audited; SC-3 coverage computed; >= 60% per SC-3 fail-condition |
| T35 | 3-cycle code review (forge-style) + smoke test + ship | review notes + git tag v0.1.0 | post-review-c3 reached; smoke test pass; tag v0.1.0 on main; CHECKPOINT 4 (week 16, hard ceiling) |

Plan duration: 16 weeks (G1 outside-view derived; see Reference Class
section). Hard ceiling: 17 weeks. Descope checkpoints at weeks 5 / 8 /
12 / 16 per Reference Class table.

## Success Criteria (with explicit fail-condition column per G6)

Engineering layer SCs (mechanical):

| ID | Criterion | Fail Condition |
|----|-----------|---------------|
| SC-1 | MANIFESTO.md exists at repo root with Sections 1-12 (1-10 v0; 11-12 added per R1) | MANIFESTO.md absent OR README.md does not reference it as "read first" OR Sections 11/12 missing post-T02b |
| SC-2a (manual, T04) | this PLAN.md passes manual G1-G10 walkthrough per Appendix A (pre-implementation self-check) | Appendix A walkthrough shows any G mechanical FAIL (section absent, field missing, < N threshold) on this PLAN |
| SC-2b (automated, T33) | this PLAN.md passes plan-forge v0.1 automated self-check post-implementation | api.check(plan_forge_v0_1_plan_text) returns FAIL or VISION on either verdict; OR evidence chain contains T4-only with no T1/T2 corroboration |
| SC-3 (revised per R1 B5) | T34 retroactive audit on forge Phase 2 archived plans (02-01..02-06) vs INDEPENDENT 02-LEARNINGS.md problem list; coverage >= 60% [anchor: tentative calibration; 100% would suggest overfitting to known cases (suspicious), < 50% means mechanical layer too weak; 60% is G7-mid threshold per Taleb barbell logic in Section 7 of MANIFESTO] | (problems_caught_by_plan_forge / total_problems_in_02-LEARNINGS.md) < 60% |
| SC-4 | F1-F7 each have 2 test cases (PASS + FAIL fixture) | any F has fewer than 2 test cases OR FAIL fixture does not trigger the check |
| SC-5 (revised R3 RN-2) | G1-G10 each have 2 test cases (PASS + FAIL fixture); LLM Part B integration required for G6/G8/G9/G10 (G4 Part B deferred to v0.1.1 per descope; SC-5 verifies G4 Part A mechanical only) | any G missing fixtures OR G6/G8/G9/G10 do not invoke search_vote OR G4 mechanical hedge-detection regex absent |
| SC-6 | Adapter A library import works: `from plan_forge import check` | ImportError OR check() signature differs from spec |
| SC-7 | Adapter B Claude Code skill registered and invocable with human-in-loop arbitration | `/plan-forge <path>` in Claude Code fails to invoke or returns no Verdict OR arbitration surface absent when mode=on_split_evidence_rich + split+evidence-rich findings present |
| SC-8 | Adapter C CLI has 5 commands functional with help text: check, scaffold, audit-retroactive, record-outcome, abandonment-check | any of 5 commands returns non-zero on `--help` OR missing |
| SC-9 | Test coverage >= 80% on src/plan_forge/ | `pytest --cov=src/plan_forge` reports < 80% line coverage |
| SC-10 | 3-cycle code review post-review-c3 reached before v0.1 tag (T35) | tag v0.1.0 created without 9-pass clean review per smoke-test/SKILL.md |
| SC-11 | All commits authored Minxi Hou <houminxi@gmail.com>; no AI markers in commit messages | grep finds "Co-Authored-By: Claude" OR "noreply@anthropic.com" OR "post-review-c3" in commit body OR review-tool names |
| SC-12 | 0 outbound subprocess calls to Claude Code skills from plan_forge library code | grep src/plan_forge/ finds `subprocess.run` referencing `gsd-*`, `plan-review`, `adversarial-qe`, or `anti-ai-audit` |
| SC-13 | Graceful LLM degradation: if N of 4 providers unavailable, plan-forge runs with remaining; if N < 2, mechanical-only fallback with warning | any LLM provider failure causes plan-forge to crash or return Verdict without engineering verdict |
| SC-14 (revised R1+R2) | LLM cost: median run < $0.75 per plan (R2 M2-DS: raised from $0.50 to allow G10 recursive headroom); hard ceiling $2.00 with mechanical-only fallback above | median across 10 sample plans exceeds $0.75 OR a single run exceeds $2.00 without fallback engaging |
| SC-15 | ASCII enforcement: no non-ASCII in any committed file under src/, MANIFESTO.md, or PLAN.md | `git diff --diff-filter=AM -U0` finds non-ASCII added in any committed file |

Corpus / arbitration / outcomes / abandonment layer SCs (R1 H1/H2/H3):

| ID | Criterion | Fail Condition |
|----|-----------|---------------|
| SC-16 | corpus_db append-only: every run writes plan_runs + findings + llm_evidence with no UPDATE outside (a) plan_runs finalize_run completion fields and (b) llm_evidence.tier monotonic transition U->T1/T2/T3/T4 | SELECT detects illegal UPDATE OR schema_version table absent OR migrations history broken |
| SC-17 | Arbitration triggers correctly per mode: on_split_evidence_rich (default) surfaces ONLY when split+rich; others per Module Designs `decide_when_to_arbitrate` | mode=on_split_evidence_rich fails to surface a split+rich finding; OR mode=off surfaces; OR captured human verdict not recorded |
| SC-18 | outcomes table CHECK constraint enforces 4 outcome_type values; recorder column NOT NULL | INSERT with invalid outcome_type accepted OR INSERT with NULL recorder accepted |
| SC-19 (self-falsifying) | After 6 calendar months [anchor: 2 typical SaaS product-retention quarters; long enough for genuine no-use signal vs vacation/sabbatical gap; comparable to npm package abandonment heuristics (e.g., npmjs.com marks packages "last published > 1 year ago" but plan-forge has higher empirical-grounding bar)] of plan-forge use, IF corpus_db plan_runs has >= 1 entry older than 6 months AND outcomes table has 0 rows, `plan-forge abandonment-check` MUST generate ABANDONMENT.md tombstone with revival criteria | tombstone not generated when conditions met OR generated when conditions not met |
| SC-20 | --corpus-private flag redacts plan_text (set NULL) while preserving plan_hash | --corpus-private run leaves plan_text non-NULL OR redacts plan_hash |

G6/G8/G9/G10 prompt SCs (R1 B4):

| ID | Criterion | Fail Condition |
|----|-----------|---------------|
| SC-21 | G6 v0 prompt body present in PLAN with >= 4 examples (>= 1 VERIFIED + >= 3 UNVERIFIED across distinct failure modes) | prompt body absent OR fewer than 4 examples OR examples lack distinct failure modes |
| SC-22 | G8 v0 prompt body present in PLAN with >= 3 examples (>= 1 RESOLVED_BY_KNOWLEDGE + >= 1 RESOLVED_VIA_SEARCH + >= 1 UNRESOLVABLE) | prompt body absent OR < 3 examples OR missing required example categories |
| SC-23 | G9 v0 prompt body present in PLAN with >= 3 examples (>= 1 SUPPORTS + >= 1 CONTRADICTS + >= 1 UNVERIFIABLE) | prompt body absent OR < 3 examples OR missing required example categories |
| SC-24 | G10 v0 prompt body present in PLAN with >= 3 examples (>= 1 T1 + >= 1 T3 + >= 1 T4) | prompt body absent OR < 3 examples OR missing required tier categories |
| SC-25 | llm_evidence.prompt_version column populated for every LLM call | SELECT COUNT WHERE prompt_version IS NULL FROM llm_evidence > 0 |
| SC-26 | Each prompt vN has >= 2 fixture files in tests/fixtures/prompts/ (1 PASS + 1 FAIL) | fixture count per prompt version < 2 OR fixtures do not match expected output spec |

LLM web search SCs (R1 E1):

| ID | Criterion | Fail Condition |
|----|-----------|---------------|
| SC-27 | Anthropic + Kimi + DeepSeek clients confirm tool_use web search works; Mimo confirmed OR falls back to no_search_judgment tier UNCLASSIFIED | any provider fails to demonstrate web search OR Mimo fallback silent (no warning emitted) |
| SC-28 (revised R2+R3) | Web search calls per LLM call capped at 3 for G4/G6/G8/G9 prompts; capped at 4 for G10 prompt (G10 needs extra search for replication evidence per its v0 prompt); soft cap $0.75/plan median for typical (<= 10 SC) plans; hard cap $2.00/plan with mechanical-only fallback above; search_evidence persisted to llm_evidence.search_evidence as JSON | per-prompt search cap exceeded OR median cost > $0.75 on typical sample OR single-run cost > $2.00 without fallback OR search_evidence column NULL when search happened |

## Out of Scope

- Editor LSP server (deferred to v0.2)
- Web UI (deferred to v1.0)
- Pre-commit hook adapter (v0.2)
- GitHub Action adapter (v0.2)
- Multi-language support beyond English + Chinese hedge regex (v0.2 i18n)
- Plan template variations beyond `default.md.j2` (v0.2)
- Auto-fix mode (plan-forge identifies issues; humans fix). v2.0+ candidate.
- Idea-stage gate (forge-idea is a separate future product per family vision)
- Code-stage gate (forge-code v1.0 ships separately)
- Real-time inline review during writing (v0.2 LSP)
- Plan version history / diff awareness (v0.2)
- Multi-author conflict detection (v0.3+)

## Risks (G2 self-dogfood: 3-class taxonomy)

### Known Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| LLM API cost spike with web search (4 providers * 12+ calls * search surcharge per plan ~$0.75-2.00 typical; large 28-SC plans approach $3-5 without cache) | 80% | M | cache by (plan-hash, prompt-hash, model, search-toolset-version) with per-prompt TTL (1wk canonical / 24h recent); soft median $0.75/plan; hard cap $2.00/plan with mechanical-only fallback; --cost-cap override up to $5.00 |
| Multi-LLM provider tool_use API drift (per memory: DeepSeek tool_use bugs, Kimi cache_control quirks) | 80% | M | LLMClient Protocol abstracts; per-provider adapter handles quirks; tool_use feature-detection at startup; degrade to no_search_judgment per provider |
| Multi-LLM vote split on G6/G8/G9 | 60% | M | arbitration_mode=on_split_evidence_rich surfaces to human (H1); ties produce "indeterminate" without arbitration; user verdict authoritative |
| False positive on G4 hedge-word lint after G4 Part B web search | 50% | L | allow inline `<!-- plan-forge: hedge-ok -->` marker; Part B downgrades to MEDIUM when LLM finds anchor |
| Parser breaks on unconventional markdown OR fails to extract G9 anchors with non-standard syntax | 50% | L | strict markdown subset enforced; reject with clear error; anchor regex documented |
| G10 recursion cap (depth 2) insufficient for evidence chains with multi-hop citations | 30% | L | escalate to human via UNCERTAIN at cap; corpus_db records the escalation for v0.2 tuning |
| corpus_db SQLite file corruption (single-writer assumption violated under concurrent CLI use) | 20% | M | document single-writer constraint; v0.1 documents limitation; v0.2 considers SQLite WAL mode + locking |

### Gray Rhinos

| Gray Rhino | Denial Reason (why people will ignore) | Counter |
|------------|---------------------------------------|---------|
| plan-forge itself overscopes: G1-G10 + corpus_db + arbitration + outcomes + G9 + G10 + LLM web search is ambitious for v0.1; will exceed 16 weeks | "R1 review concluded 16-17 weeks is honest; user accepted; the scope IS the scope" | 4 descope checkpoints (week 5/8/12/16); each checkpoint lists explicit items to drop; mechanical layer (F1-F7 + 5 of 10 G mechanical) is non-negotiable but everything else negotiable |
| Self-dogfood (SC-2) becomes infinite regress: PLAN keeps failing own enforcement (especially after G9/G10 added), requires perpetual revision | "it is just polish, almost there" | T04 self-dogfood is best-effort, not gate; T33 (post-implementation) is the real self-dogfood; if T33 fails, redesign the failing check rather than rewriting PLAN |
| Retroactive audit (SC-3) coverage < 60% on forge Phase 2 LEARNINGS-documented problems | "AI panel converged on these plans, so plans must be fine; tool must be wrong" OR "60% threshold is arbitrary" | This is the empirical-grounding commitment. Coverage < 60% means mechanical layer too weak; redesign mechanical rather than lowering threshold or abandoning |
| Multi-LLM provider integration brittleness with web search (tool_use API breaks silently) | "we tested it works today" | Integration tests run weekly via CI; per-provider feature-detection at startup; mechanical-only fallback if all providers regress |
| G10 recursive evidence tier classifier is itself LLM-dependent; cannot fully escape AI-detect-AI circularity | "MANIFESTO Section 11 already acknowledges this" | Per MANIFESTO Section 11/12: G10 mitigates not eliminates; 5 of 10 G mechanical parts independent of LLM; ground truth corpus (LEARNINGS + corpus_db) is L3 independent layer; outcomes (L5) is empirical validation; abandonment clause (SC-19) is self-falsifying |
| Arbitration UX is too friction-heavy; users disable it (mode=off) and revert to "LLM verdict = truth" anti-pattern | "I trust the LLMs; arbitration slows me down" | Default mode=on_split_evidence_rich triggers only on rich-evidence splits (relatively rare); bundle.py renders fast scan-friendly markdown; if SC-17 + SC-18 outcomes show users disabling arbitration > 30%, redesign UX rather than removing arbitration |
| corpus_db becomes write-only ledger nobody queries; outcomes never recorded; SC-19 abandonment triggers but user disputes "I just didn't record outcomes, the tool works fine" | "outcomes are tedious to record" | Adapter B prompts for outcome on any subsequent plan check ("did your last plan's predicted failure mode manifest?"); CLI command `record-outcome <run-id>` is one-line; SC-19 trigger does NOT delete corpus_db; revival path documented |
| plan-forge adopted by Minxi only; never reaches external users | "as long as I use it, it has value" | Acceptable per SC-3 ROI (retroactive value alone justifies); v0.2 considers outreach (HN post, GitHub release) if T34 retro-audit demonstrates value |

### Black Swans

| Black Swan | Survival Plan |
|------------|---------------|
| Corpus + synthesis + LEARNINGS combine to reveal forge concept itself wrong; plan-forge unmasks that forge-code v2.0 should never have been built | Accept; v1.0 forge skill still ships in production; v2.0 archived as lessons; plan-forge value undiminished |
| AI tool landscape shifts (e.g., Claude 5 catches G1-G10 natively); plan-forge becomes obsolete before v1.0 ships | Ship anyway; MANIFESTO + corpus + LEARNINGS are durable intellectual property independent of tool layer; v0.1 cost is < 17 weeks |
| User (Minxi) loses interest; project dies mid-implementation | 4 checkpoint releases (mechanical at wk5; +corpus at wk8; +G9 at wk12; +G10 at wk16) each independently useful; PR-quality README at each milestone documents what works |
| G4/G6/G8/G9 LLM judges across all four providers converge to "internally consistent = plan" bias (the very failure mode plan-forge is supposed to fix) | Mechanical layer is 5 of 10 G's independent of LLM; G7 + G3 + G2 + G1 + G5 mechanical alone catch "looks consistent but is vision" via missing reference class / pre-mortem / risk taxonomy / scope challenge / chaos response; arbitration (L4) is non-LLM; outcomes (L5) is empirical |
| G10 recursive tier classifier itself produces systematically biased verdicts (T4 false-positives flagging legitimate evidence; or T1 false-positives confirming fabricated evidence) | Per MANIFESTO Section 12: T3/T4-only chains block FAIL/VISION verdicts but T1/T2 verdicts proceed; if T1/T2 systematically biased (cannot verify), human arbitration covers; outcomes table over time reveals systematic tier bias via prediction accuracy metrics |
| Anthropic API permanent shutdown or pricing change makes multi-LLM economically infeasible | Mechanical-only fallback mode (F1-F7 + 5 of 10 G mechanical parts still work); v0.2 adds local LLM (llama.cpp / vllm) option |
| corpus_db SQLite WAL corruption from disk failure; all evidence chains lost | corpus_db is local; daily backup recommended (documented in README); plan-forge survival is independent of corpus history (each new run starts fresh corpus); only loss is retroactive prediction-accuracy metric |
| Web search tool_use providers all introduce per-search billing markup that breaks $2.00/plan hard cap | mechanical-only fallback; --cost-cap override up to $5.00 for one-off audit runs; v0.2 considers self-hosted search (e.g., SearXNG) backend |

## Reference Class (G1 self-dogfood)

| Project | Plan Estimate | Actual Duration | Ratio | Note |
|---------|--------------|----------------|-------|------|
| ruff (Python linter) | 6 months | 12 months | 2.0 | Pure mechanical lint |
| semgrep (security pattern lint) | 12 months | 18 months | 1.5 | Pattern + dataflow |
| CodeQL (semantic analysis) | 24 months | 36 months | 1.5 | Heavy semantic engine |
| SonarQube (multi-language quality) | 36 months | 48 months | 1.3 | Established baseline |
| Coccinelle (kernel semantic patch) | 12 months | 24 months | 2.0 | DSL + transformation engine |

**Mean ratio (lint-tool baseline)**: 1.66x [anchor: arithmetic mean
of Ratio column above: (2.0 + 1.5 + 1.5 + 1.3 + 2.0) / 5 = 1.66].
This applies to L1 (mechanical layer) ONLY. L2-L6 are not lint-tools
and use distinct per-layer baselines documented in the derivation
table below. Total estimate is NOT a single multiplier on plan-
forge's "inside-view 4 weeks" but the SUM of per-layer estimates
with each layer's own reference class and adjustment factor. The
1.66x figure is preserved for traceability to G1 outside-view
discipline but the actual 16-week total derives from layer-by-layer
composition, not from `4 weeks * 1.66x` (which would yield 6.6
weeks and undercount L2-L6 entirely).

**Plan estimate**: 16 weeks [anchor: per-layer derivation table below
(sum 15.6 -> round 16); 5 reference projects (ruff, semgrep, CodeQL,
SonarQube, Coccinelle) above provide L1 baseline; L2-L6 use distinct
anchors documented per-row in derivation] (G1 outside-view adjusted
with explicit new-category penalty; see derivation below).

**Hard ceiling**: 17 weeks [anchor: 16-week base + 1-week Flyvbjerg
uncertainty buffer for novel-category 10% padding; ref: Flyvbjerg et
al. 2002 "Underestimating Costs in Public Works" cited in External
Voices]. If T13 (api.check core) not complete by week 5 (descope
checkpoint 1), see "Descope Path" below.

**plan-forge v0.1 is a NEW CATEGORY of tool with no exact reference
class.** Existing reference class is PURE LINT tools (mechanical only).
plan-forge adds:

- L1 mechanical (F1-F7 + G1/G2/G3/G5/G7 mechanical parts) -- comparable
  to lint reference class
- L2 multi-provider LLM judges with web search (G4/G6/G8/G9 narrow LLM
  parts) -- no public reference class (closest analogs: research-grade
  LLM-as-judge eval frameworks like RAGAS / DeepEval, which took 18+
  months to mature)
- L3 recursive evidence tier classifier (G10) -- novel; no public analog
- L4 event-sourcing corpus_db with append-only audit ledger -- mature
  pattern from financial/ML-ops audit trails, but novel application
- L5 human arbitration UI surfacing LLM evidence -- inspired by HITL
  patterns in moderation tooling; no public analog for plan-review
- L6 outcomes tracking with self-falsifying abandonment clause -- novel

Honest derivation of 16-week estimate:

| Layer | Reference class | Baseline | Adjustment | Estimate |
|-------|----------------|----------|-----------|---------|
| L1 mechanical | ruff/semgrep | 1 week pure code | 1.66x lint baseline | 1.6 weeks |
| L2 LLM judges (4 prompts, 4 providers, web search) | RAGAS / DeepEval pattern | 2 weeks (1 prompt) | 4 prompts * provider quirks * web search integration | 4 weeks |
| L3 G10 recursive tier | novel | 1 week prompt | 2x novel-category penalty | 2 weeks |
| L4 corpus_db | financial audit ledger pattern | 1 week schema | 1.5x for Alembic + privacy redaction | 1.5 weeks |
| L5 arbitration UI | HITL moderation pattern | 1 week | 1.5x for evidence-bundle UX iteration | 1.5 weeks |
| L6 outcomes + abandonment | novel | 0.5 weeks schema + tombstone | 1x | 0.5 weeks |
| Integration + self-dogfood (T18) + retroactive audit (T19) | -- | -- | -- | 2 weeks |
| 3-cycle code review (T20-T21) | -- | -- | -- | 1 week |
| Buffer (Flyvbjerg uncertainty for novel category, ~10% of 14.1) | -- | -- | -- | 1.5 weeks |
| **Total** | | | | **15.6 weeks (~16 weeks)** |

**Honest range**: 14-17 weeks for full v0.1 with G1-G10. The prior "4
weeks initial estimate" was the inside view that G1 itself identifies as
planning fallacy bait. Discarded; not a stretch goal, not a target,
not a cap.

### Descope Path (4 checkpoints)

| Week | Trigger | Action |
|------|---------|--------|
| 5 | T13 (api.check core, F1-F7 + G1/G2/G3/G5/G7 mechanical) not done | LLM web search (E1) deferred to v0.2; v0.1 mechanical-only-judge mode shipped (G6/G8/G9 mechanical parts only; G10 deferred) |
| 8 | corpus_db (T22-T24) + arbitration scaffold (T25-T27) not done | corpus_db ships as read-only ledger (no arbitration capture, no outcomes write); H1 + H3 deferred to v0.1.1 |
| 12 | G9 + G10 (T29-T31) not done | G9 mechanical anchor-citation check ships; G9 LLM verify + G10 recursive tier deferred to v0.1.2 |
| 16 | Hard ceiling | Any remaining items deferred to v0.2; ship what works |

Each checkpoint is a release point; v0.1 ships at week 16 with all
descope decisions accumulated. Quality (3-cycle review passing) takes
precedence over completeness; partial G coverage is acceptable, but
mechanical layer (F1-F7 + 5 of 8 G mechanical parts) is non-negotiable.

## Pre-mortem (G3 self-dogfood)

Imagine plan-forge v0.1 has shipped late 2026 or did not ship. It
failed. Top 7 causes, ranked by probability:

### PM1: v0.1 took 17+ weeks not 16; week-16 hard ceiling hit, descope cascade triggered, ship is partial; user attention exhausted

- **Early warning**: T13 (api.check core) not done by week 5 (descope
  checkpoint 1) -- this is the canary
- **Counter**: descope per Reference Class section's checkpoint table;
  ship mechanical-only-judge mode at wk5; G9/G10 deferred to v0.1.x

### PM2: G1-G10 enforcement too strict; every real plan FAILs T34 retroactive audit; users (Minxi) abandon

- **Early warning**: T34 retroactive audit shows coverage > 95% on
  Phase 2 plans (sounds good but means every G fires; users perceive
  as nag tool)
- **Counter**: tune severity thresholds (BLOCKER vs HIGH vs MEDIUM);
  allow per-plan opt-out with explicit rationale via inline marker;
  track opt-out rate as quality metric in outcomes table

### PM3: 0 external users besides Minxi; plan-forge becomes personal tool

- **Early warning**: month 6 (post-ship) still 0 external imports /
  0 GitHub issues / 0 stars
- **Counter**: acceptable per SC-3 ROI (forge-code retroactive value
  alone justifies build cost); v0.2 considers outreach (HN, GitHub
  release notes) if value demonstrated; tracked but not gating

### PM4: Multi-LLM provider tool_use ecosystem fragments; integration breaks silently after ship

- **Early warning**: 2+ providers' tool_use breaks in same month;
  cost cap repeatedly exceeded; users see "no_search_judgment" tier
  > 30% of evidence
- **Counter**: weekly integration test catches silent breakage;
  per-provider feature-detection at startup; mechanical-only fallback
  mode if all 4 fail; documented in README

### PM5: Self-dogfood loop becomes religious; plan-forge own development paralyzed by perfect self-enforcement

- **Early warning**: 3+ days spent on PLAN.md polish without code
  progress; T04 manual walkthrough repeats with no implementation
- **Counter**: same as forge-code lesson L2 (polish stage is scope-
  wrong signal, not polish-needed signal); T04 is best-effort, not
  gate; T33 (post-implementation) is the real self-check

### PM6: G10 recursive cost / latency blow-up; G10 LLM calls per plan dominate cost; users disable G10 (mode = off recursion)

- **Early warning**: median plan run cost approaches $1.60 (80% of
  $2.00 hard cap) with G10 enabled OR > 30% of runs trigger
  mechanical-only fallback; user complaints about run time
- **Counter**: recursion depth cap at 2 (hard); cache G10 tier
  classifications by evidence-hash with 1-week TTL; document opt-out
  pattern (`--skip-g10` for fast iteration) WITHOUT making it a
  bypass for verdict gating (G10-skipped runs marked as TIER_UNVERIFIED
  in corpus_db, surface to human in arbitration); v0.2 explores
  cheaper tier classifier model

### PM7: Arbitration UX rejected by user; mode=off becomes default in practice; H1 layer dead code

- **Early warning**: SC-17 retroactive shows arbitration_mode=off
  used in > 30% of runs (visible in corpus_db); user reports "I just
  ignore the surface, it slows me down"
- **Counter**: redesign bundle.py for scan-friendly markdown (10-line
  summary first; details expandable); test bundle on 5+ real
  arbitration cases with Minxi UAT before v0.1 ship; if still
  rejected, simplify H1 to "annotation log only" mode where LLM
  evidence persists but no UI surface; rejection itself becomes an
  outcomes-table data point informing v0.2 redesign

## Chaos Response (G5 self-dogfood)

| Scenario | Behavior | Verdict |
|----------|----------|---------|
| Claude API outage during plan-forge invocation | L1 mechanical (F1-F7 + G1/G2/G3/G5/G7 + mechanical parts of G4/G6/G8/G9/G10) work offline (pure Python); L2 LLM Part B's degrade to "indeterminate" with explicit warning; mechanical verdict still emitted | SURVIVE (degraded but functional) |
| User submits non-English plan (German / Spanish / Chinese) | F1-F7 regex-based checks mostly language-agnostic; G1-G10 section name detection needs i18n translation table; LLM prompts work natively (LLMs multilingual) | DEGRADE (v0.1 English + Chinese hedge regex; full i18n in v0.2) |
| Malicious plan markdown (huge file, embedded scripts, unicode tricks, prompt-injection attempting to manipulate LLM gate verdict) | parser sanitizes; file size cap 100KB enforced; no script execution; non-ASCII flagged but not blocked; LLM prompts isolate plan content via clear input/output delimiters; prompt-injection mitigated by narrow LLM role (per-SC, per-citation, per-anchor; LLM cannot return arbitrary verdict for whole plan) | SURVIVE (security boundary enforced; injection surface narrowed by L2 design) |
| G10 recursive tier classifier hits depth-2 cap on a deeply-cited evidence chain | Per Module Designs `g10_evidence_tier.run` recursion_depth >= max_depth branch: returns Finding(G10.recursion_cap, MEDIUM, "escalate to human"); arbitration surface for that evidence chain | DEGRADE (gracefully escalates; does not crash; corpus_db records escalation for v0.2 tuning) |
| corpus_db SQLite lock contention from concurrent CLI invocations (e.g., 2 `plan-forge check` simultaneously) | SQLite default journal mode (WAL) prevents writer-writer deadlock; second writer blocks briefly (< 5s); if lock held > 30s, second writer fails with clear error pointing to `--corpus-db <path>` override OR `--no-corpus` for read-only run | SURVIVE (transient block; explicit guidance on lock conflict) |

**Antifragility**: each failed run produces a finding that feeds
corpus_db. New failure patterns observed across audited plans
strengthen enforcement rules (v0.2 prompt updates use real corpus
data per Prompt Versioning Policy A/B retroactive). plan-forge gets
BETTER from being challenged, not just "resilient" to challenge. The
outcomes table provides empirical feedback: predicted failure modes
that recur become reinforced; predicted failures that never manifest
become candidates for severity downgrade or removal.

## Scope Challenge (G7 self-dogfood)

### Q1: Does this need to exist?

YES. Empirical evidence:

- 122-skill Claude Code library survey: 0 of 122 skills cover G1-G8
  epistemologically. plan-review skill (closest analog) implements mechanical
  PBR but does not enforce any G-check.
- forge-code v2.0 Phase 2 took 50+ rounds of cross-AI panel review across 6
  sub-plans; per ai-review-strategic-limits memory, panel converged to wrong
  architecture multiple times, requiring 5+ user strategic interventions.
- corpus of 7 anti-patterns + synthesis of 8 epistemological frameworks
  exists as memory entries with no enforcement tool; theoretical foundation
  without tool means knowledge does not transfer to future plans.

Without plan-forge, the next 5 forge-code phases (3-7) would consume estimated
150+ additional AI panel rounds with 50% strategic drift risk per phase, plus
every future Minxi plan repeats Phase 2 anti-patterns.

### Q2: Name 3 real consumers

1. `~/code/forge/.planning/milestones/v2.0-phases/02-state-machine-rewrite/`
   (immediate use case: retroactive audit; expected to produce 4+ FAIL or
   VISION verdicts, validating tool catches what 50+ rounds missed)
2. `~/code/forge/.planning/phases/` (forge-code Phase 3+ if revived after
   retro audit; plan-forge gates Phase 3 plan before AI panel runs)
3. `~/code/ai-learning/ROADMAP.md` (Minxi's existing 75-day AI/C++ learning
   plan; G1-G8 directly applicable: missing reference class? missing pre-
   mortem? missing risk taxonomy?)

Beyond Minxi's repos: any plan author using Claude Code (skill adapter), any
CI pipeline reviewing plans (CLI adapter), and any Python tool embedding
plan quality gate (library API).

### Q3: What does "do nothing + document" cost?

Quantified:

- forge-code Phase 3-7: estimated 150+ AI panel rounds * 3 models = 450+
  model invocations
- 50% strategic drift risk per phase * 5 phases = 25+ user strategic
  interventions
- Every future Minxi plan (estimated 5-10 in 2026) repeats Phase 2 anti-
  patterns with no learning capture
- Corpus + synthesis + LEARNINGS remain memory entries with no enforcement;
  knowledge does not transfer to AI-assisted plans by other users

Cost of inaction: ~300 model invocations + 25 user interventions + 0
institutional learning capture per year, recurring.

Cost of plan-forge v0.1: 16 weeks one-time (G1 outside-view; honest
range 14-17 weeks per Reference Class) + LLM API costs (median
~$0.75/plan, hard cap $2.00; projected 100 checks in year 1 = $75-200
typical, $500 worst case).

Payback: positive within 1 quarter of v0.1 ship.

### Q4: Barbell check (Taleb)

- **Conservative baseline**: forge-code v1.0 production skill (already works
  end-to-end for code review per kimi-next-key.sh demo)
- **High-risk bet**: plan-forge v0.1 epistemological gate (this; new
  category of tool, no reference class for the G-layer)
- **Mediocre middle ground avoided**: extending forge-code v2.0 Phase 3+
  without addressing review process flaws (would compound 50+ round costs
  on each subsequent phase)

Barbell check passes: plan-forge is the high-risk high-reward bet, not
the mediocre extension of an already-failing approach.

## External Voices (G8 self-dogfood)

### Primary non-AI sources

- Popper, *The Logic of Scientific Discovery* (1934). Falsifiability
  doctrine; G6 foundation.
- Klein, "Performing a Project Premortem", Harvard Business Review (2007).
  G3 mandatory pre-mortem foundation.
- Kahneman & Tversky, "Intuitive Prediction: Biases and Corrective
  Procedures" (1979). Planning fallacy origin.
- Wucker, *The Gray Rhino* (2016). G2 gray rhino bucket.
- Taleb, *The Black Swan* (2007); *Antifragile* (2012). G2 black swan
  bucket + G5 antifragility audit + G7 barbell.
- Tetlock & Gardner, *Superforecasting* (2015). G4 calibration discipline
  + G8 source diversity foundation.
- Flyvbjerg et al., "Underestimating Costs in Public Works" (2002). G1
  reference class forecasting.
- Travassos et al., "Reading Techniques for OO Design Inspections" (2001).
  Defect taxonomy used in mechanical F-checks.
- IEEE 830 (specifications quality attributes). PBR foundation.
- Fagan, M., "Design and Code Inspections to Reduce Errors in Program
  Development", IBM Systems Journal (1976). Inspection process structure.

### Dissenting view (red team's strongest argument)

> "Plan review is theater; just ship and iterate. Perfecting plans delays
> learning from real users. forge-code v1.0 (kimi-next-key.sh demo) proved
> a minimal plan + ship works better than a 50-round-perfect plan."

**Strongest argument**: agile / lean startup philosophy says learning from
production is faster and cheaper than learning from plan review. v1.0 forge
demo is concrete evidence that minimal-plan + ship outperformed v2.0's
plan-heavy approach in catching real bugs.

**Counter-argument**: plan-forge targets domains where ship-and-iterate is
too expensive to fail: architecture decisions (cannot revert mid-system),
migration plans (cannot un-migrate a database), policy plans (cannot un-
deploy a regulation), research grants (cannot un-spend public money). For
those domains, plan review is not theater; it is the only feedback loop
that fires before failure cost becomes irreversible.

**Accommodation**: plan-forge is NOT the right tool for ship-and-iterate
domains. If your domain tolerates ship-then-revert (typical: side projects,
experimental scripts, A/B tests, prototypes), plan-forge's friction-by-
design is wrong fit. plan-forge targets domains where rollback is
impossible or extremely costly (architecture, migration, policy, grant
applications, regulatory plans, irreversible commitments).

This is not a workaround flag. It is an honest acknowledgment of tool
scope. No `--bypass`, `--skip-gates`, or `--ship-and-iterate` flag exists
in plan-forge v0.1+. Per MANIFESTO Commitment 1: G1-G10 gates are NOT
optional. If a user can bypass plan-forge by adding a CLI flag, plan-forge
has failed.

Users in ship-and-iterate domains should use lighter tools (e.g.,
`plan-review` skill for mechanical PBR-only) and accept that plan-forge
is not their tool.

### Historical failure case (similar approach that did not work)

**ISO 9000 (1987-)**: international quality management standards that
proliferated across industries through certification programs.

**Outcome**: many organizations achieved ISO 9000 certification without
quality improvement. Compliance with checklist replaced actual quality
thinking. The standard became a ritual.

**Lesson for plan-forge**: enforcement without ground-truth validation
produces ritualistic compliance. Mandatory sections in PLAN.md (G1-G8) can
become boilerplate that gets filled in just to pass plan-forge, without
genuine epistemological work.

**plan-forge counter**: SC-3 retroactive audit validates real bug catch
ratio. If plan-forge produces 0 catches across 10+ audits, it has become
ritualistic and is abandoned. The empirical-grounding commitment in
MANIFESTO Section 6 makes this an explicit accept/reject criterion, not
a face-saving avoidance.

## Reviewer Focus (historical; this section guided R2; preserved for traceability)

NOTE per R4 T7: this section was written for R2 (R1-fix verification)
and remains as historical record of what R2 reviewers focused on.
R3 and R4 reviews proceeded with their own prompts. R4 verdict
(b) STRATEGIC FIX + PASS closes the review phase; no R5 prompt is
expected. The "R2" references below are NOT stale errors; they
describe what was asked of R2 specifically.

R2 cross-AI reviewers should pay particular attention to:

1. **R1 fix sufficiency**: are R1 BLOCKERs B1-B5 fully closed by the
   changes documented in Appendix B? Specifically:
   - B1: is the `Accommodation` section now a coherent honest scope
     statement, not a covert bypass?
   - B2: does the new 16-week estimate honestly reflect new-category
     uncertainty without falling back to inside-view bait?
   - B3: do the 5 defense layers (per MANIFESTO Section 11) actually
     defend against the AI-detect-AI circularity, or are some layers
     cosmetic?
   - B4: are G6/G8/G9/G10 v0 prompts production-ready, or do they
     still rely on prompt engineering not specified here?
   - B5: is SC-3's coverage >= 60% threshold defensible, or arbitrary?

2. **Internal consistency**: do G1-G10 enforcement specs in
   Requirements match SC table fail-conditions, module designs, and
   the v0 prompt bodies?

3. **G6 self-application**: does this PLAN have explicit fail-
   condition for each SC? Are the fail-conditions measurable
   predicates (per G6 v0 prompt definition)?

4. **G9 self-application**: does this PLAN's quantitative claims
   (16-week estimate; cost soft cap $0.75 / hard cap $2.00; 60%
   coverage threshold; 6-month abandonment trigger) each have an
   anchor? Are anchors verifiable?

5. **G10 recursion bound**: is depth-2 cap sufficient? Could a
   pathological plan trigger > 2 levels of evidence chains? Should
   recursion default to depth-1 with depth-2 as opt-in?

6. **Risk register completeness**:
   - GR (new): G10 recursive cost / latency blow-up -- mitigation
     adequate?
   - GR (new): arbitration UX rejection (users disable) -- counter
     adequate?
   - GR (new): corpus_db SQLite single-writer constraint -- enough?
   - BS5 (new): G10 systematic tier bias -- survival plan adequate?

7. **Pre-mortem ranking**: PM1-PM7 ordered by perceived probability.
   PM6 (G10 cost) and PM7 (arbitration UX) are new per R1. Probability
   estimates of PM6 vs PM7 reasonable, or should be swapped/combined?

8. **Architectural commitment robustness**: is "internalize, not
   reference" sustainable now that scope includes corpus_db (new sql
   dependency: SQLAlchemy + Alembic), tool_use web search (httpx),
   and arbitration UI?

9. **Multi-LLM tool_use strategy**: 4 providers with web search is
   more ambitious than the original 4-provider vote. Should v0.1
   ship with web search disabled by default (`--no-search`) and
   enable explicitly? Or is web search the whole point of G9
   anchor-verification and must ship together?

10. **Scope creep early warnings**: 4 checkpoints listed; is the
    descope ladder at each checkpoint coherent or arbitrary? E.g.,
    week-5 descopes "LLM web search to v0.2" but week-12 descopes
    "G10 to v0.1.2" -- consistent?

11. **Self-falsifying clause robustness** (SC-19): is "6 months no
    outcomes" the right threshold? Too aggressive (real users may
    not record outcomes for non-failure reasons)? Too lenient (6
    months is a long time to discover the tool is ritualistic)?

12. **MANIFESTO -> PLAN coherence**: do MANIFESTO Sections 11 + 12
    (Defense-in-Depth + Recursive Epistemic Discipline) map cleanly
    to PLAN architecture / requirements / module designs? Are the
    5 defense layers visible end-to-end in the code path?

## Open Questions

(R1 review resolved former Q1 = G6 LLM judge prompt design; former
Q2 = AI-smell regex. Both now in v0 prompt bodies per B4 fix. R2
review M5-DS consolidated 8 items into 3 active + 5 resolved
decisions below.)

### Active questions (need decision before T35 ship)

1. **Cache strategy for LLM calls with tool_use web search**: SHA-256
   of (plan-hash + prompt-hash + model + tool_use-version) -- but
   what about search-result freshness? 1-week TTL too long when
   verifying recent papers; too short when verifying canonical works
   (Popper). v0.1 default: per-prompt TTL config; 1-week for
   canonical, 24h for "recent" prompts; user-configurable. Decision
   needed: which prompts default to "canonical" vs "recent" TTL
   class? Tentative: G8 citation = mixed (canonical for pre-2020,
   recent for 2020+); G9 anchor = recent; G10 tier = recent;
   G4/G6 = canonical. Confirm at T11/T31.

2. **License**: TBD. Defer decision to T21 (Adapter A
   v0.1.0-alpha2). Candidates: Apache 2.0 (permissive; safe for tool
   with corpus_db data flowing through), GPLv3 (stricter; aligns
   with epistemic-rigor mission). Decision factor: do we expect
   corporate adoption (Apache) or copyleft reinforcement (GPL)?

3. **G10 prompt evolution trigger**: v0 prompt classifies T1-T4
   based on citation count + retraction status; misses subtle cases
   (e.g., paper retracted then corrected). v0.1 ships v0. Decision
   needed: what corpus_db signal triggers v1 promotion? Tentative:
   >= 20 G10 verdicts retrospectively flagged wrong by arbitration
   OR outcomes (i.e., T1 evidence that led to FAIL/VISION
   subsequently shown spurious). Confirm at first v0.1.x retro
   audit.

### Resolved decisions (recorded for traceability; no further action)

- **Scaffold template variations**: v0.1 ships `default.md.j2` only;
  add `roadmap.md.j2` / `pitch.md.j2` / `grant.md.j2` in v0.2+ ONLY
  IF outcomes-table data shows template-type demand (>= 3 distinct
  plan types in corpus_db plan_runs).
- **Versioning policy**: semver. v0.x = pre-stable. v1.0 promotion
  criteria: SC-3 >= 60% retroactive coverage AND >= 1 external user
  adopts AND >= 10 outcomes recorded showing prediction precision >
  50%. Until v1.0: minor version per layer milestone (v0.2 =
  G4/G6/G9 LLM Part B if descoped at week 5; v0.3 = i18n; etc).
- **Multi-user corpus_db**: v0.1 single-user only. v0.2+ considers
  shared NFS corpus_db. Schema is forward-compatible (no UUID
  author column added; would be v0.2 migration). README documents
  single-writer constraint.
- **Outcomes recorder identity**: v0.1 captures recorder verbatim
  (free text). v0.2+ may add identity provider integration. Not a
  v0.1 blocker.
- **Tool naming**: package = `plan_forge` (Python); CLI = `plan-
  forge`; Claude Code skill = `plan-forge`. No collision with
  `forge` skill family confirmed via 122-skill survey.

## CHANGELOG

Plan-forge v0.1 PLAN versions (per F5 R-tag pruner: history outside
body):

- 2026-05-19 v5 (this revision): R4 cross-AI review integrated;
  3-model consensus verdict was (b) STRATEGIC FIX + PASS. Closed
  R4 strategic items: S1 (G9 self-application; canonical
  declarations of 16-week / $0.75 / $2.00 / 60% / 6-month / 1.66x
  given inline `[anchor: ...]`; canonical-declaration convention
  added to G9 Requirements so downstream references do not need
  duplicate anchors), T2 (MANIFESTO Section 3 "eight" -> "ten";
  G9/G10 added to concerns table; Section 8/10 "G1-G8" -> "G1-G10";
  Commitment 1 updated), T3 (PLAN "Five-layer defense" -> "Six-
  layer" aligned with MANIFESTO Section 11's 6 enumerated layers;
  table expanded to show L1-L6 explicitly). Closed R4 tactical:
  T1 (G10 degraded-provider guard moved BEFORE try/except to
  prevent spurious tier_coercion Finding), T4 (T08 narrowed to
  P1/P2/P5; T17 owns P6 alone), T5 (arbitrations.human_verdict
  gained CHECK constraint matching M-1 canonical 4-value vocab),
  T6 (Appendix A "line 426" reference clarified as v0-historical),
  T7 (Reviewer Focus section header marked historical R2-specific
  with traceability note). R4 verdict: PASS; proceed to T05
  implementation. No R5 expected. PM5 anti-pattern explicitly
  acknowledged: 4 review rounds + 36 fixes + 0 source code is the
  exact "polish stage = scope wrong" signal; further review delayed
  T05 has no review-loop justification.

- 2026-05-19 v4 (R3 revision): R3 cross-AI review integrated.
  Closed R3 BLOCKERs: RN-1 ($0.50 residual refs across Known Risks /
  PM6 / BS7 / Open Q / Scope-Challenge Q3 / Reviewer Focus /
  CHANGELOG entry replaced with $0.75 soft / $2.00 hard), RN-2
  (SC-5 G4 Part B deferred-to-v0.1.1 exemption added explicitly),
  RN-3 (G10 prompt UNCERTAIN instruction removed; LLM always emits
  T1-T4; recursion-cap deferral is code-path Finding not LLM
  verdict), RN-4 (LLMEvidence.tier default = EvidenceTier.UNCLASSIFIED
  added to allow G4/G6/G8/G9 instantiation before G10 runs), RN-5
  (G4 code-block skip changed from per-line fence-only to in-block
  state machine), RN-6 (cost model recalibrated honestly: plan-size-
  aware projection formula; $0.75 = typical-plan median; $2.00 =
  large-plan operating budget). Closed R3 MEDIUMs: M-1 (arbitration
  vocab unified to verified/unverified/deferred/abstain canonical),
  M-2 (SC-28 lifted G10 prompt search cap to 4 to match prompt
  body), M-3 (G10 EvidenceTier coercion safe with try/except + T3
  fallback + Finding emit), M-4 (G10 degraded-provider evidence
  kept UNCLASSIFIED not misclassified T4), M-5 (T17 redefined to
  P6 metadata-currency only; T08 retains P1/P2/P5; no overlap).
  Closed R3 LOWs: G4 regex 11-word list authorized in Requirements;
  Drafted date updated; G10 no-op behavior documented for descope
  path. Deferred to R4 / T05 implementation: SC-2a re-run on R3
  PLAN (M-6, not a R3-blocking issue).

- 2026-05-19 v2 (R1 revision): R1 cross-AI review integrated.
  Closed B1 (deleted --ship-and-iterate flag; Accommodation rewritten
  as honest scope statement), B2 (16-week estimate replaces 4-week
  inside-view; explicit new-category reference class derivation),
  B3 (6-layer defense via MANIFESTO Sections 11+12 + narrowed LLM
  role to per-SC/per-citation/per-anchor/per-evidence questions),
  B4 (G6/G8/G9/G10 v0 prompts inlined; Prompt Versioning Policy
  added), B5 (SC-3 revised to use independent 02-LEARNINGS.md
  coverage >= 60%). Added: G9 Feasibility Anchor gate; G10 Recursive
  Evidence Provenance gate; corpus_db event-sourcing 6-table schema
  with Alembic; arbitration_mode 4-mode config (default
  on_split_evidence_rich) with human-in-loop UI in Adapter B;
  outcomes table for empirical track record; tools/abandon.py +
  SC-19 self-falsifying clause; LLM web search via tool_use across
  4 providers with cost cap (soft $0.75 / hard $2.00, raised from
  initial $0.50 per R2/R3 reviews); 4 descope checkpoints (week
  5/8/12/16); Pre-mortem PM6 (G10 cost) + PM7 (arbitration UX)
  added; Chaos Response 2 new scenarios. See Appendix B for full
  R1 fix mapping.

- 2026-05-18 v0 (initial draft): initial scope after architecture
  correction (internalize, not reference; library-first; multi-LLM);
  supersedes /tmp/draft_20260518_202304_plan-forge-v01-scope.txt
  (v1) and /tmp/draft_20260518_203128_plan-forge-v01-scope-v2.txt.

## Appendix A: Self-Dogfood Walkthrough (T04)

**STATUS: NEEDS RE-RUN** -- This walkthrough was executed on v0 PLAN
(2026-05-18) with G1-G8 only. R2 PLAN (this file) added G9/G10,
expanded SC table 15 to 28, expanded PM 5 to 7, and revised G6 LLM role.
Appendix A data below is HISTORICAL and does not reflect current PLAN
state. SC-2a requires re-running T04 on R2 PLAN before T05
implementation begins. Expected changes: G9 (new; needs anchor check),
G10 (new; needs evidence tier check), G6 (verdict criteria changed per
H-A fix), SC count (28 not 15), PM count (7 not 5).

Manual G1-G8 enforcement walkthrough against this PLAN.md, executed
2026-05-18. Verdict per check with evidence. Result feeds T18 automated
self-check after library implementation.

### G1 Reference Class Forecasting -- PASS

- `## Reference Class` section present (line 426 in v0; current line
  shifted due to R1-R4 expansion; section presence verifiable by
  heading grep regardless of line number)
- 5 historical projects listed (ruff, semgrep, CodeQL, SonarQube, Coccinelle)
- Each row has name + scope + actual duration + ratio
- Mean ratio computed (1.66); outside-view estimate computed (6.6 weeks)
- Caveat declared: existing reference class is pure-lint; plan-forge has no
  exact reference class for G-layer; honest range widened to 4-8 weeks

### G2 Risk Taxonomy (3-class) -- PASS

- `### Known Risks` subsection: 5 risks with probability + impact + mitigation
- `### Gray Rhinos` subsection: 5 rhinos with denial_reason + counter
- `### Black Swans` subsection: 5 swans with survival_plan
- All three buckets non-empty
- Gray Rhino denial-reasons are explicitly framed as "why people will ignore"

### G3 Pre-mortem (mandatory) -- PASS

- `## Pre-mortem` section present
- 5 ranked failure causes (PM1-PM5)
- Each has `early_warning` field and `counter` field
- PM1-PM5 ordered by perceived probability (PM1 most likely failure)

### G4 Probability Calibration -- PASS (with caveat)

- Initial grep found 4 hedge instances; 3 fixed in T04:
  - Line 442 `likely higher` -> `(70% probability) higher`
  - Line 447 `Top 5 most-likely causes` -> `Top 5 causes, ranked by probability`
  - Line 648 `most likely combined` -> `potentially combined <!-- plan-forge:
    hedge-ok (reviewer-question) -->`
- One self-reference remains (line 78: G4 definition listing hedge words to
  detect). This is the check's own meta-text, not a real hedge. G4
  implementation must skip matches within its own definition or in code-
  fenced blocks. v0.1 implementation note: exempt lines containing "G4
  Probability Calibration" definition context.

### G5 Antifragility Audit -- PASS

- `## Chaos Response` section present
- 3 stressor scenarios: Claude API outage / non-English plan / malicious markdown
- Per-scenario verdicts: SURVIVE / DEGRADE / SURVIVE
- 0 scenarios show "break"
- Antifragility note: corpus expands from failed runs; tool gets better from
  challenge (this is stronger than "resilient")

### G6 Plan-vs-Vision Falsifiability -- PASS (mechanical part only)

- SC table contains 15 rows (SC-1 through SC-15)
- Every SC has explicit Fail Condition column with falsifiable predicate
- LLM judge part (multi-LLM majority vote on plan-vs-vision) NOT executed in
  T04 because LLM clients not yet implemented. This part of G6 will run in
  T18 (post-implementation self-dogfood). Risk: LLM judge could classify this
  PLAN as vision; mitigation: SC fail-conditions are concrete and measurable
  per inspection.

### G7 Scope Challenge / Barbell -- PASS

- `## Scope Challenge` section present
- Q1 (Does this need to exist?) answered with empirical evidence (122-skill
  survey result + forge-code 50+ round cost)
- Q2 (3 real consumers) answered with file paths
- Q3 (do-nothing cost) answered with quantified cost (300 invocations + 25
  interventions per year)
- Q4 (barbell check) answered with explicit conservative + high-risk + middle
  avoided

### G8 Collective Bias / Source Diversity -- PASS

- `## External Voices` section present
- 10 primary non-AI sources cited with attribution (Popper, Klein, Kahneman,
  Wucker, Taleb, Tetlock, Flyvbjerg, Travassos, IEEE 830, Fagan)
- Dissenting view explicitly addressed: "plan review is theater; just ship"
  agile/lean argument with strongest framing and counter-argument
- Historical failure case: ISO 9000 ritualistic compliance with lesson and
  plan-forge-specific counter
- AI-smell LLM judge NOT executed in T04 (same reason as G6); will run in T18

### Mechanical F1-F7 spot-check

- F1 SC-test traceability: deferred (no test list yet; T07 produces it)
- F2 Duplicate-fact: spot-checked phrase "internalize, not reference" -- 2
  occurrences (title + CHANGELOG); within F2 threshold of 3+
- F3 Cross-plan invariant: deferred (PLAN references external file paths;
  T03 of plan-forge has no cross-plan dependency since this is the first plan)
- F4 Temporal anchor: spot-checked "before" + "after"; only legitimate uses
  (e.g., "before any code shipped" in MANIFESTO commitment text)
- F5 R-tag pruner: 0 R-tags in body; CHANGELOG section present for future
- F6 Preamble-vs-body: not applicable (no orchestrator preamble for v0
  initial draft)
- F7 ASCII: PASS (verified by `grep -P '[^\x00-\x7F]'`)

### Overall self-dogfood verdict (T04)

- engineering_verdict: PASS (mechanical checks)
- epistemic_verdict: PASS (G1-G8 all sections present with content)
- LLM-dependent parts of G6 + G8 deferred to T18 post-implementation

**T04 conclusion (R1 update)**: original v0 PLAN was reviewed by Kimi,
DeepSeek, and Mimo on 2026-05-19. 5 BLOCKER consensus findings (B1-B5)
required design-level changes; full mapping in Appendix B. R2 PLAN
(this file) integrates those fixes. T04 will re-run on R2 after T02b
(MANIFESTO Sections 11+12 written) to validate G1-G10 self-application
including the new gates G9 and G10. If T04 re-run fails on R2, this
indicates the R1 fixes themselves have created new self-application
gaps; redesign rather than rationalize.

## Appendix B: R1 Cross-AI Review Fix Mapping

R1 cross-AI review of v0 PLAN by Kimi, DeepSeek, and Mimo on
2026-05-19 produced 3 / 5 / 3 BLOCKER findings respectively. After
deduplication, 5 BLOCKER findings (B1-B5) reached cross-model
consensus (>= 2 models). This appendix maps each BLOCKER to the
specific PLAN changes in v2 (this file).

### B1: --ship-and-iterate CLI flag contradicts MANIFESTO

**Consensus (3/3 models)**: External Voices section's Accommodation
introduced a `--ship-and-iterate` CLI flag that bypassed L3
epistemological gates, directly violating MANIFESTO Section 5 "NOT
optional" and Commitment 1 "G1-G10 are gates not suggestions".

**Fix location**: External Voices > Accommodation.

**Fix**: deleted the flag. Rewrote Accommodation as an honest scope
statement: "plan-forge is NOT the right tool for ship-and-iterate
domains." No bypass mechanism exists in v0.1+. Users in ship-and-
iterate domains use lighter tools (e.g., plan-review skill).

**Verification**: grep PLAN.md for `--ship-and-iterate` finds only
(a) the negated reference in External Voices > Accommodation
("No `--bypass`, `--skip-gates`, or `--ship-and-iterate` flag
exists"), and (b) this Appendix B B1 entry and CHANGELOG (historical
fix description). No implementation specification defines this flag.
Final check: grep `src/plan_forge/` post-implementation should return
0 matches.

### B2: 4-week hard cap contradicts G1 outside-view derivation

**Consensus (2/3: Mimo, DeepSeek)**: Reference Class section's G1
self-application computed outside-view-adjusted estimate of 6.6
weeks, but also declared a "hard ceiling: 4 weeks". The cap was the
inside-view that G1 identifies as planning fallacy bait.

**Fix location**: Reference Class section + Implementation Tasks
"Hard cap" footnote + Goal acceptance criterion.

**Fix**: deleted "4 weeks" entirely (not as stretch goal, not as
target, not as cap). New plan estimate: 16 weeks derived from
layer-by-layer reference class analysis with explicit new-category
penalty for L2-L6. Hard ceiling 17 weeks. 4 descope checkpoints
(week 5/8/12/16) replace the single inside-view-bait checkpoint.
G1 reference-class table preserved (5 lint-tool projects) but
honest derivation table added explicitly noting plan-forge is a
new category.

**Verification**: grep PLAN.md for "4 weeks" should return only this
Appendix B entry and the v0 historical reference in CHANGELOG.

### B3: Multi-LLM vote on AI-generated plans is recursive

**Consensus (3/3 models)**: using LLMs to detect AI-generated plan
defects inherits the same training-corpus bias that produces the
plans. Multi-provider vote reduces individual model bias but does
not eliminate collective AI bias.

**Fix locations**:
- MANIFESTO Section 11 (new): "Acknowledged Fundamental Limitation +
  Defense in Depth" -- explicitly admits the leak; documents 5
  independent layers (mechanical / narrow-LLM / corpus / arbitration
  / outcomes).
- Requirements > Epistemological layer: LLM role narrowed to per-SC
  measurability (G6.B), per-citation resolvability (G8.B), per-
  anchor feasibility (G9.B), per-evidence tier (G10.B). NOT grand
  "plan or vision" judgments.
- Requirements > Arbitration layer (H1): when LLM evidence is rich
  and split, human is final arbiter (mode=on_split_evidence_rich
  default).
- Requirements > Corpus layer (H2): corpus_db is independent ground
  truth accumulator; SC-3 validates against pre-existing 02-
  LEARNINGS.md (drafted pre-plan-forge).
- Requirements > Outcomes layer (H3): empirical track record
  validates plan-forge's own predictions over time.

**Verification**: every LLM gate's prompt body in PLAN explicitly
constrains "Do not judge the plan as a whole" or equivalent
narrowing language. MANIFESTO Section 11 enumerates 5 layers.

### B4: G6 prompt design listed as "open question" while G6 is a gate

**Consensus (2/3: DeepSeek, Mimo)**: G6 was declared a gate (verdict
VISION possible) but the LLM judge prompt was listed in Open
Questions. A gate without specified behavior is not a gate.

**Fix locations**:
- Module Designs > LLM Prompt Bodies (v0): inlined v0 prompts for
  G6, G8, G9, G10 each with >= 3-4 examples covering distinct
  verdict categories. Fully ASCII. Single-line JSON output spec.
- Module Designs > Prompt Versioning Policy: prompts are CONTRACT;
  filename suffix is version; corpus_db records prompt_version;
  fixtures required per version; A/B retroactive validation for
  promotion.
- Open Questions: deleted former Q1 (G6 prompt) + former Q2 (AI-
  smell regex). Q5 (G10 prompt evolution) added for future v0.2+
  refinement.
- SC-21..SC-24 added: prompt body present + N examples per gate.
- SC-25..SC-26 added: prompt_version column + fixture coverage.

**Verification**: PLAN.md grep for prompt body markers ("g6_sc_
measurability_v0", "g8_citation_resolvability_v0", "g9_feasibility_
anchor_v0", "g10_evidence_tier_v0") each returns >= 1 hit in Module
Designs.

### B5: SC-3 retroactive audit was circular validation

**Consensus (2/3: DeepSeek, Mimo)**: SC-3 originally required
"at least 4 of 7 forge Phase 2 plans produce FAIL or VISION
verdict" -- but the verdict was plan-forge's own output, used as
its own ground truth.

**Fix location**: Goal acceptance criterion + SC-3 row in Success
Criteria table.

**Fix**: SC-3 revised to compute coverage against the INDEPENDENT
02-LEARNINGS.md problem list (drafted pre-plan-forge by 50+ rounds
of cross-AI panel + manual extraction; the documentation predates
the tool by months). Coverage = (problems_caught_by_plan_forge /
total_problems_in_02-LEARNINGS.md) >= 60%. The 60% threshold itself
is calibrated to allow some false negatives (perfect detection is
suspicious) while requiring meaningful catch rate.

**Verification**: SC-3 fail-condition references 02-LEARNINGS.md
by path. Goal acceptance references same path. No circular
dependency on plan-forge's own verdict.

### R1 HIGH and MEDIUM items (selected)

R1 review also produced HIGH and MEDIUM findings, most absorbed
into BLOCKER fixes. Selected stand-alone HIGH fixes:

- H1 (arbitration mode config): default `on_split_evidence_rich`,
  4 modes including `off`, user-configurable. Module Designs >
  arbitration/surface.py.
- H2 (corpus_db design): SQLAlchemy 2.0 + Alembic; 6-table event-
  sourcing schema; append-only with documented exceptions
  (plan_runs.finalize + llm_evidence.tier monotonic). Module Designs
  > corpus/ subpackage + schema.sql DDL.
- H3 (ABANDONMENT.md): `tools/abandon.py` generates tombstone with
  revival criteria + revival process when SC-19 trigger fires.
  Module Designs > tools/abandon.py.
- H4 (atomic 16-17 week scope): no incremental ship of v0.1 layers;
  ship complete or descope per 4-checkpoint ladder. Implementation
  Tasks T01-T35 + Reference Class > Descope Path table.

### R1 E1/E2/E3 (LLM web search + G9 + tiered verdicts)

E1 (web search), E2 (G9 feasibility anchor), E3 (4-tier verdict
labels: RESOLVED_VIA_SEARCH / RESOLVED_BY_KNOWLEDGE / UNCERTAIN /
UNRESOLVABLE) added per user follow-up on B3/B4 discussion. Driver:
LLMs evaluating plan feasibility must do what engineers do --
search for prior art, replication evidence, comparable timelines.
A constrained "no-search" prompt failed to model engineering
review.

### R1 G10 (recursive evidence tier)

G10 added per user follow-up after E2 was introduced. Driver: LLMs
fetching web evidence inherit the same provenance crisis as the
papers they cite (replication crisis: ~50% psychology papers, 30-
40% ML papers fail replication per Pineau 2020 and OSC 2015). G10
classifies every LLM-cited evidence into T1-T4 tiers; T3/T4-only
chains cannot solely support FAIL/VISION verdicts.

### Self-reflection from R1

During R1 fix integration, two anti-patterns were observed and are
recorded as candidate corpus entries (subject to v0.1 retroactive
audit confirmation):

1. **Scope creep dressed as defense-in-depth**: across the R1
   discussion, each new gate (G9, G10, recursive E3 tiers) was
   defensible in isolation but accumulated to a 16-17 week scope
   that exceeded the original 4-week estimate by 4x. The mid-
   discussion proposal to "scale back to mechanical-only" was
   itself an anti-pattern (different incoherence: a mechanical-only
   "epistemic gate" is misnamed pattern-matcher). The honest
   resolution is to acknowledge plan-forge as a new category with
   no exact reference class and an honest 16-week scope.

2. **AI-detect-AI recursion is not solvable in v0.1**: per
   MANIFESTO Section 11, the leak is acknowledged. Multi-layer
   defense reduces but does not eliminate. Honest scoping per
   MANIFESTO Section 6 (empirical-grounding) means accepting that
   v0.1 ships with this limitation visible to users, and the
   outcomes table over time validates whether the residual leak
   matters in practice.

### Cross-references to upstream sources

- MANIFESTO.md Section 11 (Defense-in-Depth) -- written in T02b
- MANIFESTO.md Section 12 (Recursive Epistemic Discipline) -- T02b
- .planning/R1-REVIEW-SUMMARY.md -- T03b
- ~/code/forge/.planning/milestones/v2.0-phases/02-state-machine-
  rewrite/02-LEARNINGS.md -- independent ground truth for SC-3
- Memory: feedback_ai_review_strategic_limits.md (verified via
  forge-code Phase 2; 50+ rounds did not catch B1 / B2 / B5
  consensus on first pass)
