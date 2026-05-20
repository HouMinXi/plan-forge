"""Database engine and session factory.

Dual-backend: SQLite default (XDG path) or Postgres opt-in via
PLAN_FORGE_CORPUS_URL env var.  Backend swap is a URL change only.
"""
from __future__ import annotations

import os
from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

_engine = None
_SessionFactory = None


def _default_url() -> str:
    """Resolve corpus DB URL: env var > XDG SQLite default."""
    url = os.environ.get("PLAN_FORGE_CORPUS_URL")
    if url:
        return url
    xdg = os.environ.get("XDG_DATA_HOME", os.path.expanduser("~/.local/share"))
    db_dir = os.path.join(xdg, "plan-forge")
    os.makedirs(db_dir, exist_ok=True)
    return "sqlite:///" + os.path.join(db_dir, "corpus.db")


def get_engine():
    """Return the singleton SQLAlchemy engine, creating it on first call."""
    global _engine, _SessionFactory
    if _engine is None:
        url = _default_url()
        _engine = create_engine(url, pool_pre_ping=True)
        _SessionFactory = sessionmaker(bind=_engine)
    return _engine


def _reset_engine() -> None:
    """Reset singleton state.  Used by test fixtures to swap backends."""
    global _engine, _SessionFactory
    if _engine is not None:
        _engine.dispose()
    _engine = None
    _SessionFactory = None


@contextmanager
def session_scope():
    """Yield a transactional Session; commit on success, rollback on error."""
    get_engine()
    session = _SessionFactory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
