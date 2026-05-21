# T12 SUBSPEC: G1 + G2 + G3 + G5 + G7 (pure-mechanical epistemic gates)

Status: draft for subagent implementation.
Depends on: T05-T11 (parser, verdict, mechanical F-layer, PBR, LLM
layer, epistemic G4/G6/G8).
Scope: the five epistemic gates that need NO LLM.  Each is a
structural + content check on a required plan section.  After T12,
G1-G8 all exist; G9/G10 remain (T29/T30).

## 0. Phase overview

| Phase | Scope | Files |
|---|---|---|
| 1 | shared section-finder helper | checks/epistemic/_sections.py + test |
| 2 | G2 Risk Taxonomy (reuses parser.risks) | g2_risk_taxonomy.py + tests + 2 fixtures |
| 3 | G1 Reference Class | g1_reference_class.py + tests + 2 fixtures |
| 4 | G3 Pre-mortem | g3_premortem.py + tests + 2 fixtures |
| 5 | G5 Antifragility (Chaos Response) | g5_antifragility.py + tests + 2 fixtures |
| 6 | G7 Scope Challenge / Barbell | g7_scope_challenge.py + tests + 2 fixtures |
| 7 | wire all five into epistemic.run + integration test | __init__.py + integration test |

Phase 2 (G2) first because it reuses an existing parser structure
and is the simplest; it validates the test harness before the
section-parsing gates.

## 1. Design principles (load-bearing)

### 1.1 Signature: pure-mechanical gates take NO llm_clients

G4/G6/G8 (T11) take `(parsed, llm_clients)` because they have an
LLM Part B.  G1/G2/G3/G5/G7 are pure mechanical -- they never call
an LLM.  Their signature is:

```python
def check(parsed: ParsedPlan) -> list[Finding]:
    ...
```

This honestly reflects the dependency.  `epistemic.run` (Phase 7)
calls each gate with the arguments it actually needs (see 7.1);
do NOT add an unused `llm_clients` parameter "for uniformity".

### 1.2 Section lookup is a shared helper

All four section-based gates (G1/G3/G5/G7) locate their section by
heading keyword.  Centralize in `checks/epistemic/_sections.py`:

```python
from plan_forge.parser import ParsedPlan, ParsedSection

def find_section(parsed: ParsedPlan, *keywords: str) -> ParsedSection | None:
    """First section whose heading contains ALL keywords (case-insensitive)."""
    for section in parsed.sections.values():
        h = section.heading.lower()
        if all(kw.lower() in h for kw in keywords):
            return section
    return None
```

(G8 in T11 inlined this lookup; do NOT refactor G8 -- it is
read-only.  New gates use the helper.)

### 1.3 Severity convention

- Required section ABSENT -> `Severity.BLOCKER` (a plan missing a
  whole epistemic section is structurally a vision, not a plan).
- Required count NOT met (e.g. < 2 reference projects, < 5 premortem
  causes, < 3 chaos scenarios) -> `Severity.BLOCKER`.
- Section present but a sub-field missing (e.g. a Gray Rhino with no
  denial reason, a premortem cause with no counter, a missing scope
  question) -> `Severity.HIGH`.

Rationale: absence/insufficiency is a hard structural fail;
partial-completeness is a serious warning the author must address
but the scaffold exists.

### 1.4 Mechanical detection is keyword + count based

These gates use keyword presence and entry counting, not natural-
language understanding.  False positives are possible; that is the
accepted v0.1 trade-off (the LLM Part B gates handle nuance).  The
plan-forge scaffold (T14) will emit sections in the exact shape
these gates expect, so a scaffolded plan passes by construction.
Define the EXPECTED shape here; fixtures follow it.

## 2. Phase 2: G2 Risk Taxonomy 3-class

Reuses `parsed.risks` (list[ParsedRisk]; each has
`bucket` in {"known", "gray_rhino", "black_swan"}, `description`,
`denial_reason: str | None`, `survival_plan: str | None`).  No
section-body parsing needed -- the parser already did it.

check_id prefix: `G2.*`.  Algorithm:

```python
buckets = {r.bucket for r in parsed.risks}
```

1. If `parsed.risks` is empty: emit
   `Finding("G2.no_risks", BLOCKER, "plan", "## Risks section
   absent or empty", "add ## Risks with ### Known Risks / ### Gray
   Rhinos / ### Black Swans")` and return.
2. For each required bucket in ("known", "gray_rhino", "black_swan"):
   if it is not in `buckets`, emit
   `Finding(f"G2.missing_{bucket}", BLOCKER, "plan.risks",
   f"no {bucket} risks; all-in-one bucket is not a 3-class taxonomy",
   "add at least one risk to this bucket")`.
3. For each risk with `bucket == "gray_rhino"` and
   `not denial_reason`: emit
   `Finding("G2.gray_rhino_no_denial", HIGH, risk.description[:40],
   "Gray Rhino lacks a denial_reason", "state why this obvious risk
   is being ignored/deferred")`.
4. For each risk with `bucket == "black_swan"` and
   `not survival_plan`: emit
   `Finding("G2.black_swan_no_survival", HIGH, risk.description[:40],
   "Black Swan lacks a survival_plan", "state how the plan survives
   this low-probability high-impact event")`.

### 2.x G2 fixtures + tests

- `g2_pass.md`: `## Risks` with all three subsections; >=1 gray
  rhino (with denial reason), >=1 black swan (with survival plan).
- `g2_fail.md`: missing Gray Rhinos bucket OR a gray rhino without
  denial_reason.  Pick one clear failure; comment it.
- tests/unit/test_g2_risk_taxonomy.py:
  `test_pass_fixture_no_findings`, `test_missing_bucket_blocker`,
  `test_gray_rhino_no_denial_high`,
  `test_black_swan_no_survival_high`, `test_empty_risks_blocker`.

NOTE: confirm how the parser populates `parsed.risks` from a
fixture (read parser.py risk-parsing + an existing parser test).
Design `g2_pass.md` so the parser actually fills bucket +
denial_reason + survival_plan; verify by parsing the fixture in a
test and asserting `parsed.risks` is non-empty before asserting G2
output.  If the parser does not populate these for your fixture
markdown shape, match the fixture shape to what the parser expects
(do NOT modify the parser -- it is read-only).

## 3. Phase 3: G1 Reference Class Forecasting

Section: `find_section(parsed, "reference class")`.

1. Absent -> `Finding("G1.no_section", BLOCKER, "plan", "## Reference
   Class section absent", "add ## Reference Class with 2+ historical
   similar-scope projects and plan-vs-actual ratios")` and return.
2. Parse the section body for project entries.  A project entry is
   a line containing a plan-vs-actual RATIO, detected by regex
   `r"\b\d+(?:\.\d+)?\s*[xX]\b"` (e.g. "1.5x", "3 X") OR the literal
   word "ratio" with an adjacent number.  Count such lines as
   `n_projects`.
3. If `n_projects < 2` -> `Finding("G1.insufficient_reference_class",
   BLOCKER, "## Reference Class", f"only {n_projects} project(s)
   with a plan-vs-actual ratio; need >= 2", "add more historical
   reference projects with actual durations and ratios")`.

### G1 fixtures + tests

- `g1_pass.md`: `## Reference Class` with a markdown table of >= 2
  projects, each row including a ratio like "1.8x".
- `g1_fail.md`: section present but only 1 project with a ratio (or
  zero) -> insufficient.  (A second fixture variant of "section
  absent" is covered by a unit test using inline markdown, not a
  separate file.)
- tests: `test_pass`, `test_absent_section_blocker` (inline md),
  `test_insufficient_projects_blocker`, `test_ratio_regex_variants`
  (1.5x / 3X / "ratio 2.0").

## 4. Phase 4: G3 Pre-mortem

Section: `find_section(parsed, "pre-mortem")` OR
`find_section(parsed, "premortem")` (accept both spellings; try
hyphenated first, then non-hyphenated).

1. Absent -> `Finding("G3.no_section", BLOCKER, "plan", "## Pre-mortem
   section absent", "add ## Pre-mortem with >= 5 ranked failure
   causes, each with an early warning and a counter")` and return.
