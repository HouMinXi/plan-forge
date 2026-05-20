"""Tests for llm/cache.py and corpus/db.py."""
from __future__ import annotations


import pytest
from sqlalchemy.orm import Session

from plan_forge.corpus.models import LLMCache
from plan_forge.llm.cache import SqlAlchemyCacheBackend, TTL_SECONDS


class TestSqlAlchemyCacheBackend:
    """Uses corpus_engine fixture for an isolated per-session SQLite DB."""

    @pytest.fixture(autouse=True)
    def _setup_backend(self, corpus_engine, clean_cache):
        self.backend = SqlAlchemyCacheBackend()

    def test_set_and_get(self):
        self.backend.set(
            "k1", {"hello": "world"},
            provider="test", model="m1",
            prompt_version="v0", ttl_class="recent",
        )
        result = self.backend.get("k1")
        assert result == {"hello": "world"}

    def test_get_missing_returns_none(self):
        assert self.backend.get("nonexistent") is None

    def test_invalidate_removes_entry(self):
        self.backend.set("k2", {"x": 1}, provider="p", model="m",
                         prompt_version="v0", ttl_class="canonical")
        self.backend.invalidate("k2")
        assert self.backend.get("k2") is None

    def test_invalidate_nonexistent_noop(self):
        self.backend.invalidate("does-not-exist")  # must not raise

    def test_unknown_ttl_class_raises(self):
        with pytest.raises(ValueError, match="unknown ttl_class"):
            self.backend.set("k3", {}, provider="p", model="m",
                             prompt_version="v0", ttl_class="bogus")

    def test_never_expire_has_no_expires_at(self, corpus_engine):
        self.backend.set("k4", {"d": 1}, provider="p", model="m",
                         prompt_version="v0", ttl_class="never_expire")
        with Session(corpus_engine) as s:
            row = s.get(LLMCache, "k4")
            assert row is not None
            assert row.expires_at is None

    def test_stats_total_and_expired(self):
        self.backend.set("k5", {}, provider="p", model="m",
                         prompt_version="v0", ttl_class="canonical")
        stats = self.backend.stats()
        assert stats["total"] >= 1
        assert isinstance(stats["expired"], int)

    def test_merge_upsert_updates_existing(self):
        """Second set() on same key overwrites payload."""
        self.backend.set("k6", {"v": 1}, provider="p", model="m",
                         prompt_version="v0", ttl_class="canonical")
        self.backend.set("k6", {"v": 2}, provider="p", model="m",
                         prompt_version="v0", ttl_class="canonical")
        result = self.backend.get("k6")
        assert result == {"v": 2}


class TestTTLSeconds:
    def test_canonical_is_7_days(self):
        assert TTL_SECONDS["canonical"] == 7 * 24 * 3600

    def test_recent_is_24_hours(self):
        assert TTL_SECONDS["recent"] == 24 * 3600

    def test_never_expire_is_none(self):
        assert TTL_SECONDS["never_expire"] is None
