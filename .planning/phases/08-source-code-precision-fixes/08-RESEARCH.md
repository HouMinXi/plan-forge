# Phase 8: Source Code Precision Fixes - Research

**Researched:** 2026-05-27
**Domain:** Python source edits -- g8_source_diversity.py + f2_duplicate_fact.py
**Confidence:** HIGH

## Summary

Phase 8 is two surgical edits to eliminate confirmed false positives from the
v0.1.0 self-dogfood run. No new gates, no new architecture. Both fixes are
completely contained within a single file each. The parser data model is
stable and fully documented; no parser changes are needed. The existing test
suite (761 pass, 5 skip) is the pre-change baseline. Phase adds four new
fixtures and four new test functions -- one FP-suppressed and one TP-preserved
pair per fix.

**Primary recommendation:** Implement G8 first (simpler: one conditional
inserted before the existing emit), then F2 (slightly more: a set built from
`parsed.sections` keys fed into the flagging loop). Both changes are a single
worktree commit if the bug-inject cycles are recorded in the commit message.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**G8.A.no_citation Severity (GATE-01, GATE-02, GATE-03)**
- body is None (no section) -> existing G8.A.no_section BLOCKER unchanged
- body.strip() == "" (section exists but empty) -> G8.A.no_citation BLOCKER
- body.strip() != "" and len(parsed.citations) == 0 -> G8.A.no_citation HIGH
- File: src/plan_forge/checks/epistemic/g8_source_diversity.py, lines 98-107
- Change size: ~5 lines

**F2 Heading-Aware Suppression (GATE-04, GATE-05)**
- Word-subset match across ALL headings. A bigram/trigram is suppressed if
  EVERY word in the n-gram appears as a word in at least one section heading
  (case-insensitive, any heading -- not required to be the same heading).
- Build heading_words set from parsed.sections keys, tokenize to words,
  lowercase. For each flagged n-gram, check if all words appear in heading_words.
- File: src/plan_forge/checks/mechanical/f2_duplicate_fact.py
- Change size: ~8-12 lines

**Bug-Inject Form**
- Both GATE-01T and GATE-04T are manual steps documented in PLAN.md, not
  automated test cases.
- Implementer performs flip-confirm-restore cycle before committing and records
  result (fixture name, before/after finding count) in commit message.

### Claude's Discretion

None -- all implementation decisions are locked.

### Deferred Ideas (OUT OF SCOPE)

- Phase 10: skill runner + CLI detailed findings output (full per-finding
  detail with check_id, message, location, fix_hint)
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| GATE-01 | G8.A.no_citation severity changed from BLOCKER to HIGH so prose-cited plans are not blocked | Body strip check inserted before emit at g8_source_diversity.py:98-106; new HIGH fixture confirms |
| GATE-02 | Existing G8 TP fixture still fires (anti-gutting verified) | g8_biblio_citation_tp.md + existing tests -- no_citation must still fire for truly empty/no-list body |
| GATE-03 | Empty External Voices section distinction: truly empty -> BLOCKER; unparseable-but-present -> HIGH | Controlled by body.strip() branch; requires two distinct fixture cases |
| GATE-04 | F2 no longer fires on capitalized n-grams that are plan section headings | heading_words set built from parsed.sections.keys() in flagging loop; new FP fixture needed |
| GATE-05 | F2 TP fixture still fires on genuine repeated factual assertions | Existing f2_fail.md ("DatabaseConnection Pool") -- headings are "Background", "Design", "Implementation", "Testing", "Summary"; "databaseconnection pool" contains no word appearing in those headings, so exemption does not suppress it |
</phase_requirements>

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| G8 severity decision | Mechanical check (Part A) | -- | Part B (LLM) runs separately after Part A; severity of A-layer findings is pure Python logic |
| Citation presence detection | Parser (parser.py) | G8 Part A | Parser populates parsed.citations; G8 reads list length -- no parser change needed |
| Section heading enumeration | Parser (parser.py) | F2 check | Parser populates parsed.sections dict; F2 reads keys -- no parser change needed |
| N-gram heading suppression | F2 check (f2_duplicate_fact.py) | -- | All suppression logic lives in the check, not the parser |

## Standard Stack

No new packages. The fixes use only stdlib and existing plan-forge internals.

