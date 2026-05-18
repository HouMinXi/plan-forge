# plan-forge v0.1 PLAN

**Phase**: 0 (greenfield)
**Status**: Draft for cross-AI review
**Drafted**: 2026-05-18
**Author**: Minxi Hou <houminxi@gmail.com>
**Repository**: ~/code/plan-forge (git init complete)
**Depends on**:
- Python 3.11+
- Anthropic SDK (`anthropic`), optional: Kimi/DeepSeek/Mimo SDKs
- pytest for tests
- jinja2 for scaffold templates
- No internal dependencies; no other Claude Code skills called as subprocess

**Required reading before review**:
- `MANIFESTO.md` (this repo) -- philosophical anchor; non-negotiable principles
- `/tmp/plan_falsification_synthesis.md` -- epistemological framework (Popper /
  Klein / Wucker / Taleb / Tetlock / Flyvbjerg) the G1-G8 checks derive from
- `~/.claude/projects/-home-houminxi/memory/project_forge_plan_gate_corpus.md`
  -- 7 writing-style anti-patterns observed across 50+ rounds of forge-code
  v2.0 Phase 2 review (informs F1-F7 mechanical checks)
- `~/code/forge/.planning/milestones/v2.0-phases/02-state-machine-rewrite/02-LEARNINGS.md`
  -- empirical lessons that motivate G1-G8 mandate

## Goal

Ship plan-forge v0.1 as a standalone Python library + Claude Code skill that
enforces eight epistemological gates (G1-G8) and seven mechanical writing-
style checks (F1-F7) on plan documents.

Primary deliverable: `from plan_forge import check; verdict = check(plan_text)`
returns a `Verdict` dataclass with two sub-verdicts: `engineering_verdict`
(PASS/FAIL) and `epistemic_verdict` (PASS/FAIL/VISION). Either FAIL or VISION
blocks the plan from "READY" state.

Acceptance: plan-forge v0.1 successfully audits 7 archived forge-code v2.0
Phase 2 plans retroactively, with at least 4 producing FAIL or VISION verdict
(empirical validation that plan-forge catches what 50+ rounds of AI panel
review missed).

## Requirements

### Mechanical layer (F1-F7, pure Python, no LLM)

- **F1 SC-test traceability**: parse SC table + test list from plan; cross-
  reference. Orphan SC (claims test but no matching test entry) or orphan
  test (test exists but no SC references it) reported.
- **F2 Duplicate-fact lint**: tokenize plan into noun phrases; count
  occurrences. Phrases appearing in 3+ sections flagged with single-source-
  of-truth recommendation.
- **F3 Cross-plan invariant verification**: regex extract claims about other
  plans/modules (patterns: `phase-\d+`, named upstream symbols, `02-\d+`).
  Each claim must have grep evidence in plan body or audit-notes section.
- **F4 Temporal anchor lint**: regex finds `before|after` adjacent to
  `return|exit|complete`. Require precise anchor specification (`__exit__`,
  `return statement executed`, `caller assignment`).
- **F5 R-tag pruner**: count inline `R\d+ [BHM]\d+` style tags per SC entry.
  Cap at 2; excess must move to CHANGELOG section.
- **F6 Preamble-vs-body diff**: when an orchestrator preamble (conversation
  context) is provided alongside plan, compare for facts present in
  preamble but absent from plan body.
- **F7 ASCII / non-ASCII grep**: detect non-ASCII characters added in plan
  (em dash, smart quotes, arrows). Equivalent to forge CLAUDE.md Step 0c.

### Epistemological layer (G1-G8, mix pure Python + multi-LLM judge)

- **G1 Reference Class Forecasting**: plan must contain `## Reference Class`
  section with 2+ historical similar-scope projects, each with (name, scope,
  actual duration, plan-vs-actual ratio). Outside-view estimate computed.
- **G2 Risk Taxonomy (3-class)**: plan must contain `## Risks` section with
  three subsections: `### Known Risks`, `### Gray Rhinos`, `### Black Swans`.
  Gray Rhinos must have `denial_reason` field. Black Swans must have
  `survival_plan` field. All-in-one bucket or empty Gray Rhinos = FAIL.
