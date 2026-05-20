"""LLM response cache backed by the corpus DB (SQLite or Postgres).

TTL classes:
  canonical    -- 7 days  (stable prompts / well-anchored plans)
  recent       -- 24 h   (prompts tied to current-date web search)
  never_expire -- no TTL  (health check results; caller invalidates)

Cache key is a 64-char SHA-256 hex digest computed from cache_key_inputs
+ provider + model + tool_use schema version (see provider clients).
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Protocol

from plan_forge.corpus.db import session_scope
from plan_forge.corpus.models import LLMCache
from sqlalchemy import func as sqlfunc


TTL_SECONDS: dict[str, int | None] = {
    "canonical": 7 * 24 * 3600,
    "recent": 24 * 3600,
    "never_expire": None,
}


class CacheBackend(Protocol):
    """Protocol for cache implementations (allows test doubles)."""

    def get(self, key: str) -> dict | None: ...

    def set(
        self,
        key: str,
        value: dict,
        *,
        provider: str,
        model: str,
        prompt_version: str,
        ttl_class: str,
    ) -> None: ...

    def invalidate(self, key: str) -> None: ...

    def stats(self) -> dict: ...


class SqlAlchemyCacheBackend:
    """Cache backend that stores entries in the corpus DB llm_cache table.

    UPSERT uses session.merge() (dialect-agnostic SELECT+INSERT/UPDATE).
    Cleanup of expired entries happens lazily on read.
    """

    def get(self, key: str) -> dict | None:
        with session_scope() as s:
            row = s.get(LLMCache, key)
            if row is None:
                return None
            if row.expires_at is not None:
                now = datetime.now(timezone.utc)
                exp = row.expires_at
                # SQLite returns naive datetimes; normalize to UTC for comparison.
                if exp.tzinfo is None:
                    exp = exp.replace(tzinfo=timezone.utc)
                if exp < now:
                    s.delete(row)
                    return None
            return row.payload

    def set(
        self,
        key: str,
        value: dict,
        *,
        provider: str,
        model: str,
        prompt_version: str,
        ttl_class: str,
    ) -> None:
        if ttl_class not in TTL_SECONDS:
            raise ValueError(f"unknown ttl_class: {ttl_class!r}")
        seconds = TTL_SECONDS[ttl_class]
        expires_at = (
            (datetime.now(timezone.utc) + timedelta(seconds=seconds))
            if seconds is not None
            else None
        )
        with session_scope() as s:
            # Dialect-agnostic UPSERT: merge does SELECT then INSERT or UPDATE.
            s.merge(
                LLMCache(
                    key=key,
                    provider=provider,
                    model=model,
                    prompt_version=prompt_version,
                    payload=value,
                    ttl_class=ttl_class,
                    expires_at=expires_at,
                )
            )

    def invalidate(self, key: str) -> None:
        with session_scope() as s:
            row = s.get(LLMCache, key)
            if row is not None:
                s.delete(row)

    def stats(self) -> dict:
        now = datetime.now(timezone.utc)
        with session_scope() as s:
            total = s.query(sqlfunc.count(LLMCache.key)).scalar()
            expired = (
                s.query(sqlfunc.count(LLMCache.key))
                .filter(LLMCache.expires_at < now)
                .scalar()
            )
            return {"total": total, "expired": expired}
