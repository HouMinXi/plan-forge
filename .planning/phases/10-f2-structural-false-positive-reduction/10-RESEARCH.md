# Phase 10: F2 Structural False-Positive Reduction - Research

**Researched:** 2026-05-29
**Domain:** Python source edit -- single-file mechanical lint check (f2_duplicate_fact.py)
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** Single union filter: `exclusion = _STRUCTURAL_WORDS | signoff_words | heading_words`, then skip any n-gram where `set(ng.split()) <= exclusion`. (Note: CONTEXT.md abbreviates as `_STRUCTURAL_WORDS | signoff_words` but heading_words MUST also be included to preserve Phase 8 heading suppression -- see Critical Finding section.)
- **D-02:** Module-level `frozenset` constant `_STRUCTURAL_WORDS` in `f2_duplicate_fact.py`, alongside the existing `_FINDING_CAP`. No new file, no new import beyond what already exists.
- **D-03:** 13-token set: `step, run, expected, pass, files, create, modify, append, commit, test, write, add, signed-off-by`
- **D-04:** Signed-off-by extraction via raw text scan (`parsed.raw_text.splitlines()`), not `section.body`. Regex: `r'^\s*signed-off-by\s*:\s*(.*)'` on each line. Strip `<email@...>` with `re.sub(r'<[^>]+>', '', ...)`. Split and lowercase remaining name tokens into `signoff_words`.
- **D-05:** 3 plans, same wave pattern as Phase 8: Plan 10-01 (Wave 1: worktree + fixtures + RED stubs), Plan 10-02 (Wave 2: impl + bug-inject), Plan 10-03 (Wave 3: forge review + merge + cleanup)
- **D-06:** `tests/fixtures/f2_fail.md` TP fixture must continue to fire. Plan 10-02 must include bug-inject cycle (GATE-04T pattern from Phase 8).

### Claude's Discretion

None specified.

### Deferred Ideas (OUT OF SCOPE)

- Configurable stopwords via user config file (1 consumer today)
- Frequency-based suppression (plan-size-dependent threshold)
- Sub-heading extension of heading_words (ineffective for body-text phrases)
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| F2-01 | check_mechanical on a plan with structural template phrases produces zero F2 LOW findings | Verified: union filter with 13-token frozenset suppresses all 20 FP phrases from real-world smoke test |
| F2-02 | check_mechanical on a plan with repeated Signed-off-by lines produces zero F2 LOW findings for author-name phrases | Verified: `parsed.raw_text` scan extracts signoff_words; union filter suppresses 'minxi hou', 'signed-off-by minxi', etc. |
</phase_requirements>

---

## Summary

Phase 10 adds two new suppression mechanisms to `f2_duplicate_fact.check()` to eliminate false positives caused by structural template phrases (step/run/expected/pass) and commit-signature tokens (Signed-off-by author names) that repeat across sections by design in implementation plans.

The change is a surgical extension of Phase 8's heading-words guard. Phase 8 introduced `heading_words` and the `set(ng.split()) <= heading_words` subset test. Phase 10 extends the exclusion set to include a module-level `_STRUCTURAL_WORDS` frozenset and a dynamically extracted `signoff_words` set, then replaces the heading-words guard with a unified `set(ng.split()) <= exclusion` test where `exclusion = _STRUCTURAL_WORDS | signoff_words | heading_words`.

Empirically verified on the real-world antishirk-m1-plan.md: baseline 20 F2 LOW, post-fix 0 F2 LOW. Genuine TP fixture (f2_fail.md) continues to fire 4 findings. Total code change: 2 module-level constants + ~7 lines inside `check()` + 1 changed line.

