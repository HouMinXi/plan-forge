# Phase 13: Plan-Gate Mechanical Checks (F10-F15) - Research

**Researched:** 2026-05-31
**Domain:** Python mechanical gate implementation; plan-forge F-gate framework
**Confidence:** HIGH

## Summary

Phase 13 adds six new F-gates (F10-F15) to `src/plan_forge/checks/mechanical/`.
The research confirms all implementation patterns from existing gates (F2, F3, F4)
and surfaces one critical discrepancy between CONTEXT.md and the actual codebase:
the gate registry is NOT auto-discovery -- it is explicit imports in `__init__.py`.
Every new gate requires a manual import and `findings.extend()` line added there.

A second critical finding: `ParsedPlan` has NO `frontmatter` field. CONTEXT.md's
code context block states `frontmatter: dict` exists, but the actual dataclass in
`parser.py` has eight fields and none is `frontmatter`. F15's D-18 guard (exclude
paths also in `files_modified`) must parse YAML frontmatter directly from
`parsed.raw_text`, following the same pattern used in F3's `_own_id_set()`.

All six gates operate exclusively on `parsed.raw_text` and/or `parsed.sections`,
which are populated by the existing parser. No parser changes are needed.

**Primary recommendation:** Add each gate as `fNN_name.py` plus one import and one
`findings.extend()` line in `__init__.py`. Frontmatter is always read from
`raw_text` via regex, never from a `.frontmatter` attribute. Repo root for F11
and F15 file checks is derived from the gate's own `__file__` path walking up
from `src/plan_forge/checks/mechanical/` to the project root (5 `.parent` calls).

## Project Constraints (from CLAUDE.md)

- All new code passes the full forge review pipeline (Step 0 + 3-cycle static
  review + smoke test). Implementation agent and review agent must be separate
  sub-sessions.
- Remove AI smell before review: no plan/task labels (D-01, T28, etc.) in code
  or comments.
- Tests run via `uv run pytest` (not `python -m pytest` -- system python lacks
  sqlalchemy and fails to collect).
- `rtk proxy uv run pytest` to see uncompressed output when rtk hook is active.
- No `.venv` in main worktree; per-task venvs live in `.worktrees/feat-*/`.
- Commit messages: no task IDs, no model names, no AI co-author lines. Write WHY.
- Version bump in Plan 13-03: `pyproject.toml` version string from `0.1.4` to
  `0.1.5`.
- Files over 800 lines blocked by the PreToolUse hook -- write focused modules.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Gate logic (F10-F15) | `checks/mechanical/` | -- | All existing gates live here |
| Gate registration | `checks/mechanical/__init__.py` | -- | Explicit import list, not auto-discovery |
| Plan parsing | `parser.py` | -- | No changes; gates read `raw_text` + `sections` |
| Test fixtures | `tests/fixtures/` | -- | 12 new .md files (2 per gate) |
| Unit tests | `tests/unit/` | -- | One test file per gate following F2/F3 pattern |
| Version bump | `pyproject.toml` | -- | Single source of version truth |

## Gate Registry: Critical Finding

**D-22 in CONTEXT.md states:** "Gate registry auto-discovery already in place
(files matching `f[0-9]+_*.py`). No changes to `check_mechanical()` entry point
needed."

**Actual code in `checks/mechanical/__init__.py`:**

```python
from . import (
    f1_sc_traceability,
    f2_duplicate_fact,
    f3_cross_plan_invariant,
    f4_temporal_anchor,
    f5_r_tag_pruner,
    f6_preamble_body,
    f7_ascii,
    f8_plan_consistency,
    f9_plan_length,
)

def run(parsed: ParsedPlan, preamble: str | None = None) -> list[Finding]:
    findings: list[Finding] = []
    findings.extend(f1_sc_traceability.check(parsed))
    findings.extend(f2_duplicate_fact.check(parsed))
    # ... one line per gate, in order ...
    findings.extend(pbr.run(parsed))
    return findings
```

