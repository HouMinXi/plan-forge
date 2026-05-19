# T08 SUBSPEC: PBR P1 / P2 / P5 mechanical checks

Status: draft for subagent implementation.
Depends on: T05 skeleton, T06 parser, T07 mechanical F1-F7.
Scope: P1 / P2 / P5 only.  P6 is split to T17 per PLAN R4 T4 fix.
G1-G10 is T11/T12.

## 1. Severity philosophy (read this first)

PBR is NOT code lint.  PBR severity is decided by "is this a plan-
failure signal?", not by "what is the runtime bug risk?".  A
false-positive (FP) in PBR is a FEATURE, not a cost: when an FP
fires, the author must add a marker / cross-reference / invariant
comment.  That action is itself a plan improvement.

Consequence: P1 / P2 / P5 are all HIGH.  None are downgraded for
heuristic FP risk -- the heuristic FP IS the dimension being
exercised.  Escape hatches (inline markers, named cross-references)
let the author take ownership of clarity rather than have the tool
silently lower the bar.

This severity discipline is the inverse of F2 / F4 / F5 / F6, which
are LOW because the FP-resolution action is form-only (rewrites,
moves, restatements) and rarely yields true plan improvement.

## 2. Architecture

```
src/plan_forge/checks/
    mechanical/         # T07 (existing; minor edit to __init__.py)
    pbr/                # T08 (new)
        __init__.py     # exposes run(parsed) -> list[Finding]
        p1_symbol_closure.py
        p2_null_propagation.py
        p5_interface_symmetry.py
```

Each `p<N>_*.py` exports exactly:

```python
def check(parsed: ParsedPlan) -> list[Finding]:
    ...
```

`pbr.run` aggregates by calling P1, P2, P5 in order:

```python
def run(parsed: ParsedPlan) -> list[Finding]:
    findings: list[Finding] = []
    findings.extend(p1_symbol_closure.check(parsed))
    findings.extend(p2_null_propagation.check(parsed))
    findings.extend(p5_interface_symmetry.check(parsed))
    return findings
```

### 2.1 Integration with T07 mechanical.run

PLAN line 117: "PBR checks run as part of `checks.mechanical.run`;
same Finding schema; same severity grading."

T08 modifies `src/plan_forge/checks/mechanical/__init__.py` to append
`pbr.run(parsed)` results after F7.  Final F+PBR ordering:

```
F1, F2, F3, F4, F5, F6, F7, P1, P2, P5
```

This is the ONLY edit T08 makes to T07-area files.  Do not change F1-
F7 modules or their tests.

## 3. Finding contract (shared across P1 / P2 / P5)

Same dataclass shape as T07.  `llm_evidence` and
`evidence_tier_summary` left at default (empty) -- PBR is pure
mechanical.

```
Finding(
    check_id=<see per-P table>,
    severity=Severity.HIGH,         # ALL three P's
    location=<"line:<N>" OR "section:<heading>:line:<N>">,
    message=<see per-P format>,
    fix_hint=<see per-P format>,
)
```

## 4. Per-P specs

### P1 Symbol closure

- check_id: `P1.orphan_identifier`
- severity: HIGH
- Inputs from ParsedPlan: `raw_text`, `sections`

#### Identifier extraction

From `raw_text`, scan for these patterns (all case-sensitive unless
noted):

1. **Backtick-quoted identifiers**: regex
   `r"\`([A-Za-z_][A-Za-z0-9_.]{2,})\`"` -- captured group is the
   identifier.  Length >= 3 chars to avoid trivial tokens.
2. **SC IDs**: `r"\bSC-\d+[a-z]?\b"`.
3. **T-task IDs**: `r"\bT\d{2,3}\b"`.
4. **Phase IDs**: `r"\bphase[-\s]\d+\b"` (case-insensitive).
5. **Subplan IDs**: `r"\b0[1-9]-\d{2}\b"` (matches `02-03`, `01-05`).

Build `occurrences: dict[str, list[int]]` mapping identifier ->
list of line numbers where it appears.

#### Definition / cross-reference detection

For each unique identifier `X`:

1. If `len(occurrences[X]) >= 2`: considered defined (multiple uses
   implies definition + reference within the plan).  NO finding.
