# T07 SUBSPEC: F1-F7 mechanical checks

Status: draft for subagent implementation.
Depends on: T05 skeleton, T06 parser.py + verdict.py.
Scope: F1-F7 only.  P1/P2/P5/P6 (PBR) is T08.  G1-G10 is T11/T12.

## 1. Architecture

```
src/plan_forge/checks/
    __init__.py
    mechanical/
        __init__.py              # exposes run(parsed, preamble=None) -> list[Finding]
        f1_sc_traceability.py
        f2_duplicate_fact.py
        f3_cross_plan_invariant.py
        f4_temporal_anchor.py
        f5_r_tag_pruner.py
        f6_preamble_body.py
        f7_ascii.py
```

Each `f<N>_*.py` module exports exactly one public function:

```python
def check(parsed: ParsedPlan, **kwargs) -> list[Finding]:
    ...
```

`checks.mechanical.run` aggregates by calling each `check` in order F1..F7
and concatenating `Finding` lists.  Order is stable so callers can rely on
deterministic ordering for snapshot tests.

`kwargs`:
- F6 accepts `preamble: str | None = None` (the orchestrator preamble
  text against which the plan body is diffed).  When `None`, F6 returns
  `[]`.
- All other F's ignore `**kwargs` (forward-compat slot only).

`run` signature:

```python
def run(parsed: ParsedPlan, preamble: str | None = None) -> list[Finding]:
    findings: list[Finding] = []
    findings.extend(f1_sc_traceability.check(parsed))
    findings.extend(f2_duplicate_fact.check(parsed))
    findings.extend(f3_cross_plan_invariant.check(parsed))
    findings.extend(f4_temporal_anchor.check(parsed))
    findings.extend(f5_r_tag_pruner.check(parsed))
    findings.extend(f6_preamble_body.check(parsed, preamble=preamble))
    findings.extend(f7_ascii.check(parsed))
    return findings
```

## 2. Finding contract (shared across F1-F7)

```
Finding(
    check_id=<see per-F table>,
    severity=<see per-F table>,
    location=<"line:<N>" OR "SC-<id>:line:<N>" OR "section:<heading>:line:<N>">,
    message=<see per-F format>,
    fix_hint=<see per-F format>,
)
```

`llm_evidence` and `evidence_tier_summary` are left at default (empty)
because F1-F7 are pure mechanical.

## 3. Per-F specs

### F1 SC-test traceability

- check_id values: `F1.orphan_sc`, `F1.orphan_test`
- severity: HIGH (missing test coverage breaks SC-4)
- Inputs from ParsedPlan: `sc_table`, `sections`, `raw_text`

Algorithm:

1. Build `claimed_tests` = set of test references found by scanning each
   `ParsedSC.body` with regex `r"\btest_[A-Za-z0-9_]+\b"`.  Index claims
   per SC: `{sc_id: set[test_name]}`.
2. Build `defined_tests` = union of:
   - Every match of `r"\btest_[A-Za-z0-9_]+\b"` inside any section whose
     heading (case-insensitive) contains `"test plan"`, `"test list"`,
     `"tests"` (as a standalone word), or `"verification"`.
   - Every match of the same regex inside any markdown list item
     (`^\s*[-*]\s+`) anywhere in the plan body.
3. For each SC, for each `t` in `claimed_tests[sc_id]`, if `t not in
   defined_tests`: emit `Finding(check_id="F1.orphan_sc", severity=HIGH,
   location=f"SC-{sc_id}:line:{sc.line}", message=f"SC-{sc_id} references
   test {t!r} but no such test is listed in the plan",
   fix_hint=f"add {t} to ## Test Plan section, or fix the reference in
   SC-{sc_id}")`.
4. For each `t` in `defined_tests`, if not referenced by any SC: emit
   `Finding(check_id="F1.orphan_test", severity=HIGH, location=f"line:0",
   message=f"test {t!r} is defined in the plan but no SC references it",
   fix_hint=f"add an SC entry that covers {t}, or remove {t} from the test
   list if it is obsolete")`.