There is NO filesystem glob or dynamic import. Each new gate requires:
1. An explicit `from . import fNN_name` in the import block.
2. An explicit `findings.extend(fNN_name.check(parsed))` in `run()`.

The planner must include tasks to add both lines for each of the six new gates.
The `check_mechanical()` function in `api.py` delegates to `mechanical.run()` and
needs no changes, but `mechanical/__init__.py` does.

[VERIFIED: codebase read of `src/plan_forge/checks/mechanical/__init__.py`]

## ParsedPlan Fields: Critical Finding

**CONTEXT.md code context block states:** `frontmatter: dict -- YAML frontmatter
(includes files_modified)`.

**Actual `ParsedPlan` dataclass fields (from `parser.py`):**

```python
@dataclass
class ParsedPlan:
    raw_text: str
    sections: dict[str, ParsedSection] = field(default_factory=dict)
    sc_table: list[ParsedSC] = field(default_factory=list)
    risks: list[ParsedRisk] = field(default_factory=list)
    hedge_word_locations: list[tuple[int, str]] = field(default_factory=list)
    citations: list[str] = field(default_factory=list)
    ai_smell_phrases: list[tuple[int, str]] = field(default_factory=list)
    anchors: list[ParsedAnchor] = field(default_factory=list)
    quantitative_claims_without_anchor: list[tuple[int, str]] = field(...)
```

There is no `frontmatter` field. Gates that need `files_modified` (F15 D-18) must
parse it from `parsed.raw_text` using regex, exactly as F3's `_own_id_set()` does.

[VERIFIED: codebase read of `src/plan_forge/parser.py` lines 69-81]

## Standard Stack

### Core (all already present; no new dependencies)

| Library | Version | Purpose | Note |
|---------|---------|---------|------|
| `re` (stdlib) | stdlib | regex for all pattern matching | all existing gates use only this |
| `pathlib.Path` | stdlib | file existence check (F11, F15) | already used in test files |

No new packages required. F10-F15 are pure Python using only stdlib.

[VERIFIED: review of all existing gate implementations]

## Package Legitimacy Audit

Not applicable. Phase installs zero external packages. All gates use stdlib only.

## F10: Noun-Phrase Duplicate Detection

### Pattern Differences from F2

F2 extracts bigrams and trigrams of **capitalized tokens** (`[A-Z][A-Za-z0-9_-]{2,}`).

F10 uses a **sliding window over all tokens** (stopwords excluded), targeting 3-4
word phrases:

| Property | F2 | F10 |
|----------|-----|-----|
| Token filter | Capitalized only | Any token, stopwords excluded |
| N-gram width | 2 and 3 | 3 and 4 |
| Min non-stopword len | none | 4+ chars (D-03) |
| Scope | All section bodies | Section bodies, code fences excluded |
| Threshold | 3+ distinct sections | 3+ distinct sections (D-04) |
| Severity | LOW | LOW |

F10 reuses F2's section iteration pattern and cross-section counting pattern.
The core loop structure (`for heading, section in parsed.sections.items()`,
phrase -> set of section headings) is directly reusable.

### Heading Lines Are NOT in section.body

Confirmed: the `_extract_sections` state machine appends non-heading lines to
`body_lines` for all open sections on the stack. Heading lines trigger close/open
logic and are never appended. Therefore `section.body` never contains `##`/`###`
heading lines, even for parent sections spanning nested subsections.

**F10 does not need to filter `#` lines from section bodies.**

[VERIFIED: parser.py `_extract_sections` lines 241-263]

### Stopword List

```python
_STOPWORDS = frozenset({
    "a", "an", "the", "and", "or", "but", "in", "on", "at", "to",
    "for", "of", "with", "by", "from", "as", "is", "are", "was",
    "were", "be", "been", "being", "have", "has", "had", "do",
    "does", "did", "will", "would", "could", "should", "may",
    "might", "must", "shall", "can", "this", "that", "these",
    "those", "it", "its", "not", "no", "so", "if", "then",
})
```

The 4+ character non-stopword filter (D-03) prevents trivial phrases like
"run the test" from firing.

