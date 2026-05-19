# T09 SUBSPEC: api.check_mechanical()

Status: draft for subagent implementation.
Depends on: T05 (api.py stub), T06 (parser + verdict), T07 (F1-F7),
T08 (PBR P1/P2/P5 + integrated mechanical.run).
Scope: ONE public function `check_mechanical()` in api.py + tests.

## 1. Design decisions (load-bearing, do not deviate)

Four decisions were resolved before this SUBSPEC was written.  They
shape the entire module:

### D1: Return type is `Verdict`, not `list[Finding]`

`check_mechanical()` returns a fully-constructed `Verdict` object,
not a raw list of findings.  This matches the signature shape T13's
`check()` will use, so callers can swap T09 -> T13 without rewriting
client code.  The Verdict's `findings` field carries the raw list;
the `engineering` and `epistemic` fields carry the computed verdicts
per rules D2 and D3.

### D2: Engineering verdict triggers on HIGH or higher

Rule: `engineering = FAIL` if any finding has severity in
{BLOCKER, HIGH}.  Otherwise `engineering = PASS`.

Rationale: T08 established that HIGH means "plan-failure signal"
(per SUBSPEC section 1 of T08).  If HIGH does not trigger FAIL,
the severity assignment becomes a lie.  Medium and Low are
informational; they appear in `findings` but do not flip
engineering.

There is no MEDIUM tier in current Severity usage by F/PBR layers
(T07/T08 prescribed only LOW and HIGH), but the rule still mentions
MEDIUM-not-triggering for forward-compat with G layer.

### D3: Epistemic verdict defaults to VISION in mechanical-only mode

Rule: `epistemic = EpistemicVerdict.VISION` always, in T09.

Rationale: epistemic correctness requires G1-G10 evaluation (T11,
T12, T29, T30).  T09 has not run any G check.  Per MANIFESTO
default-skepticism, an unevaluated plan is assumed unverified-as-
plan until proven otherwise.  VISION is the canonical "not yet
shown to be a plan" verdict.

T13 will recompute epistemic after running G checks.  Do NOT add a
new EpistemicVerdict enum value -- modifying verdict.py is out of
scope.

### D4: Single signature, accepts `plan_text: str` only

```python
def check_mechanical(
    plan_text: str,
    preamble: str | None = None,
) -> Verdict:
    ...
```

Callers needing path-based input call `Path(p).read_text()` first.
File-IO is the CLI adapter's responsibility (T16), not the API
core's.

## 2. Architecture

T09 modifies exactly ONE existing file and adds two test files:

```
src/plan_forge/api.py            # rewrite check() stub area;
                                 # add check_mechanical()
                                 # keep scaffold() stub unchanged
tests/unit/test_api_mechanical.py        # NEW
tests/integration/test_api_mechanical_e2e.py  # NEW
```

No new dataclasses.  No new fixtures (reuse T06/T07/T08 fixtures
under tests/fixtures/).

### api.py post-T09 structure

```python
"""Public API: check_mechanical() now; check() and scaffold() in
later tasks."""
from __future__ import annotations
from pathlib import Path
from .parser import parse
from .checks import mechanical
from .verdict import (
    Verdict, EngineeringVerdict, EpistemicVerdict, Severity,
)


def check_mechanical(
    plan_text: str,
    preamble: str | None = None,
) -> Verdict:
    """Run mechanical checks (F1-F7 + PBR P1/P2/P5) only.

    Does NOT run epistemological gates (G1-G10).  Use check()
    (T13) for the full pipeline.
    """
    parsed = parse(plan_text)
    findings = mechanical.run(parsed, preamble=preamble)
    engineering = _compute_engineering(findings)
    return Verdict(
        engineering=engineering,
        epistemic=EpistemicVerdict.VISION,
        findings=findings,
    )


def _compute_engineering(findings: list[Finding]) -> EngineeringVerdict:
    """Engineering verdict: FAIL iff any finding has severity
    BLOCKER or HIGH; PASS otherwise.

    Per T09 D2: HIGH means plan-failure signal, so HIGH must
    flip engineering to FAIL.
    """
    fail_severities = {Severity.BLOCKER, Severity.HIGH}
    if any(f.severity in fail_severities for f in findings):
        return EngineeringVerdict.FAIL
    return EngineeringVerdict.PASS


def check(plan_text: str, **kwargs) -> Verdict:
    """Run all gates on plan_text and return a Verdict.

    T13 implements this.
    """
    raise NotImplementedError


def scaffold(name: str, output_dir: Path | None = None) -> Path:
    """Generate a plan skeleton from the default template.

    T14 implements this.
    """
    raise NotImplementedError
```

