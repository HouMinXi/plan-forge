# T11 SUBSPEC: G4 (Part A) + G6 (A+B) + G8 (A+B) epistemic gates

Status: draft for subagent implementation.
Depends on: T05-T09 + T10 (llm/ subpackage, search_vote, cache,
provider clients).
Scope: epistemic gate layer first slice -- the gates that need
narrow LLM Part B (G6, G8) plus G4 mechanical-only.  G1/G2/G3/G5/G7
are T12; G9 is T29; G10 is T30.

## 0. Phase overview

| Phase | Scope | Files |
|---|---|---|
| 0 | Fix T10 JSON-parse gap in provider clients | client.py + 4 provider clients + their tests |
| 1 | epistemic scaffold + prompt loader + evidence adapter | checks/epistemic/__init__.py + _evidence.py + llm/prompts/__init__.py |
| 2 | G4 Probability Calibration (Part A only) | g4_calibration.py + tests + 2 fixtures |
| 3 | G6 SC Falsifiability (Part A + Part B) | g6_sc_falsifiability.py + prompt + tests + 2 fixtures |
| 4 | G8 Source Diversity (Part A + Part B) | g8_source_diversity.py + prompt + tests + 2 fixtures |
| 5 | epistemic.run aggregator + integration test | __init__.py run() + integration test |

Each phase has a verification gate.  Do not start phase N+1 until
phase N is green.

## 1. Scope clarification (load-bearing)

- **G4: Part A ONLY.**  Part B (LLM hedge-anchor lookup) is
  deferred to v0.1.1 per the project's success-criterion that
  defers G4 Part B and verifies only G4 Part A mechanical hedge
  detection.  Do NOT implement G4 Part B.  G4's `check` signature
  still accepts `llm_clients` for uniformity but ignores it (with
  a comment noting Part B is deferred).
- **G6: Part A + Part B.**  Mechanical fail_condition presence +
  LLM per-SC measurability vote.
- **G8: Part A + Part B.**  Mechanical External Voices structure +
  LLM per-citation resolvability vote.
- **2 prompts**: g6_sc_measurability_v0.txt, g8_citation_resolvability_v0.txt.
  Both prompt bodies already exist in the PLAN; extract verbatim
  (see Phase 3/4).  G4 needs NO prompt in T11.
- **6 fixtures**: g4_pass/fail, g6_pass/fail, g8_pass/fail.

## 2. Interface reconciliation (PLAN draft is stale; follow THIS)

The PLAN's Module Designs section contains draft code for G4/G6
that predates the actual T10 implementation.  Where the draft
conflicts with reality, follow this SUBSPEC.

### 2.1 G module signature (NO corpus, NO run_id)

PLAN draft: `check(parsed, llm_clients, run_id, corpus)`.
The corpus subsystem is T22-T24 (later than T11 AND later than the
T13 checkpoint).  T11 G modules MUST NOT depend on corpus.

Actual T11 signature for all three gates:

```python
def check(parsed: ParsedPlan, llm_clients: list[LLMClient]) -> list[Finding]:
    ...
```

Evidence is carried inside `Finding.llm_evidence`; it is NOT
recorded to a database in T11.  `LLMEvidence.run_id` is a required
field (no default) -- set it to `0` as a sentinel meaning
"not yet persisted".  A later corpus-integration task backfills
real run_ids.

### 2.2 search_vote actual signature

PLAN draft: `verdict, evidence, cost = search_vote(clients, template, payload)`.

Actual T10 signature:

```python
def search_vote(
    prompt: str,                    # fully-rendered prompt text
    active_clients: list[LLMClient],
    *,
    cache_key_inputs: dict,
    tool_use_schemas: dict,         # provider_name -> schema | None
) -> VoteResult
```

`VoteResult` fields: `status` (majority / consensus /
indeterminate / single_opinion / no_providers), `verdict`
(the agreed token or None), `evidences` (list[LLMResponse]),
`active_providers` (list[str], same order as evidences),
`threshold` (int | None).

The G module renders the prompt itself:

```python
full_prompt = prompt_template + "\n\nACTUAL INPUT:\n" + json.dumps(payload)
```

### 2.3 Verdict tokens are UPPERCASE (PLAN draft lowercase is a bug)

The G6 prompt OUTPUT schema specifies `"VERIFIED"` / `"UNVERIFIED"`
(uppercase).  The PLAN G6 draft code compares `verdict == "unverified"`
(lowercase) -- that is a defect.  Define the tokens as constants in
`_evidence.py` (single source of truth) and compare
case-insensitively:

```python
# checks/epistemic/_evidence.py
# G6 tokens -- MUST match llm/prompts/g6_sc_measurability_v0.txt OUTPUT
G6_VERIFIED = "VERIFIED"
G6_UNVERIFIED = "UNVERIFIED"
# G8 tokens -- MUST match llm/prompts/g8_citation_resolvability_v0.txt
G8_RESOLVED_VIA_SEARCH = "RESOLVED_VIA_SEARCH"
G8_RESOLVED_BY_KNOWLEDGE = "RESOLVED_BY_KNOWLEDGE"
G8_UNCERTAIN = "UNCERTAIN"
G8_UNRESOLVABLE = "UNRESOLVABLE"
```

Comparison helper:

```python
def verdict_matches(vote_verdict: str | None, token: str) -> bool:
    return vote_verdict is not None and vote_verdict.strip().upper() == token
```

### 2.4 LLMResponse -> LLMEvidence adapter

`search_vote` returns `VoteResult.evidences: list[LLMResponse]`.
`Finding.llm_evidence` wants `list[LLMEvidence]`.  `LLMResponse`
has no provider/model fields; `LLMClient` Protocol does
(`.name`, `.model`).  Convert via a shared helper in
`_evidence.py`, using the clients list to map provider -> model:

```python
def responses_to_evidence(
    vote: VoteResult,
    llm_clients: list[LLMClient],
    prompt_version: str,
) -> list[LLMEvidence]:
    model_by_name = {c.name: c.model for c in llm_clients}
    out: list[LLMEvidence] = []
    for provider_name, resp in zip(vote.active_providers, vote.evidences):
        out.append(LLMEvidence(
            provider=provider_name,
            model=model_by_name.get(provider_name, "unknown"),
            verdict=resp.verdict,
            reasoning=resp.reasoning,
            prompt_version=prompt_version,
            run_id=0,  # sentinel: not yet persisted to corpus
            cited_instances=resp.cited_instances,
            search_evidence=resp.search_evidence,
            tier=EvidenceTier.UNCLASSIFIED,  # G10 fills later
        ))
    return out
```

## 3. Phase 0: Fix the T10 JSON-parse gap

### 3.1 The defect

T10 provider clients put the LLM's entire response text into
`LLMResponse.verdict` (e.g., anthropic_client `verdict = block.text`).
They do NOT parse the unified JSON output convention that all
plan-forge judge prompts use:

```json
{"verdict": "<TOKEN>", "reason": "<text>",
 "cited_instances": [...], "search_evidence": [...]}
```

Consequence: `search_vote` votes on whole JSON strings; different
providers' JSON differs in wording, so majority NEVER forms.
T10's mock tests hid this because mocks returned bare tokens.

### 3.2 The fix (root cause, in client.py)

Add a shared parser to `client.py`:

```python
import json

def parse_verdict_response(raw_text: str) -> tuple[str, str, list, list]:
    """Parse the unified JSON verdict convention from LLM output.

    Returns (verdict, reasoning, cited_instances, search_evidence).
    Falls back to (raw_text, "", [], []) if the text is not the
    expected JSON object (back-compat for non-judge prompts).
    """
    text = raw_text.strip()
    # Strip a markdown code fence if the model wrapped its JSON.
    if text.startswith("```"):
        lines = [ln for ln in text.split("\n")
                 if not ln.strip().startswith("```")]
        text = "\n".join(lines).strip()
    try:
        data = json.loads(text)
    except (json.JSONDecodeError, ValueError):
        return raw_text, "", [], []
    if not isinstance(data, dict) or "verdict" not in data:
        return raw_text, "", [], []
    return (
        str(data["verdict"]),
        str(data.get("reason", "")),
        list(data.get("cited_instances") or []),
        list(data.get("search_evidence") or []),
    )
