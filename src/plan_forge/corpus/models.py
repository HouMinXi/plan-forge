"""SQLAlchemy ORM models for the plan-forge corpus DB.

Contains the LLMCache model for caching LLM call results.
The 6 corpus outcomes, schema_version) live in a later migration.
outcomes, schema_version) live in a later migration.
outcomes, schema_version).

Dialect-agnostic: all column types use SQLAlchemy generic types
so the same models work on SQLite (default) and Postgres (opt-in).
"""
from __future__ import annotations


from sqlalchemy import Column, DateTime, Index, String
from sqlalchemy import JSON
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.sql import func


class Base(DeclarativeBase):
    pass


class LLMCache(Base):
    """LLM prompt/response cache.

    key: SHA-256 hex digest (64 chars) of cache_key_inputs + provider +
         model + tool_use schema version.
    payload: full LLMResponse as dict; generic JSON maps to JSONB on
             Postgres and TEXT (auto-encoded) on SQLite.
    ttl_class: "canonical" (7 days) / "recent" (24 h) / "never_expire".
    expires_at: None for never_expire; set for others.
    """
    __tablename__ = "llm_cache"

    # Primary key: SHA-256 hex digest
    key = Column(String(64), primary_key=True)
    provider = Column(String(32), nullable=False)
    model = Column(String(64), nullable=False)
    prompt_version = Column(String(32), nullable=False)
    # generic JSON: JSONB on Postgres, TEXT on SQLite
    payload = Column(JSON, nullable=False)
    ttl_class = Column(String(16), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


# Plain b-tree indexes only (no GIN/GiST -- those are PG-specific)
Index("idx_llm_cache_expires_at", LLMCache.expires_at)
Index("idx_llm_cache_provider_model", LLMCache.provider, LLMCache.model)