Note: `Finding` import is needed for the type hint in
`_compute_engineering`.  Add to the import block.

`_compute_engineering` is private (underscore prefix) so T13 can
choose to either reuse it or define its own aggregator without
breaking back-compat (no public name exported).

## 3. Test plan

### Unit tests (tests/unit/test_api_mechanical.py)

Required test cases:

1. `test_check_mechanical_empty_plan` -- empty string input;
   returns a Verdict with engineering=PASS and epistemic=VISION;
   findings list may be empty or contain trivial F-findings
   (whatever the F/PBR layer produces on empty input -- do not
   assert content, only structure).

2. `test_check_mechanical_returns_verdict_type` -- non-empty plan;
   assert `isinstance(result, Verdict)`; assert `result.findings`
   is `list`; assert all elements are `Finding` instances.

3. `test_check_mechanical_epistemic_always_vision` -- run on three
   different inputs (empty / pass-fixture content / fail-fixture
   content); each call's `result.epistemic` MUST equal
   `EpistemicVerdict.VISION`.  This is the contract guarantee from
   D3.

4. `test_check_mechanical_engineering_pass_on_clean_input` --
   feed an input that produces only LOW findings (or no findings);
   assert `result.engineering == EngineeringVerdict.PASS`.  Use
   tests/fixtures/f5_pass.md as the input (F5 PASS fixture is
   minimal and clean).

5. `test_check_mechanical_engineering_fail_on_high_finding` --
   feed an input that triggers at least one HIGH finding.  Use
   tests/fixtures/f7_fail.md (the non-ASCII fixture; F7 emits
   HIGH).  Assert `result.engineering == EngineeringVerdict.FAIL`.

6. `test_check_mechanical_preamble_kwarg_passed_through` -- feed
   a plan AND a preamble where the preamble contains a sentence
   absent from the plan body.  Assert at least one finding with
   `check_id == "F6.preamble_only_fact"` appears.  Preamble plumbing
   is fragile; explicit regression test.

7. `test_compute_engineering_rule` -- direct unit test of
   `_compute_engineering`.  Pass crafted Finding lists:
   - empty list -> PASS
   - one LOW -> PASS
   - one HIGH -> FAIL
   - one BLOCKER -> FAIL
   - mix of LOW + HIGH -> FAIL
   - mix of LOW + MEDIUM only -> PASS (MEDIUM does not trigger)

   Import `_compute_engineering` from `plan_forge.api`; private
   import is acceptable for unit testing the rule directly.

### Integration test (tests/integration/test_api_mechanical_e2e.py)

End-to-end test running `check_mechanical()` on each of the
three T06 fixtures plus three new path-style assertions:

1. `test_api_mechanical_on_pass_well_formed` -- input is
   `tests/fixtures/pass_well_formed.md` content; assert returned
   Verdict; assert epistemic == VISION; engineering value is
   whatever F + PBR compute (do NOT hardcode PASS or FAIL -- the
   T06 well-formed fixture was designed for G layer, may or may not
   trip F/PBR).  Snapshot the engineering value and check_id
   counts; if any subsequent commit changes them, the test fails
   loudly forcing the author to confirm intent.

2. `test_api_mechanical_on_fail_missing_premortem` -- same shape;
   document any engineering / findings change.

3. `test_api_mechanical_on_fail_no_g9_anchor` -- same shape.