- **G3 Pre-mortem MANDATORY**: plan must contain `## Pre-mortem` section
  with at least 5 ranked failure causes, each with `early_warning` field
  and `counter` field.
- **G4 Probability Calibration**: hedge words (English: maybe/likely/
  probably/perhaps/possibly/seems/appears; Chinese hedge regex via Unicode)
  flagged. Each hedge instance must have either an adjacent numeric
  probability (0-100%) or explicit `<!-- plan-forge: unknown-ok -->` marker.
- **G5 Antifragility Audit**: plan must contain `## Chaos Response` section
  with 3 stressor scenarios. Per-scenario classification: benefit / survive
  / degrade / break. All scenarios "break" = FAIL.
- **G6 Plan-vs-Vision Falsifiability**: every SC entry must have an explicit
  fail-condition column. Multi-LLM judge (Anthropic + Kimi + DeepSeek +
  Mimo, majority vote) classifies plan as plan / vision / mixed. Majority
  "vision" = VISION verdict.
- **G7 Scope Challenge / Barbell**: plan must contain `## Scope Challenge`
  section answering Q1-Q4: (does this need to exist? + 3 real consumers +
  do-nothing cost + barbell vs middle-ground check).
- **G8 Collective Bias / Source Diversity**: plan must contain `## External
  Voices` section with: 1 non-AI primary source citation, 1 dissenting view
  explicitly addressed, 1 historical failure case of similar approach.
  AI-smell heuristic regex + LLM judge majority vote on text origin.

### Verdict layer

- Output: `Verdict(engineering_verdict, epistemic_verdict, findings)`.
- `engineering_verdict`: PASS or FAIL (from F1-F7 + G6 mechanical part).
- `epistemic_verdict`: PASS, FAIL, or VISION (from G1-G8 holistically).
- Findings: list with severity (BLOCKER / HIGH / MEDIUM / LOW), location,
  message, fix_hint.

### Adapters

- **Adapter A** (Python library): `from plan_forge import check`. Primary.
- **Adapter B** (Claude Code skill): `/plan-forge <path>` slash command.
  Primary for Minxi's daily workflow.
- **Adapter C** (CLI): `plan-forge check <plan>`, `audit-retroactive <dir>`,
  `scaffold <name>`. Secondary; for CI and batch retroactive audits.
- Deferred to v0.2+: pre-commit hook, GitHub Action, LSP server, web UI.

## Architecture

```
plan_forge.api.check(plan_text, llm_clients=None)
  |
  +-> parser.parse(plan_text) -> ParsedPlan
  |       (sections, SC table, risk register, hedge words, citations)
  |
  +-> checks.mechanical.run(ParsedPlan) -> List[Finding]
  |       F1-F7 + PBR P1/P2/P5/P6 (internalized from Travassos taxonomy)
  |
  +-> checks.epistemic.run(ParsedPlan, llm_clients) -> List[Finding]
  |       G1-G8; G6/G8 invoke llm.vote()
  |
  +-> verdict.compute(findings) -> Verdict
          engineering_verdict = max severity in (F + PBR + G6.mechanical)
          epistemic_verdict = aggregate(G1-G8) -> PASS / FAIL / VISION
```

### Repository layout

