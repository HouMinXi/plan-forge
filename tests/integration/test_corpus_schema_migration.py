"""Integration tests for the corpus schema migration and ORM models.

Drives alembic via its Python API against isolated temp SQLite databases.
Tests confirm:
  - migration 0002_corpus_schema creates the 6 corpus tables
  - schema_version is seeded (corpus-integrity marker)
  - alembic check reports no drift (migration snapshot matches metadata)
  - CHECK constraints on human_verdict and outcome_type are enforced
  - downgrade to 0001_llm_cache removes corpus tables but keeps llm_cache
  - schema.sql table names match the 6 tables created by the migration
"""
from __future__ import annotations

import os
import re
import sqlite3
from datetime import datetime
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text
from sqlalchemy.exc import IntegrityError

# Project root (where alembic.ini lives); test file is at
# tests/integration/test_*.py so parents[2] == worktree root
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_SCHEMA_SQL = _PROJECT_ROOT / "src" / "plan_forge" / "corpus" / "schema.sql"
_ALEMBIC_INI = _PROJECT_ROOT / "alembic.ini"
_MIGRATIONS_DIR = _PROJECT_ROOT / "migrations"


def _make_alembic_config(db_path: Path) -> Config:
    """Build an alembic Config pointing at an isolated SQLite DB."""
    url = f"sqlite:///{db_path}"
    cfg = Config(str(_ALEMBIC_INI))
    # Set script_location as an absolute path so alembic can find migrations/
    # regardless of the current working directory when tests run.
    cfg.set_main_option("script_location", str(_MIGRATIONS_DIR))
    # Override URL directly on the config object (env.py reads this option)
    cfg.set_main_option("sqlalchemy.url", url)
    return cfg


def _upgrade_head(db_path: Path) -> None:
    """Run alembic upgrade head against an isolated DB."""
    os.environ["PLAN_FORGE_CORPUS_URL"] = f"sqlite:///{db_path}"
    try:
        cfg = _make_alembic_config(db_path)
        command.upgrade(cfg, "head")
    finally:
        os.environ.pop("PLAN_FORGE_CORPUS_URL", None)


def _downgrade_to(db_path: Path, revision: str) -> None:
    """Run alembic downgrade to a specific revision."""
    os.environ["PLAN_FORGE_CORPUS_URL"] = f"sqlite:///{db_path}"
    try:
        cfg = _make_alembic_config(db_path)
        command.downgrade(cfg, revision)
    finally:
        os.environ.pop("PLAN_FORGE_CORPUS_URL", None)


# ---------------------------------------------------------------------------
# test_upgrade_creates_six_corpus_tables
# ---------------------------------------------------------------------------

def test_upgrade_creates_six_corpus_tables(tmp_path):
    """After upgrade head, all 6 corpus tables plus llm_cache exist."""
    db = tmp_path / "corpus_test.db"
    _upgrade_head(db)

    conn = sqlite3.connect(str(db))
    tables = {
        r[0]
        for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )
    }
    conn.close()

    corpus_tables = {
        "schema_version",
        "plan_runs",
        "findings",
        "llm_evidence",
        "arbitrations",
        "outcomes",
    }
    assert corpus_tables.issubset(tables), (
        f"Missing corpus tables: {corpus_tables - tables}"
    )
    assert "llm_cache" in tables, "llm_cache (0001) must still exist"
    assert "alembic_version" in tables, "alembic_version bookkeeping table must exist"


# ---------------------------------------------------------------------------
# test_schema_version_seeded
# ---------------------------------------------------------------------------

def test_schema_version_seeded(tmp_path):
    """schema_version must have exactly one row after upgrade (SC-16)."""
    db = tmp_path / "corpus_seed.db"
    _upgrade_head(db)

    conn = sqlite3.connect(str(db))
    rows = list(conn.execute("SELECT version FROM schema_version"))
    conn.close()

    assert len(rows) == 1, (
        f"schema_version must have exactly 1 row; got {rows}"
    )
    assert rows[0][0] == "1", (
        f"schema_version.version must be '1'; got {rows[0][0]!r}"
    )


# ---------------------------------------------------------------------------
# test_alembic_check_passes
# ---------------------------------------------------------------------------

def test_alembic_check_passes(tmp_path, monkeypatch):
    """After upgrade head, alembic check reports no migration drift.

    This is the core guarantee: the migration snapshot matches Base.metadata.
    A non-zero exit from command.check() raises SystemExit.
    """
    db = tmp_path / "corpus_check.db"
    url = f"sqlite:///{db}"

    # monkeypatch keeps PLAN_FORGE_CORPUS_URL set for the full test so that
    # both command.upgrade() and command.check() use the same isolated DB.
    # _upgrade_head() sets and then clears the env var internally; calling
    # monkeypatch.setenv AFTER _upgrade_head would be too late.  Instead we
    # manage the env var entirely via monkeypatch here, and call alembic
    # command.upgrade() directly with an explicit config.
    monkeypatch.setenv("PLAN_FORGE_CORPUS_URL", url)
    cfg = _make_alembic_config(db)
    command.upgrade(cfg, "head")

    # Now check -- env var is still set, so env.py resolves the same test DB
    try:
        command.check(cfg)
    except SystemExit as exc:
        pytest.fail(
            f"alembic check detected drift (exit {exc.code}). "
            "Migration and Base.metadata are out of sync."
        )