For each integration test: assert the returned object's structure
(Verdict type, findings is list, etc.) is invariant; the specific
verdict values may shift between commits, so use snapshot-style
assertions with comments explaining each expected value.  If the
sub-agent finds a fixture trips an unexpected check (e.g.,
pass_well_formed.md trips F7 because of a smart quote we missed),
treat it as a sign the fixture needs touch-up; document in the
test comment and proceed.

## 4. Non-goals (do NOT do in T09)

- Do NOT implement `check()` (T13).
- Do NOT implement `scaffold()` (T14).
- Do NOT modify `parser.py`, `verdict.py`, or any T07 / T08 module
  under `src/plan_forge/checks/`.
- Do NOT add new EpistemicVerdict or Severity enum values.
- Do NOT create new fixture files.  Reuse existing fixtures.
- Do NOT add LLM imports, network access, or subprocess calls.
- Do NOT change any existing test (T06 / T07 / T08 tests must all
  still pass unchanged).

## 5. Verification gates (must pass before report-back)

```
cd /home/houminxi/code/plan-forge/.worktrees/feat-t09-api-mechanical

# Gate 1: full test suite (baseline 125 + new T09 tests).
.venv/bin/pytest -q tests/ 2>&1 | tail -5
# Expect 125 + ~10 new T09 tests = ~135 total passing.

# Gate 2: py_compile clean.
.venv/bin/python -m py_compile src/plan_forge/api.py

# Gate 3: ASCII clean on new files + modified api.py.
for f in src/plan_forge/api.py \
         tests/unit/test_api_mechanical.py \
         tests/integration/test_api_mechanical_e2e.py; do
    n=$(python3 -c "print(sum(1 for b in open('$f','rb').read() if b>127))")
    echo "$f: $n non-ASCII"
    test "$n" = "0" || echo "FAIL: $f has non-ASCII bytes"
done

# Gate 4: scope creep check -- ONLY these files may differ from
# HEAD~1.
git diff --name-only HEAD | grep -vE "^(src/plan_forge/api\.py|tests/unit/test_api_mechanical\.py|tests/integration/test_api_mechanical_e2e\.py|\.planning/)"
# Expect zero output.

# Gate 5: coverage on api.py.
.venv/bin/pytest --cov=src/plan_forge/api \
    tests/unit/test_api_mechanical.py \
    tests/integration/test_api_mechanical_e2e.py \
    2>&1 | tail -10
# Expect >= 90% coverage on api.py (the only T09 production module).

# Gate 6: import smoke test.
.venv/bin/python -c "
from plan_forge.api import check_mechanical
from plan_forge.verdict import Verdict, EngineeringVerdict, EpistemicVerdict
result = check_mechanical('# Hello')
assert isinstance(result, Verdict)
assert result.epistemic == EpistemicVerdict.VISION
print('import smoke: OK')
"
```

All gates pass: pytest green; py_compile clean; ASCII clean; no
scope creep; coverage on api.py >= 90%; import smoke OK.

## 6. Hard constraints (subagent contract)

1. ASCII only in every modified or new file.  `--` not em-dash;
   `->` not arrow; straight quotes; ASCII only.
2. No AI markers in any file (no "Generated by Claude" / "Co-
   Authored-By: Claude" / "Anthropic" / "GPT" / "Opus" / "Sonnet"
   / "DeepSeek" / "Kimi" / "Mimo" / "subagent" / etc.).  Author is
   Minxi Hou.
3. SUBSPEC wins: if SUBSPEC contradicts PLAN, follow SUBSPEC.
4. No new dependencies: stdlib only.
5. Do NOT modify any file outside the 3 allowed files (api.py,
   2 new test files) plus the .planning/ directory if you need to
   add anything there.  Specifically:
   - parser.py: read-only
   - verdict.py: read-only
   - checks/mechanical/*.py: read-only
   - checks/pbr/*.py: read-only
   - all existing tests: read-only
   - all existing fixtures: read-only
6. `_compute_engineering` must be private (underscore prefix).
   `check_mechanical` must be public (no underscore).
7. Epistemic verdict in T09 output is ALWAYS VISION.  No
   conditional logic on this; D3 is a contract.
8. Engineering verdict triggers on {BLOCKER, HIGH}, not on MEDIUM
   or LOW.  D2 contract.