**Primary recommendation:** Implement as a three-plan operation following Phase 8 wave pattern. The fix itself is small; the review pipeline is the dominant effort.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Structural-word suppression | Mechanical lint check layer (f2_duplicate_fact.py) | -- | Single file, no cross-layer dependency; purely deterministic filter |
| Signed-off-by extraction | Mechanical lint check layer (f2_duplicate_fact.py) | -- | Reads ParsedPlan.raw_text; no parser change needed |
| Test coverage | pytest fixtures + unit tests | -- | Standard project test pattern |

---

## Standard Stack

No new packages are installed. All implementation uses the existing project toolchain.

| Tool | Purpose | Verified |
|------|---------|---------|
| `uv run pytest` | Test runner | Yes -- only valid runner (system python lacks sqlalchemy) |
| `ruff check` | Step 0b lint | Yes |
| `python3 -m py_compile` | Step 0a syntax check | Yes |

---

## Package Legitimacy Audit

No packages installed in this phase. Legitimacy gate: not applicable.

---

## Architecture Patterns

### System Architecture Diagram

```
antishirk-m1-plan.md (raw text)
         |
         v
    parse() -> ParsedPlan
         |         |
         |         +-- .sections: dict[heading, ParsedSection]
         |         +-- .raw_text: full plan text
         |
         v
    f2_duplicate_fact.check(parsed)
         |
         +-- _extract_ngrams(section.body) for each section
         |       -> occurrences: {ngram: {set of headings}}
         |
         +-- flagged: ngrams in >= 3 sections
         |
         +-- Build exclusion set:
         |       heading_words  <- parsed.sections keys (existing Phase 8)
         |       signoff_words  <- parsed.raw_text signed-off-by scan (NEW)
         |       exclusion = _STRUCTURAL_WORDS | signoff_words | heading_words
         |
         +-- For each flagged ngram:
                 if set(ng.split()) <= exclusion: SKIP (FP suppressed)
                 else: emit Finding(F2.duplicate_fact, LOW)
```

### Recommended Project Structure

No new directories. All changes are in existing files:

```
src/plan_forge/checks/mechanical/
    f2_duplicate_fact.py         # EDIT TARGET: 2 constants + 7 lines + 1 line change
tests/fixtures/
    f2_structural_fp.md          # NEW (Wave 1)
    f2_signoff_fp.md             # NEW (Wave 1)
    f2_fail.md                   # UNCHANGED: existing TP fixture
    f2_heading_fp.md             # UNCHANGED: Phase 8 heading FP fixture
tests/unit/
    test_f2_duplicate_fact.py    # EXTEND: 4 new test functions
```

### Pattern 1: Module-Level Constants

[VERIFIED: codebase 2026-05-29] The project uses module-level constants `_FINDING_CAP = 20` and `_CAP_TOKEN_RE = re.compile(...)` for values used inside `check()`. `_STRUCTURAL_WORDS` and `_SIGNOFF_RE` follow the same pattern, inserted after `_FINDING_CAP = 20`.

```python
# After _FINDING_CAP = 20, before def _extract_ngrams():
_STRUCTURAL_WORDS: frozenset[str] = frozenset({
    "step", "run", "expected", "pass", "files",
    "create", "modify", "append", "commit", "test",
    "write", "add", "signed-off-by",
})

_SIGNOFF_RE = re.compile(r"^\s*signed-off-by\s*:\s*(.*)", re.IGNORECASE)
```

### Pattern 2: Union Filter (replaces the Phase 8 heading-words guard)

[VERIFIED: codebase analysis + live execution 2026-05-29]

```python
# Current code (lines 61-68, post Phase 8):
heading_words: set[str] = set()
for heading in parsed.sections:
    heading_words.update(heading.lower().split())

findings: list[Finding] = []
for ng, headings in flagged[:_FINDING_CAP]:
    if set(ng.split()) <= heading_words:        # REPLACED
        continue

# After Phase 10 (insert between line 63 and line 65):
heading_words: set[str] = set()
for heading in parsed.sections:
    heading_words.update(heading.lower().split())

signoff_words: set[str] = set()
for line in parsed.raw_text.splitlines():
    m = _SIGNOFF_RE.match(line)
    if m:
        name = re.sub(r"<[^>]+>", "", m.group(1)).strip()
        signoff_words.update(t.lower() for t in name.split())
exclusion = _STRUCTURAL_WORDS | signoff_words | heading_words

findings: list[Finding] = []
for ng, headings in flagged[:_FINDING_CAP]:
    if set(ng.split()) <= exclusion:            # NEW
        continue
```