```

### 3.3 Apply in each provider client

In anthropic_client, kimi_client, deepseek_client, mimo_client:
where the client currently builds `LLMResponse(verdict=<raw text>,
...)`, change to:

```python
verdict, reasoning, cited_instances, search_evidence = \
    parse_verdict_response(raw_text)
resp = LLMResponse(
    verdict=verdict,
    reasoning=reasoning,
    cited_instances=cited_instances,
    search_evidence=search_evidence,
    cost_usd=<unchanged>,
    raw_response=<unchanged>,
)
```

Preserve all caching logic.  The cache stores the parsed
LLMResponse (verdict = token), which is what we want.

### 3.4 Phase 0 tests

Update each provider's test file to add:
- `test_<provider>_call_parses_json_verdict`: mock the SDK to
  return `'{"verdict": "VERIFIED", "reason": "ok", "cited_instances": [], "search_evidence": []}'`;
  assert `resp.verdict == "VERIFIED"` and `resp.reasoning == "ok"`.
- `test_<provider>_call_non_json_fallback`: mock SDK returns plain
  text `"hello"`; assert `resp.verdict == "hello"` (graceful
  fallback).
- `test_<provider>_call_markdown_fenced_json`: mock returns
  ` ```json\n{"verdict":"UNVERIFIED",...}\n``` `; assert parsed.

Keep existing Phase-3-era tests passing.

### 3.5 Phase 0 verification

```
cd /home/houminxi/code/plan-forge/.worktrees/feat-t11-epistemic-g468
unset PLAN_FORGE_CORPUS_URL
.venv/bin/pytest tests/unit/test_anthropic_client.py \
                 tests/unit/test_kimi_client.py \
                 tests/unit/test_deepseek_client.py \
                 tests/unit/test_mimo_client.py -q 2>&1 | tail -5
.venv/bin/pytest tests/ -q 2>&1 | tail -3   # 200 baseline + new still green
```

## 4. Phase 1: epistemic scaffold + prompt loader + evidence adapter

### 4.1 llm/prompts/ package (prompt loader)

Create `src/plan_forge/llm/prompts/__init__.py`:

```python
"""Versioned LLM prompt templates loaded from sibling .txt files."""
from __future__ import annotations
from pathlib import Path

_PROMPT_DIR = Path(__file__).parent

def load(name: str) -> str:
    """Load a prompt template by name (without .txt extension)."""
    path = _PROMPT_DIR / f"{name}.txt"
    if not path.exists():
        raise FileNotFoundError(f"prompt not found: {path}")
    return path.read_text(encoding="utf-8")
```

The .txt files themselves are created in Phase 3/4.

### 4.2 checks/epistemic/_evidence.py

Contains: the verdict-token constants (2.3), `verdict_matches`
(2.3), `responses_to_evidence` (2.4), AND `schema_for` (below).
Imports `VoteResult` from `plan_forge.llm.search_vote`,
`LLMEvidence`/`EvidenceTier` from `plan_forge.verdict`,
`LLMClient` from `plan_forge.llm.client`, and the web-search tool
constants from `plan_forge.llm.tool_use`.

`tool_use.py` exposes module-level constants
(`ANTHROPIC_WEB_SEARCH_TOOL`, `KIMI_WEB_SEARCH_TOOL`,
`DEEPSEEK_WEB_SEARCH_TOOL`, `MIMO_WEB_SEARCH_TOOL` which is None),
NOT a function.  Provide the lookup here (tool_use.py is
read-only):

```python
from plan_forge.llm import tool_use

_TOOL_BY_PROVIDER = {
    "anthropic": tool_use.ANTHROPIC_WEB_SEARCH_TOOL,
    "kimi": tool_use.KIMI_WEB_SEARCH_TOOL,
    "deepseek": tool_use.DEEPSEEK_WEB_SEARCH_TOOL,
    "mimo": tool_use.MIMO_WEB_SEARCH_TOOL,  # None -> no tool_use
}