Test runner: `uv run pytest` (deps from pyproject.toml). [VERIFIED: read pyproject.toml]

## Package Legitimacy Audit

Not applicable -- Phase 8 installs no external packages.

## Architecture Patterns

### System Architecture Diagram

```
parse(plan_text)
     |
     v
ParsedPlan
  .sections   dict[str, ParsedSection]  <- F2 reads .keys()
  .citations  list[str]                 <- G8.A reads len()
     |
     +-- G8 Part A check(parsed, [])
     |       _find_external_voices_body(parsed) -> body: str | None
     |       if body is None  -> G8.A.no_section BLOCKER  (unchanged)
     |       if body.strip() == ""  -> G8.A.no_citation BLOCKER  (NEW branch)
     |       if body.strip() != "" and len(citations)==0 -> G8.A.no_citation HIGH  (NEW)
     |       if len(citations) > 0  -> no G8.A.no_citation finding  (unchanged)
     |
     +-- F2 check(parsed, **kwargs)
             heading_words = {word for heading in parsed.sections
                              for word in heading.lower().split()}
             for each flagged n-gram (ng, headings):
                 if set(ng.split()) <= heading_words:  skip  (NEW guard)
                 else: emit Finding
```

### Recommended Project Structure

No changes to project structure. Edits are confined to:

```
src/plan_forge/checks/epistemic/g8_source_diversity.py
src/plan_forge/checks/mechanical/f2_duplicate_fact.py
tests/unit/test_g8_source_diversity.py
tests/unit/test_f2_duplicate_fact.py
tests/fixtures/  (4 new .md files)
```

## G8 Change: Exact Code Anatomy

**Current code (lines 98-106, verbatim):** [VERIFIED: read source]

```python
if len(parsed.citations) == 0:
    findings.append(Finding(
        check_id="G8.A.no_citation",
        severity=Severity.BLOCKER,
        location="External Voices",
        message="no citation found in External Voices section",
        fix_hint="add at least one citation in Author (Year) format",
    ))
```

**After the fix -- two-branch replacement:**

```python
if len(parsed.citations) == 0:
    severity = (
        Severity.BLOCKER if not body.strip()
        else Severity.HIGH
    )
    findings.append(Finding(
        check_id="G8.A.no_citation",
        severity=severity,
        location="External Voices",
        message="no citation found in External Voices section",
        fix_hint="add at least one citation in Author (Year) format",
    ))
```

Key facts:

- `body` is already in scope at line 98 (assigned at line 80 via
  `_find_external_voices_body`). [VERIFIED: read source]
- The `body is None` branch at line 82 returns early, so at line 98 `body`
  is guaranteed to be a `str`. No None guard needed inside this block.
- `not body.strip()` is True for both empty string and whitespace-only.

**MUST verify before coding:** Run
`grep -n 'HIGH' /home/houminxi/code/plan-forge/src/plan_forge/verdict.py`
to confirm `Severity.HIGH` exists. If absent, add it to the enum in the same
commit (see Assumptions Log). [ASSUMED: Severity.HIGH is defined]

## F2 Change: Exact Code Anatomy

**Current flagging loop (lines 61-75, verbatim):** [VERIFIED: read source]

```python
findings: list[Finding] = []
for ng, headings in flagged[:_FINDING_CAP]:
    findings.append(Finding(
        check_id="F2.duplicate_fact",
        severity=Severity.LOW,
        location="line:0",
        message=(
            f"phrase {ng!r} appears in {len(headings)} sections:"
            f" {sorted(headings)!r}"
        ),
        fix_hint=(
            f"declare {ng!r} canonically in one section and"
            f" reference it elsewhere"
        ),
    ))
```

**After the fix -- heading_words guard inserted before the loop:**

```python
heading_words: set[str] = set()
for heading in parsed.sections:
    heading_words.update(heading.lower().split())

findings: list[Finding] = []
for ng, headings in flagged[:_FINDING_CAP]:
    ng_words = set(ng.split())
    if ng_words <= heading_words:
        continue
    findings.append(Finding(
        check_id="F2.duplicate_fact",
        severity=Severity.LOW,
        location="line:0",
        message=(
            f"phrase {ng!r} appears in {len(headings)} sections:"
            f" {sorted(headings)!r}"
        ),
        fix_hint=(
            f"declare {ng!r} canonically in one section and"
            f" reference it elsewhere"
        ),
    ))
```

