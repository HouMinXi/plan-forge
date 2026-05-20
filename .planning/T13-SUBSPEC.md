# T13 SUBSPEC: api.check() aggregation (CHECKPOINT 1)

Status: draft for subagent implementation.
Depends on: T01-T12 (parser, verdict, F1-F7, PBR, G1-G8).
Scope: implement the full `api.check()` that aggregates all three
layers (mechanical F, PBR, epistemic G1-G8) and computes both
engineering and epistemic verdicts per the PLAN's decision rules.
This is CHECKPOINT 1 (week 5): after T13, plan-forge is a usable
tool that can evaluate a complete plan document.

## 0. Phase overview

| Phase | Scope | Files |
|---|---|---|
| 1 | LLM client bootstrap (registry + credentials) | api.py helper |
| 2 | api.check() core aggregation | api.py check() + _compute_epistemic |
| 3 | End-to-end integration test | tests/integration/test_api_check_e2e.py + well_formed.md fixture |
| 4 | Verdict summary helpers | verdict.py summary() method |

T13 does NOT implement corpus recording (T22-T24), arbitration UI
(T25-T27), or G9/G10 (T29/T30).  It wires the existing gates into
a single entry point and applies the PLAN's verdict decision rules.

## 1. Design principles (load-bearing)

### 1.1 api.check() signature and defaults

```python
def check(
    plan_text: str,
    *,
    llm_clients: list[LLMClient] | None = None,
    preamble: str | None = None,
) -> Verdict:
    """Run all gates (F1-F7 + PBR + G1-G8) and return aggregated Verdict.
    
    Args:
        plan_text: raw markdown text of the plan document.
        llm_clients: optional list of LLMClient instances for G4/G6/G8
            Part B.  If None, bootstraps from environment via registry +
            credentials (see 1.2).  If empty list [], skips LLM Part B
            (mechanical-only mode).
        preamble: optional orchestrator preamble for F6 preamble-body
            diff check.  When None, F6 returns no findings.
    
    Returns:
        Verdict with engineering (PASS/FAIL), epistemic (PASS/FAIL/VISION),
        and combined findings from all three layers.
    """
```

The `llm_clients=None` default triggers bootstrap (1.2).  Passing
`llm_clients=[]` explicitly skips LLM gates (mechanical-only mode,
useful for CI without credentials).

### 1.2 LLM client bootstrap (when llm_clients=None)

When the caller does not provide `llm_clients`, `api.check()` builds
the list from environment via the existing T10 registry + credentials:

```python
from plan_forge.llm.registry import get_all_clients
from plan_forge.llm.credentials import resolve_credentials

def _bootstrap_llm_clients() -> list[LLMClient]:
    """Build LLM client list from environment credentials.
    
    Uses the T10 registry + credentials resolver.  Returns all clients
    whose credentials resolve (may be empty if no env vars set).
    Silently skips providers with missing credentials (no error).
    """
    return get_all_clients()  # T10 already does credential resolution
```

This is a thin wrapper; the T10 `get_all_clients()` already handles
credential resolution and health checks.  If it returns an empty
list (no credentials), that is fine -- G4/G6/G8 Part B will skip
(their `no_providers` path).

### 1.3 Verdict decision rules (PLAN lines 383-422)

**Epistemic verdict** (computed from findings alone; does NOT key
off the engineering verdict):

Serious findings (BLOCKER or HIGH) are partitioned by check_id
prefix into two buckets:

- **Vision gates** G1/G2/G3/G5/G7: structural absence of a plan
  section.  A plan missing these sections is by construction a
  vision document.  Both BLOCKER (section absent) and HIGH
  (partial-field missing, e.g. G7.missing_barbell, G2.gray_rhino_no_denial)
  are vision triggers.

- **All other gates** (F*, P*, G4/G6/G8): non-vision serious
  findings.  These are FAIL triggers.

Decision rules:
1. **FAIL** if any non-vision serious finding exists.
2. **VISION** else if any vision-gate serious finding exists.
3. **PASS** otherwise.

Precedence FAIL > VISION > PASS is inherent in the evaluation order.

Note: an earlier revision keyed the FAIL trigger off
`engineering == FAIL`, which fires on any BLOCKER/HIGH including
vision-gate findings.  That made VISION mathematically unreachable
because every vision trigger is itself a BLOCKER/HIGH that flips
engineering to FAIL.  The partition rule above fixes this by
separating the two concerns.