2. Else (`len(occurrences[X]) == 1`):
   a. If the single occurrence is inside a section whose heading
      contains (case-insensitive) any of: `"audit notes"`,
      `"references"`, `"appendix"`, `"implementation tasks"`,
      `"cross-plan references"`, `"external voices"`,
      `"open questions"`, `"changelog"`, `"glossary"`: NO finding
      (cross-reference section is its own evidence).
   b. If the line containing the occurrence (or the line immediately
      above) contains the marker
      `<!-- plan-forge: p1-ok` (regex `r"<!--\s*plan-forge:\s*p1-ok"`):
      NO finding (explicit author exemption).
   c. Otherwise: emit `Finding(check_id="P1.orphan_identifier",
      severity=HIGH, location=f"line:{N}", message=f"identifier
      {X!r} appears once in plan with no upstream cross-reference",
      fix_hint=f"add a definition / cross-reference under ##
      References, ## Audit Notes, or ## Glossary; or add inline
      <!-- plan-forge: p1-ok (reason) --> if the identifier is
      intentionally external and self-explanatory")`.

#### Exemptions (built-in, not author-controlled)

- Common English words that survive the regex but are not
  identifiers: skip the identifier if it matches (case-insensitive)
  any of: `python`, `none`, `true`, `false`, `null`, `optional`,
  `int`, `str`, `bool`, `list`, `dict`, `set`, `tuple`, `bytes`,
  `float`, `any`, `type`, `self`, `class`, `def`, `import`, `from`,
  `as`, `if`, `else`, `for`, `while`, `return`, `yield`, `pass`.
- Identifiers appearing inside fenced code blocks count as a use
  but NOT as a definition (code blocks are illustrative; definition
  must be in prose or table form).  Use the SAME fence-width state
  machine pattern as parser.py.

### P2 Null propagation

- check_id: `P2.orphan_optional`
- severity: HIGH
- Inputs from ParsedPlan: `raw_text`

#### Nullable declaration detection

Scan ONLY content inside fenced code blocks (PBR P2 examines design
pseudocode, not prose).  Use the fence-width state machine.

Within each fenced block, find all matches of:

1. `r"(\w+)\s*:\s*\w+(?:\[[^\]]+\])?\s*\|\s*None\b"` -- captures
   variable name; pattern `name: Type | None`.
2. `r"(\w+)\s*:\s*Optional\[[^\]]+\]"` -- captures variable name;
   pattern `name: Optional[Type]`.
3. `r"def\s+\w+\([^)]*\)\s*->\s*\w+(?:\[[^\]]+\])?\s*\|\s*None\b"`
   -- function return type `-> T | None` (capture function name
   instead of variable).
4. `r"def\s+\w+\([^)]*\)\s*->\s*Optional\["` -- function returning
   `Optional[T]` (capture function name).

For each captured nullable `X` at line `N`:

#### Null-handling detection

Search the same fenced code block (entire block, not just nearby
lines) for ANY of these patterns:

1. `r"\bif\s+" + re.escape(X) + r"\s+is\s+None\b"`
2. `r"\bif\s+not\s+" + re.escape(X) + r"\b"`
3. `r"\bif\s+" + re.escape(X) + r"\s+is\s+not\s+None\b"`
4. `r"\bassert\s+" + re.escape(X) + r"\s+is\s+not\s+None\b"`
5. `re.escape(X) + r"\s+or\s+\w+"` (default-value pattern
   `X or default`)

Also search the 10 lines BEFORE the fenced block opening for a
prose escape hatch:

6. `r"non-null invariant enforced by\b"` (PLAN line 103-104
   canonical phrasing).
7. `r"<!--\s*plan-forge:\s*p2-ok"` (inline marker).

If ANY of patterns 1-7 found: NO finding.  Otherwise: emit
`Finding(check_id="P2.orphan_optional", severity=HIGH, location=
f"line:{N}", message=f"nullable {X!r} declared but no null-check or
non-null invariant comment found", fix_hint="add 'if X is None'
branch, 'assert X is not None' guard, default-value pattern
('X or default'), prose 'non-null invariant enforced by ...'
within 10 lines before the block, or inline
<!-- plan-forge: p2-ok (reason) --> marker")`.

### P5 Interface symmetry

- check_id: `P5.module_design_orphan` (Module Designs has API not in
  T-row) and `P5.t_row_orphan` (T-row claims output not in Module
  Designs)
- severity: HIGH
- Inputs from ParsedPlan: `sections`, `raw_text`

#### Module Designs API extraction

For each section whose heading (case-insensitive) contains
`"module designs"` OR starts with `"###"` and is inside a `"##
Module Designs"` parent: scan the section body's fenced code blocks
for `def <name>(` definitions.