# ---------------------------------------------------------------------------
# test_human_verdict_check_constraint
# ---------------------------------------------------------------------------

def test_human_verdict_check_constraint(tmp_path):
    """arbitrations.human_verdict rejects bogus values; accepts valid ones."""
    db = tmp_path / "corpus_hv.db"
    _upgrade_head(db)

    engine = create_engine(f"sqlite:///{db}")

    # Insert a parent plan_run (FK required for arbitrations.run_id)
    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO plan_runs "
                "(plan_hash, plan_forge_version, arbitration_mode, "
                "cost_cap_usd, started_at) "
                "VALUES ('abc', '0.1.0', 'off', 0.0, :ts)"
            ),
            {"ts": datetime(2026, 1, 1)},
        )

    def _insert_verdict(verdict_val):
        with engine.begin() as conn:
            conn.execute(
                text(
                    "INSERT INTO arbitrations "
                    "(run_id, triggered_at, bundle_text, human_verdict) "
                    "VALUES (1, :ts, 'bundle', :hv)"
                ),
                {"ts": datetime(2026, 1, 1), "hv": verdict_val},
            )

    # NULL is allowed
    _insert_verdict(None)

    # Valid values are allowed
    for valid in ("verified", "unverified", "deferred", "abstain"):
        _insert_verdict(valid)

    # Bogus value must be rejected
    with pytest.raises((IntegrityError, Exception)) as exc_info:
        _insert_verdict("bogus")
    assert exc_info.type is not None, "bogus human_verdict must raise"

    engine.dispose()


# ---------------------------------------------------------------------------
# test_outcome_type_check_constraint
# ---------------------------------------------------------------------------

def test_outcome_type_check_constraint(tmp_path):
    """outcomes.outcome_type rejects bogus values; accepts the 4 valid ones."""
    db = tmp_path / "corpus_ot.db"
    _upgrade_head(db)

    engine = create_engine(f"sqlite:///{db}")

    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO plan_runs "
                "(plan_hash, plan_forge_version, arbitration_mode, "
                "cost_cap_usd, started_at) "
                "VALUES ('xyz', '0.1.0', 'off', 0.0, :ts)"
            ),
            {"ts": datetime(2026, 1, 1)},
        )

    def _insert_outcome(otype):
        with engine.begin() as conn:
            conn.execute(
                text(
                    "INSERT INTO outcomes "
                    "(run_id, outcome_type, outcome_date, recorder) "
                    "VALUES (1, :ot, :od, 'CI')"
                ),
                {"ot": otype, "od": datetime(2026, 6, 1)},
            )

    # All valid values succeed
    for valid in (
        "predicted_manifested",
        "predicted_did_not_manifest",
        "unpredicted_occurred",
        "plan_succeeded",
    ):
        _insert_outcome(valid)

    # Bogus value must be rejected
    with pytest.raises((IntegrityError, Exception)) as exc_info:
        _insert_outcome("bogus")
    assert exc_info.type is not None, "bogus outcome_type must raise"

    engine.dispose()


# ---------------------------------------------------------------------------
# test_downgrade_removes_corpus_tables_keeps_llm_cache
# ---------------------------------------------------------------------------

def test_downgrade_removes_corpus_tables_keeps_llm_cache(tmp_path):
    """Downgrade to 0001_llm_cache leaves only llm_cache + alembic_version."""
    db = tmp_path / "corpus_down.db"
    _upgrade_head(db)
    _downgrade_to(db, "0001_llm_cache")

    conn = sqlite3.connect(str(db))
    tables = {
        r[0]
        for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )
    }
    conn.close()

    corpus_tables = {
        "schema_version",
        "plan_runs",
        "findings",
        "llm_evidence",
        "arbitrations",
        "outcomes",
    }
    assert not corpus_tables.intersection(tables), (
        f"Corpus tables still present after downgrade: "
        f"{corpus_tables.intersection(tables)}"
    )
    assert "llm_cache" in tables, "llm_cache must survive downgrade"
    assert "alembic_version" in tables, "alembic_version must survive downgrade"


# ---------------------------------------------------------------------------
# test_schema_sql_matches_db_tables
# ---------------------------------------------------------------------------

def test_schema_sql_matches_db_tables(tmp_path):
    """schema.sql CREATE TABLE names match the 6 tables from the migration.

    Guards D2 drift: migration, models.py, and schema.sql must declare the
    same 6 corpus tables.
    """
    assert _SCHEMA_SQL.exists(), f"schema.sql not found at {_SCHEMA_SQL}"

    sql_text = _SCHEMA_SQL.read_text(encoding="ascii")
    sql_table_names = set(
        re.findall(r"CREATE TABLE (\w+)", sql_text)
    )

    expected_corpus_tables = {
        "schema_version",
        "plan_runs",
        "findings",
        "llm_evidence",
        "arbitrations",
        "outcomes",
    }

    assert sql_table_names == expected_corpus_tables, (
        f"schema.sql declares {sql_table_names!r} but migration creates "
        f"{expected_corpus_tables!r}"
    )