[ASSUMED -- specific word list not prescribed in CONTEXT.md]

### Code Fence Exclusion

Apply the fence-width-aware state machine from F4/parser to each `section.body`
string before tokenizing (iterate lines, track `in_code`/`fence_width` state,
skip lines inside fences).

### Implementation Skeleton

```python
def _extract_noun_phrases(body: str) -> set[str]:
    phrases: set[str] = set()
    in_code = False
    fence_width = ""
    clean_lines: list[str] = []
    for line in body.splitlines():
        stripped = line.strip()
        fence_m = re.match(r'^(`{3,})', stripped)
        if fence_m:
            fence = fence_m.group(1)
            if not in_code:
                in_code = True
                fence_width = fence
            elif fence == fence_width:
                in_code = False
                fence_width = ""
            continue
        if in_code:
            continue
        clean_lines.append(stripped)
    tokens = re.findall(r'\b[a-z][a-z0-9_-]*\b', " ".join(clean_lines).lower())
    tokens = [t for t in tokens if t not in _STOPWORDS]
    for i in range(len(tokens)):
        for width in (3, 4):
            if i + width <= len(tokens):
                phrase = " ".join(tokens[i:i + width])
                if any(len(w) >= 4 for w in phrase.split()):
                    phrases.add(phrase)
    return phrases
```

[ASSUMED -- exact token regex not prescribed in CONTEXT.md]

## F11: AC-to-Test Traceability

### XML Block Extraction

No existing gate in F1-F9 extracts XML blocks. F11 is the first gate to do this.

```python
re.findall(r'<acceptance_criteria>(.*?)</acceptance_criteria>',
           parsed.raw_text, re.DOTALL)
```

[VERIFIED: Phase 10-02-PLAN.md lines 132-144 confirm this exact tag structure]

### Test Function Name Pattern

D-07: match `test_[a-z_]{4,}`. For backtick-wrapped pytest invocations:

```python
_TEST_FUNC_RE = re.compile(r'\btest_[a-z_]{4,}\b')
_PYTEST_DOUBLE_COLON_RE = re.compile(r'::(test_[a-z_]{4,})\b')
_PYTEST_K_FLAG_RE = re.compile(r'-k\s+(test_[a-z_]{4,})\b')
```

### Repo Root Resolution

Gate file path: `<repo>/src/plan_forge/checks/mechanical/f11_*.py`

Five `.parent` calls reach the repo root:
- mechanical/ (1) -> checks/ (2) -> plan_forge/ (3) -> src/ (4) -> <repo>/ (5)

```python
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent
_TESTS_DIR = _REPO_ROOT / "tests"
```

If `_TESTS_DIR` does not exist (installed package), return `[]`.

[VERIFIED: `ls tests/unit/` confirms `tests/` is at repo root]

### Grep Strategy

```python
def _test_function_exists(func_name: str, tests_dir: Path) -> bool:
    pattern = re.compile(r'\bdef\s+' + re.escape(func_name) + r'\b')
    for py_file in tests_dir.rglob("*.py"):
        try:
            if pattern.search(py_file.read_text(encoding="utf-8", errors="ignore")):
                return True
        except OSError:
            pass
    return False
```

[ASSUMED -- no subprocess; uses stdlib pathlib + re only]

## F12: Temporal Anchor Lint

### Scope: AC and Action Blocks Only

```python
ac_blocks = re.findall(
    r'<acceptance_criteria>(.*?)</acceptance_criteria>',
    parsed.raw_text, re.DOTALL)
action_blocks = re.findall(
    r'<action>(.*?)</action>',
    parsed.raw_text, re.DOTALL)