Key facts about the data model:

- `parsed.sections` is `dict[str, ParsedSection]` where keys are the raw
  heading text as extracted by `_HEADING_RE` group 2 with `.strip()`.
  [VERIFIED: read parser.py lines 244-257]
- Heading keys are NOT pre-lowercased. Examples from real fixtures: "Background",
  "Design", "Implementation", "Testing", "Summary", "External Voices". The
  `heading.lower().split()` in the heading_words build is mandatory.
  [VERIFIED: read parser.py -- `heading_text = m.group(2).strip()` stored as-is]
- `ParsedSection` fields: `heading: str`, `level: int`, `body: str`,
  `line_start: int`, `line_end: int`. [VERIFIED: read parser.py lines 24-30]
- `_extract_ngrams` returns lowercase bigrams and trigrams; `ng.split()` on a
  lowercase bigram "implementation tasks" yields `["implementation", "tasks"]`.
  No further lowercasing needed on the n-gram side.
  [VERIFIED: read f2_duplicate_fact.py lines 21-31]
- The `heading_words` block goes BETWEEN `flagged.sort(...)` (line 59) and the
  existing `findings: list[Finding] = []` (line 61). The `findings = []` line
  stays in place; the heading_words build and the modified loop body are
  inserted around it.

## TP Preservation Analysis (GATE-05)

The existing `f2_fail.md` fixture has sections named "Background", "Design",
"Implementation", "Testing", "Summary". The flagged n-gram is "databaseconnection
pool". `set("databaseconnection pool".split())` = `{"databaseconnection", "pool"}`.
heading_words built from those headings contains "background", "design",
"implementation", "testing", "summary" and words from the H1 title line
("f2", "fail", "fixture", "a", "plan", "where", "one", "noun-phrase", "bigram",
"appears", "in", "three", "or", "more", "sections"). Neither "databaseconnection"
nor "pool" is present. The guard does NOT suppress the TP. [VERIFIED: read
f2_fail.md + parser heading extraction logic]

## FP Fixture Design for F2 (GATE-04)

The FP fixture needs an n-gram where both words appear somewhere in section
headings. Simplest case: a section literally named "Implementation Tasks" (or
two sections "Implementation" + "Tasks"). The repeated n-gram "implementation
tasks" has words {"implementation", "tasks"} -- both present in heading_words.

A concrete minimal fixture:

```markdown
# Plan

## Background

Implementation Tasks must be prioritized carefully.
Implementation Tasks define the project scope.

## Implementation Tasks

Implementation Tasks are listed below.

## Design

Implementation Tasks emerge from design.

## Delivery

Final Implementation Tasks get signed off here.
```

heading_words from headings "Plan" (H1), "Background", "Implementation Tasks",
"Design", "Delivery" contains "implementation" and "tasks". The n-gram
"implementation tasks" (appearing in 4+ sections) matches the guard and is
suppressed. Without the guard, 4 >= 3 means F2 fires. With the guard: silent.

## Existing Fixture Inventory

Fixtures used by G8 tests: [VERIFIED: read test file + fixtures dir]
- `g8_pass.md` -- well-formed, one citation (Popper), dissent, failure case
- `g8_fail.md` -- no External Voices section at all (triggers no_section)
- `g8_biblio_citation_fp.md` -- bibliography-order citations (4 items, all
  match `_CITATION_BIBLIO_RE`); used by biblio tests
- `g8_biblio_citation_tp.md` -- prose bullets (no parseable citation format);
  currently named "TP" but represents the prose-cited FP scenario for GATE-01

Note: `g8_biblio_citation_tp.md` already demonstrates the citations==0 case
with non-empty body. The new `g8_prose_cited_fp.md` fixture should use
INLINE prose (not list bullets) to be distinct from g8_biblio_citation_tp.md.

Fixtures used by F2 tests: [VERIFIED: read test file + fixtures dir]
- `f2_pass.md` -- no n-gram in 3+ sections
- `f2_fail.md` -- "DatabaseConnection Pool" in 4 sections

## Common Pitfalls

