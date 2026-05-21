# T14 SUBSPEC: scaffold() + default.md.j2 template

Status: draft for implementation.
Depends on: T01-T13 (parser, verdict, all gates, api.check).
Scope: implement `api.scaffold(name, output_dir=None) -> Path` and the
single `default.md.j2` plan template. After T14, plan-forge both
EVALUATES plans (check) and GENERATES plan skeletons (scaffold) that pass
the mechanical gates by construction.

## 0. Scope challenge (answered before design)

Q1 Does this need to exist? Yes -- roadmap task T14 (PLAN line 1839). A
scaffold gives users a structurally complete starting point that passes
the mechanical gates by construction, so the human spends effort on
content (the semantic/strategic part), not on remembering which sections
G1-G8 require. Without it the gates only ever say "no"; there is no "here
is the shape" on-ramp.

Q2 Three real consumers:
- T16 CLI `plan-forge scaffold <name>` (PLAN line 1841/1880) calls this.
- A human starting a new plan from scratch.
- forge / gsd-style flows that begin a plan document.

Q3 Do-nothing cost: tell users to copy well_formed.md. Costs: it is a
FILLED example, not a placeholder skeleton -- users must delete example
prose and will drop sections or break the table shapes the gates expect;
and there is no programmatic entry point for the CLI/API. The scaffold
turns "copy and hope" into "generate a guaranteed-shaped skeleton".

Q4 do-less candidate: ship a static default.md and copy it verbatim.
Rejected only because the title must be injected; a one-variable render is
the minimum. See alternatives (section 8).

## 1. Design principles (load-bearing)

### 1.1 Contract: scaffold output passes the MECHANICAL gates by construction

`check(scaffold_output, llm_clients=[])` MUST produce zero BLOCKER and
zero HIGH findings from the mechanical layer (F1-F7 + PBR + the mechanical
epistemic gates G1/G2/G3/G5/G7 + G8 Part A). This is the point of the task
and its ground-truth test (Phase 3).

It does NOT need to pass the LLM gates (G4/G6/G8 Part B): those judge
semantics (hedge calibration, SC measurability, citation truth), which a
placeholder skeleton cannot and SHOULD not satisfy -- the human fills real
content, then the LLM gates + human review judge it. A scaffolded-then-
unfilled plan is structurally complete but semantically empty; that is
correct and expected.

### 1.2 Placeholder style: angle-bracket markers that still satisfy the mechanical shape

Every fill-in slot uses an explicit `<...>` angle-bracket placeholder so
the user can see what to replace. BUT each placeholder must preserve the
format / keyword / count the mechanical gate checks, so the skeleton
passes by construction. Examples:
- G1 Reference Class needs >= 2 rows each with a plan-vs-actual ratio
  matching `\d+(?:\.\d+)?\s*[xX]`: a row is
  `| <project> | <scope> | <duration> | 1.0x |` -- the `1.0x` satisfies
  the ratio regex; the `<...>` cells signal "replace me".
- G3 Pre-mortem needs >= 5 numbered causes each mentioning "early_warning"
  and "counter": `1. <failure cause>. early_warning: <signal>. counter: <action>.`
- G5 Chaos Response needs >= 3 scenarios and must NOT be all-"break":
  include a mix (survive / degrade / benefit), never three breaks.
The result: a valid, gate-passing skeleton that is unmistakably a template.

### 1.3 Module split: rendering in scaffold/, file IO + contract in api

- `scaffold/__init__.py`: `render(name: str) -> str` -- renders
  `templates/default.md.j2` via jinja2 with the plan title; returns the
  markdown string. No file IO here.
- `api.scaffold(name, output_dir=None) -> Path`: path resolution, name
  sanitisation, render(), write, boundary handling; returns the written
  Path.
Rendering (reusable, testable without the filesystem) lives in the
scaffold subpackage; the filesystem contract lives in the public api.

### 1.4 Template loading reuses the prompts pattern

`plan_forge.llm.prompts.load()` loads sibling files via
`Path(__file__).parent / name`. Reuse the same plain pattern in
`scaffold/__init__.py`
(`Path(__file__).parent / "templates"` as the jinja2 search dir). Do NOT
introduce importlib.resources -- stay consistent with existing in-tree
resource loading.

### 1.5 jinja2 is the chosen renderer (already a declared dependency)

jinja2 3.1 is in pyproject `dependencies` (PLAN line 14); NOT a new dep.
The template's only real variable is the plan title (`{{ plan_name }}`).
jinja2 over str.format because: PLAN mandates it, it reserves room for the
v0.2 template-logic variations, and markdown tables contain `{` / `|` that
make str.format fragile. (See alternatives, section 8.)

### 1.6 Safety + boundaries (security-relevant)

