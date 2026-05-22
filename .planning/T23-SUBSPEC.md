# T23 SUBSPEC: corpus record/query layer + db.py FK enforcement

Status: implemented (pending three-cycle review).
Depends on: T22 (corpus schema + ORM models + alembic migration).
Worktree base: feat-t22-corpus-schema (d7434ef).
Branch: feat-t23-corpus-record.

## Scope

Three modules + two integration test files + one planning document edit:

- MODIFY src/plan_forge/corpus/record.py  (stub -> CorpusRecorder)
- MODIFY src/plan_forge/corpus/query.py   (stub -> D5 read helpers)
- MODIFY src/plan_forge/corpus/db.py      (+ D6 SQLite FK listener)
- MODIFY src/plan_forge/corpus/__init__.py (+ CorpusRecorder export)
- MODIFY src/plan_forge/verdict.py        (+ evidence_id field; D3)
- NEW    tests/integration/test_corpus_record.py  (19 tests)
- NEW    tests/integration/test_corpus_query.py   (17 tests)
- MODIFY .planning/plan-forge-v0.1-PLAN.md (T23 done-when row only)

NOT in scope: api.py wiring (later), redact (T24), arbitration
(T25-T27), g10 implementation (later), g10 wiring for update_evidence_tier
(later), plan_hash refactor (belongs in T24 redact_plan_text path).

## Ground-truth findings (G-1..G-6)

G-1: ParsedPlan (parser.py:69) has raw_text: str but no plan_path field.
     start_run takes plan_path as a separate parameter.

G-2: LLMEvidence (verdict.py:52-69) has provider, model, verdict, reasoning,
     prompt_version, run_id, cited_instances, search_evidence,
     tier:EvidenceTier=UNCLASSIFIED.  No evidence_id -- D3 adds it.

G-3: Finding (verdict.py:73-88) has check_id, severity:Severity, location,
     message, fix_hint, llm_evidence, evidence_tier_summary.
     severity.value is "BLOCKER"/"HIGH"/"MEDIUM"/"LOW" -> TEXT in DB.

G-4: EvidenceTier values: T1_GOLD="T1", T2_SILVER="T2", T3_BRONZE="T3",
     T4_SUSPECT="T4", UNCLASSIFIED="UNCLASSIFIED".

G-5: ORM column names confirmed in corpus/models.py (T22 output).
     g10_run is Boolean; recorded_at/started_at use server_default;
     cited_instances/search_evidence are JSON columns.

G-6: db.py (T22 output) has get_engine() singleton, session_scope(),
     _reset_engine().  No FK PRAGMA.  D6 adds the listener.

## Decisions (D1-D8)

D1 naming: start_run (not record_plan_run).  Paired with finalize_run as
   open/close lifecycle bracket.  3-model consensus (Kimi/DeepSeek/Mimo).
   PLAN done-when cell updated to reflect this.

D2 redact: CorpusRecorder takes no redact param.  start_run stores
   plan.raw_text verbatim.  T24 adds the redact param + redact_plan_text
   + --corpus-private + the redact=True path.  A redact param T23 cannot
   exercise is a dead arg.

D3 evidence_id: added `evidence_id: int | None = None` to LLMEvidence
   dataclass in verdict.py (optional block after tier; default-factory
   list/dict fields confirmed on all collection fields -- Mimo's
   mutable-default claim is FALSE, ground-truthed at lines 67,68,87,88,
   104,107,108).  record_evidence returns evidence_id AND sets
   ev.evidence_id on the passed object (mirrors run_id backfill pattern).
   3-model consensus chose option A.

D4 append-only enforcement: structural.  CorpusRecorder exposes INSERT-only
   methods plus exactly two controlled UPDATEs:
     finalize_run: sets plan_runs.completed_at/verdicts/actual_cost_usd.
       Idempotent-guard: already-set completed_at -> raise ValueError.
     update_evidence_tier: sets llm_evidence.tier.  3-way monotonic rule
       (Kimi's tighter formulation adopted over DeepSeek/Mimo blanket raise):
         UNCLASSIFIED -> T*    : UPDATE
         T* -> same T*         : no-op (idempotent retry OK)
         T* -> different T*    : raise ValueError (real conflict, bug surfaced)
       Missing evidence_id -> raise ValueError.

D5 query.py surface (minimal, limit-ready): get_run, list_findings,
   list_evidence (tier + gate_id filters), list_outcomes,
   list_arbitrations.  Each takes limit: int | None = None.
   No joins beyond the above; no generic DSL.

D6 FK PRAGMA: SQLite ignores FK constraints unless PRAGMA foreign_keys=ON
   per connection.  connect-event listener registered on SQLite backends
   only (_engine.dialect.name == "sqlite"); Postgres enforces natively.
   Listener is per-connection (survives pool recycle).

D7 CorpusRecorder construction: no-arg.  Methods use db.session_scope()
   (singleton engine).  Tests inject temp DB via PLAN_FORGE_CORPUS_URL +
   db._reset_engine() -- the T22 test pattern.

D8 run_id canonical: record_evidence(run_id, ...) param run_id is
   canonical; written to the DB row and backfilled to evidence.run_id
   regardless of any stale value on the object.  No assert/raise on
   mismatch; param simply wins.

## 3-model review outcome

### Consensus (all three: Kimi / DeepSeek / Mimo)
- D3 = A (add evidence_id to LLMEvidence).  run_id already follows the
  recorder-backfill pattern; evidence_id is consistent, not new.
- D1 = start_run (paired with finalize_run lifecycle bracket).

### Adopted hardening
- Monotonic tier = 3-way (Kimi): U->T* allowed; same value -> no-op;
  different value -> raise ValueError.  Stricter than "already-classified
  -> skip"; surfaces a real conflict instead of swallowing it.
- finalize_run idempotent-guard (Kimi): re-finalizing a run with
  completed_at already set raises ValueError.
- record_evidence run_id conflict (DeepSeek -> D8): param is canonical.
- record_evidence double-backfill (Mimo): set ev.evidence_id AND return it.
- query.py limit-ready (Kimi): each helper takes limit now to avoid a
  breaking change later.
- corpus/__init__.py exports CorpusRecorder (Mimo): stable package-level
  API boundary.

### Rejected (ground-truthed against the code)
- Mimo: "Finding(llm_evidence=[]) is a mutable-default footgun."
  FALSE.  verdict.py uses field(default_factory=list/dict) on ALL six
  collection fields (lines 67,68,87,88,104,107,108).  No bare `= []`
  or `= {}`.  No fix needed.  Same class of error as Kimi asserting
  wrong CHECK values in the T22 review -- an external model asserting a
  defect the code already handles.

### Deferred (record here; do not build in T23)
- FK pre-check before record_evidence: a friendly "run_id not found"
  message instead of the raw IntegrityError.  Costs a SELECT on the hot
  write path; D6 already makes the FK fire.  Add only if a consumer needs
  the better message.
- ORM-level DELETE/UPDATE interceptor: append-only is structural (no
  such methods exist on CorpusRecorder).  Heavy for v0.1.

## Non-goals

- api.py wiring (later task)
- redact.py logic (T24)
- arbitration surface/bundle/capture (T25-T27)
- g10 module implementation (later)
- wiring update_evidence_tier into g10 (later)
- plan_hash refactor into redact_plan_text (T24)
- ORM-level mutation interceptor (deferred above)