2. Count failure-cause entries in the body.  A cause entry is a
   numbered list item (regex `r"^\s*\d+\."` multiline) OR a markdown
   table data row OR a bullet (`r"^\s*[-*]"`).  Count distinct
   entries as `n_causes`.
3. If `n_causes < 5` -> `Finding("G3.insufficient_causes", BLOCKER,
   "## Pre-mortem", f"only {n_causes} failure cause(s); need >= 5",
   "add more ranked failure causes")`.
4. Check the body contains BOTH the phrase "early warning" (case-
   insensitive) and "counter" (case-insensitive).  If "early
   warning" missing -> `Finding("G3.no_early_warning", HIGH,
   "## Pre-mortem", "no early-warning indicators found", "add an
   early-warning signal to each failure cause")`.  If "counter"
   missing -> `Finding("G3.no_counter", HIGH, "## Pre-mortem", "no
   counter-measures found", "add a counter to each failure cause")`.

SUBSPEC interpretation: T12 verifies the section has >= 5 entries
and mentions early-warning + counter at the section level (not
per-entry); strict per-entry field validation is deferred (the
keyword presence is the v0.1 mechanical proxy).  Document with a
`# SUBSPEC interpretation:` comment.

### G3 fixtures + tests

- `g3_pass.md`: >= 5 numbered failure causes; body mentions "early
  warning" and "counter" for each.
- `g3_fail.md`: < 5 causes OR missing early-warning/counter keywords.
- tests: `test_pass`, `test_absent_blocker`,
  `test_insufficient_causes_blocker`, `test_missing_early_warning_high`,
  `test_missing_counter_high`.

## 5. Phase 5: G5 Antifragility Audit (Chaos Response)

Section: `find_section(parsed, "chaos response")` (fallback
`find_section(parsed, "chaos")`).

1. Absent -> `Finding("G5.no_section", BLOCKER, "plan", "## Chaos
   Response section absent", "add ## Chaos Response with 3 stressor
   scenarios classified benefit/survive/degrade/break")` and return.
2. Classify scenarios by counting occurrences of the four
   classification words (case-insensitive, word-boundary):
   `benefit`, `survive`, `degrade`, `break`.  A scenario is an entry
   (numbered/bullet/table row) that contains at least one
   classification word.  Count `n_scenarios` = entries containing a
   classification word.
3. If `n_scenarios < 3` -> `Finding("G5.insufficient_scenarios",
   BLOCKER, "## Chaos Response", f"only {n_scenarios} classified
   stressor scenario(s); need >= 3", "add more stressor scenarios")`.