### Pattern 3: Fixture Design Rules

[VERIFIED: tested against `_CAP_TOKEN_RE` and `_extract_ngrams` 2026-05-29]

`_CAP_TOKEN_RE = re.compile(r'\b[A-Z][A-Za-z0-9_-]{2,}\b')` captures capitalized tokens of length >= 3. A valid FP fixture needs at least one ngram appearing in >= 3 distinct section bodies.

**f2_structural_fp.md** generates `'run expected'`, `'expected pass'`, `'run expected pass'` each in 4 sections:

```markdown
## Task A

Step 1: Write the module.
Run tests.
Expected: Pass.

## Task B

Step 2: Create the config.
Run linter.
Expected: Pass.

## Task C

Step 3: Modify the schema.
Run migration.
Expected: Pass.

## Task D

Step 4: Add tests.
Run coverage.
Expected: Pass.
```

**f2_signoff_fp.md** generates `'minxi hou'`, `'signed-off-by minxi'`, `'signed-off-by minxi hou'` each in 3 sections:

```markdown
## Task A

Do this task.

Signed-off-by: Minxi Hou <houminxi@gmail.com>

## Task B

Do that task.

Signed-off-by: Minxi Hou <houminxi@gmail.com>

## Task C

Do another task.

Signed-off-by: Minxi Hou <houminxi@gmail.com>
```

### Anti-Patterns to Avoid

- **Omitting heading_words from exclusion:** Causes `test_f2_heading_fp_suppressed` to regress (Phase 8 fix silently breaks). [VERIFIED: tested 2026-05-29]
- **Two separate guards:** Cross-category n-grams like `'signed-off-by minxi'` need one word from `_STRUCTURAL_WORDS` and one from `signoff_words`. Two `if ... continue` blocks each require ALL words in their own set, so the cross-category phrase slips through both. [VERIFIED: CONTEXT.md D-01]
- **Scanning `section.body` for Signed-off-by:** May miss lines in XML/code blocks the parser excludes. Use `parsed.raw_text` instead. [VERIFIED: CONTEXT.md D-04]
- **`python -m pytest` instead of `uv run pytest`:** System python lacks sqlalchemy; produces misleading output. [VERIFIED: CLAUDE.md]

---

## Critical Finding: D-01 Union Must Include heading_words

[VERIFIED: live execution 2026-05-29]

CONTEXT.md D-01 states `exclusion = _STRUCTURAL_WORDS | signoff_words` but this abbreviation omits a required third term. Without `heading_words`, the Phase 8 suppression of heading-derived phrases silently regresses:

```
heading_words = {'implementation', 'tasks', ...}
_STRUCTURAL_WORDS = {'step', 'run', ..., 'signed-off-by'}

exclusion = _STRUCTURAL_WORDS | signoff_words  (D-01 as written)
set(['implementation', 'tasks']) <= exclusion => FALSE  => FIRES (regression!)

exclusion = _STRUCTURAL_WORDS | signoff_words | heading_words  (correct)
set(['implementation', 'tasks']) <= exclusion => TRUE   => SUPPRESSED
```

The CONTEXT.md code_context note "New code inserts after line 63 (end of heading_words build)" confirms heading_words is still built and must participate. The `test_f2_heading_fp_suppressed` test catches this at the RED stage.