```

### Pattern

```python
_TEMPORAL_ACTION_RE = re.compile(
    r'\b(before|after|once|when|until)\b'
    r'(?:(?!\n).){0,60}'
    r'\b(commit|merge|run|execute|complete|finish|pass|fail)\b',
    re.IGNORECASE,
)
```

### Anchor Exclusion (per line)

A phrase is anchored if its line contains any of:

```python
_ANCHOR_SIGNALS = (
    re.compile(r'`'),
    re.compile(r'\buv\s+run\b'),
    re.compile(r'\b[a-z]+_[a-z]'),   # snake_case identifier
    re.compile(r'\bgit\s+\w+'),       # git command
)
```

Test anchor signals against the LINE containing the match. GSD AC items are
one-item-per-line so line = sentence is correct for this format.

[ASSUMED -- sentence boundary not defined in D-09/D-10; derived from GSD format]

## F13: Cross-Plan Claim Verifier

### Relationship to F3

Additive to F3 (D-11). F3 flags refs absent from exempt sections. F13 flags refs
present in exempt sections but described with fewer than 10 prose words.

### Reusing F3 Patterns

```python
from plan_forge.checks.mechanical.f3_cross_plan_invariant import (
    _PHASE_RE, _SUBPLAN_RE, _TASK_RE,
    _heading_is_exempt, _own_id_set,
)
```

Import direction: F13 -> F3 only. Never the reverse.

[ASSUMED -- import approach not stated in CONTEXT.md; standard DRY practice]

### Prose Word Count

For each cross-plan ref in an exempt section body, extract up to 200 chars
centered on it (D-12), then count non-ref words:

```python
def _prose_word_count(sentence: str) -> int:
    words = sentence.split()
    count = 0
    for word in words:
        clean = word.strip(".,;:()")
        if (_PHASE_RE.fullmatch(clean)
                or _SUBPLAN_RE.fullmatch(clean)
                or _TASK_RE.fullmatch(clean)):
            continue
        count += 1
    return count
```

[ASSUMED -- implementation not specified in D-12]

## F14: Task-Without-Acceptance-Criteria

### Task Extraction

```python
_TASK_FULL_RE = re.compile(r'<task\b([^>]*)>(.*?)</task>', re.DOTALL)
_TYPE_ATTR_RE = re.compile(r'\btype=["\']([^"\']*)["\']')
```

Group 1: attribute string. Group 2: task body.

[VERIFIED: Phase 10-02-PLAN.md shows `<task type="auto" tdd="true">` and
`<task type="checkpoint:human-verify" gate="blocking">` patterns]

Exempt if `type_val.startswith("checkpoint:")` (D-14). When `type` attribute is
absent, treat `type_val = ""` -- task is NOT exempt.

### Child Block Detection

```python
def _has_ac_or_verify(task_body: str) -> bool:
    return bool(
        re.search(r'<acceptance_criteria\b', task_body)
        or re.search(r'<verify\b', task_body)
    )
```

### Line Number

```python
for m in _TASK_FULL_RE.finditer(parsed.raw_text):
    lineno = parsed.raw_text[:m.start()].count('\n') + 1
    location = f"line:{lineno}"
```

## F15: Read-First File Validity

### Extraction

```python
_READ_FIRST_RE = re.compile(r'<read_first>(.*?)</read_first>', re.DOTALL)
_PATH_LINE_RE = re.compile(r'^\s*-\s+(\S+)', re.MULTILINE)
```

[VERIFIED: Phase 10-02-PLAN.md lines 103-112 show absolute paths followed by
parenthetical comments on the next line, not the same line]

### Repo Root

Same as F11: 5 `.parent` calls from `__file__`.

Relative paths resolve as `_REPO_ROOT / path_str`. Absolute paths use
`Path(path_str)` directly.

### files_modified Guard

Since `ParsedPlan` has no `frontmatter` field, parse from `parsed.raw_text`:

```python
def _extract_files_modified(raw_text: str) -> set[str]:
    lines = raw_text.splitlines()
    if not lines or lines[0].strip() != '---':
        return set()
    result: set[str] = set()
    collecting = False
    for line in lines[1:]:
        stripped = line.strip()
        if stripped == '---':
            break
        if stripped.startswith('files_modified:'):
            collecting = True
            continue
        if collecting:
            m = re.match(r'^\s{2,}-\s+(.+)', line)
            if m:
                result.add(m.group(1).strip())
            elif stripped and not stripped.startswith((' ', '-')):
                collecting = False
    return result
