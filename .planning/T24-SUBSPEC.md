# T24 SUBSPEC: corpus run lifecycle wire + redact + --corpus-private

Status: implemented.
Depends on: T23 (corpus record/query layer).
Worktree base: feat-t23-corpus-record (c0801f9).
Branch: feat-t24-redact-wire.

## Scope

Six files modified, one file created, one planning document edited:

- MODIFY src/plan_forge/corpus/redact.py  (stub -> compute_plan_hash + redact_plan_text)
- MODIFY src/plan_forge/corpus/record.py  (add redact param; route through redact_mod; widen actual_cost_usd to float | None)
- MODIFY src/plan_forge/api.py            (corpus wiring: env-var gate, importlib.metadata version, start_run/finalize_run, corpus_private param)
- MODIFY src/plan_forge/adapters/cli/main.py  (--corpus-private flag on check + audit-retroactive)
- MODIFY tests/conftest.py               (corpus_engine scope: session -> function)
- NEW    tests/integration/test_corpus_redact.py  (22 tests)
- MODIFY .planning/plan-forge-v0.1-PLAN.md (T24 done-when row only)

NOT in scope: findings/evidence recording into corpus (later tasks), arbitration (T25-T27), G9/G10 (later).

## Key decisions (from 4-model reviewed plan)

D1  T24 = run lifecycle wire + redact only (findings/evidence recording deferred).
D2  Corpus is gated on PLAN_FORGE_CORPUS_URL env var; unset = pure function, no DB touch.
D3  check() gains plan_path + corpus_private params; NO corpus_db_path param.
D4  Verdict.corpus_run_id (field already exists) is filled with the new run_id.
D5  Wire start_run + finalize_run only; findings/evidence wiring is a later task.
D6  CorpusRecorder.__init__(redact=False); redact is a session-level policy flag.
D7  redact.py: compute_plan_hash (single hash source) + redact_plan_text (full omission).
D8  Corpus errors -> warnings.warn; never crash check().
D9  Corpus try/except MUST NOT wrap functional gates (mechanical/epistemic runs).
D10 version via importlib.metadata (avoids circular import); arbitration_mode="off"; cost_cap=0.0; actual_cost=None.
D11 All new imports at module top (no import-outside-toplevel).
D12 conftest corpus_engine -> function-scoped (env-var must not leak across tests).

## Circular import (critical -- do not regress)

Using `from plan_forge import __version__` in api.py causes a circular import:
  __init__.py imports .api first; __version__ is defined after that import.
  Fix: use importlib.metadata.version("plan-forge") in api.py.
Gate: `uv run python -c "import plan_forge"` must succeed.

## Test results

460 passed, 4 skipped in 1.59s (uv run python -m pytest tests/ -q).
New test file: tests/integration/test_corpus_redact.py (22 tests).
