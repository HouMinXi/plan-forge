# Phase 13: Plan-Gate Mechanical Checks - Context

**Gathered:** 2026-05-31
**Status:** Ready for planning

<domain>
## Phase Boundary

Six new mechanical F-gates (F10-F15) that catch plan quality issues before AI
panel review. Based on empirical corpus of 50+ cross-AI plan review rounds
(project_forge_plan_gate_corpus memory), adapted for GSD plan format via
smoke/bite tests on Phases 10-12 plans.

Checks #5 and #6 from the original corpus (R-tag pruner, body-vs-preamble)
are replaced by higher-signal checks discovered during the bite test:
F14 (task-without-AC) and F15 (read-first file validity).

All six are implemented as F-gate extensions in the existing mechanical gate
framework. Zero changes outside `src/plan_forge/checks/mechanical/` and its
tests/fixtures.

</domain>

<decisions>
## Implementation Decisions

### Gate Taxonomy

- **D-01:** All six new checks extend the F-gate namespace: F10 through F15.
  Each gets its own file (`f10_noun_phrase_duplicate.py` etc.) following the
  same register/check() pattern as F1-F9. `check_mechanical()` auto-discovers
  them via the existing gate registry. No changes to the API layer.

### F10: Noun-Phrase Duplicate Detection

- **D-02:** Enhanced F2 variant: detect 3+-word noun phrases appearing 3 or
  more times across DISTINCT plan sections. Exclude section headings and fenced
  code blocks from extraction and counting. Severity: LOW.
- **D-03:** Phrase candidate: sliding window of 3-4 word tokens (stopwords
  excluded). A phrase must contain at least one non-stopword token with 4+
  characters (filters trivial phrases like "run test").
- **D-04:** False-positive guard: phrases repeated within ONE section (even
  many times) are NOT flagged. Only cross-section repetition of 3+ occurrences
  triggers the gate.

### F11: AC-to-Test Traceability

- **D-05:** Scan `<acceptance_criteria>` XML blocks for test function names
  (`test_\w{4,}` pattern or backtick-wrapped pytest invocations). For each
  referenced test function, grep `tests/` to verify the name exists on disk.
  If not found: MEDIUM finding.
- **D-06:** Bite test: 7/9 Phase 10-12 plans reference test function names in
  AC blocks. The gate catches stale references (renamed test, wrong name).
- **D-07:** Only fire when the pattern looks like a specific function
  (must match `test_[a-z_]{4,}` -- at least 4 lowercase/underscore chars after
  prefix). Backtick-wrapped pytest commands: extract from `::` notation or
  `-k` flag.

### F12: Temporal Anchor Lint

- **D-08:** Scan ONLY `<acceptance_criteria>` and `<action>` XML blocks (not
  full plan body). Pattern: temporal word (before|after|once|when|until) +
  context + action verb (commit|merge|run|execute|complete|finish|pass|fail)
  without a concrete anchor. Severity: LOW.
- **D-09:** Anchor exclusion: exempt phrases containing a backtick, a git
  command, a `uv run` invocation, or a Python identifier with underscore.
  Rationale: bite test showed review plans have ~10 legitimate temporal phrases
  (before merging, after committing) that are anchored by context.
- **D-10:** Concrete anchor detection: if the same sentence contains a
  backtick-wrapped command or a snake_case identifier, the phrase is anchored
  and not flagged.

### F13: Cross-Plan Claim Verifier

- **D-11:** Enhancement ADDITIVE to F3 (both gates run). F3 flags cross-plan
  refs absent from audit sections; F13 flags refs present in audit/references
  sections but described with fewer than 10 words of prose (bare "see 10-02"
  without explanation). Severity: MEDIUM.
- **D-12:** Implementation: for each cross-plan ref found in an exempt section,
  extract the surrounding sentence (up to 200 chars). Count non-ref words. If
  < 10 words of prose context: MEDIUM finding.

### F14: Task-Without-Acceptance-Criteria

- **D-13:** Flag any `<task>` element that lacks an `<acceptance_criteria>`
  child block. Severity: HIGH. Rationale: GSD execute-plan contract mandates
  AC on every executable task; missing AC means no verifiable exit condition.
- **D-14:** Exemption: tasks with `type` attribute starting with `checkpoint:`
  are explicitly exempt (`checkpoint:human-action`, `checkpoint:human-verify`).
- **D-15:** Exemption: tasks with a non-empty `<verify>` block are considered
  to have implicit AC. Only tasks with neither `<acceptance_criteria>` nor
  `<verify>` (and type not checkpoint:*) trigger the gate.
- **D-16:** Bite test: 6/9 Phase 10-12 plans have exactly 1 checkpoint task
  without AC -- all correctly exempt under D-14.

### F15: Read-First File Validity

- **D-17:** For each file path in `<read_first>` blocks, check existence on disk
  relative to the repository root. Missing files: MEDIUM finding.
- **D-18:** False-positive guards: (a) exclude paths also in `files_modified`
  frontmatter (files to be created by this plan); (b) exclude paths containing
  `*`, `{`, or `}` (glob/template patterns).
