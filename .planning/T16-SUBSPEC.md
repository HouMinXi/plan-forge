# T16 SUBSPEC: Adapter C (CLI) -- check / scaffold / audit-retroactive

Status: REVISED after pre-review by deepseek + mimo (via aicc) and kimi
(--print). Findings folded in; see section 12 for the review log.
Depends on: T01-T14 (api.check, api.scaffold, Verdict.summary).
Scope: implement the argparse CLI at `adapters/cli/main.py` with three
subcommands -- check, scaffold, audit-retroactive -- each functional with
`--help`. record-outcome and abandonment-check are T32 (out of scope).

## 0. Scope challenge
Q1 Need to exist? Yes -- roadmap T16 (PLAN 1841). The CLI is Adapter C, the
CI / batch entry point (PLAN 433); it makes check() and scaffold() callable
from a shell and CI without hand-written `python -c` glue.
Q2 Three consumers: (1) a CI pipeline gating a plan file; (2) batch audit
of a directory of plans; (3) a human at a terminal.
Q3 Do-nothing cost: users hand-write `python -c "from plan_forge import
check; ..."` -- clumsy, no exit-code contract for CI, no discoverable entry.
Q4 do-less candidate: ship only `check`. Rejected: scaffold (T14) is done
and wrapping it is trivial; audit-retroactive is a thin loop over check.
Three commands is cheap and PLAN/SC-8 mandate all three.

## 1. Design principles

### 1.1 main(argv=None) -> int; argparse SystemExit propagates; handlers guarded
- Handlers (`_cmd_check/_cmd_scaffold/_cmd_audit`) return int. `main`
  returns the handler's int (setuptools console_scripts wraps the entry as
  `sys.exit(main())`).
- argparse `--help` and missing/invalid subcommand RAISE SystemExit (0 for
  --help, 2 for usage error) BEFORE any handler runs. This is expected;
  let it propagate -- do not suppress it. Tests use
  `pytest.raises(SystemExit)` for those paths.
- main wraps the HANDLER dispatch in `except Exception -> stderr + return 4`
  so an unexpected bug in api.check/api.scaffold yields a clean exit 4, not
  a traceback. SystemExit is a BaseException (not caught by `except
  Exception`), so argparse's --help/usage exits still propagate correctly.

### 1.2 Exit-code contract (CI-facing; load-bearing)

| code | meaning |
|------|---------|
| 0 | check/audit: verdict PASS; scaffold: file written |
| 1 | check/audit: engineering FAIL or epistemic FAIL |
| 2 | RESERVED by argparse for CLI usage errors -- do not assign |
| 3 | check/audit: epistemic VISION (structurally a vision, not a defect) |
| 4 | runtime/IO error (missing/unreadable file, dir-as-file, scaffold error, unexpected exception) |