```

[VERIFIED: prototype execution confirmed against Phase 12-02-PLAN.md format]

### Glob Guard

```python
def _is_glob_pattern(path_str: str) -> bool:
    return any(c in path_str for c in ('*', '{', '}'))
```

## Severity Enum: Confirmed Values

```
BLOCKER, HIGH, MEDIUM, LOW, ARBITRATION
```

Phase 13 assignments:
- F10: LOW (D-02)
- F11: MEDIUM (D-05)
- F12: LOW (D-08)
- F13: MEDIUM (D-11)
- F14: HIGH (D-13) -- flips engineering verdict to FAIL
- F15: MEDIUM (D-17)

[VERIFIED: `src/plan_forge/verdict.py` lines 12-26]

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| XML parsing | xml.etree.ElementTree | regex `<tag>(.*?)</tag>` with re.DOTALL | Plan tags may be malformed; all CONTEXT.md patterns use regex |
| File content search | subprocess grep | `pathlib.rglob + re.search` | No shell injection; no grep binary dependency |
| Stopword list | NLTK download | inline `frozenset` ~30 words | No network dependency |
| YAML parsing | PyYAML | regex on raw_text lines | No new dep; F3 already parses frontmatter this way |

## Common Pitfalls

### Pitfall 1: Assuming Auto-Discovery

**What goes wrong:** Planner writes tasks that only add `fNN_name.py` files, not
the `__init__.py` edit. Gates exist on disk but are never called.

**Root cause:** CONTEXT.md D-22 says "auto-discovery already in place" but the
codebase uses explicit imports.

**How to avoid:** Every gate implementation wave must include an `__init__.py`
edit task adding both the import and `findings.extend()` call.

### Pitfall 2: Using ParsedPlan.frontmatter

**What goes wrong:** F15 accesses `parsed.frontmatter` -- AttributeError.

**Root cause:** CONTEXT.md code context incorrectly lists `frontmatter: dict`.

**How to avoid:** Parse from `parsed.raw_text` following F3's `_own_id_set()`.

### Pitfall 3: Repo Root Off-by-One

`f11.py` -> `mechanical/` (1) -> `checks/` (2) -> `plan_forge/` (3) ->
`src/` (4) -> `<repo>/` (5). Exactly 5 `.parent` calls. Using 4 lands in
`src/` where `tests/` does not exist.

### Pitfall 4: F14 Task with No type Attribute

When `_TYPE_ATTR_RE.search(attrs)` returns None, treat `type_val = ""`.
Empty string does not `startswith("checkpoint:")` so the task is subject to F14.

### Pitfall 5: F13 Import Direction

Import is F13 -> F3 only. Never write F3 to import from F13.

### Pitfall 6: test_check_id_prefix_invariant

`api.py` references a test that enforces check_id prefix conventions. It may
enumerate permitted F-gate prefixes and need updating for F10-F15. Plan 13-01
Wave 1 must include a task to inspect and update this test.

[ASSUMED -- test file not read in this research session]

## Architecture Patterns

### Recommended Project Structure Addition

```
src/plan_forge/checks/mechanical/
    __init__.py                       ADD 6 imports + 6 extend() calls
    f10_noun_phrase_duplicate.py      new
    f11_ac_test_traceability.py       new
    f12_temporal_anchor_lint.py       new
    f13_cross_plan_claim_verifier.py  new
    f14_task_without_ac.py            new
    f15_read_first_validity.py        new
tests/
    fixtures/
        f10_tp.md  f10_fp.md
        f11_tp.md  f11_fp.md
        f12_tp.md  f12_fp.md
        f13_tp.md  f13_fp.md
        f14_tp.md  f14_fp.md
        f15_tp.md  f15_fp.md
    unit/
        test_f10_noun_phrase_duplicate.py
        test_f11_ac_test_traceability.py
        test_f12_temporal_anchor_lint.py
        test_f13_cross_plan_claim_verifier.py
        test_f14_task_without_ac.py
        test_f15_read_first_validity.py
