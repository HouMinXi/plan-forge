# Phase 11: F3 Per-Mention Dedup and Own-ID Suppression - Research

**Researched:** 2026-05-30
**Domain:** Python / plan-forge mechanical gate (F3)
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** `seen` set key from `(claim, lineno)` to `claim.lower()`. First occurrence
  fires; subsequent occurrences of the same claim text are skipped.
- **D-02:** `location` for the deduplicated finding = `line:{first_lineno}`.
- **D-03:** Extend `_own_id_set()` to scan YAML frontmatter before heading scan.
  Strip U+FEFF BOM with `line.lstrip(chr(0xFEFF)).strip()` before `---` check.
  Opening `---` must be on line 1 (or line 2 if line 1 is empty after BOM strip).
  Closing `---` or first `#` heading ends frontmatter. Extract `phase:` and `plan:`
  fields; both must be zero-padded with `.zfill(2)`. If either field is absent,
  skip own-id construction (no partial IDs).
- **D-04:** Frontmatter scan and heading scan are ADDITIVE (union), not exclusive
  fallback. Both always run.
- **D-05:** `_own_id_set` returns `set[str]` of lowercase own-id strings -- no
  return type or downstream usage change.
- **D-06:** 3 plans, same wave pattern as Phase 10:
  - Plan 11-01 (Wave 1): worktree + fixtures + RED test stubs
  - Plan 11-02 (Wave 2): dedup fix + frontmatter own-ID extension + bite test
  - Plan 11-03 (Wave 3): forge review (separate sub-session) + merge + cleanup
- **D-07:** P1.orphan_identifier false positives are NOT in scope.
- **D-08 (known limitation):** `_SUBPLAN_RE` requires first digit to be `0`, so
  Phase 10+ IDs like "10-02" are never extracted as claims from body text.
  Frontmatter extraction correctly adds "10-02" to `verified`, but suppression
  has no practical effect for Phase >= 10. Record in code comment; extending
  `_SUBPLAN_RE` is out of scope.

### Claude's Discretion

None specified -- all implementation decisions are locked.

### Deferred Ideas (OUT OF SCOPE)

- P1.orphan_identifier false positives -- separate gate, separate phase.
- `_PHASE_RE` self-reference suppression (e.g., "Phase 8" in a Phase 8 plan).
- G2 heading-flex.
- Configurable own-ID extraction.
- Extending `_SUBPLAN_RE` to match two-digit phase numbers (Phase 10+).

</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| F3-01 | F3.unverified_cross_plan_ref fires at most once per unique cross-plan reference | D-01: change `seen` key from `(claim, lineno)` to `claim.lower()` eliminates per-line duplicates |
| F3-02 | F3 never fires on identifiers defined within the same plan | D-03/D-04: frontmatter scan extracts own IDs from GSD PLAN.md YAML block; union with heading scan covers all plan formats |

</phase_requirements>

---

## Summary

Phase 11 makes two targeted changes to `f3_cross_plan_invariant.py`. The file is
127 lines; both changes are self-contained within `_own_id_set()` (lines 46-65)
and `check()` (lines 78-127). No other files in `src/` are modified.

**Root cause of F3-01:** The `seen` set uses `(claim, lineno)` as the key. When a
plan references "Phase 8" on six different lines, six distinct keys are inserted
and six findings are emitted. Changing the key to `claim.lower()` deduplicates
across lines -- the first occurrence records the finding with `line:{first_lineno}`;
subsequent occurrences are skipped.

**Root cause of F3-02:** `_own_id_set()` scans only ATX headings (`#`). GSD
PLAN.md files (Phases 8-11) start with a YAML frontmatter block followed by an
`<objective>` XML element -- there is no `#` heading before body content, so
`_own_id_set()` returns an empty set and every subplan self-reference fires F3.
Adding a frontmatter parser that extracts `phase:` and `plan:` fields and
constructs the zero-padded ID before the heading scan closes this gap for
Phases 1-9 (Phase 10+ IDs are outside `_SUBPLAN_RE` scope per D-08).

**Primary recommendation:** Apply the verified reference implementation from
CONTEXT.md specifics section verbatim. Both changes are low-risk:
the `seen` key change is local to `check()`; the frontmatter extension only adds
code before the existing heading-scan loop.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Dedup F3 per unique claim | check() in f3_cross_plan_invariant.py | -- | `seen` set is local to check(); no cross-function impact |
| Extract own ID from frontmatter | _own_id_set() in f3_cross_plan_invariant.py | parser.py (provides raw_text) | raw_text already available; no parser change needed |
| Test scaffolding (RED stubs) | tests/unit/test_f3_cross_plan_invariant.py | tests/fixtures/ | unit test + fixtures follow Phase 10 pattern |
| Snapshot integrity | tests/integration/test_api_mechanical_e2e.py | -- | snapshot counts must stay stable; confirmed safe |