**Planner must spell out `_STRUCTURAL_WORDS | signoff_words | heading_words` in Plan 10-02.**

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Case-insensitive Signed-off-by scan | Custom parser | `re.compile(r"^\s*signed-off-by\s*:\s*(.*)", re.IGNORECASE)` | One line; handles leading whitespace |
| Email address stripping | Custom tokenizer | `re.sub(r"<[^>]+>", "", name_part)` | Standard stdlib |
| Subset membership test | Custom loop | `set(ng.split()) <= exclusion` | Idiomatic Python; same as Phase 8 pattern |

---

## Runtime State Inventory

Not applicable (greenfield addition to existing check, no rename/refactor).

---

## Common Pitfalls

### Pitfall 1: Forgetting heading_words in the union

**What goes wrong:** `test_f2_heading_fp_suppressed` fails (Phase 8 regression).
**Why it happens:** CONTEXT.md D-01 abbreviates the formula.
**How to avoid:** Always use `exclusion = _STRUCTURAL_WORDS | signoff_words | heading_words`.
**Warning signs:** `test_f2_heading_fp_suppressed` turns RED after implementing the new guard.

### Pitfall 2: Invalid RED state

**What goes wrong:** New test stubs pass before fix; RED gate is meaningless.
**Why it happens:** Section bodies do not repeat capitalized tokens in >= 3 sections, or tokens are too short.
**How to avoid:** Verify RED state before adding stubs: run fixture against unmodified source, confirm >= 1 flagged ngram.
**Warning signs:** Stub passes immediately against unmodified source.

### Pitfall 3: Wrong pytest invocation

**What goes wrong:** `ModuleNotFoundError` shown as "No tests collected" (rtk compresses output).
**How to avoid:** Always `uv run pytest` from inside the worktree.

### Pitfall 4: Non-ASCII characters in source edits

**What goes wrong:** CLAUDE.md Step 0c gate fails.
**How to avoid:** Step 0c: `git diff HEAD --diff-filter=AM -U0 | grep '^+' | grep -P '[^\x00-\x7F]'`

### Pitfall 5: Bug-inject verifies wrong fixture

**What goes wrong:** Bug-inject removes new guard but tests the old TP fixture.
**How to avoid:** Use `test_f2_structural_fp_suppressed` or `test_f2_signoff_fp_suppressed` in bug-inject.

---

## Code Examples

### Exact implementation diff

```python
# Source: based on verified f2_duplicate_fact.py analysis (2026-05-29)

# Module-level additions (after _FINDING_CAP = 20):

_STRUCTURAL_WORDS: frozenset[str] = frozenset({
    "step", "run", "expected", "pass", "files",
    "create", "modify", "append", "commit", "test",
    "write", "add", "signed-off-by",
})

_SIGNOFF_RE = re.compile(r"^\s*signed-off-by\s*:\s*(.*)", re.IGNORECASE)


# Inside check(), after heading_words build (line 63), before findings = [] (line 65):

    signoff_words: set[str] = set()
    for line in parsed.raw_text.splitlines():
        m = _SIGNOFF_RE.match(line)
        if m:
            name = re.sub(r"<[^>]+>", "", m.group(1)).strip()
            signoff_words.update(t.lower() for t in name.split())
    exclusion = _STRUCTURAL_WORDS | signoff_words | heading_words


# Change line 67 from:
    if set(ng.split()) <= heading_words:
# To:
    if set(ng.split()) <= exclusion:
```

### New test stubs

```python
# Source: pattern from existing test_f2_heading_fp_suppressed (verified 2026-05-29)

def test_f2_structural_fp_suppressed():
    """Structural template phrases must not trigger F2."""
    parsed = parse(_load("f2_structural_fp.md"))
    findings = f2_duplicate_fact.check(parsed)
    assert findings == [], (
        f"Expected structural phrases suppressed, got: {findings}"
    )


def test_f2_signoff_fp_suppressed():
    """Signed-off-by author names must not trigger F2."""
    parsed = parse(_load("f2_signoff_fp.md"))
    findings = f2_duplicate_fact.check(parsed)
    assert findings == [], (
        f"Expected signoff names suppressed, got: {findings}"
    )
```