```

### Test File Pattern

Confirmed from `tests/unit/test_f2_duplicate_fact.py` and
`tests/unit/test_f3_cross_plan_invariant.py`:

```python
import pathlib
from plan_forge.parser import parse
from plan_forge.checks.mechanical import fNN_name
from plan_forge.verdict import Severity

_FIXTURES = pathlib.Path(__file__).parent.parent / "fixtures"

def _load(name: str) -> str:
    return (_FIXTURES / name).read_text(encoding="utf-8")

def test_fNN_pass_fixture():
    parsed = parse(_load("fNN_fp.md"))
    assert fNN_name.check(parsed) == []

def test_fNN_fail_fixture():
    parsed = parse(_load("fNN_tp.md"))
    ids = [f.check_id for f in fNN_name.check(parsed)]
    assert "FNN.check_name" in ids

def test_fNN_severity():
    parsed = parse(_load("fNN_tp.md"))
    findings = fNN_name.check(parsed)
    assert findings
    for f in findings:
        assert f.severity == Severity.EXPECTED_LEVEL
```

### Check ID Convention

Check IDs must start with `FNN.` per the prefix invariant in `api.py`.

Proposed IDs:
- `F10.noun_phrase_duplicate`
- `F11.ac_test_missing`
- `F12.temporal_anchor_unanchored`
- `F13.cross_plan_claim_thin`
- `F14.task_without_ac`
- `F15.read_first_missing`

[ASSUMED -- exact strings not prescribed in CONTEXT.md; follow observed F1-F9 pattern]

## Runtime State Inventory

Not applicable. Greenfield feature phase -- new files only.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.x | All gates | Yes | 3.14 (system) | -- |
| `uv` | Test runner | Yes | confirmed | -- |
| `ruff` | Step 0 lint | Yes | confirmed | -- |
| `tests/` directory | F11, F15 | Yes (dev env) | -- | Gate returns [] if absent |

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest |
| Config file | pyproject.toml |
| Quick run command | `uv run pytest tests/unit/test_fNN_name.py -q` |
| Full suite command | `uv run pytest tests/ -q` |

### Phase Requirements to Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| PG-01 | F10 fires on cross-section noun phrase (3+) | unit | `uv run pytest tests/unit/test_f10_noun_phrase_duplicate.py -q` | No - Wave 1 |
| PG-01 | F10 does not fire on single-section repetition | unit | same | No - Wave 1 |
| PG-02 | F11 fires on AC referencing nonexistent test | unit | `uv run pytest tests/unit/test_f11_ac_test_traceability.py -q` | No - Wave 1 |
| PG-02 | F11 does not fire when test function exists | unit | same | No - Wave 1 |
| PG-03 | F14 fires on auto task lacking AC and verify | unit | `uv run pytest tests/unit/test_f14_task_without_ac.py -q` | No - Wave 1 |
| PG-03 | F14 exempts checkpoint: tasks | unit | same | No - Wave 1 |
| PG-03 | F15 fires on missing read_first file | unit | `uv run pytest tests/unit/test_f15_read_first_validity.py -q` | No - Wave 1 |
| PG-03 | F15 does not fire on files in files_modified | unit | same | No - Wave 1 |

### Wave 0 Gaps

- [ ] `tests/unit/test_f10_noun_phrase_duplicate.py`
- [ ] `tests/unit/test_f11_ac_test_traceability.py`
- [ ] `tests/unit/test_f12_temporal_anchor_lint.py`
- [ ] `tests/unit/test_f13_cross_plan_claim_verifier.py`
- [ ] `tests/unit/test_f14_task_without_ac.py`
- [ ] `tests/unit/test_f15_read_first_validity.py`
- [ ] `tests/fixtures/f10_tp.md` through `tests/fixtures/f15_fp.md` (12 files)
- [ ] Inspect `test_check_id_prefix_invariant` -- may need updating for F10-F15

Framework install: not needed (pytest already installed and configured).

## Security Domain

F10-F15 are pure static analysis gates. The only external access is read-only
filesystem for F11 and F15 (`Path.exists()`, `Path.read_text()`).

ASVS V5: path values from `<read_first>` blocks go only to `Path.exists()` --
no shell execution, no writes. The glob guard (D-18b) on `*`, `{`, `}` prevents
regex amplification from pathological paths.

## Open Questions

1. **F10 stopword list tuning**
   - Domain terms like "plan", "phase", "task" may need adding after Wave 2 bite
     test shows FP rate.

2. **test_check_id_prefix_invariant scope**
   - May have a hardcoded list of F-gate prefixes needing update for F10-F15.
   - Plan 13-01 Wave 1 must include a task to read and update it.

3. **F11 installed-package silence**
   - Return `[]` silently when `_TESTS_DIR.exists()` is False. Document in gate.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Stopword list is standard English ~30 words | F10 section | FP rate higher; tunable after bite test |
| A2 | F10 token regex is `[a-z][a-z0-9_-]*` after lowercasing | F10 skeleton | Edge cases at token boundaries; easy to tune |
| A3 | F12 uses line as sentence boundary for anchor detection | F12 section | Multi-line AC items get incomplete context; low risk for GSD format |
| A4 | F11 silently returns [] when tests/ absent | F11 section | Gate silent in installed-package environments |
| A5 | F13 imports _PHASE_RE etc. from f3_cross_plan_invariant | F13 section | Breaks if F3 internal symbols are renamed |
| A6 | F13 excludes own-ID refs from thin-prose findings | F13 section | Without this, own-ID in audit section generates MEDIUM noise |
| A7 | Check IDs follow FNN.snake_case_description convention | Check IDs section | test_check_id_prefix_invariant may fail |

## Sources

### Primary (HIGH confidence)

- Codebase: `src/plan_forge/checks/mechanical/__init__.py` -- gate registration is explicit imports, not auto-discovery
- Codebase: `src/plan_forge/parser.py` lines 69-81 -- ParsedPlan fields; no frontmatter field
- Codebase: `src/plan_forge/verdict.py` lines 12-26 -- Severity enum
- Codebase: `src/plan_forge/api.py` -- engineering verdict logic, check_id prefix invariant
- Codebase: `src/plan_forge/checks/mechanical/f2_duplicate_fact.py` -- F10 reference
- Codebase: `src/plan_forge/checks/mechanical/f3_cross_plan_invariant.py` -- F13 reference, frontmatter parsing approach
- Codebase: `src/plan_forge/checks/mechanical/f4_temporal_anchor.py` -- F12 reference
- Codebase: `tests/unit/test_f2_duplicate_fact.py` and `test_f3_cross_plan_invariant.py` -- test structure
- Codebase: `.planning/phases/10-f2-structural-false-positive-reduction/10-02-PLAN.md` lines 97-224 -- GSD XML block format
- Codebase: `.planning/phases/12-f3-phase10-and-phase-text-suppression/12-02-PLAN.md` lines 1-30 -- files_modified frontmatter format
- Bash: `ls tests/fixtures/` -- 72 existing fixtures; none use XML blocks
- Bash: `ls tests/unit/` -- 49 existing test files
- Bash: `grep version pyproject.toml` -- current version 0.1.4
- Bash: prototype of files_modified extraction regex confirmed working

### Tertiary (LOW confidence)

- Exact stopword list (A1): derived from common practice, not corpus data
- Exact check ID strings (A7): follow observed naming pattern, not stated in CONTEXT.md

## Metadata

**Confidence breakdown:**
- Gate registration mechanism: HIGH -- verified from actual source
- ParsedPlan fields (no frontmatter): HIGH -- verified from actual source
- XML block extraction pattern: HIGH -- verified from real plan files
- Severity enum values: HIGH -- verified from actual source
- F10 stopword list: LOW -- derived from general practice
- F11/F15 repo root path: MEDIUM -- derived from directory structure
- F12 sentence boundary: MEDIUM -- derived from F4 pattern and GSD format

**Research date:** 2026-05-31
**Valid until:** 2026-06-30 (invalidated if parser.py or verdict.py change)