---

## Standard Stack

No new packages. This phase installs nothing. All dependencies are already
present in the project's pyproject.toml.

| Tool | Purpose | Already present |
|------|---------|----------------|
| re (stdlib) | Regex for frontmatter field extraction | Yes (imported at line 14 of f3 file) |
| uv run pytest | Test runner | Yes |
| python3 -m py_compile | Syntax check (Step 0) | Yes |
| ruff check | Linting (Step 0) | Yes |

## Package Legitimacy Audit

No packages installed in this phase. Legitimacy gate not applicable.

---

## Architecture Patterns

### Phase 10 Precedent (reuse exactly)

Phase 10 (F2 fix) used this pattern and is the direct model for Phase 11:

- Wave 1 plan: git worktree add .worktrees/<slug> -b fix/<slug> then RED
  failing tests + fixtures committed.
- Wave 2 plan: source edit inside worktree, GREEN, bug-inject cycle
  (checkpoint:human-verify gate), full suite, commit.
- Wave 3 plan: forge review sub-session (separate agent), merge, cleanup.
- Worktree slug for Phase 10: f2-structural-fp, branch fix/f2-structural-fp-v012.
- Suggested slug for Phase 11: f3-per-mention-dedup, branch fix/f3-dedup-v013.

### Recommended Project Structure (unchanged)

The only structural change is two new fixture files and new test functions in an
existing test file:

  src/plan_forge/checks/mechanical/
      f3_cross_plan_invariant.py   <- ONLY file modified in Wave 2

  tests/fixtures/
      f3_dedup_fp.md               <- NEW: "Phase 8" x6, expect 1 finding post-fix
      f3_own_id_fp.md              <- NEW: GSD frontmatter, "08-02" in body, expect 0

  tests/unit/
      test_f3_cross_plan_invariant.py  <- new test stubs added in Wave 1

### Pattern: Bug-Inject (Bite Test)

Identical to Phase 8 (GATE-04T) and Phase 10 (GATE-10T). After the source fix
is GREEN:

1. Comment out the dedup / frontmatter guard (working tree only, no commit).
2. Run the new FP fixture test -- expect FAIL.
3. Restore via git checkout -- <file>.
4. Run same test -- expect PASS.
5. Run TP fixture -- confirm it still fires.

The checkpoint:human-verify task in Wave 2 gates the commit on this outcome.

---

## Edit Targets: Exact Line Numbers (verified from codebase read)

f3_cross_plan_invariant.py (127 lines total)

Lines 46-65: _own_id_set()
  Line 56: own: set[str] = set()
  Line 57: for line in parsed.raw_text.splitlines():
  Line 58:     stripped = line.strip()
  Line 59:     if stripped.startswith('#'):
  ...
  INSERT frontmatter scan BEFORE line 57 (before the heading loop)

Lines 78-127: check()
  Line 104: seen: set[tuple[str, int]] = set()
  Line 109: key = (claim, lineno)
  Line 110: if key in seen:
  Line 111:     continue
  Line 112: seen.add(key)
  REPLACE lines 104, 109-112 with claim.lower() key pattern

D-01 change -- seen key (minimal diff):

  Before:
    seen: set[tuple[str, int]] = set()
    ...
    key = (claim, lineno)

  After:
    seen: set[str] = set()
    ...
    key = claim.lower()

location=f"line:{lineno}" is unchanged. Because dedup skips later occurrences,
lineno at the time of findings.append() is always the first occurrence.

D-03/D-04 -- new _own_id_set (complete replacement):

The _BOM module-level constant must be added near the other module-level
constants (after _EXEMPT_KEYWORDS, before _heading_is_exempt):

  _BOM = chr(0xFEFF)  # U+FEFF; not removed by str.strip()

Replace the body of _own_id_set with the reference implementation from
CONTEXT.md specifics section. The function signature and docstring are updated
to describe the new behavior (frontmatter + heading union). See CONTEXT.md for
the full verified implementation; copy it verbatim.

---

## Existing Test Structure (verified from codebase read)

Eight tests exist in test_f3_cross_plan_invariant.py. All assert
check_id in ids or findings == [] or absence of specific messages -- none
assert exact finding count. D-01 is safe for all existing tests.