Single-verdict mapping (a verdict is computed ONCE by api.check, then
mapped): if engineering==FAIL or epistemic==FAIL -> 1; elif
epistemic==VISION -> 3; else 0. So when a plan triggers both FAIL and
VISION conditions, exit is 1 -- FAIL takes precedence over VISION (this
mirrors the verdict's own FAIL>VISION rule from T13). EngineeringVerdict
is PASS|FAIL only (no VISION value), so there is no engineering==VISION
case to map.

audit-retroactive worst-code rollup across files:
any 4 -> 4; else any 1 -> 1; else any 3 -> 3; else 0.

### 1.3 check command
`plan-forge check <path> [--mechanical-only] [--preamble FILE]`
- Read <path> as text with `encoding="utf-8"`. Map IO problems to stderr +
  exit 4: missing (FileNotFoundError), path-is-a-directory
  (IsADirectoryError), unreadable (PermissionError). Catch `OSError`
  broadly so no IO traceback escapes.
- Any NON-IO exception from api.check (parse / mechanical / epistemic
  errors) is caught by main's except-guard (1.1) and yields exit 4, NOT
  exit 1. A malformed plan is a runtime error, not a verdict.
- llm_clients: default None (bootstrap from env; no creds -> mechanical
  only automatically via the registry). `--mechanical-only` forces
  llm_clients=[].
- `--preamble FILE`: read the file with `encoding="utf-8"` (same OSError ->
  exit 4 handling as the plan path); pass its contents as preamble (F6). If
  the flag is absent, no preamble.
- Print verdict.summary() to stdout; exit per 1.2.
- NOTE: VISION is MECHANICALLY reachable -- G1/G7 structural BLOCKERs route
  to VISION even with llm_clients=[] (verified in T13). So `check
  --mechanical-only` CAN return 3; the vision test in 4.1 is valid.

### 1.4 scaffold command
`plan-forge scaffold <name> [--output-dir DIR]`
- `--output-dir` defaults to the current working directory.
- Call api.scaffold(name, output_dir); print the written Path to stdout;
  exit 0.
- Catch `(ValueError, OSError, RuntimeError)` -> stderr + exit 4.
  ValueError = unsafe name; OSError covers FileExistsError /
  FileNotFoundError / NotADirectoryError / PermissionError; RuntimeError
  covers a missing bundled template.

### 1.5 audit-retroactive command (lightweight batch; the user-facing form)
`plan-forge audit-retroactive <dir> [--mechanical-only]`
- SUBSPEC interpretation: glob `<dir>/*.md` (NON-recursive; case-sensitive
  lowercase `.md` per POSIX glob -- `.MD`/`.mD` are NOT matched), iterate
  in SORTED filename order (deterministic CI output + stable tests), run
  check() on each (read with `encoding="utf-8"`), print one COMPACT line
  per file to STDOUT, then a totals line. Exit = worst-code rollup (1.2).
- per-file line (documented exception to 1.6, NOT Verdict.summary), to
  STDOUT so every file emits exactly one line:
  `{filename}: engineering={E} epistemic={EP}`.
- the per-file loop catches `Exception` PER FILE (not just OSError): on any
  per-file failure print `{filename}: ERROR {message}` (also to stdout, one
  line) and count that file as rollup code 4; the batch CONTINUES (one bad
  plan never aborts the run).
- totals line counts by ROLLUP CODE, not by raw verdict dimension: a file
  that is engineering=FAIL AND epistemic=VISION rolls up to 1 and counts as
  fail, not vision. Format:
  `{n} plans: {p} pass, {f} fail, {v} vision, {e} error` where p/f/v/e =
  count of files whose rollup code is 0 / 1 / 3 / 4 respectively.
- empty dir / no `*.md` -> stdout "no plans found" + exit 0.
- dir missing / not a directory -> stderr + exit 4 (a CLI-level error,
  unlike per-file errors which stay on stdout as part of the batch output).
- NAMING: `audit-retroactive` is fixed by SC-8 (PLAN 1880); keep it. This
  CLI command IS the user-facing batch-audit form -- it is NOT a temporary
  stand-in. `tools/retroactive_audit.py` (skeleton T20, data T34; PLAN
  1845/1859) is a SEPARATE project self-audit producing LESSONS-RETRO.md,
  not a heavier version of this command. No breaking rename is implied.
- `--preamble` is NOT accepted by audit (non-goal): a batch audit applies
  no single orchestrator preamble across heterogeneous plans.

### 1.6 stdout vs stderr; one human format
Verdicts/summaries to stdout (pipeable). CLI-level errors (missing/invalid
arguments, missing plan/dir, unsafe name) go to stderr. `check` uses
Verdict.summary() (T13). `audit` uses the compact per-file line (1.5) --
the single documented exception, because summary() is 7-8 lines and is
unreadable repeated across N files. NOTE: audit's per-file lines, INCLUDING
the `ERROR` lines, all go to stdout (one line per file, so the batch output
is a stable N-line block); only CLI-level errors (dir missing / not a
directory) go to stderr. No --json in v0.1 (non-goal).

## 2. Phase 0: worktree
Created: `.worktrees/feat-t16-cli` off T14 HEAD 3c3d895 (branch
feat-t16-cli). venv set up; baseline confirmed 340 passed, 4 skipped, 0
warnings (count is approximate -- confirm with the baseline run, do not
hardcode-assert it).

## 3. Phase 1: argparse skeleton + dispatch + error guard
- `argparse.ArgumentParser(prog="plan-forge")`, subparsers
  (`dest="command"`, `required=True`).
- three subparsers (check/scaffold/audit-retroactive) with their args
  (1.3-1.5) and help strings.
- `main(argv=None) -> int`: parse, dispatch to a handler inside
  `try/except Exception` (-> stderr + 4), return the handler's int.
### 3.1 tests (tests/unit/test_cli_dispatch.py)
argparse `--help` / missing-subcommand RAISE SystemExit; handlers return
int. Wrap the former in `pytest.raises(SystemExit)`.
- test_top_help_exits_zero: main(["--help"]) -> SystemExit(0).
- test_each_subcommand_help_exits_zero: ["check","--help"] etc -> SystemExit(0).
- test_no_command_errors: main([]) -> SystemExit(2).
- test_unexpected_exception_exits_4: monkeypatch a handler (or api.check)
  to raise RuntimeError; main(["check", somefile]) returns 4, message on
  stderr (proves the except-guard).

## 4. Phase 2: check + scaffold handlers
Implement _cmd_check (1.3) and _cmd_scaffold (1.4).
### 4.1 tests (tests/unit/test_cli_check_scaffold.py; capsys + tmp_path)
- test_check_pass_exit0: well_formed.md, check --mechanical-only -> 0; summary on stdout.
- test_check_fail_exit1: a plan with a BLOCKER -> 1.
- test_check_vision_exit3: a vision plan (G1/G7 absent, External Voices present) --mechanical-only -> 3.
- test_check_missing_file_exit4: nonexistent path -> 4; stderr.
- test_check_dir_as_file_exit4: pass a directory path -> 4; stderr (IsADirectoryError handled).
- test_check_preamble_passes: write a preamble file; check --preamble -> runs, exit per verdict (proves preamble reaches api.check).
- test_check_preamble_missing_exit4: --preamble points at a missing file -> 4; stderr.
- test_scaffold_writes_exit0: scaffold a name with --output-dir tmp -> 0; file exists; path on stdout.
- test_scaffold_default_output_dir: scaffold without --output-dir, cwd=tmp -> file in tmp.
- test_scaffold_existing_exit4: scaffold same name twice -> second returns 4; stderr.
- test_scaffold_unsafe_name_exit4: "../evil" -> 4.

## 5. Phase 3: audit-retroactive handler
Implement _cmd_audit (1.5): glob *.md, check each, compact per-file line +
totals, worst-code rollup; per-file errors -> code 4 contribution.
### 5.1 tests (tests/integration/test_cli_audit.py; tmp_path)
- test_audit_all_pass_exit0: dir with 2 well_formed copies -> 0; 2 lines + totals.
- test_audit_one_fail_exit1: one good + one BLOCKER plan -> 1.
- test_audit_all_vision_exit3: dir with 2 vision-only plans (G1/G7 absent, External Voices present) --mechanical-only -> 3; both count as vision in totals.
- test_audit_empty_dir_exit0: empty dir -> "no plans found"; 0.
- test_audit_missing_dir_exit4: nonexistent dir -> 4; stderr.
- test_audit_ignores_non_md: dir with a .txt and a subdir -> not counted; only *.md audited.
- test_audit_sorted_order: files emitted in sorted filename order (deterministic).
- test_audit_per_file_error_continues: an unparseable .md among good ones -> its line is `ERROR ...` on stdout, rollup code 4, batch still processes the others.
- test_audit_totals_line: assert the totals format `N plans: P pass, F fail, V vision, E error` counted by rollup code.

## 6. Phase 4: review + commit
Three-cycle review THEN smoke THEN commit. (This SUBSPEC was itself
pre-reviewed by deepseek/mimo/kimi.) If multi-model code review does not
converge on this small change, diagnose substance directly (suite green +
scope/ASCII clean) and converge via single-model + human (T13/T14 lesson)
rather than spinning. Commit msg: WHY the CLI exists (CI/batch entry with
an exit-code contract), no AI markers, author Minxi Hou.

## 7. Verification gates
- Full suite green (baseline + new), 0 warnings (confirm count from the run).
- py_compile main.py.
- ASCII clean on changed files (git show + git ls-files --others).
- Scope (git show --name-only, NOT git diff): only
  src/plan_forge/adapters/cli/main.py, tests/unit/test_cli_dispatch.py,
  tests/unit/test_cli_check_scaffold.py, tests/integration/test_cli_audit.py,
  .planning/T16-SUBSPEC.md.
- Console script wires up: `.venv/bin/plan-forge check <plan> --mechanical-only`
  returns the right exit code (entry point resolves).
- Each subcommand `--help` exits 0 (SC-8 partial: 3 of the 5 commands).
- No traceback on any error path (missing file, dir-as-file, missing
  preamble, unsafe name, missing dir): each is a clean stderr + exit 4.

## 8. Alternatives considered
1. argparse (CHOSEN): PLAN-mandated (line 582), stdlib, no new dep.
2. click / typer: nicer UX but a new dependency, and PLAN says argparse.
3. do-less (check only): rejected; scaffold/audit are cheap wrappers.
4. audit-retroactive as the full T34 driver now: rejected -- pulls unbuilt
   corpus/LESSONS machinery into a "basic CLI" task.
5. rename to `audit` (kimi suggestion): rejected -- SC-8 fixes the name
   audit-retroactive; the command is the final user-facing form, not a
   stand-in (see 1.5 NAMING).

## 9. Non-goals
- record-outcome, abandonment-check (T32).
- The project self-audit driver tools/retroactive_audit.py + LESSONS-RETRO
  (skeleton T20, data T34).
- --json / machine-readable output (v0.2).
- skill adapter (adapters/skill).
- recursive directory walk in audit (top-level *.md only in v0.1).
- --preamble for audit-retroactive.

## 10. Hard constraints
1. ASCII only. 2. No AI markers; author Minxi Hou; comments describe
   behaviour. 3. SUBSPEC wins over PLAN; document interpretations with
   `# SUBSPEC interpretation:`. 4. No new dependencies (argparse is stdlib).
5. Phase order; tests green at each phase. 6. READ-ONLY: api.py, scaffold/,
   verdict.py, all checks/*, llm/*. PERMITTED edits: adapters/cli/main.py,
   the three new test files, .planning/T16-SUBSPEC.md.
7. Honour the 1.2 exit-code contract and the 1.1 main/SystemExit rules; no
   error path may emit a traceback. 8. Reuse Verdict.summary() for check;
   audit uses the compact per-file line (1.5) as the sole exception.

## 11. Report-back (< 35 lines)
Files + line counts; total tests + confirm 0 warnings; each of the three
commands `--help` exits 0; exit-code contract verified (PASS/FAIL/VISION/
error each tested, incl. dir-as-file and missing-preamble -> 4); console
script wired (`.venv/bin/plan-forge` runs); audit confirmed lightweight
batch (compact per-file line + totals + worst-code rollup); ASCII + scope
clean. Any SUBSPEC interpretations made.

## 12. Pre-review log (deepseek + mimo + kimi)
Folded in: directory-as-file -> exit 4 (A); missing/unreadable --preamble
-> exit 4 (B); audit compact per-file format vs summary() (C); exit 4 in
audit rollup + per-file IO error contribution (D); FAIL>VISION exit
precedence stated (E); scaffold catch widened to (ValueError, OSError,
RuntimeError) (G); main except-guard -> exit 4 (H); glob case-sensitivity
documented (K); VISION mechanically reachable noted (L); T19 -> T34
reference fix (S); plus output-dir default, non-.md test, totals format,
de-duplicated constraints, dynamic baseline count.
Rejected: rename audit-retroactive to `audit` (kimi) -- SC-8 fixes the
name; command is the final user-facing form, not a stand-in for the T34
project self-audit (see 1.5 NAMING).

Round 2 (re-review of v2): all three models confirmed NO regression and
implementation-ready. Folded 8 clarifications: per-file ERROR line to
stdout (deepseek); added audit exit-3 test (deepseek); api.check internal
exceptions -> exit 4 via the guard, not exit 1 (mimo); totals counted by
rollup code, not raw verdict dimension (kimi); sorted glob iteration
(kimi); encoding="utf-8" on all reads (kimi); per-file loop catches
Exception (kimi); EngineeringVerdict is PASS|FAIL only, stated (kimi). No
blockers remained -- v2 was sound; these pin down behaviour the
implementer would otherwise guess.

## 13. Implementation notes (T16 delivery)

SUBSPEC interpretation (exit 3 reachability): with api.check(llm_clients=[]),
vision_plan.md produces engineering=FAIL + epistemic=VISION because G1/G7
BLOCKERs fail engineering (BLOCKER/HIGH -> engineering FAIL) and also trigger
epistemic VISION. Per 1.2, FAIL>VISION -> exit 1, not 3. Exit 3 requires
engineering=PASS + epistemic=VISION, which is architecturally unreachable via
api.check() because any BLOCKER/HIGH on a vision gate fails engineering too.
Tests for exit 3 (test_check_vision_exit3, test_audit_all_vision_exit3) use
monkeypatched verdicts to prove the mapping works; a separate test
(test_check_vision_plan_fail_beats_vision) verifies the real fixture behaviour.
This does NOT contradict SUBSPEC 1.3's NOTE ("VISION is mechanically
reachable") -- the VISION verdict IS reachable, but exit code 3 is not because
FAIL precedence in the exit mapping.