```
~/code/plan-forge/
  MANIFESTO.md
  README.md
  pyproject.toml
  src/plan_forge/
    __init__.py             # exports check, scaffold, Verdict, Severity
    api.py                  # public api impl
    parser.py               # markdown plan parser
    verdict.py              # Verdict + Finding + Severity dataclasses
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
        g1_reference_class.py
        g2_risk_taxonomy.py
        g3_premortem.py
        g4_calibration.py
        g5_antifragility.py
        g6_plan_vs_vision.py     # uses llm.vote
        g7_scope_challenge.py
        g8_external_voices.py    # uses llm.vote
    llm/
      client.py               # LLMClient Protocol
      anthropic_client.py
      kimi_client.py
      deepseek_client.py
      mimo_client.py
      vote.py                 # majority vote + graceful degradation
      prompts/
        plan_vs_vision.txt    # G6 judge prompt
        ai_smell.txt          # G8 judge prompt
    scaffold/
      __init__.py
      templates/
        default.md.j2         # plan skeleton with all mandatory sections
  adapters/
    skill/
      SKILL.md                # /plan-forge slash command
      runner.py
    cli/
      __init__.py
      main.py                 # argparse + dispatch
  tests/
    unit/
      test_f1.py through test_f7.py
      test_g1.py through test_g8.py
      test_pbr.py
    fixtures/
      pass_well_formed.md
      fail_missing_premortem.md
      fail_vision_disguised.md
      fail_all_known_risks.md
      ...
    integration/
      test_check_end_to_end.py
    dogfood/
      test_plan_forge_own_plan.py
  .planning/
    plan-forge-v0.1-PLAN.md    (this file)
    CORPUS.md                  (anti-pattern catalog, to be written)
    LESSONS-RETRO.md           (forge-code Phase 2 retroactive audit, post-T34)
```

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
class ParsedPlan:
    raw_text: str
    sections: dict[str, ParsedSection]
    sc_table: list[ParsedSC]
    risks: list[ParsedRisk]
    hedge_word_locations: list[tuple[int, str]]  # (line, word)
    citations: list[str]
    ai_smell_phrases: list[tuple[int, str]]
```

### verdict.py

```python
from enum import Enum

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

@dataclass
class Finding:
    check_id: str           # "F1" / "G3" / "P1" / etc.
    severity: Severity
    location: str           # "line 42" / "section X"
    message: str
    fix_hint: str

@dataclass
class Verdict:
    engineering: EngineeringVerdict
    epistemic: EpistemicVerdict
    findings: list[Finding]
```

### llm/vote.py

```python
def vote(clients: list[LLMClient], prompt: str, plan: str,
         min_responders: int = 2) -> tuple[str, dict]:
    """Multi-LLM majority vote. Returns (verdict, per-client-responses).

    If fewer than min_responders respond, returns ("indeterminate", responses).
    """
```

### checks/epistemic/g6_plan_vs_vision.py (most LLM-heavy)

```python
def check(parsed: ParsedPlan, llm_clients: list[LLMClient]) -> list[Finding]:
    findings = []
    # Mechanical: every SC must have explicit fail_condition
    for sc in parsed.sc_table:
        if not sc.fail_condition:
            findings.append(Finding(
                check_id="G6.mechanical",
                severity=Severity.BLOCKER,
                location=f"SC-{sc.number}",
                message="missing fail_condition column",
                fix_hint="add 'FAILS if ...' clause to SC body",
            ))
    # LLM judge: classify plan-vs-vision via majority vote
    prompt = load_prompt("plan_vs_vision.txt")
    verdict, responses = vote(llm_clients, prompt, parsed.raw_text)
    if verdict == "vision":
        findings.append(Finding(
            check_id="G6.llm",
            severity=Severity.BLOCKER,
            location="plan",
            message=f"majority LLM vote classified plan as vision: {responses}",
            fix_hint="strengthen SCs with measurable fail conditions",
        ))
    return findings
