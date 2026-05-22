# T21 SUBSPEC: Adapter A v0.1.0-alpha2 (pre-corpus integration)

Status: draft for subagent implementation.
Depends on: T13 (check core), T15 (library exports).
Scope: version bump + public-API lock test. check() is ALREADY complete; do not
change it.

## 1. Version bump (two files, MUST match)
- src/plan_forge/__init__.py:  __version__ = "0.1.0a1"  ->  "0.1.0a2"
- pyproject.toml:              version = "0.1.0a1"      ->  "0.1.0a2"
(Confirmed: no existing test asserts the old version, so nothing else breaks.
The new test in section 3 will guard the new value going forward.)

## 2. Exports -- confirm, do NOT expand
Current __all__ = ["check", "scaffold", "Verdict", "Finding", "Severity"] is
complete for alpha2. Do NOT add corpus params, hooks, or new exports (no T22
consumer exists yet -- see plan section 1 do-less).

## 3. Tests: tests/unit/test_library_api.py (new)
- test_version_is_alpha2: import plan_forge; assert plan_forge.__version__ ==
  "0.1.0a2".
- test_public_surface_importable: `from plan_forge import check, scaffold,
  Verdict, Finding, Severity` all succeed; assert plan_forge.__all__ equals the
  expected 5-name list.
- test_check_returns_verdict_mechanical_only: load tests/fixtures/g1_pass.md,
  call check(text, llm_clients=[]) (empty list -> mechanical-only, no network),
  assert the result is a Verdict and has engineering / epistemic / findings
  attributes. (Using llm_clients=[] keeps the test offline and deterministic.)

## 4. Non-goals (T21)
- Do NOT modify api.check() / api.py logic.
- Do NOT add corpus integration anything.
- Do NOT add dependencies.