### Pitfall 1: Forgetting body is guaranteed str at the citations check

**What goes wrong:** Adding a `body is None` guard inside the
`len(parsed.citations) == 0` block -- redundant because the None branch
returns early at line 82.
**How to avoid:** Read the existing early return before writing new code.

### Pitfall 2: Iterating section bodies instead of section keys for heading_words

**What goes wrong:** Building heading_words from `section.body` words instead
of the dict key. Every body word enters the suppression set, destroying F2
sensitivity.
**How to avoid:** Iterate `parsed.sections` (the dict directly); keys are
heading strings. Do not use `section.body`.

### Pitfall 3: FP fixture that does not trigger without the fix

**What goes wrong:** Writing a fixture where heading_words does not contain all
n-gram words, so the FP test passes both before and after the fix (vacuous).
**How to avoid:** Run `uv run pytest` with the fixture against unmodified
f2_duplicate_fact.py first. Confirm at least one F2 finding before adding the
fix. The fix should silence it.

### Pitfall 4: Bug-inject committed as a real commit

**What goes wrong:** Committing the reverted (broken) state into git.
**How to avoid:** Bug-inject is working-tree-only: modify -> pytest -> observe
-> `git checkout -- <file>` -> pytest again. No commit during inject.

### Pitfall 5: Case mismatch in subset test

**What goes wrong:** ng is lowercase (from `_extract_ngrams`); heading key
is mixed-case. The `heading.lower().split()` in the build step handles this.
Forgetting `.lower()` means "Implementation" never matches "implementation"
from the n-gram side.
**How to avoid:** Always lowercase headings when building heading_words. The
n-gram side needs no lowercasing (already lowercase by construction).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Subset membership | Loop over ng words with `in` checks | Python `set <= set` | Same result, more idiomatic, O(n) |
| Case normalization | Custom casefold | `.lower()` | Sufficient for English heading text |
| Severity branching | New helper function | Inline ternary | 2-branch decision, one line |

## Runtime State Inventory

SKIPPED -- greenfield code edits, no rename/refactor/migration involved.

## Environment Availability Audit

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| uv | test runner | yes | confirmed by existing test run | -- |
| pytest | tests | yes | resolved via uv from pyproject.toml | -- |
| plan_forge (editable install) | test imports | yes | confirmed: 761 tests collected | -- |

No missing dependencies.

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest (uv-managed, no standalone venv in main worktree) |
| Config file | pyproject.toml [tool.pytest.ini_options] |
| Quick run command | `uv run pytest tests/unit/test_g8_source_diversity.py tests/unit/test_f2_duplicate_fact.py -q` |
| Full suite command | `uv run pytest tests/ -q` |
| Baseline | 761 passed, 5 skipped in 2.79s |

### Phase Requirements -> Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|--------------|
| GATE-01 | Prose-cited plan: no_citation fires as HIGH | unit | `uv run pytest tests/unit/test_g8_source_diversity.py::TestG8PartA::test_prose_cited_emits_high -xvs` | No -- Wave 0 |
| GATE-02 | Anti-gutting: no_citation still fires on empty body | unit | `uv run pytest tests/unit/test_g8_source_diversity.py::TestG8PartA::test_empty_body_emits_blocker -xvs` | No -- Wave 0 |
| GATE-03 | Both branches verified: empty -> BLOCKER, non-empty -> HIGH | unit | Same two tests above | No -- Wave 0 |
| GATE-04 | Heading-derived n-gram suppressed | unit | `uv run pytest tests/unit/test_f2_duplicate_fact.py::test_f2_heading_fp_suppressed -xvs` | No -- Wave 0 |
| GATE-05 | Genuine n-gram not suppressed by heading exemption | unit | `uv run pytest tests/unit/test_f2_duplicate_fact.py::test_f2_genuine_phrase_not_suppressed -xvs` | No -- Wave 0 |
| GATE-01T | Bug-inject: revert HIGH to BLOCKER, confirm prose fixture fires BLOCKER | manual | -- (manual working-tree flip) | N/A |
| GATE-04T | Bug-inject: remove heading guard, confirm heading-term fires F2 | manual | -- (manual working-tree flip) | N/A |

### Sampling Rate