- **D-19:** Bite test: 3/9 Phase 10-12 plans have 1-2 missing read_first files.

### Phase Structure

- **D-20:** 3 plans, same wave pattern as Phases 10-12:
  - Plan 13-01 (Wave 1): worktree + 12 fixtures (TP+FP per gate) + RED stubs
  - Plan 13-02 (Wave 2): implement all 6 gates + Step 0 + GREEN + bite tests
  - Plan 13-03 (Wave 3): forge review (separate sub-session) + merge + v0.1.5

### Scope Boundary

- **D-21:** Only `src/plan_forge/checks/mechanical/` (6 new files) + tests +
  fixtures. No parser, verdict, or API changes.
- **D-22:** Gate registry auto-discovery already in place (files matching
  `f[0-9]+_*.py`). No changes to `check_mechanical()` entry point needed.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Implementation Targets
- `src/plan_forge/checks/mechanical/` -- add f10_*.py through f15_*.py here
- `src/plan_forge/checks/mechanical/f2_duplicate_fact.py` -- F10 follows this
  pattern (exclusion sets, n-gram logic)
- `src/plan_forge/checks/mechanical/f3_cross_plan_invariant.py` -- F13 extends
  this gate; read before implementing F13
- `tests/unit/test_f2_duplicate_fact.py` -- test structure for F10
- `tests/unit/test_f3_cross_plan_invariant.py` -- test structure for F13
- `tests/fixtures/` -- existing fixtures as regression baseline

### Corpus Reference
- Global memory `project_forge_plan_gate_corpus` -- 7 anti-patterns, 6 original
  checks with empirical distribution data
- `.planning/phases/12-f3-phase10-and-phase-text-suppression/12-CONTEXT.md` --
  gate implementation pattern (D-01 through D-08 structure)

</canonical_refs>

<code_context>
## Existing Code Insights

### Gate Registration
- Each gate: `check(parsed: ParsedPlan, **kwargs) -> list[Finding]`
- Auto-discovered from `f[0-9]+_*.py` pattern in mechanical/ directory
- `Finding(check_id="F10.noun_phrase_duplicate", severity=Severity.LOW,
  location="section:{name}", message="...", fix_hint="...")`

### ParsedPlan Fields
- `raw_text: str` -- full document text
- `sections: dict[str, Section]` -- heading -> Section(body, level)
- `frontmatter: dict` -- YAML frontmatter (includes `files_modified`)
- `Section.body: str` -- section content without heading line

### XML Block Extraction (for F11-F15)
- GSD plans use: `<task>`, `<acceptance_criteria>`, `<action>`, `<read_first>`,
  `<verify>`
- Extract: `re.findall(r'<acceptance_criteria>(.*?)</acceptance_criteria>',
  text, re.DOTALL)`
- Task with type attr: `re.findall(r'<task\b([^>]*)>(.*?)</task>',
  text, re.DOTALL)` -- group(1) is attrs, group(2) is body

### Bite Test Evidence (2026-05-31)
- F14: fires on 6/9 plans (checkpoint tasks, all exempt under D-14)
- F15: fires on 3/9 plans (1-2 missing files each)
- F11: fires on 7/9 plans (test function refs in AC blocks)
- F12: ~9-10 temporal phrases in *-03 plans; D-09 anchor exclusion expected
  to reduce to 0-2 after filtering git/pytest anchored phrases
- F10, F13: 0-2 expected findings per plan (low noise)
- R-tag pattern and TODO/FIXME: 0 hits (NOT applicable to GSD plan format)

</code_context>

<specifics>
## Specific Ideas

### Fixture Design (12 fixtures: TP + FP per gate)

| Gate | TP fixture | FP fixture |
|------|-----------|-----------|
| F10 | noun phrase "lock release timing" in 3 sections | same phrase in 1 section |
| F11 | AC refs `test_nonexistent_function` | AC refs `test_f3_fail_fixture` (exists) |
| F12 | AC: "after execution completes with no anchor" | AC: "after `uv run pytest` passes" |
| F13 | ref "10-02" in audit section with bare "see 10-02" | ref with 15+ prose words |
| F14 | `<task type="auto">` with no `<acceptance_criteria>` | `<task type="checkpoint:human-verify">` |
| F15 | `<read_first>` lists `/path/nonexistent.py` | path also in `files_modified` frontmatter |

### Version Bump
Plan 13-03: `__init__.py` and `pyproject.toml`: `0.1.4` -> `0.1.5`

</specifics>

<deferred>
## Deferred Ideas

- Original corpus Check #5 (R-tag pruner): 0 hits on all GSD plans; specific
  to code-forge's iterative annotation style. Defer.
- Original corpus Check #6 (body-vs-preamble): requires AI conversation history
  access. Architecturally blocked. Captured as F15 (read_first validity) instead.
- F11 pytest integration mode: run pytest --collect-only for precise test names
  vs grep. Defer to post-v0.1.5 config option.
- F12 severity escalation: MEDIUM for AC blocks, LOW for action blocks. Deferred
  pending first real-world data on false-positive rate.

</deferred>

---

*Phase: 13-Plan-Gate Mechanical Checks*
*Context gathered: 2026-05-31*