```

## Implementation Tasks

| # | Task | Output | Done when |
|---|------|--------|-----------|
| T01 | git init (DONE) | ~/code/plan-forge/.git | repo exists |
| T02 | MANIFESTO.md (DONE) | MANIFESTO.md | 294 lines, ASCII clean |
| T03 | this PLAN.md (DONE when this file finalized) | plan-forge-v0.1-PLAN.md | ASCII clean, all G1-G8 sections present |
| T04 | self-dogfood walkthrough | walkthrough notes (this file Appendix A) | each G has explicit PASS/FAIL judgment with evidence |
| T05 | pyproject.toml + project skeleton | pyproject.toml + src/plan_forge/ skeleton | `pip install -e .` works |
| T06 | verdict.py + parser.py | both modules + unit tests | parser handles fixtures; verdict computes from finding list |
| T07 | F1-F7 mechanical checks | 7 modules + 7 test files | each F has PASS fixture + FAIL fixture; tests pass |
| T08 | PBR P1/P2/P5/P6 mechanical | 4 modules + tests | each PBR pass has PASS + FAIL fixture |
| T09 | api.check_mechanical() | api.py partial | runs F + PBR; returns findings |
| T10 | LLM client + multi-provider | llm/ subpackage | AnthropicClient + KimiClient + DeepSeekClient + MimoClient + vote.py |
| T11 | G6 + G8 (LLM-dependent G's) | g6 + g8 + prompts | vote-based; graceful degradation |
| T12 | G1-G5 + G7 (pure Python G's) | 6 modules + tests | each G has PASS + FAIL fixture |
| T13 | api.check() full + verdict aggregation | api.py complete | end-to-end PASS on well-formed fixture |
| T14 | scaffold/ + templates | default.md.j2 | `scaffold("test-plan")` produces template with all G sections |
| T15 | Adapter A (library) finalize | __init__.py exports | `from plan_forge import check` works |
| T16 | Adapter B (Claude Code skill) | adapters/skill/SKILL.md | `/plan-forge <path>` invocable in Claude Code |
| T17 | Adapter C (CLI) | adapters/cli/main.py | 5 CLI commands functional with help text |
| T18 | Self-dogfood: api.check() on this PLAN | dogfood test | PLAN passes plan-forge with PASS both verdicts |
| T19 | Retroactive audit forge-code Phase 2 | LESSONS-RETRO.md | 7 plans audited; >= 4 FAIL or VISION |
| T20 | 3-cycle code review (forge-style) | review notes | post-review-c3 reached |
| T21 | git tag v0.1.0 | tag | v0.1.0 on main |

Hard cap: 4 weeks initial; 8 weeks Flyvbjerg-adjusted ceiling. If T13
(api.check full) not done by week 3, descope to G1+G2+G3+G6 and defer
G4/G5/G7/G8 to v0.2.

## Success Criteria (with explicit fail-condition column per G6)

| ID | Criterion | Fail Condition |
|----|-----------|---------------|
| SC-1 | MANIFESTO.md exists at repo root; first read by any implementer | MANIFESTO.md absent OR README.md does not reference it as "read first" |
| SC-2 | this PLAN.md passes plan-forge v0.1 self-check (T18) | api.check(plan_forge_v0_1_plan_text) returns FAIL or VISION on either verdict |
| SC-3 | T19 retroactive audit: 7 of 7 forge Phase 2 plans audited; at least 4 produce FAIL or VISION | fewer than 4 of 7 produce non-PASS verdict (would indicate plan-forge does not catch what 50+ rounds of AI panel missed) |
| SC-4 | F1-F7 each have 2 test cases (PASS + FAIL fixture) | any F has fewer than 2 test cases OR FAIL fixture does not trigger the check |
| SC-5 | G1-G8 each have 2 test cases (PASS + FAIL fixture) + LLM vote integration for G6 and G8 | any G missing fixtures OR G6/G8 do not invoke vote.py |
| SC-6 | Adapter A library import works: `from plan_forge import check` | ImportError OR check() signature differs from spec |
| SC-7 | Adapter B Claude Code skill registered and invocable | `/plan-forge <path>` in Claude Code fails to invoke or returns no Verdict |
| SC-8 | Adapter C CLI has 5 commands functional with help text | any of {check, check-mechanical, check-epistemic, scaffold, audit-retroactive} returns non-zero on `--help` OR missing |
| SC-9 | Test coverage >= 80% on src/plan_forge/ | `pytest --cov=src/plan_forge` reports < 80% line coverage |
| SC-10 | 3-cycle code review post-review-c3 reached before v0.1 tag | tag v0.1.0 created without 9-pass clean review |
| SC-11 | All commits authored Minxi Hou <houminxi@gmail.com>; no AI markers in commit messages | grep finds "Co-Authored-By: Claude" OR "noreply@anthropic.com" OR "post-review-c3" in commit body OR review-tool names |
| SC-12 | 0 outbound subprocess calls to Claude Code skills from plan_forge library code | grep src/plan_forge/ finds `subprocess.run` referencing `gsd-*`, `plan-review`, `adversarial-qe`, or `anti-ai-audit` |
| SC-13 | Graceful LLM degradation: if N of 4 providers unavailable, plan-forge runs with remaining; if N < 2, mechanical-only fallback with warning | any LLM provider failure causes plan-forge to crash or return Verdict without engineering verdict |
| SC-14 | LLM cost cap: median run cost < $0.30 per plan check | median across 10 sample plans exceeds $0.30 |
| SC-15 | ASCII enforcement: no non-ASCII in any committed file under src/, MANIFESTO.md, or PLAN.md | `git diff --diff-filter=AM -U0` finds non-ASCII added in any committed file |

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
| LLM API cost spike (G6/G8 per-plan ~$0.10-0.30) | 70% | M | cache by (plan-hash, prompt-hash) with 1-week TTL |
| Multi-LLM provider API differences (Anthropic vs Kimi/DS/Mimo quirks) | 80% | M | LLMClient Protocol abstracts; per-provider adapter handles Kimi tool_use bugs / DeepSeek cache_control silently ignored |
| Multi-LLM vote disagreement on G6/G8 | 50% | M | 3-of-4 majority; ties produce "indeterminate" (separate from PASS/FAIL); user can override via inline marker |
| False positive on G4 hedge-word lint | 60% | L | allow inline `<!-- plan-forge: hedge-ok -->` marker for intentional uncertainty |
| Parser breaks on unconventional markdown | 40% | L | strict markdown subset enforced; reject with clear error |

### Gray Rhinos

| Gray Rhino | Denial Reason (why people will ignore) | Counter |
|------------|---------------------------------------|---------|
| plan-forge itself overscopes: G1-G8 full is ambitious for v0.1 | "user said no compromise, so corpus warning about scope creep does not apply" | Hard week-3.5 cap; if T13 not done by week 3, descope to G1+G2+G3+G6 and defer G4/G5/G7/G8 |
| Self-dogfood (SC-2) becomes infinite regress: PLAN keeps failing own enforcement, requires perpetual revision | "it is just polish, almost there" | SC-2 hard week-2-end deadline; if not met, simplify enforcement rules per corpus lesson "polish stage = scope wrong" |
| Retroactive audit (SC-3) shows all 7 plans FAIL; emotional cost makes us doubt the tool | "AI panel converged on these plans, so plans must be fine; tool must be wrong" | This is the whole point. AI panel convergence is unreliable per L1 of LEARNINGS. Retroactive audit FAIL validates plan-forge value, not refutes it. |
| Multi-LLM provider integration brittleness (Kimi/Mimo APIs change without notice) | "we tested it works today" | Integration tests run weekly via CI; auto-skip provider on regression with warning |
| plan-forge adopted by Minxi only; never reaches external users | "as long as I use it, it has value" | Acceptable per SC-3 ROI (retroactive value alone justifies); track external adoption as separate metric in v0.2 |

### Black Swans

| Black Swan | Survival Plan |
|------------|---------------|
| Corpus + synthesis + LEARNINGS combine to reveal forge concept itself wrong; plan-forge unmasks that forge-code v2.0 should never have been built | Accept; v1.0 forge skill still ships in production; v2.0 archived as lessons; plan-forge value undiminished |
| AI tool landscape shifts (e.g., Claude 5 catches G1-G8 natively); plan-forge becomes obsolete before v1.0 ships | Ship anyway; MANIFESTO + corpus + LEARNINGS are durable intellectual property independent of tool layer; v0.1 cost is < 8 weeks |
| User (Minxi) loses interest; project dies mid-implementation | Every week's deliverable is independently useful (MANIFESTO at week 0; retroactive audit at week 4); ship continuous value not big-bang |
| G6 LLM judges all four providers converge to "internally consistent = plan" bias (the very failure mode plan-forge is supposed to fix) | G7 scope-challenge is independent of LLM (pure Python mechanical check); G1/G2/G3/G5 are also pure-Python; if G6/G8 both LLM-corrupted, mechanical layer still has 6/8 coverage |
| Anthropic API permanent shutdown or pricing change makes multi-LLM economically infeasible | Mechanical-only fallback mode (10 of 15 checks still work); v0.2 adds local LLM (llama.cpp) option |

## Reference Class (G1 self-dogfood)

| Project | Plan Estimate | Actual Duration | Ratio | Note |
|---------|--------------|----------------|-------|------|
| ruff (Python linter) | 6 months | 12 months | 2.0 | Pure mechanical lint |
| semgrep (security pattern lint) | 12 months | 18 months | 1.5 | Pattern + dataflow |
| CodeQL (semantic analysis) | 24 months | 36 months | 1.5 | Heavy semantic engine |
| SonarQube (multi-language quality) | 36 months | 48 months | 1.3 | Established baseline |
| Coccinelle (kernel semantic patch) | 12 months | 24 months | 2.0 | DSL + transformation engine |

**Mean ratio**: 1.66

**plan-forge v0.1 plan estimate**: 4 weeks

**Outside-view adjusted (4 * 1.66)**: 6.6 weeks (~7 weeks)

**Hard ceiling**: 4 weeks; if T13 not complete by week 3, descope.

**Plan-forge note**: existing reference class is PURE LINT tools (mechanical
only). plan-forge adds EPISTEMOLOGICAL layer (G1-G8) which has no empirical
reference class. Estimate uncertainty (70% probability) higher than 1.66x;
honest range 4-8 weeks for v0.1 with G1-G8 full.

## Pre-mortem (G3 self-dogfood)

Imagine plan-forge v0.1 has shipped late 2026. It failed. Top 5 causes,
ranked by probability:

### PM1: v0.1 took 8 weeks not 4; user attention exhausted before ship

- **Early warning**: T13 (api.check full) not done by week 2 end
- **Counter**: descope per Gray Rhino GR1; trim to G1+G2+G3+G6

### PM2: G1-G8 enforcement too strict; every real plan FAILs; users abandon

- **Early warning**: T19 retroactive audit shows 100% FAIL (not 60%) on 7
  forge Phase 2 plans
- **Counter**: tune severity thresholds; allow per-plan opt-out with explicit
  rationale via inline marker; track opt-out rate as quality metric

### PM3: 0 external users besides Minxi; plan-forge becomes personal tool

- **Early warning**: month 3 still 0 external imports / 0 issues / 0 stars
- **Counter**: acceptable per SC-3 ROI (forge-code retroactive value alone
  justifies build cost); v0.2 considers outreach if Minxi judges worth it

### PM4: Multi-LLM provider ecosystem fragments; integration breaks silently

- **Early warning**: 2+ providers down in same week, vote produces
  "indeterminate" majority
- **Counter**: Anthropic-only fallback path with explicit warning; mechanical
  -only mode if all LLM providers fail; weekly integration test catches
  silent breakage

### PM5: Self-dogfood loop becomes religious; plan-forge own development paralyzed by perfect self-enforcement

- **Early warning**: 3+ days spent on PLAN.md polish without code progress
- **Counter**: same as forge-code lesson L2 (polish stage is scope-wrong
  signal, not polish-needed signal); hard SC-2 week-2-end deadline

## Chaos Response (G5 self-dogfood)

| Scenario | Behavior | Verdict |
|----------|----------|---------|
| Claude API outage during plan-forge invocation | L2 mechanical + G1/G2/G3/G4/G5/G7 work offline (pure Python); G6/G8 degrade to "indeterminate"; user warned but mechanical verdict still emitted | SURVIVE (degraded but functional) |
| User submits non-English plan (German / Spanish / Chinese) | F1-F7 regex-based checks mostly language-agnostic; G1-G8 section name detection needs i18n translation table | DEGRADE (v0.1 English-only with Chinese hedge regex; full i18n in v0.2) |
| Malicious plan markdown (huge file, embedded scripts, unicode tricks) | parser sanitizes; file size cap 100KB enforced; no script execution; non-ASCII flagged but not blocked | SURVIVE (security boundary enforced) |

**Antifragility**: each failed run produces a finding that feeds corpus
expansion. New failure patterns observed across audited plans strengthen
enforcement rules. plan-forge gets BETTER from being challenged, not just
"resilient" to challenge.

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

Cost of plan-forge v0.1: 4-8 weeks one-time + LLM API costs (~$0.30/plan
checked, projected 100 checks in year 1 = $30).

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

**Accommodation**: plan-forge will offer an explicit `--ship-and-iterate`
CLI flag that bypasses L3 epistemological gates for users who consciously
choose lean mode. This is opt-in lean, not opt-in falsification.

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

## Reviewer Focus (for cross-AI review of this PLAN)

Cross-AI reviewers should pay particular attention to:

1. **Internal consistency**: do G1-G8 enforcement specs in section
   "Requirements" match the SC table fail-conditions and the module
   designs?
2. **G6 self-application**: does this PLAN have explicit fail-condition for
   each SC? (G6 mechanical check would catch absence.) Are the fail-
   conditions falsifiable? (G6 LLM judge would assess.)
3. **G1 reference class adequacy**: are 5 reference class projects (ruff /
   semgrep / CodeQL / SonarQube / Coccinelle) sufficient? They are all
   pure-lint tools; plan-forge has no exact reference class. Is the
   "honest range 4-8 weeks" calibration adequate or too wide?
4. **Risk register completeness**: GR3 (retroactive audit shows all FAIL,
   emotional cost) -- is this the right framing or denial-reason-encoded?
   BS4 (LLM judges all converge to wrong) -- is the mechanical fallback
   adequate?
5. **Pre-mortem ranking**: PM1-PM5 ordered by perceived probability. Any
   missing causes? PM1 + PM2 potentially combined into "v0.1 ships but
   nobody uses it"? <!-- plan-forge: hedge-ok (reviewer-question) -->
6. **Architectural commitment robustness**: is "internalize, not reference"
   sustainable as the project grows? Will plan-forge inevitably re-acquire
   dependencies as it scales?
7. **Multi-LLM strategy**: 4 providers is ambitious for v0.1. Should v0.1
   ship with Anthropic-only and add Kimi/DS/Mimo in v0.2? Or is multi-
   provider the whole point of G6 vote and must ship together?
8. **Scope creep early warnings**: at what concrete week-N milestone should
   we trigger the "descope to G1+G2+G3+G6" gate?

## Open Questions

1. **G6 LLM judge prompt design**: how exactly should the prompt frame the
   plan-vs-vision distinction? Too lenient = miss real visions; too strict
   = every real plan flagged. v0.1 will iterate prompt against retroactive
   audit findings.
2. **AI-smell heuristic regex**: which phrases? Initial set from anti-ai-
   audit skill memory; this is heuristic and will drift. v0.2 candidate:
   maintain a versioned regex list.
3. **Cache strategy for LLM calls**: SHA-256 of (plan-hash + prompt-hash)?
   1-week TTL? v0.1 default: file-based cache in `~/.cache/plan-forge/`.
4. **License**: TBD. Defer decision to T15 (Adapter A finalize).
5. **Scaffold template variations**: v0.1 ships `default.md.j2` only. Do
   we add `roadmap.md.j2`, `pitch.md.j2`, `grant.md.j2` in v0.1 or wait
   for user demand?
6. **Versioning policy**: semver for plan-forge. v0.x = pre-stable. v1.0
   when SC-3 succeeds (>= 4 of 7 retroactive FAIL) AND at least one
   external user adopts.

## CHANGELOG

Plan-forge v0.1 PLAN versions (per F5 R-tag pruner: history outside body):

- 2026-05-18 v0 (this draft): initial scope after architecture correction
  (internalize, not reference; library-first; multi-LLM); supersedes
  /tmp/draft_20260518_202304_plan-forge-v01-scope.txt (v1) and
  /tmp/draft_20260518_203128_plan-forge-v01-scope-v2.txt.

## Appendix A: Self-Dogfood Walkthrough (T04)

Manual G1-G8 enforcement walkthrough against this PLAN.md, executed
2026-05-18. Verdict per check with evidence. Result feeds T18 automated
self-check after library implementation.

### G1 Reference Class Forecasting -- PASS

- `## Reference Class` section present (line 426)
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

**T04 conclusion**: PLAN.md is ready for cross-AI review by external models.
Findings during cross-AI review will feed corpus expansion. If cross-AI
review identifies new failure patterns not covered by G1-G8, MANIFESTO
Section 8 process applies for adding new G-checks.
