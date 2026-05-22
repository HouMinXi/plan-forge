"""Shared pytest fixtures for plan-forge tests.

Fixtures provided:
  corpus_engine   -- function-scoped SQLAlchemy engine (SQLite by default);
                     isolates tests from the user corpus DB.
  clean_cache     -- function-scoped: deletes all llm_cache rows before test.
  postgres_engine -- session-scoped, constructed only when
                     PLAN_FORGE_TEST_POSTGRES_URL is set; tests skip otherwise.
  has_<provider>_credentials -- functions that return bool; used by live
                     test discovery in pytest_collection_modifyitems.

Custom markers registered in pyproject.toml [tool.pytest.ini_options]:
  live     -- real API calls; requires provider credentials
  postgres -- requires running Postgres (PLAN_FORGE_TEST_POSTGRES_URL)
"""
from __future__ import annotations

import os
import subprocess

import pytest
from sqlalchemy import create_engine

from plan_forge.corpus.db import _reset_engine
from plan_forge.corpus.models import Base, LLMCache


# ---------------------------------------------------------------------------
# Credential scanner (used at collection time)
# ---------------------------------------------------------------------------

def _has_env_key(provider: str) -> bool:
    val = os.environ.get(f"PLAN_FORGE_{provider.upper()}_API_KEY", "").strip()
    return bool(val)


def _has_pass_key(provider: str) -> bool:
    try:
        result = subprocess.run(
            ["pass", "ls", f"plan-forge/{provider}"],
            capture_output=True, text=True, timeout=5,
        )
        return result.returncode == 0 and "key" in result.stdout
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def _scan_credentials() -> dict[str, bool]:
    """Return {provider: has_creds} for all known providers."""
    providers = ["anthropic", "kimi", "deepseek", "mimo"]
    return {
        p: _has_env_key(p) or _has_pass_key(p)
        for p in providers
    }


def _provider_from_test(item) -> str:
    """Guess provider name from test module name (test_<provider>_client.py)."""
    mod = item.module.__name__  # e.g. tests.unit.test_kimi_client
    for p in ("anthropic", "kimi", "deepseek", "mimo"):
        if p in mod:
            return p
    return "unknown"


def pytest_collection_modifyitems(config, items):
    """Skip live tests for providers without credentials."""
    has_creds = _scan_credentials()
    for item in items:
        if "live" in item.keywords:
            provider = _provider_from_test(item)
            if not has_creds.get(provider, False):
                item.add_marker(
                    pytest.mark.skip(reason=f"no {provider} credentials")
                )


# ---------------------------------------------------------------------------
# corpus_engine: per-session SQLite in tmp dir; avoids polluting user corpus
# ---------------------------------------------------------------------------

@pytest.fixture(scope="function")
def corpus_engine(tmp_path_factory):
    """Function-scoped engine pointing to an isolated test SQLite DB.

    Creates the schema via Base.metadata.create_all (faster than alembic).
    Resets the singleton after the test so the env var does not leak
    across tests (env-var must not persist between check() calls that
    test corpus-off behavior).
    """
    test_db = tmp_path_factory.mktemp("corpus") / "test_corpus.db"
    url = f"sqlite:///{test_db}"

    # Temporarily set env var so db.py singleton uses this URL
    original = os.environ.get("PLAN_FORGE_CORPUS_URL")
    os.environ["PLAN_FORGE_CORPUS_URL"] = url
    _reset_engine()

    engine = create_engine(url)
    # Create schema directly (faster than invoking alembic subprocess)
    Base.metadata.create_all(engine)

    yield engine

    engine.dispose()
    _reset_engine()
    if original is not None:
        os.environ["PLAN_FORGE_CORPUS_URL"] = original
    else:
        os.environ.pop("PLAN_FORGE_CORPUS_URL", None)


# ---------------------------------------------------------------------------
# clean_cache: wipe llm_cache rows before each test that requests it
# ---------------------------------------------------------------------------

@pytest.fixture
def clean_cache(corpus_engine):
    """Delete all llm_cache rows before the test.  Dialect-agnostic DELETE."""
    from sqlalchemy.orm import Session
    with Session(corpus_engine) as session:
        # Use session.query().delete() -- dialect-agnostic (no TRUNCATE)
        session.query(LLMCache).delete()
        session.commit()
    yield


# ---------------------------------------------------------------------------
# postgres_engine: optional; only when PLAN_FORGE_TEST_POSTGRES_URL is set
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def postgres_engine():
    """Session-scoped Postgres engine.

    Skipped unless PLAN_FORGE_TEST_POSTGRES_URL is set.  Tests marked
    with @pytest.mark.postgres use this fixture to verify dual-backend
    parity.
    """
    url = os.environ.get("PLAN_FORGE_TEST_POSTGRES_URL")
    if not url:
        pytest.skip("PLAN_FORGE_TEST_POSTGRES_URL not set")

    engine = create_engine(url)
    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()
