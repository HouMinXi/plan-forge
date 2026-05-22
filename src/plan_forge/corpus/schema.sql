-- Human-readable reference for the plan-forge corpus event-sourcing schema.
-- The ORM in models.py is the source of truth; the Alembic migration is the
-- executable snapshot.  Keep all three consistent; schema changes go through a
-- NEW migration.
--
-- 6 tables, append-only event ledger.
-- All tables use INTEGER primary keys (AUTOINCREMENT) except schema_version
-- (TEXT PK, one row, serves as the corpus-integrity marker).

CREATE TABLE schema_version (
    version TEXT PRIMARY KEY,
    applied_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE plan_runs (
    run_id INTEGER PRIMARY KEY AUTOINCREMENT,
    plan_hash TEXT NOT NULL,                  -- sha256(plan_text)[:16]
    plan_text TEXT,                            -- nullable if --corpus-private
    plan_path TEXT,                            -- source path (may be /tmp)
    plan_forge_version TEXT NOT NULL,          -- e.g., "0.1.0"
    arbitration_mode TEXT NOT NULL,
    cost_cap_usd REAL NOT NULL,
    actual_cost_usd REAL,
    started_at TIMESTAMP NOT NULL,
    completed_at TIMESTAMP,
    engineering_verdict TEXT,                  -- "PASS" / "FAIL"
    epistemic_verdict TEXT                     -- "PASS" / "FAIL" / "VISION"
);

CREATE INDEX idx_plan_runs_plan_hash ON plan_runs(plan_hash);

CREATE TABLE findings (
    finding_id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id INTEGER NOT NULL REFERENCES plan_runs(run_id),
    check_id TEXT NOT NULL,                    -- "F1" / "G6.A.mechanical"
    severity TEXT NOT NULL,
    location TEXT NOT NULL,
    message TEXT NOT NULL,
    fix_hint TEXT
);

CREATE INDEX idx_findings_run_id ON findings(run_id);
CREATE INDEX idx_findings_check_id ON findings(check_id);

CREATE TABLE llm_evidence (
    evidence_id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id INTEGER NOT NULL REFERENCES plan_runs(run_id),
    gate_id TEXT NOT NULL,                     -- "G6.B" / "G8.B" / "G10.B"
    target_id TEXT,                            -- SC number / anchor line / etc.
    provider TEXT NOT NULL,
    model TEXT NOT NULL,
    prompt_version TEXT NOT NULL,
    verdict TEXT NOT NULL,                     -- provider's verdict
    reasoning TEXT,
    cited_instances TEXT,                      -- JSON array
    search_evidence TEXT,                      -- JSON array
    tier TEXT,                                  -- T1 / T2 / T3 / T4 (G10 output)
    g10_run BOOLEAN NOT NULL DEFAULT FALSE,
    cost_usd REAL,
    recorded_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_llm_evidence_run_id ON llm_evidence(run_id);
CREATE INDEX idx_llm_evidence_tier ON llm_evidence(tier);

CREATE TABLE arbitrations (
    arbitration_id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id INTEGER NOT NULL REFERENCES plan_runs(run_id),
    finding_id INTEGER REFERENCES findings(finding_id),
    triggered_at TIMESTAMP NOT NULL,
    bundle_text TEXT NOT NULL,                 -- the evidence bundle shown
    human_verdict TEXT CHECK(human_verdict IS NULL OR human_verdict IN (
        'verified', 'unverified', 'deferred', 'abstain'
    )),                                        -- canonical 4-value vocabulary
                                               -- (see bundle.py)
    human_rationale TEXT,
    overrode_llm BOOLEAN,                      -- true if user disagreed
    captured_at TIMESTAMP
);

CREATE INDEX idx_arbitrations_run_id ON arbitrations(run_id);

CREATE TABLE outcomes (
    outcome_id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id INTEGER NOT NULL REFERENCES plan_runs(run_id),
    finding_id INTEGER REFERENCES findings(finding_id),
    outcome_type TEXT NOT NULL CHECK(outcome_type IN (
        'predicted_manifested',
        'predicted_did_not_manifest',
        'unpredicted_occurred',
        'plan_succeeded'
    )),
    outcome_date TIMESTAMP NOT NULL,
    evidence TEXT,                             -- post-hoc evidence (commit/incident)
    recorder TEXT NOT NULL,                    -- who recorded ("Minxi" / CI)
    notes TEXT,
    recorded_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_outcomes_run_id ON outcomes(run_id);
CREATE INDEX idx_outcomes_type ON outcomes(outcome_type);