4. If ALL classified scenarios are "break" (i.e. every scenario
   entry's only classification word is "break", and there are >= 3)
   -> `Finding("G5.all_break", BLOCKER, "## Chaos Response", "all
   stressor scenarios break; the plan is fragile under every
   stressor", "redesign so at least one stressor is survived or
   benefited from")`.

### G5 fixtures + tests

- `g5_pass.md`: >= 3 scenarios with a mix (e.g. one benefit, one
  survive, one degrade).
- `g5_fail.md`: all 3+ scenarios classified "break" -> G5.all_break;
  OR < 3 scenarios.
- tests: `test_pass`, `test_absent_blocker`,
  `test_insufficient_scenarios_blocker`, `test_all_break_blocker`,
  `test_mixed_classification_passes`.

## 6. Phase 6: G7 Scope Challenge / Barbell

Section: `find_section(parsed, "scope challenge")` (fallback
`find_section(parsed, "scope")`).

1. Absent -> `Finding("G7.no_section", BLOCKER, "plan", "## Scope
   Challenge section absent", "add ## Scope Challenge answering Q1-Q4
   (need to exist / 3 consumers / do-nothing cost / barbell)")` and
   return.
2. Check the body answers four questions, each detected by keyword
   group (case-insensitive). Missing any -> a HIGH finding:
   - Q1 "need to exist": keywords {"need to exist", "does this need",
     "why this exists", "justif"} -> miss = `G7.missing_necessity`.
   - Q2 consumers / public-artifact alternative: {"consumer",
     "public artifact", "public-artifact", "demand signal"} -> miss
     = `G7.missing_consumers`.
   - Q3 do-nothing cost: {"do nothing", "do-nothing", "cost of
     inaction", "status quo cost"} -> miss = `G7.missing_donothing_cost`.
   - Q4 barbell / middle-ground: {"barbell", "middle ground",
     "middle-ground"} -> miss = `G7.missing_barbell`.
   Each miss: `Finding(<id>, HIGH, "## Scope Challenge", "<question>
   not addressed", "<hint>")`.

### G7 fixtures + tests

- `g7_pass.md`: section answers all four (uses the keyword groups).
- `g7_fail.md`: section present but missing one or more questions
  (e.g. no barbell discussion).
- tests: `test_pass`, `test_absent_blocker`,
  `test_missing_necessity_high`, `test_missing_consumers_high`,
  `test_missing_donothing_high`, `test_missing_barbell_high`.

## 7. Phase 7: wire into epistemic.run + integration test

### 7.1 epistemic/__init__.py run() extension

The T11 `run` calls g4/g6/g8.  Extend it to call all eight gates in
numeric order, passing llm_clients ONLY to the LLM gates:

```python
from . import (
    g1_reference_class, g2_risk_taxonomy, g3_premortem,
    g4_calibration, g5_antifragility, g6_sc_falsifiability,
    g7_scope_challenge, g8_source_diversity,
)

def run(parsed: ParsedPlan, llm_clients: list[LLMClient]) -> list[Finding]:
    findings: list[Finding] = []
    findings.extend(g1_reference_class.check(parsed))
    findings.extend(g2_risk_taxonomy.check(parsed))
    findings.extend(g3_premortem.check(parsed))
    findings.extend(g4_calibration.check(parsed, llm_clients))
    findings.extend(g5_antifragility.check(parsed))
    findings.extend(g6_sc_falsifiability.check(parsed, llm_clients))
    findings.extend(g7_scope_challenge.check(parsed))
    findings.extend(g8_source_diversity.check(parsed, llm_clients))
    return findings
```

This edits the T11 file `epistemic/__init__.py`.  That is the ONLY
permitted edit to a T11 epistemic file (it is the natural extension
point; the gate modules themselves are untouched).

### 7.2 Integration test (tests/integration/test_epistemic_mechanical_run.py)

- `test_run_on_well_formed_plan_no_mechanical_g_findings`: a fixture
  (or compose one) that satisfies G1/G2/G3/G5/G7 -> assert no
  G1/G2/G3/G5/G7 findings (G4/G6/G8 may fire; filter to the five).
- `test_run_on_empty_plan_all_sections_missing`: minimal plan ->
  assert one no_section BLOCKER per mechanical gate (G1/G2/G3/G5/G7).
- `test_run_passes_empty_llm_clients`: call with `llm_clients=[]`;
  mechanical gates unaffected; no crash.

## 8. Verification gates

```
cd /home/houminxi/code/plan-forge/.worktrees/feat-t12-epistemic-mechanical
unset PLAN_FORGE_CORPUS_URL

# Gate A: full suite
.venv/bin/pytest tests/ -q 2>&1 | tail -6
# Expect 244 baseline + ~35 new T12 tests; 0 warnings.

# Gate B: py_compile
.venv/bin/python -m py_compile \
    src/plan_forge/checks/epistemic/_sections.py \
    src/plan_forge/checks/epistemic/g1_reference_class.py \
    src/plan_forge/checks/epistemic/g2_risk_taxonomy.py \
    src/plan_forge/checks/epistemic/g3_premortem.py \
    src/plan_forge/checks/epistemic/g5_antifragility.py \
    src/plan_forge/checks/epistemic/g7_scope_challenge.py \
    src/plan_forge/checks/epistemic/__init__.py

# Gate C: ASCII on changed files
for f in $(git show --name-only --format='' HEAD 2>/dev/null; git ls-files --others --exclude-standard); do
    [ -f "$f" ] || continue
    n=$(python3 -c "print(sum(1 for b in open('$f','rb').read() if b>127))")
    test "$n" = "0" || echo "FAIL non-ASCII: $f ($n)"
done; echo "ascii done"

# Gate D: scope creep (use git show, NOT git diff -- a local hook
# rewrites git diff output and yields false positives)
git show --name-only --format='' HEAD 2>/dev/null | grep -vE "^(src/plan_forge/checks/epistemic/(_sections|g[12357]_[a-z_]+|__init__)\.py|tests/unit/test_(g[12357]_|sections)|tests/integration/test_epistemic_mechanical|tests/fixtures/g[12357]_(pass|fail)\.md|\.planning/|^$)"
# Expect empty.

# Gate E: no llm import in pure-mechanical gates
grep -lE "search_vote|llm_clients|from plan_forge.llm" \
    src/plan_forge/checks/epistemic/g1_reference_class.py \
    src/plan_forge/checks/epistemic/g2_risk_taxonomy.py \
    src/plan_forge/checks/epistemic/g3_premortem.py \
    src/plan_forge/checks/epistemic/g5_antifragility.py \
    src/plan_forge/checks/epistemic/g7_scope_challenge.py \
    && echo "FAIL: pure-mechanical gate imports llm" || echo "  clean (no llm in mechanical gates)"

# Gate F: coverage on the five new gates
.venv/bin/pytest --cov=src/plan_forge/checks/epistemic \
    tests/unit/test_g1_reference_class.py \
    tests/unit/test_g2_risk_taxonomy.py \
    tests/unit/test_g3_premortem.py \
    tests/unit/test_g5_antifragility.py \
    tests/unit/test_g7_scope_challenge.py \
    tests/unit/test_sections.py 2>&1 | tail -12
# Expect >= 90% on the five gate modules + _sections.py.
```

## 9. Hard constraints

1. ASCII only in every new/modified file.
2. No AI markers; author is Minxi Hou.  Comments describe behavior,
   not task IDs / round labels / spec section numbers.
3. SUBSPEC wins over PLAN on conflict.  Document interpretations
   with `# SUBSPEC interpretation: ...`.
4. No new dependencies (stdlib re + the existing parser/verdict).
5. Phase order; tests green at each phase.
6. READ-ONLY: parser.py, verdict.py, all checks/mechanical/*, all
   checks/pbr/*, api.py, the entire llm/ subpackage, and ALL T11
   epistemic gate modules (g4_calibration.py, g6_sc_falsifiability.py,
   g8_source_diversity.py, _evidence.py) and their tests/fixtures.
   PERMITTED edit: ONLY `checks/epistemic/__init__.py` (run()
   extension per 7.1).
7. Pure-mechanical gates take `check(parsed)` -- NO llm_clients
   parameter.  They MUST NOT import anything from plan_forge.llm.
8. Required-section-absent and insufficient-count -> BLOCKER;
   partial-field-missing -> HIGH (severity convention 1.3).
9. Section lookup goes through `_sections.find_section`; do not
   re-inline the loop in each gate.

## 10. Non-goals

- Do NOT implement G9 (T29) or G10 (T30).
- Do NOT modify the T11 gate modules or parser.
- Do NOT implement api.check() aggregation (T13).
- Do NOT add LLM calls to any T12 gate (all five are mechanical).
- Do NOT build the scaffold template (T14) even though these gates
  define the shape it will emit.

## 11. Report-back format (< 40 lines)

- Files created (grouped by phase) + line counts.
- The one modified file (epistemic/__init__.py) +/- lines.
- Total test count (244 baseline + new T12); confirm 0 warnings.
- Coverage % on the five gate modules + _sections.py.
- Confirmation: pure-mechanical signatures (no llm_clients); no llm
  import in the five gates; section lookup via shared helper; ASCII
  clean; scope-creep gate empty.
- Any SUBSPEC interpretations made (with comment locations).
- For G2: confirm the parser actually populated parsed.risks for
  your g2_pass.md fixture (state how you verified).