Capture the identifier preceded by `def `:
- Regex: `r"^def\s+(\w+)\s*\(" `(multiline mode).

Also capture top-level class method declarations:
- Regex: `r"^\s{4}def\s+(\w+)\s*\("` (4-space indent assumed for
  method indent inside a class).

Exclude dunder methods (`__init__`, `__repr__`, etc.) and methods
whose name starts with underscore (private).

Resulting set: `module_designs_apis: set[str]`.

#### T-row output extraction

Find the section whose heading is `"## Implementation Tasks"` (or
contains `"implementation tasks"` case-insensitive).  Within its
body, parse the markdown table.  The table has columns including an
"Output" or similar column.

For each row, extract identifiers from the output cell using:
- Backtick-quoted identifiers: `r"\`(\w+)\`"`
- Standalone `def name(` mentions: `r"def\s+(\w+)\s*\("`
- File path + function references: `r"(\w+)\.py:(\w+)"` -- capture
  the function name (group 2).

Resulting set: `t_row_outputs: set[str]`.

#### Symmetric matching

1. `module_designs_apis - t_row_outputs` (in Module Designs, not in
   T-row): for each `X`: emit `Finding(check_id=
   "P5.module_design_orphan", severity=HIGH, location=
   f"section:Module Designs:line:0", message=f"API {X!r} appears in
   Module Designs but is not listed as a T-row output",
   fix_hint=f"add {X!r} to the Output column of the relevant T-row,
   or add inline <!-- plan-forge: p5-ok (reason) --> if intentionally
   internal-only")`.
2. `t_row_outputs - module_designs_apis`: for each `X`: emit
   `Finding(check_id="P5.t_row_orphan", severity=HIGH, location=
   f"section:Implementation Tasks:line:0", message=f"T-row claims
   output {X!r} but no matching Module Designs entry",
   fix_hint=f"add {X!r} to ## Module Designs as a documented public
   API, or remove from T-row Output column")`.

#### Built-in exemptions

- Identifiers starting with underscore (private).
- Names matching `r"^(test_|_test)"` (test-only helpers).
- The literal strings `"check"` and `"run"` -- these are the PBR /
  mechanical check entry points, named by convention and not
  expected to be enumerated per-module in T-rows.

## 5. Test plan

3 unit test files in `tests/unit/`:

- `test_p1_symbol_closure.py`
- `test_p2_null_propagation.py`
- `test_p5_interface_symmetry.py`

Per P (mandatory test cases):

1. `test_p<N>_pass_fixture`: load `tests/fixtures/p<N>_pass.md`,
   call parser + check, assert findings == [].
2. `test_p<N>_fail_fixture`: load `tests/fixtures/p<N>_fail.md`,
   call parser + check, assert at least one finding with expected
   check_id.
3. `test_p<N>_severity`: assert all emitted findings have
   `Severity.HIGH`.
4. P-specific edge cases (extra tests per P):
   - P1: `test_p1_marker_exemption` -- fixture with orphan
     identifier AND `<!-- plan-forge: p1-ok -->` marker on same
     line -> NO finding.
   - P1: `test_p1_cross_reference_section_exemption` -- fixture
     with identifier appearing ONCE inside `## References` section
     -> NO finding.
   - P1: `test_p1_python_keyword_skip` -- fixture mentioning `int`
     / `str` / `None` once each -> NO finding (built-in exemption).
   - P2: `test_p2_non_null_invariant_comment` -- fixture with
     nullable declaration AND `non-null invariant enforced by ...`
     prose 5 lines before the block -> NO finding.
   - P2: `test_p2_default_value_pattern` -- fixture with `X or
     default` pattern in same block -> NO finding.
   - P2: `test_p2_optional_type` -- fixture with `name:
     Optional[int]` and `if name is None: ...` -> NO finding.
   - P5: `test_p5_bidirectional` -- fixture missing both directions
     (Module Designs has X not in T-row, AND T-row has Y not in
     Module Designs) -> exactly 2 findings, one of each check_id.
   - P5: `test_p5_underscore_method_exemption` -- fixture with
     `def _internal_helper(` in Module Designs -> NO finding for
     that method.

Plus one integration test:

- `tests/integration/test_pbr_run_end_to_end.py`: call `pbr.run`
  directly on each P fixture; assert returned list is `list[Finding]`
  and check_id values present match expectation.
- Also smoke-test `mechanical.run` (T07 entry point) returns
  combined F + PBR findings after T08 integration; verify ordering
  F1..F7, P1, P2, P5.