### Bug-inject cycle

```bash
# From inside worktree, remove new guard (working-tree only):
# Comment out signoff_words build + exclusion = ... + revert guard to heading_words

uv run pytest tests/unit/test_f2_duplicate_fact.py::test_f2_structural_fp_suppressed -xvs
# Expected: FAILED (findings != [])

git checkout -- src/plan_forge/checks/mechanical/f2_duplicate_fact.py

uv run pytest tests/unit/test_f2_duplicate_fact.py::test_f2_structural_fp_suppressed -xvs
# Expected: PASSED

uv run pytest tests/unit/test_f2_duplicate_fact.py::test_f2_fail_fixture -xvs
# Expected: PASSED (TP still fires)
```

### Commit message pattern (Phase 8 human-voice format)

```
checks/f2: suppress structural template phrases and signoff tokens

Implementation plans repeat structural terms like "Step N: Run ...",
"Expected: Pass", and "Signed-off-by: Name" across every task section
by design. F2 treated these as duplicate-fact violations, producing up
to 20 LOW findings on a real-world 28-task plan.

Add a 13-token frozenset of structural vocabulary and a dynamic set of
Signed-off-by author tokens (extracted from raw plan text). Union both
with the existing heading_words set; skip any flagged n-gram whose words
are all in the combined exclusion set.

Bug-inject confirmed: removing the guard causes f2_structural_fp.md to
fire F2 findings. Restoring silences it. TP fixture f2_fail.md continues
to fire (genuine phrases unaffected). Real-world check: 0 F2 LOW after
fix on antishirk-m1-plan.md (was 20).

Signed-off-by: Minxi Hou <houminxi@gmail.com>
```

---

## Key Numbers (for planner must_haves)

| Item | Value | Source |
|------|-------|--------|
| Test baseline | 764 passed, 1 pre-existing failure, 5 skipped | `uv run pytest tests/ -q` (2026-05-29) |
| Pre-existing failure | `test_version_is_alpha2` (version mismatch, unrelated) | known baseline |
| Current F2 tests | 6 passing | `uv run pytest tests/unit/test_f2_duplicate_fact.py -q` |
| Expected after Phase 10 | 768+ passed | +4 new F2 tests |
| Real-world FP count | 20 before fix, 0 after | antishirk-m1-plan.md (verified 2026-05-29) |
| TP fixture count | 4 findings (unchanged) | f2_fail.md (verified 2026-05-29) |
| Source lines changed | ~8 added + 1 changed | f2_duplicate_fact.py |

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| No suppression | heading_words subset guard | Phase 8 (v0.1.1) | Suppresses heading-derived FPs |
| heading_words only | union: structural + signoff + heading_words | Phase 10 (v0.1.2) | Suppresses structural + signoff FPs |

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | CONTEXT.md D-01 formula must include heading_words (not just `_STRUCTURAL_WORDS | signoff_words`) | Critical Finding | Phase 8 regression: test_f2_heading_fp_suppressed fails |

A1 was verified via live execution. The planner must use the full three-way union formula.

---

## Open Questions (RESOLVED)

1. **Worktree name for Phase 10**
   - **RESOLVED:** `.worktrees/f2-structural-fp/` on branch `fix/f2-structural-fp-v012`
   - Phase 8 used `.worktrees/fix-precision/` on `fix/precision-v011`
   - Recommendation: `.worktrees/f2-structural-fp/` on `fix/f2-structural-fp-v012`