`name` becomes a filename -- treat it as untrusted input.
- Reject names that are not a safe slug: require `^[A-Za-z0-9._-]+$` AND
  reject any `..`; raise ValueError otherwise. Blocks path traversal
  (`../etc/x`, `a/b`, absolute paths).
- output_dir=None -> Path.cwd(). If output_dir is given but does not
  exist -> FileNotFoundError (do NOT silently mkdir a tree at a possibly-
  mistyped path).
- Target is `<output_dir>/<name>.md`. If it already exists ->
  FileExistsError (never silently overwrite a plan the user may have
  written).
- Return the absolute Path of the written file.

## 2. Phase 0: worktree

Worktree already created: `.worktrees/feat-t14-scaffold` off T13 HEAD
f4fed1b (branch feat-t14-scaffold). Set up venv and confirm baseline:
```
cd /home/houminxi/code/plan-forge/.worktrees/feat-t14-scaffold
python3 -m venv .venv && .venv/bin/pip install -q -e ".[dev]"
unset PLAN_FORGE_CORPUS_URL && .venv/bin/pytest tests/ -q
# expect 315 passed, 4 skipped, 0 warnings
```

## 3. Phase 1: scaffold subpackage + default.md.j2

### 3.1 templates/default.md.j2

Blueprint = `tests/fixtures/well_formed.md` (it passes ALL mechanical
gates; READ it first). Reproduce its SECTION STRUCTURE, replacing filled
prose with `<...>` placeholders while preserving every mechanical
requirement below. The ONLY jinja2 variable is `{{ plan_name }}` in the
H1 title. Add a brief HTML comment at the very top:
`<!-- plan-forge scaffold: replace every <...> placeholder, then run plan-forge check -->`