| Test | Fixture | Assertion style |
|------|---------|-----------------|
| test_f3_pass_fixture | f3_pass.md | findings == [] |
| test_f3_fail_fixture | f3_fail.md | F3... in ids |
| test_f3_severity | f3_fail.md | all severity == HIGH |
| test_f3_edge_case_insensitive_exemption | inline md | findings == [] |
| test_f3_edge_audit_notes_exemption | inline md | findings == [] |
| test_f3_self_ref_silent | f3_self_ref.md | no finding with 02-01 |
| test_f3_date_fragment_silent | f3_date_nofire.md | findings == [] |
| test_f3_cross_ref_still_fires | f3_cross_ref_fires.md | 02-03 still fires |

---

## Existing Fixture Inventory (verified from codebase read)

| Fixture | Content summary | Role |
|---------|----------------|------|
| f3_pass.md | T05/T06 in References section | TP pass |
| f3_fail.md | T08 + phase 3, no audit section | TP fail |
| f3_self_ref.md | # 02-01 ... heading; body mentions 02-01 | heading-scan self-ref |
| f3_date_nofire.md | ISO dates embedding NN-NN fragments | date fragment guard |
| f3_cross_ref_fires.md | 02-01 plan referencing 02-03 (no audit entry) | anti-gutting |

New fixtures to create in Wave 1:

- f3_dedup_fp.md -- Phase 8 referenced six times; no References/Audit Notes
  section. Pre-fix: 6 findings. Post-fix: 1.
- f3_own_id_fp.md -- GSD PLAN.md with phase: 8 and plan: 2 in YAML
  frontmatter; body contains 08-02. Pre-fix: 1 finding. Post-fix: 0.

---

## Integration Test Snapshot Impact Analysis

Two integration fixtures (pass_well_formed.md, fail_missing_premortem.md)
each contain exactly 1 unique F3 claim (phase 2 from the Goal anchor line
[anchor: forge-code project, phase 2 took 6 weeks]).

Snapshot assertions for those tests:
- F3.unverified_cross_plan_ref: 1
- len(result.findings): 22 (F2 x20 + F3 x1 + P1 x1)

After D-01, dedup applies only when the same claim text appears on MULTIPLE lines.
Since these fixtures have exactly 1 unique phase 2 reference, the count stays 1
and the snapshots do not change.

The fail_no_g9_anchor.md fixture has zero F3 references; unaffected by either
change.

Conclusion: No integration snapshot updates needed. Executor must re-run
test_api_mechanical_e2e.py after implementation to confirm.

---

## Common Pitfalls

### Pitfall 1: BOM not stripped by str.strip()

What goes wrong: lines[0].strip() == --- returns False when the file has
a UTF-8 BOM (U+FEFF). str.strip() removes only ASCII whitespace codepoints;
U+FEFF is not in that set.

How to avoid: Use line.lstrip(chr(0xFEFF)).strip() as specified in D-03.
The _BOM = chr(0xFEFF) constant makes the intent explicit.

Warning signs: Frontmatter detection silently failing on BOM-prefixed files.

### Pitfall 2: Partial IDs when one field is absent

What goes wrong: f{phase_num}-{plan_num} when one is None produces
None-02 or 08-None -- invalid IDs that pollute the verified set.

How to avoid: Gate on if phase_num and plan_num: before own.add(...).

### Pitfall 3: Frontmatter loop reading body content after heading

What goes wrong: If the loop does not stop at the first heading, body
content after a horizontal rule --- may be parsed as frontmatter.

How to avoid: Break on stripped.startswith("#") or stripped == "---".

### Pitfall 4: Regression on test_f3_self_ref_silent

