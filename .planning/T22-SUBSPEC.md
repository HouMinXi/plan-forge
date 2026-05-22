# T22 SUBSPEC: corpus_db schema + migration + ORM models (Option C)

Status: implemented (implementation complete; pending three-cycle review).
Depends on: T05 (alembic + 0001_llm_cache), T10 (corpus/db.py engine + env.py +
models.Base). Scope: schema.sql + migration 0002 + 6 ORM models + tests + a
2-line PLAN task-table edit. NO record/query/redact logic (T23). NO db.py edit.

## 1. The 6 tables (authority = PLAN lines 1091-1190; mirror EXACTLY)
schema_version, plan_runs, findings, llm_evidence, arbitrations, outcomes.
Column lists, PKs, FKs, indexes, and the TWO CHECK constraints
(arbitrations.human_verdict IN verified/unverified/deferred/abstain;
outcomes.outcome_type IN the 4 values) are defined there. Do NOT add CHECKs to
any other column (severity/verdict/arbitration_mode are internal enums; see
section 6). Do NOT redesign columns.

## 2. models.py (MODIFY src/plan_forge/corpus/models.py)
- Add 6 ORM classes to the EXISTING `Base` (DeclarativeBase), classic `Column`
  style matching LLMCache. Generic SQLAlchemy types only (Integer, String, Text,
  Boolean, Float, DateTime, JSON, ForeignKey, CheckConstraint, Index) so SQLite
  and Postgres both work.
- Column types must mirror PLAN DDL: run_id Integer PK autoincrement; FKs via
  ForeignKey("plan_runs.run_id") etc.; the 2 CHECKs via CheckConstraint in
  __table_args__; JSON columns (cited_instances, search_evidence) use generic
  JSON (matches LLMCache.payload precedent).
- Also FIX the existing broken docstring at the top of models.py (lines ~4-6 had
  duplicated/garbled fragments). Replaced with a clean one-paragraph docstring.
- Declarations only -- NO methods, NO relationships needed for T22.

## 3. schema.sql (NEW src/plan_forge/corpus/schema.sql)
Raw DDL block from PLAN 1091-1190 verbatim (6 CREATE TABLE + indexes +
the 2 CHECKs). Added a header comment: "AUTHORITATIVE human reference..."

## 4. migration (NEW migrations/versions/0002_corpus_schema.py)
- revision="0002_corpus_schema"; down_revision="0001_llm_cache".
- upgrade(): op.create_table x6 (+ op.create_index) matching models, in FK order
  (schema_version, plan_runs, findings, llm_evidence, arbitrations, outcomes),
  then op.execute("INSERT INTO schema_version (version) VALUES ('1')").
- downgrade(): drop the 6 tables in reverse order.
- Same header/comment style as 0001_llm_cache (human voice, no task tags).

## 5. PLAN task-table edit (.planning/plan-forge-v0.1-PLAN.md)
- T22 row: scope -> "corpus/schema.sql + models.py (6 ORM) + Alembic migration";
  done-when -> "alembic upgrade head creates 6 tables on fresh DB AND alembic
  check passes".
- T23 row: scope -> "corpus/db.py refinements + record.py + query.py +
  redact.py" (removed models.py).
- No other PLAN references assumed "T23 builds models.py" (grep confirmed zero).

## 6. Tests: tests/integration/test_corpus_schema_migration.py
Drives alembic via its Python API against temp DBs (env.py reads
PLAN_FORGE_CORPUS_URL via monkeypatch.setenv or os.environ).
All 7 tests pass as of implementation:
- test_upgrade_creates_six_corpus_tables: after upgrade head, the 6 tables exist
  (plus llm_cache + alembic_version).
- test_schema_version_seeded: schema_version has exactly one row (SC-16 marker
  non-empty, version='1').
- test_alembic_check_passes: after upgrade head, command.check() reports NO drift
  (migration == Base.metadata). THIS is the Option-C guarantee.
- test_human_verdict_check_constraint: arbitrations human_verdict='bogus' raises;
  'verified' and NULL succeed.
- test_outcome_type_check_constraint: outcome_type='bogus' raises; valid passes.
- test_downgrade_removes_corpus_tables_keeps_llm_cache: downgrade to
  0001_llm_cache leaves only llm_cache + alembic_version.
- test_schema_sql_matches_db_tables: parse schema.sql for CREATE TABLE names;
  assert they equal the 6 tables the migration creates (D2 drift guard).

SQLite FK enforcement note: FK *declarations* exist in the ORM and migration but
PRAGMA foreign_keys=ON is not enabled by default (belongs in corpus/db.py, T23).
Tests do not assert FK enforcement by default.

## 7. Non-goals (T22)
- NO record/query/redact logic (T23). NO db.py edit (so NO FK PRAGMA -- T23).
- NO CHECK constraints beyond the two PLAN already specifies.
- NO column redesign. NO new dependencies.

## 8. Known/deferred (record, do not fix here)
- FK enforcement needs PRAGMA foreign_keys=ON in db.py -> T23.
- plan_text bloat (mitigated by nullable + --corpus-private design).
- cost_usd is REAL (precision note only).
- cited_instances/search_evidence are JSON (SQLite stores as TEXT auto-encoded).
- AUTOINCREMENT is SQLite-specific behavior.
- outcome_date NOT NULL.
- findings has no UNIQUE(run_id,check_id,location).
All acceptable for v0.1; noted here, no PLAN schema changes.