Required sections and their mechanical minimums (VERIFY against the gate
modules, not memory):
- `# {{ plan_name }}`
- `## Success Criteria` table: >= 2 rows `| SC-1 | <criterion> | <fail condition> |`.
- `## Test Plan`: one entry per SC -- `- test_<name>: covers SC-1; <what it verifies>` (F1 SC<->Test traceability).
- `## Overview`, `## Deliverables`, `## Module Designs`, `## Implementation Tasks` (keep well_formed's shapes; F-layer).
- `## Reference Class`: >= 2 rows each with a ratio like `1.0x` (G1).
- `## Risks` with `### Known Risks`, `### Gray Rhinos` (denial-reason column filled), `### Black Swans` (survival-plan column filled) (G2 three buckets).
- `## Pre-mortem`: >= 5 numbered causes, each with `early_warning:` and `counter:` (G3).
- `## Scope Challenge`: Q1-Q4 using the keyword groups -- "need to exist", "consumer", "do-nothing" cost, "barbell" (G7).
- `## Chaos Response`: >= 3 scenarios with classification words, MIXED (NOT all "break") (G5).
- `## External Voices`: >= 1 non-AI citation, a dissenting note ("However, critics ..."), and a failure case (G8 Part A).

### 3.2 scaffold/__init__.py

```python
"""Plan skeleton rendering. render() returns markdown; api.scaffold writes it."""
from __future__ import annotations
from pathlib import Path
import jinja2

_TEMPLATE_DIR = Path(__file__).parent / "templates"


def render(name: str) -> str:
    """Render the default plan skeleton with the given plan title."""
    env = jinja2.Environment(
        loader=jinja2.FileSystemLoader(str(_TEMPLATE_DIR)),
        autoescape=False,  # markdown output, not HTML
        keep_trailing_newline=True,
    )
    return env.get_template("default.md.j2").render(plan_name=name)
```

### 3.3 Phase 1 tests (tests/unit/test_scaffold_render.py)
- test_render_contains_title: render("my-plan") has "my-plan" in the H1.
- test_render_has_all_sections: every required `## ` heading present.
- test_render_is_deterministic: two renders of the same name are identical.

## 4. Phase 2: api.scaffold()

Replace the NotImplementedError stub. Implement per 1.6:
```python
import re
_SAFE_NAME = re.compile(r"^[A-Za-z0-9._-]+$")

def scaffold(name: str, output_dir: Path | None = None) -> Path:
    if not name or ".." in name or not _SAFE_NAME.match(name):
        raise ValueError(f"unsafe scaffold name: {name!r}")
    target_dir = Path(output_dir) if output_dir is not None else Path.cwd()
    if not target_dir.is_dir():
        raise FileNotFoundError(f"output_dir does not exist: {target_dir}")
    path = target_dir / f"{name}.md"
    if path.exists():
        raise FileExistsError(f"refusing to overwrite existing file: {path}")
    from .scaffold import render
    path.write_text(render(name), encoding="utf-8")
    return path.resolve()
```

### 4.1 Phase 2 tests (tests/unit/test_api_scaffold.py)
- test_scaffold_writes_md_and_returns_path: scaffold("p", tmp_path) -> file exists, suffix .md, returned path resolves to it.
- test_scaffold_default_dir_is_cwd: monkeypatch.chdir(tmp_path); scaffold("p") writes p.md under tmp_path.
- test_scaffold_refuses_existing: second scaffold of same name -> FileExistsError.
- test_scaffold_rejects_unsafe_name: "../evil", "a/b", "" -> ValueError.
- test_scaffold_missing_output_dir: scaffold("p", tmp_path / "nope") -> FileNotFoundError.

## 5. Phase 3: the contract ground-truth test (THE point of T14)

tests/integration/test_scaffold_passes_gates.py:
```python
def test_scaffold_output_passes_mechanical_gates(tmp_path):
    p = scaffold("contract-check", tmp_path)
    v = check(p.read_text(encoding="utf-8"), llm_clients=[])
    serious = [f for f in v.findings
               if f.severity in {Severity.BLOCKER, Severity.HIGH}]
    assert serious == [], [(f.check_id, f.severity.name) for f in serious]
```
This is the acceptance heart of T14: do NOT assume the template is right
-- generate and run check on it. If any mechanical BLOCKER/HIGH fires, fix
the TEMPLATE (not the gate) until clean.

## 6. Phase 4: review + commit

Three-cycle forge review THEN smoke test THEN commit. Given the T13 lesson
(multi-model review can spin on small changes), if forge does not converge
in a reasonable window, diagnose substance directly (full suite green +
contract test green + scope/ASCII clean) and converge via single-model
review + human confirm rather than spinning. Commit message: WHY scaffold
exists (a gate-passing on-ramp so humans spend effort on content), no AI
markers, author Minxi Hou.

## 7. Verification gates
- Full suite green (315 + new), 0 warnings.
- py_compile scaffold/__init__.py + api.py.
- ASCII clean on changed files (git show + git ls-files --others).
- Scope (git show --name-only, NOT git diff): only
  src/plan_forge/scaffold/__init__.py,
  src/plan_forge/scaffold/templates/default.md.j2,
  src/plan_forge/api.py (scaffold() only),
  tests/unit/test_scaffold_render.py, tests/unit/test_api_scaffold.py,
  tests/integration/test_scaffold_passes_gates.py, .planning/T14-SUBSPEC.md.
- CONTRACT gate (Phase 3): scaffold output passes mechanical gates.
- Security: unsafe names rejected (test present).

## 8. Alternatives considered
1. jinja2 render (CHOSEN): PLAN-mandated, declared dep, reserves v0.2 logic.
2. stdlib string.Template / str.format: lighter, but markdown `{` / `|`
   collide and PLAN mandates jinja2.
3. Static default.md copied verbatim + single title replace: simplest, but
   no render path for v0.2 and still needs title substitution.
4. do-nothing (document well_formed.md as the template): no programmatic
   entry, filled-example misleads, sections get dropped. Rejected.

## 9. Non-goals
- No template variations beyond default.md.j2 (v0.2; PLAN 1924/2411).
- No CLI `scaffold` command (that is T16).
- Do NOT make the skeleton pass the LLM gates G4/G6/G8 Part B (semantics
  are the human's to fill).
- Do NOT modify any gate / parser / verdict / check logic to make the
  template pass -- fix the template instead.
- No slugify beyond the safe-name check (v0.1 keeps name simple).

## 10. Hard constraints
1. ASCII only in every new/modified file.
2. No AI markers; author Minxi Hou; comments describe behavior.
3. SUBSPEC wins over PLAN on conflict; document interpretations with
   `# SUBSPEC interpretation: ...`.
4. No NEW dependencies (jinja2 is already declared).
5. Phase order; tests green at each phase.
6. READ-ONLY: parser.py, verdict.py, all checks/*, llm/*, the check()
   logic in api.py. PERMITTED edits: scaffold/__init__.py,
   scaffold/templates/default.md.j2, api.py (scaffold() function only),
   the three new test files, .planning/T14-SUBSPEC.md.
7. Reuse the prompts Path(__file__).parent loading pattern; no
   importlib.resources.
8. Template blueprint is well_formed.md; placeholders are `<...>`; the
   skeleton passes mechanical gates by construction (the Phase 3 contract).

## 11. Report-back (< 35 lines)
Files created + line counts; api.py +/- lines; total tests (315 + new),
confirm 0 warnings; CONTRACT confirmed (scaffold output -> check mechanical
layer 0 BLOCKER/HIGH, state how verified); unsafe-name rejection confirmed;
ASCII clean; scope clean. State default.md.j2 line count. Any SUBSPEC
interpretations made.