f3_self_ref.md starts with # 02-01 State Machine Rewrite (no frontmatter).
After the change, fm_start is None (first line starts with #, not ---).
The heading scan extracts 02-01 exactly as before. Test continues to pass.
No action required.

### Pitfall 5: AI smell in code comments

CLAUDE.md prohibits plan/task labels in committed code. The code comment for the
Phase 10+ limitation should read as a human engineering note, not a label
reference: "Phase 10+ IDs (two-digit phase numbers) are not matched by
_SUBPLAN_RE; extending the pattern is deferred."

### Pitfall 6: zfill(2) on multi-digit values

.zfill(2) on 8 -> 08, on 02 -> 02, on 10 -> 10.
Safe and idempotent for all valid inputs. No special handling needed.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| BOM detection | Manual byte scan | lstrip(chr(0xFEFF)) | stdlib str method, correct and idiomatic |
| YAML parse of frontmatter | PyYAML / ruamel | Regex on phase: / plan: lines | 2 fields only; a YAML dep is overkill |
| Subplan ID format validation | Custom validator | _SUBPLAN_RE.finditer() | Pattern already enforces the format |

---

## Runtime State Inventory

Not applicable. Greenfield addition to an existing module. No rename, refactor,
or migration. No runtime state.

---

## Environment Availability

| Dependency | Required By | Available | Fallback |
|------------|------------|-----------|----------|
| Python 3.14 | All tests | Yes | -- |
| uv | Test runner | Yes | -- |
| ruff | Step 0 lint | Yes | -- |
| git worktree | Wave 1 setup | Yes | -- |

All dependencies are present. No installation required.

---

## Validation Architecture

nyquist_validation: false is set in .planning/config.json. This section is
SKIPPED per configuration.

---

## Security Domain

No new packages. No user input handling changes. No network calls. No
authentication or authorization logic. The frontmatter parser accepts untrusted
plan text; a malformed frontmatter at worst suppresses a finding (false negative),
never crashes. No security concerns beyond those already present in the gate.

---

## New Test Stubs (Wave 1 additions to test_f3_cross_plan_invariant.py)

The following two tests must be added as RED stubs in Wave 1. They assert the
desired post-fix behavior; they will FAIL on unmodified code.

  def test_f3_dedup_fires_once():
      parsed = parse(_load("f3_dedup_fp.md"))
      findings = f3_cross_plan_invariant.check(parsed)
      f3_findings = [f for f in findings if f.check_id == "F3.unverified_cross_plan_ref"]
      phase8_findings = [f for f in f3_findings if "Phase 8" in f.message or "phase 8" in f.message]
      assert len(phase8_findings) == 1, (
          f"Expected exactly 1 F3 finding for Phase 8, got {len(phase8_findings)}: "
          f"{[f.message for f in phase8_findings]}"
      )

  def test_f3_own_id_suppressed_via_frontmatter():
      parsed = parse(_load("f3_own_id_fp.md"))
      findings = f3_cross_plan_invariant.check(parsed)
      own_id_findings = [
          f for f in findings
          if f.check_id == "F3.unverified_cross_plan_ref" and "08-02" in f.message
      ]
      assert own_id_findings == [], (
          f"Own id 08-02 from frontmatter should be exempt, got: {own_id_findings}"
      )

---

## Worktree and Branch Naming Convention

Based on Phase 10 pattern:

- Worktree: .worktrees/f3-per-mention-dedup/
- Branch: fix/f3-dedup-v013
- All code changes happen inside the worktree, never in main.
- .worktrees/ is already in .gitignore.

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| seen = set[tuple[str, int]] per line | seen = set[str] (claim.lower()) | Phase 11 | One finding per unique claim text, not per occurrence |
| Heading-only own-ID extraction | Frontmatter + heading (union) | Phase 11 | GSD PLAN.md own-IDs extracted from YAML block |

---

## Assumptions Log

No claims tagged [ASSUMED]. All claims verified by direct codebase read or
confirmed in CONTEXT.md.

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| (none) | | | |

All claims in this research were verified or cited -- no user confirmation needed.

---

## Open Questions (RESOLVED)

None. CONTEXT.md provides a complete verified reference implementation and locked
decisions for every design choice. The planner can proceed directly to plan creation.

---

## Sources

### Primary (HIGH confidence)

- Direct codebase read: src/plan_forge/checks/mechanical/f3_cross_plan_invariant.py
  (127 lines; line numbers for edit targets verified)
- Direct codebase read: tests/unit/test_f3_cross_plan_invariant.py
  (8 tests; assertion patterns verified)
- Direct codebase read: tests/fixtures/f3_*.md (5 files; content verified)
- Direct codebase read: tests/integration/test_api_mechanical_e2e.py
  (snapshot assertions verified; F3 count = 1 in both affected fixtures)
- Grep: tests/fixtures/pass_well_formed.md and fail_missing_premortem.md
  (confirmed single phase 2 reference each)
- uv run pytest tests/ -q: baseline = 766 passed, 1 pre-existing failure
  (test_version_is_alpha2), 5 skipped
- uv run pytest tests/unit/test_f3_cross_plan_invariant.py -q: 8 passed
- .planning/config.json: nyquist_validation: false confirmed
- .planning/phases/11-f3-per-mention-dedup-and-own-id-suppression/11-CONTEXT.md
- .planning/phases/10-f2-structural-false-positive-reduction/10-02-PLAN.md
- .planning/phases/08-source-code-precision-fixes/08-03-PLAN.md

---

## Metadata

**Confidence breakdown:**
- Edit targets (line numbers): HIGH -- verified by reading full file
- Test assertion patterns: HIGH -- verified by reading test file
- Snapshot impact: HIGH -- verified by grepping fixture content
- Worktree naming: HIGH -- verified from Phase 10 plan
- Reference implementation: HIGH -- sourced from CONTEXT.md (4 rounds cross-AI review)

**Research date:** 2026-05-30
**Valid until:** Until f3_cross_plan_invariant.py is next modified (stable)