### 1.4 Three-layer aggregation order

```python
parsed = parse(plan_text)
findings: list[Finding] = []

# Layer 1: mechanical F1-F7
findings.extend(mechanical.run(parsed, preamble=preamble))

# Layer 2: PBR
findings.extend(pbr.run(parsed))

# Layer 3: epistemic G1-G8
if llm_clients is None:
    llm_clients = _bootstrap_llm_clients()
findings.extend(epistemic.run(parsed, llm_clients))

engineering = _compute_engineering(findings)
epistemic_verdict = _compute_epistemic(findings)
return Verdict(engineering=engineering, epistemic=epistemic_verdict,
               findings=findings)
```

The order (F -> PBR -> G) is not load-bearing for correctness (all
findings are collected before verdict computation), but it matches
the conceptual layering and makes the integration test's finding
order predictable.

## 2. Phase 1: LLM client bootstrap helper

Add `_bootstrap_llm_clients()` to `api.py` per 1.2.  This is a
2-line function wrapping `get_all_clients()`.  No test needed (T10
already tested the registry + credentials; this is a trivial
delegation).

## 3. Phase 2: api.check() core aggregation

### 3.1 Implement check()

Replace the `raise NotImplementedError` stub with the full
implementation per 1.4.  Imports:

```python
from .checks import mechanical, pbr, epistemic
from .llm.registry import get_all_clients
```

### 3.2 Implement _compute_epistemic()

```python
def _compute_epistemic(findings: list[Finding]) -> EpistemicVerdict:
    """Compute epistemic verdict from findings alone (PLAN 383-422).

    Serious (BLOCKER/HIGH) findings are partitioned by gate prefix:
    vision gates G1/G2/G3/G5/G7 yield a VISION trigger; all other gates
    (F*, P*, G4/G6/G8) yield a FAIL trigger. Precedence FAIL > VISION >
    PASS. This deliberately does NOT key off the engineering verdict:
    engineering FAIL fires on any BLOCKER/HIGH including vision gates,
    which would make VISION unreachable.
    """
    vision_gate_prefixes = ("G1.", "G2.", "G3.", "G5.", "G7.")
    serious = (Severity.BLOCKER, Severity.HIGH)
    has_fail_trigger = any(
        f.severity in serious
        and not f.check_id.startswith(vision_gate_prefixes)
        for f in findings
    )
    has_vision_trigger = any(
        f.severity in serious
        and f.check_id.startswith(vision_gate_prefixes)
        for f in findings
    )
    if has_fail_trigger:
        return EpistemicVerdict.FAIL
    if has_vision_trigger:
        return EpistemicVerdict.VISION
    return EpistemicVerdict.PASS
```

### 3.3 Phase 2 tests (tests/unit/test_api_check.py)

- `test_check_mechanical_only_mode`: call `check(plan, llm_clients=[])`
  (empty list, not None).  A minimal plan has G1-G7 absent (vision
  triggers) AND G8.A.no_section (non-vision BLOCKER = FAIL trigger).
  FAIL > VISION, so epistemic is FAIL.  Engineering is also FAIL.

- `test_check_bootstrap_llm_clients_none`: call `check(plan,
  llm_clients=None)` (default); mock `build_active_list` to return
  `[]`; assert no crash, epistemic computed.

- `test_compute_epistemic_vision_trigger`: build findings with a
  G1.no_section BLOCKER; assert `_compute_epistemic(findings)
  == EpistemicVerdict.VISION`.

- `test_compute_epistemic_fail_precedence`: build findings with both
  a G1.no_section BLOCKER (VISION trigger) and an F1.orphan_sc HIGH
  (non-vision FAIL trigger); assert epistemic is FAIL (precedence).

- `test_compute_epistemic_g6_aggregate_fail`: build findings with
  G6.B.aggregate BLOCKER; assert FAIL.

- `test_compute_epistemic_pass`: no VISION/FAIL triggers; assert PASS.

## 4. Phase 3: End-to-end integration test + well_formed fixture

### 4.1 Fixture: tests/fixtures/well_formed.md

A plan that satisfies ALL gates (F1-F7 + PBR + G1-G8 mechanical +
G4/G6/G8 Part B with MockClients).  This is the "golden path"
fixture.  Requirements:

- F1: SC table + test list with full traceability (no orphans).
- F2: no duplicate facts (each fact appears in <= 2 sections).
- F3: no cross-plan invariant violations (if it references other
  plans, they are in Audit Notes exemption).
- F4: no vague temporal anchors ("soon", "later").
- F5: SC table with <= 2 inline R-tags per SC.
- F6: (skip; preamble=None in the test).
- F7: ASCII only.
- P1: symbol closure (all referenced symbols defined in Deliverables).
- P2: no scope drift (all deliverables in Overview appear in
  Deliverables table).
- P5: interface symmetry (public API in Deliverables matches
  Module Designs).
- G1: ## Reference Class with >= 2 projects + ratios.
- G2: ## Risks with Known / Gray Rhinos / Black Swans; gray rhinos
  have denial_reason, black swans have survival_plan.
- G3: ## Pre-mortem with >= 5 causes, mentions "early warning" and
  "counter".
- G4: <= 10 uncalibrated hedges (or all hedges have % or hedge-ok).
- G5: ## Chaos Response with >= 3 scenarios, not all "break".
- G6: all SCs have fail_condition; MockClients vote VERIFIED.
- G7: ## Scope Challenge answers Q1-Q4 (necessity / consumers /
  do-nothing / barbell).
- G8: ## External Voices with citation + dissent + failure case;
  MockClients vote RESOLVED_BY_KNOWLEDGE.

This is a large fixture (~150-200 lines).  Build it incrementally:
start with a minimal plan, add sections until all gates pass.  Use
the existing pass fixtures (f3_pass.md, g1_pass.md, etc.) as
templates for each section.

### 4.2 Integration test (tests/integration/test_api_check_e2e.py)

```python
def test_check_well_formed_plan_pass():
    """End-to-end: well_formed.md passes all gates -> PASS/PASS."""
    plan_text = (Path(__file__).parent.parent / "fixtures" / "well_formed.md").read_text()
    
    # Mock LLM clients for G4/G6/G8 Part B
    mock_clients = [
        MockClient("mock_a", "model-a"),
        MockClient("mock_b", "model-b"),
    ]
    # Configure mocks to vote VERIFIED for G6, RESOLVED_BY_KNOWLEDGE for G8
    # (see T11 test_g6/test_g8 for the JSON response pattern)
    
    verdict = check(plan_text, llm_clients=mock_clients, preamble=None)
    
    assert verdict.engineering == EngineeringVerdict.PASS
    assert verdict.epistemic == EpistemicVerdict.PASS
    # Findings may be non-empty (MEDIUM/LOW informational), but no
    # BLOCKER/HIGH.
    assert all(f.severity not in {Severity.BLOCKER, Severity.HIGH}
               for f in verdict.findings)
```

Additional integration tests:
- `test_check_vision_plan`: a plan missing G1/G7 sections (G3 satisfied
  by Pre-mortem) -> epistemic VISION.
- `test_check_fail_plan`: a plan with F1 orphan SC (BLOCKER) ->
  engineering FAIL, epistemic FAIL (precedence).

## 5. Phase 4: Verdict summary helpers

Add a `summary()` method to `Verdict` (in `verdict.py`) that returns
a human-readable string summarizing the verdict + finding counts by
severity.  This is used by Adapter B (T25 skill) and Adapter C (T28
CLI) to display results.

```python
@dataclass
class Verdict:
    engineering: EngineeringVerdict
    epistemic: EpistemicVerdict
    findings: list[Finding] = field(default_factory=list)
    active_providers: list[str] = field(default_factory=list)
    
    def summary(self) -> str:
        """Human-readable summary of verdict + finding counts."""
        counts = {s: 0 for s in Severity}
        for f in self.findings:
            counts[f.severity] += 1
        
        lines = [
            f"Engineering: {self.engineering.value}",
            f"Epistemic: {self.epistemic.value}",
            f"Findings: {len(self.findings)} total",
            f"  BLOCKER: {counts[Severity.BLOCKER]}",
            f"  HIGH: {counts[Severity.HIGH]}",
            f"  MEDIUM: {counts[Severity.MEDIUM]}",
            f"  LOW: {counts[Severity.LOW]}",
        ]
        if self.active_providers:
            lines.append(f"LLM providers: {', '.join(self.active_providers)}")
        return "\n".join(lines)
```

Test: `tests/unit/test_verdict_summary.py` with a Verdict containing
mixed findings; assert the summary string format.

## 6. Verification gates