- Per task commit: `uv run pytest tests/unit/test_g8_source_diversity.py tests/unit/test_f2_duplicate_fact.py -q`
- Per wave merge: `uv run pytest tests/ -q`
- Phase gate: full suite green before `/gsd:verify-work`

### Wave 0 Gaps

- [ ] `tests/fixtures/g8_prose_cited_fp.md` -- inline-prose citation (no
  parseable list item); covers GATE-01 and GATE-03 HIGH branch
- [ ] `tests/fixtures/g8_empty_body_blocker.md` -- External Voices with
  empty body between two headings; covers GATE-03 BLOCKER branch
- [ ] `tests/fixtures/f2_heading_fp.md` -- n-gram whose words all appear in
  section headings; covers GATE-04
- [ ] `test_g8_prose_cited_emits_high` in TestG8PartA -- GATE-01
- [ ] `test_g8_empty_body_emits_blocker` in TestG8PartA -- GATE-02/GATE-03
- [ ] `test_f2_heading_fp_suppressed` in test_f2_duplicate_fact.py -- GATE-04
- [ ] `test_f2_genuine_phrase_not_suppressed` in test_f2_duplicate_fact.py -- GATE-05

## Security Domain

Not applicable. Phase is internal Python logic with no network I/O, no user
input handling, and no persistence layer changes.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `Severity.HIGH` is defined in plan_forge/verdict.py | G8 Change: Exact Code Anatomy | G8 code fails at import; must grep before coding -- one-line fix if absent |

**If A1 is wrong:** Add `HIGH` to the Severity enum in verdict.py in the same
commit. The enum already has BLOCKER, MEDIUM, LOW, ARBITRATION from Part B
usage -- HIGH is the only candidate value that might be missing.

## Open Questions (RESOLVED)

1. **Is `Severity.HIGH` defined in the verdict module?**
   - RESOLVED: YES. `grep -n HIGH src/plan_forge/verdict.py` returns line 22:
     `HIGH = "HIGH"` inside the `Severity(str, Enum)` class.
     `Severity.HIGH` is defined and already used in formatting output
     (verdict.py lines 136, 139). No enum addition needed.
   - What we knew: Part A uses BLOCKER; Part B uses BLOCKER, MEDIUM,
     ARBITRATION. CONTEXT.md specifies HIGH.
   - Resolution source: direct grep of src/plan_forge/verdict.py (confirmed
     2026-05-27).

## Sources

### Primary (HIGH confidence)

- Direct read of `src/plan_forge/checks/epistemic/g8_source_diversity.py`
  (all 285 lines, current in-repo state)
- Direct read of `src/plan_forge/checks/mechanical/f2_duplicate_fact.py`
  (all 77 lines)
- Direct read of `src/plan_forge/parser.py` -- ParsedPlan/ParsedSection
  dataclass, `_extract_sections`, `_extract_citations` (all 736 lines)
- Direct read of `tests/unit/test_g8_source_diversity.py` (all 330 lines)
- Direct read of `tests/unit/test_f2_duplicate_fact.py` (all 62 lines)
- Direct read of fixtures: g8_pass.md, g8_fail.md, g8_biblio_citation_fp.md,
  g8_biblio_citation_tp.md, f2_pass.md, f2_fail.md
- `uv run pytest tests/ -q` baseline: 761 passed, 5 skipped in 2.79s
- `uv run pytest tests/unit/test_g8_source_diversity.py tests/unit/test_f2_duplicate_fact.py -q`: 17 passed in 0.40s

### Secondary (MEDIUM confidence)

None needed.

### Tertiary (LOW confidence)

None.

## Metadata

**Confidence breakdown:**
- G8 change: HIGH -- exact line numbers read, body variable scope confirmed,
  insertion point unambiguous
- F2 change: HIGH -- data flow confirmed (sections dict keys are raw heading
  strings, n-grams are lowercase), TP preservation verified by analysis
- Test fixtures: HIGH -- parser citation extraction confirmed (list items only),
  heading extraction confirmed (raw stripped text, not lowercased)
- Severity.HIGH availability: HIGH (RESOLVED) -- confirmed via grep: verdict.py line 22 `HIGH = "HIGH"`

**Research date:** 2026-05-27
**Valid until:** 2026-06-27 (stable Python codebase, no external dependencies)