Empty-SC-table OR empty-defined-tests case: emit no findings (the check
relies on both sides existing; absence-of-test-section is G3/G7 territory,
not F1).

### F2 Duplicate-fact lint

- check_id: `F2.duplicate_fact`
- severity: LOW (single-source-of-truth hygiene)
- Inputs from ParsedPlan: `sections`

Algorithm (simplified noun-phrase proxy):

1. For each ParsedSection, extract candidate "facts" as the set of all
   bigrams and trigrams of tokens matching `r"[A-Z][A-Za-z0-9_-]{2,}"`
   (capitalized words / identifiers of length >= 3).  N-gram = 2 or 3
   consecutive tokens joined by single space.  Lowercase for comparison.
2. Build `occurrences: dict[str, set[str]]` mapping ngram -> set of section
   headings.  An ngram counts once per section regardless of repeat count
   inside the section.
3. For each ngram with `len(occurrences[ngram]) >= 3`: emit `Finding(
   check_id="F2.duplicate_fact", severity=LOW, location=f"line:0",
   message=f"phrase {ngram!r} appears in {len(occurrences[ngram])}
   sections: {sorted(occurrences[ngram])!r}", fix_hint=f"declare {ngram!r}
   canonically in one section and reference it elsewhere")`.

Skip ngrams that appear within fenced code blocks (already excluded since
ParsedSection.body should include code blocks but tokens like
`from dataclasses import` are filtered out naturally by the capital-letter
requirement; do not add separate fence handling here -- this is by-design
simple).

Per-finding cap: emit at most 20 F2 findings per plan (sort by occurrence
count descending, then alphabetically, take top 20).  Excess ngrams are
silently dropped.  This avoids spam on plans with many genuine technical
identifiers.

### F3 Cross-plan invariant verification

- check_id: `F3.unverified_cross_plan_ref`
- severity: HIGH (cross-module integration risk)
- Inputs from ParsedPlan: `raw_text`, `sections`

Algorithm:

1. Build `claims` = all matches in `raw_text` of these regexes:
   - `r"\bphase[-\s]\d+\b"` (case-insensitive)
   - `r"\b0[1-9]-\d{2}\b"` (e.g., `02-03`, `01-05` -- subplan IDs)
   - `r"\bT\d{2,3}\b"` (e.g., `T05`, `T100` -- task IDs; but only outside
     this plan's own Implementation Tasks table -- see exemption below)
2. Build `verified` = set of identical regex matches found inside any
   section whose heading (case-insensitive) contains `"audit notes"`,
   `"cross-plan references"`, `"references"`, `"appendix"`, or
   `"implementation tasks"`.  Section-heading inclusion = exemption: the
   match in that section is its own evidence, but a match elsewhere is
   "verified" if the exact same token also appears in an exempted section.
3. For each claim not in verified: emit `Finding(check_id=
   "F3.unverified_cross_plan_ref", severity=HIGH, location=f"line:{N}",
   message=f"reference {claim!r} is used but has no audit-notes / appendix
   / cross-plan-references entry", fix_hint=f"add an entry under ##
   References or ## Audit Notes documenting what {claim!r} refers to")`.

De-duplicate findings per `(claim, line)`.  If the same claim appears on
multiple lines unverified, emit one finding per line.

### F4 Temporal anchor lint

- check_id: `F4.imprecise_temporal_anchor`
- severity: LOW
- Inputs from ParsedPlan: `raw_text`

Algorithm:

1. For each line in `raw_text.splitlines()` (1-indexed line number), find
   all matches of regex
   `r"\b(before|after)\s+(\w+(?:\s+\w+){0,3})"`
   (case-insensitive).  Captures the verb (`before`/`after`) and the
   following 1-4 word phrase.
2. For each match where the captured phrase contains any of `return`,
   `exit`, `complete`, `finish`, `done` (lowercased word match):
   - Acceptable anchor phrases (no finding):
     - `return statement` followed by `executed` / `evaluated` /
       `processed`
     - `__exit__` / `__enter__` / `__init__` (any dunder)
     - `caller assignment` / `caller returns` / `caller assigns`
     - The token immediately after `return`/`exit` is a specific symbol
       starting with `_` or matching `r"\b[A-Z][A-Za-z0-9_]*\b"`
       (capitalized identifier; presumed precise)
   - Otherwise: emit `Finding(check_id="F4.imprecise_temporal_anchor",
     severity=LOW, location=f"line:{N}", message=f"temporal phrase
     'before/after X' lacks precise anchor: {match!r}",
     fix_hint="specify which exact point: __exit__, return statement
     executed, caller assignment, etc.")`.
3. Skip lines inside fenced code blocks (use the same fence-width state
   machine as parser.py G4; do NOT regress to per-line fence-only).
4. Skip lines containing `"F4 Temporal Anchor"` (self-reference exemption).

### F5 R-tag pruner

- check_id: `F5.r_tag_overflow`
- severity: LOW
- Inputs from ParsedPlan: `sc_table`

Algorithm:

1. For each ParsedSC, count matches of `r"R\d+\s+[BHML]\d+"` in
   `sc.body` (BHML = Blocker/High/Medium/Low).
2. If count > 2: emit `Finding(check_id="F5.r_tag_overflow", severity=LOW,
   location=f"SC-{sc.number}{sc.suffix or ''}:line:{sc.line}",
   message=f"SC-{sc.number} has {count} inline R-tags (cap is 2)",
   fix_hint=f"move {count - 2} tag(s) to ## CHANGELOG section with full
   review context")`.

If `ParsedSC` does not currently expose `suffix` separately and only has a
combined `name`/string, use whatever the parser exposes verbatim.  Do NOT
modify parser.py to add fields.

Severity rationale: LOW because R-tag overflow does not break plan
correctness -- parser does not consume R-tags, verdict computation does
not parse R-tags, and executor cannot mis-execute on R-tag presence.  It
is a readability / writing-discipline problem: SC body should read like
spec, not like a review log.  Same severity tier as F2 and F4 (heuristic
reminders about plan quality, not correctness violations).  Detecting
the broader "plan is degenerating into a review log" anti-pattern is
NOT a responsibility of F5; that is a known gap (see .planning/GAPS.md
Gap 1).

### F6 Preamble-vs-body diff

- check_id: `F6.preamble_only_fact`
- severity: LOW
- Inputs from ParsedPlan: `raw_text`; plus `preamble: str | None` kwarg.

Algorithm:

1. If `preamble is None` or `preamble.strip() == ""`: return `[]`.
2. Extract "facts" from preamble = set of sentences after splitting on
   `r"(?<=[.!?])\s+"` and stripping; filter to sentences of >= 20 chars.
3. For each preamble sentence `s`: compute normalized form (lowercase,
   collapse whitespace).  If normalized form is not a substring of
   normalized plan body, AND no token sequence of length >= 5 from `s`
   appears in body: emit `Finding(check_id="F6.preamble_only_fact",
   severity=LOW, location=f"preamble:sentence:{idx}", message=f"fact
   from preamble not present in plan body: {s[:80]!r}",
   fix_hint="incorporate this fact into the relevant section of the
   plan, or document why it is intentionally omitted")`.

Token-sequence test: split `s` and body into whitespace-separated tokens
(lowercased); look for any contiguous 5-token subsequence of `s` that
appears in body.

Cap: emit at most 10 F6 findings per plan (top 10 by sentence length).

Severity rationale: LOW because F6 is a substring + token-sequence
heuristic; the mechanical layer cannot reliably distinguish "author
intentionally omitted a binding constraint" from "author paraphrased and
the substring check missed".  False-positive rate is high; the high-risk
"missing critical constraint" cases are surfaced by G3 pre-mortem + G6
SC falsifiability (LLM layer) and L4 human arbitration, not by F6.
Same severity tier as F2 / F4 / F5 (heuristic reminders).

### F7 ASCII / non-ASCII grep

- check_id: `F7.non_ascii_char`
- severity: HIGH (per CLAUDE.md Step 0c rule -- LLMs silently emit
  non-ASCII lookalikes)
- Inputs from ParsedPlan: `raw_text`

Algorithm:

1. For each (1-indexed line_num, line) in `raw_text.splitlines()`:
   - For each character `c` in line: if `ord(c) > 127`: emit `Finding(
     check_id="F7.non_ascii_char", severity=HIGH, location=f"line:
     {line_num}:col:{col}", message=f"non-ASCII U+{ord(c):04X} ({c!r})
     found", fix_hint=<see table below>)`.
2. Fix-hint table (the canonical lookalike substitutions):
   - `U+2014` (em dash) -> "use ASCII `--`"
   - `U+2013` (en dash) -> "use ASCII `-`"
   - `U+2018` / `U+2019` (smart single quotes) -> "use ASCII `'`"
   - `U+201C` / `U+201D` (smart double quotes) -> "use ASCII `\"`"
   - `U+2026` (ellipsis) -> "use ASCII `...`"
   - `U+2192` (right arrow) -> "use ASCII `->`"
   - `U+2190` (left arrow) -> "use ASCII `<-`"
   - All other code points: "remove or transliterate to ASCII"
3. De-duplicate findings per `(line_num, col, ord(c))`.
4. Cap: emit at most 50 F7 findings per plan (sort by line/col, take
   first 50).  After cap, append a single summary finding `Finding(
   check_id="F7.non_ascii_char", severity=HIGH, location="line:0",
   message=f"... {total_count - 50} more non-ASCII characters
   suppressed", fix_hint="run `git diff | grep -P '[^\\x00-\\x7F]'` for
   full list")`.

## 4. Test plan

7 test files in `tests/unit/`:

- `test_f1_sc_traceability.py`
- `test_f2_duplicate_fact.py`
- `test_f3_cross_plan_invariant.py`
- `test_f4_temporal_anchor.py`
- `test_f5_r_tag_pruner.py`
- `test_f6_preamble_body.py`
- `test_f7_ascii.py`

Per F (mandatory test cases):

1. `test_<f>_pass_fixture`: load `tests/fixtures/f<N>_pass.md` (string),
   call parser, call F.check, assert findings == [].
2. `test_<f>_fail_fixture`: load `tests/fixtures/f<N>_fail.md`, call
   parser, call F.check, assert at least one finding with the expected
   `check_id` value.
3. `test_<f>_severity`: assert all emitted findings have the prescribed
   severity from section 3.
4. F-specific edge case (one extra test per F):
   - F1: orphan SC AND orphan test in same plan -> both finding types
     emitted in one call.
   - F2: ngram appearing in exactly 2 sections -> NO finding (boundary
     of >=3 rule).
   - F3: claim AND audit-notes mention -> NO finding (exemption works).
   - F4: `after __exit__` -> NO finding; `after the function` -> finding.
   - F5: SC with exactly 2 tags -> NO finding; SC with 3 tags -> finding.
   - F6: preamble is None -> NO findings.  Preamble == "" -> NO findings.
   - F7: empty plan -> NO findings.  Plan with em dash -> 1 finding with
     correct fix_hint mentioning `U+2014` and `--`.

Plus one integration test in `tests/integration/`:

- `test_mechanical_run_end_to_end.py`: load each of the existing 3
  fixtures from T06 (`pass_well_formed.md`, `fail_missing_premortem.md`,
  `fail_no_g9_anchor.md`); call `mechanical.run(parsed)`; assert run
  returns `list[Finding]` and does not raise for any fixture.  Do NOT
  assert specific findings -- these fixtures were designed for G1-G10 and
  may legitimately trip F's; just smoke-test the integration.

## 5. Fixtures

14 fixtures total in `tests/fixtures/`, one PASS + one FAIL per F:

- `f1_pass.md` / `f1_fail.md`
- `f2_pass.md` / `f2_fail.md`
- ...
- `f7_pass.md` / `f7_fail.md`

Each fixture: 30-80 lines, ASCII-only, valid markdown.  PASS fixture
must include the minimum structure needed for the F to evaluate
(e.g., F1 PASS needs both SC table and Test Plan section with matching
references).  FAIL fixture must trigger exactly the F under test (other
F's may also trip; tests assert only the F-under-test's check_id is
present).

For F6: `f6_pass.md` = normal plan (preamble param is `None`);
`f6_fail.md` = normal plan + a separate fixture string passed as
preamble parameter inside the test, where the preamble contains one
sentence that does not appear in the plan body.

For F7: `f7_pass.md` = pure ASCII content; `f7_fail.md` must contain at
least one em dash, one smart quote, and one arrow.  CRITICAL: the
fixture file itself contains non-ASCII -- this is intentional, but the
ASCII gate on `src/` and `tests/unit/*.py` MUST still pass.  Mark
`tests/fixtures/f7_fail.md` as exempt from the worktree-level ASCII
gate via a comment in the test:
`# F7 fail fixture is intentionally non-ASCII; do not include in ASCII
sweep`.

## 6. Non-goals (do NOT do in T07)

- Do not implement P1/P2/P5/P6.  Those are T08.
- Do not modify `parser.py`, `verdict.py`, or any T06 file.
- Do not introduce new dataclass types beyond `Finding`/`Severity` from
  verdict.py.
- Do not add LLM imports anywhere in `checks/mechanical/`.  Pure Python
  stdlib + re module only.
- Do not implement `api.check_mechanical()` (that is T09).
- Do not invoke `subprocess`, `os.system`, or call other Claude Code
  skills.

## 7. Verification gates (must pass before report-back)

```
cd /home/houminxi/code/plan-forge/.worktrees/feat-t07-mechanical
.venv/bin/pytest -xvs tests/ 2>&1 | tail -20
.venv/bin/python -m py_compile src/plan_forge/checks/mechanical/*.py
for f in src/plan_forge/checks/mechanical/*.py tests/unit/test_f*.py \
         tests/integration/test_mechanical_run_end_to_end.py; do
    n=$(python3 -c "print(sum(1 for b in open('$f','rb').read() if b>127))")
    echo "$f: $n non-ASCII"
done
.venv/bin/pytest --cov=src/plan_forge/checks/mechanical \
    tests/unit/test_f*.py tests/integration/test_mechanical_run_end_to_end.py \
    2>&1 | tail -15
```

All gates pass: pytest green; py_compile clean; ASCII clean on src + py
test files (f7_fail.md fixture is the only exception per section 5);
coverage on `checks/mechanical/` reported and >= 90%.

Existing 54 tests from T06 must still pass.

## 8. Hard constraints (subagent contract)

1. ASCII only in all `.py` files and `f1_pass.md` through `f7_pass.md`
   plus `f1_fail.md` through `f6_fail.md`.  `f7_fail.md` is the sole
   non-ASCII fixture.
2. No AI markers in any file: do not write "Generated by Claude" /
   "Co-Authored-By: Claude" / "Anthropic" / "GPT" / "Opus" / "Sonnet" /
   "DeepSeek" / "Kimi" / "Mimo" in any comment, docstring, fixture, or
   test name.  Author is Minxi Hou.
3. No new dependencies.  Only stdlib + already-installed deps.
4. Do not commit.  Leave changes in worktree; orchestrator commits.
5. Stable ordering: `mechanical.run` returns findings in F1..F7 order.
6. Pure mechanical: no LLM calls, no network, no filesystem writes
   outside of the test fixtures directory.