```
cd /home/houminxi/code/plan-forge/.worktrees/feat-t13-api-check
unset PLAN_FORGE_CORPUS_URL

# Gate A: full suite
.venv/bin/pytest tests/ -q 2>&1 | tail -6
# Expect 286 baseline + ~10 new T13 tests; 0 warnings.

# Gate B: py_compile
.venv/bin/python -m py_compile src/plan_forge/api.py src/plan_forge/verdict.py

# Gate C: ASCII
for f in $(git show --name-only --format='' HEAD 2>/dev/null); do
    [ -f "$f" ] || continue
    n=$(python3 -c "print(sum(1 for b in open('$f','rb').read() if b>127))")
    test "$n" = "0" || echo "FAIL $f: $n"
done; echo "ascii done"

# Gate D: scope creep (use git show)
git show --name-only --format='' HEAD 2>/dev/null | grep -vE "^(src/plan_forge/(api|verdict)\.py|tests/unit/test_(api_check|verdict_summary)\.py|tests/integration/test_api_check_e2e\.py|tests/fixtures/well_formed\.md|\.planning/|^$)"
# Expect empty.

# Gate E: well_formed.md fixture completeness
# Parse it and assert all gate modules return findings (or no BLOCKER/HIGH)
.venv/bin/python -c "
from pathlib import Path
from plan_forge.parser import parse
from plan_forge.checks import mechanical, pbr, epistemic
from plan_forge.llm.mocks import MockClient

plan = Path('tests/fixtures/well_formed.md').read_text()
parsed = parse(plan)
mocks = [MockClient('a', 'm'), MockClient('b', 'm')]

f_findings = mechanical.run(parsed, preamble=None)
pbr_findings = pbr.run(parsed)
g_findings = epistemic.run(parsed, mocks)

print(f'F: {len(f_findings)}, PBR: {len(pbr_findings)}, G: {len(g_findings)}')
# All should be >= 0; if any gate crashes, this fails.
"

# Gate F: end-to-end smoke
.venv/bin/python -c "
from pathlib import Path
from plan_forge.api import check

plan = Path('tests/fixtures/well_formed.md').read_text()
v = check(plan, llm_clients=[])  # mechanical-only
print(f'{v.engineering.value} / {v.epistemic.value}')
assert v.engineering.value in ('PASS', 'FAIL')
assert v.epistemic.value in ('PASS', 'FAIL', 'VISION')
print('smoke pass')
"
```

## 7. Hard constraints

1. ASCII only.
2. No AI markers; author Minxi Hou; comments describe behavior.
3. SUBSPEC wins; document interpretations with
   `# SUBSPEC interpretation: ...`.
4. No new dependencies.
5. Phase order; tests green at each phase.
6. READ-ONLY: parser.py, all checks/* modules (mechanical, pbr,
   epistemic gate modules), llm/* (except you import from registry),
   and all existing tests/fixtures.  PERMITTED edits: api.py (check()
   + _compute_epistemic + _bootstrap_llm_clients), verdict.py
   (summary() method).
7. `llm_clients=None` triggers bootstrap; `llm_clients=[]` is
   mechanical-only mode (no LLM calls).
8. Verdict precedence: FAIL > VISION > PASS.  Apply after computing
   both conditions.
9. well_formed.md must satisfy ALL gates (F1-F7 + PBR + G1-G8); use
   existing pass fixtures as section templates.

## 8. Non-goals

- Do NOT implement corpus recording (T22-T24).
- Do NOT implement arbitration UI (T25-T27).
- Do NOT implement G9/G10 (T29/T30).
- Do NOT implement scaffold() (T14).
- Do NOT implement CLI adapter (T28) or skill adapter (T25).
- Do NOT add real live-API tests; MockClients cover the logic.

## 9. Report-back format (< 35 lines)

- Files modified (api.py, verdict.py) +/- lines.
- Files created (well_formed.md, test_api_check_e2e.py,
  test_api_check.py, test_verdict_summary.py) + line counts.
- Total test count (286 baseline + new T13); confirm 0 warnings.
- Confirmation: llm_clients=None bootstrap works; llm_clients=[]
  mechanical-only works; FAIL > VISION > PASS precedence correct;
  well_formed.md passes all gates; ASCII clean; scope-creep gate
  empty.
- Any SUBSPEC interpretations made (with comment locations).
- well_formed.md fixture size (line count).