## 6. Fixtures

6 fixtures total in `tests/fixtures/`, one PASS + one FAIL per P:

- `p1_pass.md` / `p1_fail.md`
- `p2_pass.md` / `p2_fail.md`
- `p5_pass.md` / `p5_fail.md`

Each fixture: 30-80 lines, ASCII-only, valid markdown.

- P1 PASS: every backtick identifier mentioned >= 2 times OR appears
  once in `## References` / `## Audit Notes` / `## Glossary` / with
  inline marker.
- P1 FAIL: at least one backtick identifier appearing exactly once
  in main body, no cross-ref section entry, no marker.
- P2 PASS: every nullable declaration has matching null-check or
  invariant comment.
- P2 FAIL: at least one nullable with no null-handling anywhere.
- P5 PASS: Module Designs APIs match T-row Output column exactly.
- P5 FAIL: Module Designs has one API not in T-row AND T-row has
  one entry not in Module Designs (covers both check_id values).

## 7. Non-goals (do NOT do in T08)

- Do not implement P6 (split to T17 per PLAN R4 T4 fix).
- Do not modify F1-F7 modules, parser.py, verdict.py, or any T06 /
  T07 test files.  ONLY edit `mechanical/__init__.py` to add the
  one-line `findings.extend(pbr.run(parsed))` integration.
- Do not introduce new dataclass types beyond reusing
  `Finding` / `Severity` from verdict.py.
- Do not add LLM imports, network access, or subprocess calls.
- Do not implement `api.check_mechanical()` (T09).
- Do not invoke other Claude Code skills as subprocesses.

## 8. Verification gates (must pass before report-back)

```
cd /home/houminxi/code/plan-forge/.worktrees/feat-t08-pbr
.venv/bin/pytest -xvs tests/ 2>&1 | tail -20
.venv/bin/python -m py_compile \
    src/plan_forge/checks/pbr/__init__.py \
    src/plan_forge/checks/pbr/p1_symbol_closure.py \
    src/plan_forge/checks/pbr/p2_null_propagation.py \
    src/plan_forge/checks/pbr/p5_interface_symmetry.py \
    src/plan_forge/checks/mechanical/__init__.py
for f in src/plan_forge/checks/pbr/*.py tests/unit/test_p*.py \
         tests/integration/test_pbr_run_end_to_end.py \
         tests/fixtures/p*.md; do
    n=$(python3 -c "print(sum(1 for b in open('$f','rb').read() if b>127))")
    echo "$f: $n non-ASCII"
done
.venv/bin/pytest --cov=src/plan_forge/checks/pbr \
    tests/unit/test_p*.py \
    tests/integration/test_pbr_run_end_to_end.py \
    2>&1 | tail -15
```

All gates pass: pytest green (88 T07 baseline + new T08 tests);
py_compile clean; ASCII clean on all new files; coverage on
`checks/pbr/` reported >= 90%.

T07's 88 tests must still pass.

## 9. Hard constraints (subagent contract)

1. ASCII only: zero non-ASCII bytes in every new file and in the
   one-line edit to `mechanical/__init__.py`.  `--` not em-dash;
   `->` not arrow; straight quotes; ASCII only.
2. No AI markers: do NOT write "Generated by Claude" /
   "Co-Authored-By: Claude" / "Anthropic" / "GPT" / "Opus" /
   "Sonnet" / "DeepSeek" / "Kimi" / "Mimo" / "subagent" in any
   comment, docstring, fixture body, test name, or file.  Author
   is Minxi Hou.
3. No new dependencies: stdlib (re, pathlib, dataclasses, typing)
   only.
4. Do not modify T06 or T07 files except for the ONE integration
   line in `mechanical/__init__.py`.  Specifically:
   - DO NOT change `parser.py` or `verdict.py`.
   - DO NOT change any `f1_*` ... `f7_*.py` module.
   - DO NOT change any `test_f*.py` or `test_parser.py` /
     `test_verdict.py`.
   - DO NOT change any pre-existing fixture.
5. Stable ordering: `mechanical.run` returns findings in F1..F7
   then P1, P2, P5 order.
6. Pure mechanical: no LLM calls, no network, no filesystem writes
   outside test fixtures directory.
7. SUBSPEC wins: if SUBSPEC contradicts PLAN, follow SUBSPEC.  If
   ambiguous within SUBSPEC, document interpretation as
   `# SUBSPEC interpretation: ...` comment and proceed.