2. **Pre-existing test failure**
   - **RESOLVED:** `test_version_is_alpha2` (unrelated version string mismatch; plans note this as pre-existing)
   - `test_version_is_alpha2` fails on baseline (version mismatch, unrelated to Phase 10)
   - Plans must note "1 pre-existing failure expected" to prevent confusion

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| uv | Test runner | Yes | existing | None -- use uv run pytest only |
| ruff | Step 0b lint | Yes | existing | None |
| python3 | Step 0a syntax | Yes | 3.14 | None |
| antishirk-m1-plan.md | Real-world verification | Yes (path confirmed) | N/A | Fixture-only verification |

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest (via `uv run pytest`) |
| Config file | `pyproject.toml` |
| Quick run command | `uv run pytest tests/unit/test_f2_duplicate_fact.py -q` |
| Full suite command | `uv run pytest tests/ -q` |

### Phase Requirements to Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| F2-01 | Structural template phrases produce 0 F2 LOW | unit | `uv run pytest tests/unit/test_f2_duplicate_fact.py::test_f2_structural_fp_suppressed -xvs` | No -- Wave 1 |
| F2-02 | Signed-off-by names produce 0 F2 LOW | unit | `uv run pytest tests/unit/test_f2_duplicate_fact.py::test_f2_signoff_fp_suppressed -xvs` | No -- Wave 1 |
| D-06 anti-gutting | TP fixture still fires | unit | `uv run pytest tests/unit/test_f2_duplicate_fact.py::test_f2_fail_fixture -xvs` | Yes (existing) |
| D-06 bug-inject | Guard is load-bearing | manual | bug-inject cycle in Plan 10-02 | N/A |

### Sampling Rate

- **Per task commit:** `uv run pytest tests/unit/test_f2_duplicate_fact.py -q`
- **Per wave merge:** `uv run pytest tests/ -q`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps

- [ ] `tests/fixtures/f2_structural_fp.md` -- covers F2-01
- [ ] `tests/fixtures/f2_signoff_fp.md` -- covers F2-02
- [ ] `tests/unit/test_f2_duplicate_fact.py::test_f2_structural_fp_suppressed` -- Wave 1 RED stub
- [ ] `tests/unit/test_f2_duplicate_fact.py::test_f2_signoff_fp_suppressed` -- Wave 1 RED stub

---

## Security Domain

No new external inputs, network calls, file system operations, or user-facing surfaces. The phase adds a regex scan over `parsed.raw_text` (trusted internal data from the parser) and a module-level frozenset constant. No ASVS categories apply.

---

## Sources

### Primary (HIGH confidence)

- `src/plan_forge/checks/mechanical/f2_duplicate_fact.py` -- full file read, line-by-line analysis [VERIFIED: codebase 2026-05-29]
- `tests/fixtures/f2_fail.md`, `tests/fixtures/f2_heading_fp.md` -- fixture content verified [VERIFIED: codebase 2026-05-29]
- `tests/unit/test_f2_duplicate_fact.py` -- all 6 test functions read [VERIFIED: codebase 2026-05-29]
- `src/plan_forge/parser.py` line 70 -- ParsedPlan.raw_text confirmed [VERIFIED: codebase 2026-05-29]
- `10-CONTEXT.md` -- all decisions read and cross-referenced [VERIFIED: 2026-05-29]
- Live Python execution on antishirk-m1-plan.md -- 20 FP phrases all suppressed by union filter [VERIFIED: 2026-05-29]

### Secondary (MEDIUM confidence)

- `.planning/phases/08-source-code-precision-fixes/08-03-PLAN.md` -- task structure, bug-inject pattern [CITED: codebase]
- `.planning/phases/08-source-code-precision-fixes/08-01-PLAN.md` -- worktree setup, fixture design [CITED: codebase]

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- no new packages; existing toolchain verified in repo
- Architecture: HIGH -- complete code analysis with exact line numbers; all variants verified via live execution
- Pitfalls: HIGH -- each pitfall verified by deliberately testing the wrong approach
- Critical Finding (D-01): HIGH -- confirmed by running both union variants against fixtures

**Research date:** 2026-05-29
**Valid until:** 2026-06-29