def schema_for(provider_name: str) -> dict | None:
    """Return the web-search tool schema for a provider, or None."""
    return _TOOL_BY_PROVIDER.get(provider_name)
```

### 4.3 checks/epistemic/__init__.py (stub for now)

```python
"""Epistemic gates (G-layer).  T11 implements G4/G6/G8."""
from __future__ import annotations
from plan_forge.parser import ParsedPlan
from plan_forge.verdict import Finding
from plan_forge.llm.client import LLMClient
from . import g4_calibration, g6_sc_falsifiability, g8_source_diversity

def run(parsed: ParsedPlan, llm_clients: list[LLMClient]) -> list[Finding]:
    """Run G4 + G6 + G8 in order; return combined findings.

    G1/G2/G3/G5/G7 (T12) and G9/G10 (T29/T30) are not included here.
    """
    findings: list[Finding] = []
    findings.extend(g4_calibration.check(parsed, llm_clients))
    findings.extend(g6_sc_falsifiability.check(parsed, llm_clients))
    findings.extend(g8_source_diversity.check(parsed, llm_clients))
    return findings
```

(The imports of g4/g6/g8 will fail until Phase 2-4 create them;
build __init__.py incrementally or stub the imports.)

### 4.4 Phase 1 tests

`tests/unit/test_epistemic_evidence.py`:
- `test_verdict_matches_case_insensitive`
- `test_verdict_matches_none_returns_false`
- `test_responses_to_evidence_maps_provider_model` (build 2
  MockClients with known name/model; build a VoteResult with 2
  evidences; assert resulting LLMEvidence has correct provider +
  model + run_id==0 + tier==UNCLASSIFIED)
- `test_prompt_loader_loads_existing` + `test_prompt_loader_missing_raises`

## 5. Phase 2: G4 Probability Calibration (Part A only)

### 5.1 Algorithm (per PLAN Requirements + draft)

11-word hedge list is the SOURCE OF TRUTH (must match Requirements
exactly to satisfy P5 interface symmetry):
`maybe, likely, probably, perhaps, possibly, seems, appears,
should, could, might, may`.

Reuse `parsed.hedge_word_locations` (T06 parser already extracts
hedges with a fence-width-aware code-block skip -- do NOT
re-implement the state machine).  Each location is
`(line_number, hedge_word)`.

For each hedge location:
1. Get the line text: `parsed.raw_text.splitlines()[line_number - 1]`.
2. Skip if the line contains the self-reference exemption
   `"G4 Probability Calibration"` (definition meta-context).
3. Check for adjacent numeric probability: regex `r"\b\d{1,3}%\b"`
   on the line.
4. Check for exemption marker: regex
   `r"<!--\s*plan-forge:\s*hedge-ok\s*-->"` on the line.
5. If neither present, emit:
   `Finding(check_id="G4.A.mechanical", severity=Severity.MEDIUM,
   location=f"line {line_number}", message=f"hedge word {word!r}
   without numeric probability or exemption marker",
   fix_hint="add adjacent numeric probability (e.g. '70%') or
   <!-- plan-forge: hedge-ok --> if uncertainty is intentional")`.

After the loop, count the per-hedge MEDIUM findings.  If
`count > 10`, append an aggregate:
`Finding(check_id="G4.A.aggregate", severity=Severity.BLOCKER,
location="plan", message=f"{count} hedge instances without
calibration (>10 threshold)", fix_hint="calibrate probabilities
or add exemption markers")`.

`llm_clients` parameter is accepted but unused (Part B deferred to
v0.1.1).  Add a comment saying so.

### 5.2 G4 fixtures

- `g4_pass.md`: <= 10 hedges, each with numeric % or hedge-ok
  marker, OR very few uncalibrated hedges (count <= 10 so no
  aggregate BLOCKER; per-hedge MEDIUMs allowed but PASS fixture
  should ideally have 0 by giving every hedge a marker/number).
- `g4_fail.md`: > 10 uncalibrated hedges -> triggers G4.A.aggregate
  BLOCKER.

### 5.3 G4 tests (tests/unit/test_g4_calibration.py)

- `test_g4_pass_fixture_no_aggregate`
- `test_g4_fail_fixture_triggers_aggregate_blocker`
- `test_g4_numeric_probability_exempts`
- `test_g4_hedge_ok_marker_exempts`
- `test_g4_code_block_hedges_skipped` (hedge inside fenced block
  not flagged -- verifies parser reuse)
- `test_g4_ignores_llm_clients` (pass MockClients; assert no LLM
  call happens -- e.g. clients' call count stays 0)

## 6. Phase 3: G6 SC Falsifiability (Part A + Part B)

### 6.1 Part A (mechanical)

For each `sc` in `parsed.sc_table`:
- If `not sc.fail_condition` (None or empty): emit
  `Finding(check_id="G6.A.mechanical", severity=Severity.BLOCKER,
  location=sc.full_id, message="missing fail_condition column",
  fix_hint="add 'FAILS if ...' clause to SC")`.

### 6.2 Part B (LLM)

Load prompt `g6_sc_measurability_v0` via `prompts.load`.
`prompt_version = "g6_sc_measurability_v0"`.

Build tool_use_schemas via the `_evidence.schema_for` helper (4.2):
`{c.name: schema_for(c.name) for c in llm_clients}`.

`unverified_count = 0`.
For each `sc` with a non-empty `fail_condition`:
- payload = `{"sc_id": sc.number, "sc_text": sc.name,
  "fail_condition_text": sc.fail_condition}`
- full_prompt = template + "\n\nACTUAL INPUT:\n" + json.dumps(payload)
- vote = `search_vote(full_prompt, llm_clients,
  cache_key_inputs={"gate": "G6.B", "sc_id": sc.number,
  "prompt_version": prompt_version}, tool_use_schemas=schemas)`
- If `vote.status == "no_providers"`: skip Part B entirely
  (LLM unavailable; mechanical-only).  Break out / return after
  Part A findings.  Do not raise.
- evidence = `responses_to_evidence(vote, llm_clients, prompt_version)`
- If `verdict_matches(vote.verdict, G6_UNVERIFIED)`:
  - `unverified_count += 1`
  - emit `Finding(check_id="G6.B.llm", severity=Severity.HIGH,
    location=sc.full_id, message="LLM majority: fail-condition not
    measurable", fix_hint="strengthen with concrete observable
    state + detection procedure", llm_evidence=evidence)`
- (status indeterminate / single_opinion: attach evidence to a
  record but do NOT count as unverified; see note below.)

After the loop, if `parsed.sc_table` is non-empty and
`unverified_count / len(parsed.sc_table) > 0.30`:
emit `Finding(check_id="G6.B.aggregate", severity=Severity.BLOCKER,
location="plan.sc_table", message=f"{unverified_count}/{len(sc_table)}
SCs not measurable (>30% threshold)", fix_hint="rewrite SCs with
concrete fail-conditions")`.

Note on non-majority statuses: `single_opinion` -> treat its lone
verdict as the verdict (search_vote already returns it as
`vote.verdict`).  `indeterminate` -> `vote.verdict is None` ->
`verdict_matches` returns False -> not counted unverified (the
plan gets benefit of the doubt when providers disagree; this is
intentional -- disagreement is not failure).

### 6.3 G6 prompt extraction

Extract the fenced block at PLAN `#### llm/prompts/g6_sc_measurability_v0.txt`
(the prompt body between the opening and closing triple-backtick
after that heading) verbatim into
`src/plan_forge/llm/prompts/g6_sc_measurability_v0.txt`.
Verify it contains >= 4 examples (>= 1 VERIFIED + >= 3 UNVERIFIED)
per SC-21.  Do NOT paraphrase; copy exactly (ASCII only).

### 6.4 G6 fixtures

- `g6_pass.md`: SC table where every SC has a concrete measurable
  fail_condition (so Part A clean; Part B with MockClients voting
  VERIFIED gives no aggregate).
- `g6_fail.md`: SC table where > 30% of SCs lack fail_condition
  (Part A BLOCKER for each + ... ) OR have vague fail_conditions
  (Part B UNVERIFIED via MockClients).  The mechanical fixture
  must trigger G6.A.mechanical for the missing ones.

### 6.5 G6 tests (tests/unit/test_g6_sc_falsifiability.py)

- `test_g6_part_a_missing_fail_condition_blocker`
- `test_g6_part_a_all_present_no_finding`
- `test_g6_part_b_unverified_emits_high` (MockClients all vote
  `{"verdict": "UNVERIFIED", ...}` JSON)
- `test_g6_part_b_aggregate_over_30pct` (enough UNVERIFIED to cross
  threshold -> BLOCKER)
- `test_g6_part_b_no_providers_skips` (empty llm_clients ->
  no Part B findings, no crash)
- `test_g6_part_b_indeterminate_not_counted` (MockClients split
  votes -> indeterminate -> not unverified)
- `test_g6_evidence_attached_to_finding` (Finding.llm_evidence
  populated with correct provider/model)

MockClients must return JSON strings (the Phase 0 parser turns
them into tokens).  Verify the full path: JSON -> parse -> vote ->
token comparison.

## 7. Phase 4: G8 Source Diversity (Part A + Part B)

PLAN has NO module-design draft for G8.  Design per Requirements
(External Voices + non-AI primary source + dissenting view +
historical failure case + citation regex).

### 7.1 Part A (mechanical)

Find the External Voices section: look in `parsed.sections` for a
heading containing (case-insensitive) "external voices".

- If absent: emit `Finding(check_id="G8.A.no_section",
  severity=Severity.BLOCKER, location="plan", message="## External
  Voices section absent", fix_hint="add ## External Voices with a
  primary source, a dissenting view, and a historical failure
  case")` and RETURN (no point checking sub-requirements).

If present, run these checks on the section body (and use
`parsed.citations` which the parser already extracts from External
Voices):

- No citation: if `len(parsed.citations) == 0`: emit
  `G8.A.no_citation` BLOCKER.
- No dissenting view: if the section body contains none of
  (case-insensitive) {"dissent", "disagree", "counter", "critic",
  "objection", "however", "contrary", "opposing"}: emit
  `G8.A.no_dissent` BLOCKER.
- No historical failure case: if body contains none of
  {"failure", "failed", "postmortem", "post-mortem", "went wrong",
  "lesson", "incident", "retrospective"}: emit
  `G8.A.no_failure_case` BLOCKER.

SUBSPEC interpretation: "non-AI primary source" cannot be reliably
detected mechanically; T11 treats "at least one citation present"
as the mechanical proxy.  True non-AI provenance is a Part B / human
concern.  Document this with a `# SUBSPEC interpretation:` comment.

### 7.2 Part B (LLM)

Load `g8_citation_resolvability_v0`.
`prompt_version = "g8_citation_resolvability_v0"`.

For each `citation` in `parsed.citations`:
- payload = `{"citation_text": citation, "context": "External Voices"}`
- full_prompt = template + "\n\nACTUAL INPUT:\n" + json.dumps(payload)
- vote = search_vote(...) with cache_key_inputs
  `{"gate": "G8.B", "citation": citation, "prompt_version": prompt_version}`
- if `vote.status == "no_providers"`: skip Part B.
- evidence = responses_to_evidence(...)
- if `verdict_matches(vote.verdict, G8_UNRESOLVABLE)`:
  emit `Finding(check_id="G8.B.llm", severity=Severity.BLOCKER,
  location="External Voices", message=f"citation unresolvable
  (likely fabricated): {citation!r}", fix_hint="replace with a
  verifiable citation", llm_evidence=evidence)`
- elif `verdict_matches(vote.verdict, G8_UNCERTAIN)`:
  emit `Finding(check_id="G8.B.uncertain", severity=Severity.MEDIUM,
  location="External Voices", message=f"citation uncertain;
  needs human verification: {citation!r}", fix_hint="confirm the
  source manually or provide a stronger citation",
  llm_evidence=evidence)`
- RESOLVED_VIA_SEARCH / RESOLVED_BY_KNOWLEDGE: no finding (attach
  evidence to nothing; it is a pass).

### 7.3 G8 prompt extraction

Extract the fenced block at PLAN
`#### llm/prompts/g8_citation_resolvability_v0.txt` verbatim into
`src/plan_forge/llm/prompts/g8_citation_resolvability_v0.txt`.
Verify >= 3 examples (>= 1 RESOLVED_BY_KNOWLEDGE + >= 1
RESOLVED_VIA_SEARCH + >= 1 UNRESOLVABLE) per SC-22.  ASCII only,
verbatim.

### 7.4 G8 fixtures

- `g8_pass.md`: has `## External Voices` with >= 1 citation, a
  dissenting view (contains e.g. "However, critics argue..."), and
  a historical failure case (contains e.g. "the 2016 ... incident
  ... lesson"); citations are real (MockClients vote
  RESOLVED_BY_KNOWLEDGE).
- `g8_fail.md`: missing the External Voices section OR missing one
  of the three sub-requirements; OR contains a fabricated citation
  (MockClients vote UNRESOLVABLE).  Pick ONE clear failure mode and
  document it in a fixture comment.

### 7.5 G8 tests (tests/unit/test_g8_source_diversity.py)

- `test_g8_no_external_voices_section_blocker`
- `test_g8_missing_dissent_blocker`
- `test_g8_missing_failure_case_blocker`
- `test_g8_part_b_unresolvable_blocker` (MockClients vote
  UNRESOLVABLE JSON)
- `test_g8_part_b_uncertain_medium`
- `test_g8_part_b_resolved_no_finding`
- `test_g8_part_b_no_providers_skips`

## 8. Phase 5: epistemic.run aggregator + integration test

### 8.1 Finalize __init__.py run()

Per 4.3.  Ensure imports resolve now that g4/g6/g8 exist.

### 8.2 Integration test (tests/integration/test_epistemic_run_end_to_end.py)

- `test_epistemic_run_on_g6_fail_fixture` -- call
  `epistemic.run(parsed, mock_clients)`; assert combined findings
  include expected G6 check_ids.
- `test_epistemic_run_no_providers` -- call with `llm_clients=[]`;
  assert only mechanical (Part A) findings present, no crash.
- `test_epistemic_run_returns_finding_list` -- type + structure.

## 9. Verification gates (final)

```
cd /home/houminxi/code/plan-forge/.worktrees/feat-t11-epistemic-g468
unset PLAN_FORGE_CORPUS_URL

# Gate A: full suite
.venv/bin/pytest tests/ -q 2>&1 | tail -6
# Expect 200 baseline + ~35 new T11 tests; live/postgres skipped.

# Gate B: py_compile
.venv/bin/python -m py_compile \
    src/plan_forge/llm/client.py \
    src/plan_forge/llm/prompts/__init__.py \
    src/plan_forge/checks/epistemic/__init__.py \
    src/plan_forge/checks/epistemic/_evidence.py \
    src/plan_forge/checks/epistemic/g4_calibration.py \
    src/plan_forge/checks/epistemic/g6_sc_falsifiability.py \
    src/plan_forge/checks/epistemic/g8_source_diversity.py

# Gate C: ASCII clean on every changed/added file
for f in $(git diff --name-only HEAD; git ls-files --others --exclude-standard); do
    [ -f "$f" ] || continue
    n=$(python3 -c "print(sum(1 for b in open('$f','rb').read() if b>127))")
    test "$n" = "0" || { echo "FAIL non-ASCII: $f ($n)"; }
done
echo "ASCII gate done"

# Gate D: prompt fidelity -- extracted prompts match PLAN example counts
grep -c '"verdict": "VERIFIED"\|"verdict": "UNVERIFIED"' \
    src/plan_forge/llm/prompts/g6_sc_measurability_v0.txt
# >= 4 (SC-21)
grep -c 'RESOLVED_BY_KNOWLEDGE\|RESOLVED_VIA_SEARCH\|UNRESOLVABLE' \
    src/plan_forge/llm/prompts/g8_citation_resolvability_v0.txt
# >= 3 example verdicts (SC-22)

# Gate E: scope creep
git diff --name-only HEAD | grep -vE "^(src/plan_forge/llm/client\.py|src/plan_forge/llm/(anthropic|kimi|deepseek|mimo)_client\.py|src/plan_forge/llm/prompts/|src/plan_forge/checks/epistemic/|tests/unit/test_(anthropic|kimi|deepseek|mimo)_client\.py|tests/unit/test_g[468]_|tests/unit/test_epistemic_|tests/integration/test_epistemic_|tests/fixtures/g[468]_(pass|fail)\.md|\.planning/)"
# Expect zero output

# Gate F: coverage on epistemic/
.venv/bin/pytest --cov=src/plan_forge/checks/epistemic \
    tests/unit/test_g4_calibration.py \
    tests/unit/test_g6_sc_falsifiability.py \
    tests/unit/test_g8_source_diversity.py \
    tests/unit/test_epistemic_evidence.py 2>&1 | tail -12
# Expect >= 90% on epistemic/
```

## 10. Hard constraints

1. ASCII only in every new/modified file (no em-dash, no arrows,
   no smart quotes).  Exception: the extracted prompt .txt files
   must be VERBATIM copies of the PLAN prompt bodies -- if the PLAN
   prompt body is ASCII (it is), the copy is ASCII; do not
   "improve" it.
2. No AI markers anywhere ("Generated by Claude" / "Co-Authored-By"
   / model names as origin attribution).  Author is Minxi Hou.
3. SUBSPEC wins over PLAN draft on any conflict (Section 2).
   Where SUBSPEC is silent, document interpretation as
   `# SUBSPEC interpretation: ...`.
4. No new dependencies.
5. Phase order is a constraint; keep tests green at each phase.
6. Read-only files: parser.py, verdict.py, all checks/mechanical/*,
   all checks/pbr/*, api.py, search_vote.py, registry.py,
   credentials.py, cache.py, tool_use.py, mocks.py, all existing
   test_f*/test_p*/test_parser/test_verdict/test_api* and their
   fixtures.
   PERMITTED modifications: client.py + the 4 provider client
   modules + their 4 test files (Phase 0 JSON-parse fix only).
7. G4 implements Part A ONLY.  Do NOT implement G4 Part B.
8. G modules MUST NOT import or call corpus (it does not exist
   yet).  Evidence lives in Finding.llm_evidence with run_id=0.
9. Verdict tokens come from `_evidence.py` constants; never inline
   string literals like "UNVERIFIED" in g6/g8 logic.
10. MockClients in tests return JSON strings (not bare tokens), so
    tests exercise the Phase 0 parser end-to-end.

## 11. Non-goals

- Do NOT implement G1/G2/G3/G5/G7 (T12).
- Do NOT implement G9 (T29) or G10 (T30).
- Do NOT implement G4 Part B (v0.1.1).
- Do NOT implement api.check() aggregation (T13).
- Do NOT wire corpus recording (T22-T24).
- Do NOT add real live-API tests for G6/G8 Part B; MockClients
  cover the logic.  (A `@pytest.mark.live` smoke test is optional;
  if added, it must skip without credentials.)

## 12. Report-back format (< 45 lines)

- Files created (grouped by phase) + line counts.
- Files modified for Phase 0 (client.py + 4 clients + 4 tests),
  with +/- line counts.
- Total test count (200 baseline + new T11).
- Coverage % on checks/epistemic/.
- Confirmation: Phase 0 JSON fix verified (the 3 parse tests
  pass); G4 Part-A-only; verdict tokens centralized; no corpus
  import; ASCII clean; scope-creep gate clean.
- Any SUBSPEC interpretations made (with comment locations).
- Prompt fidelity: example counts in the two extracted prompts.
