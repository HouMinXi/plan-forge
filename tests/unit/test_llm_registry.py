"""Tests for llm/registry.py (Phase 2)."""
from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

from plan_forge.llm.client import HealthStatus, LLMResponse
from plan_forge.llm.mocks import MockClient
from plan_forge.llm.registry import (
    _REGISTRY,
    get_class,
    list_registered,
    register,
    build_active_list,
    _cached_health,
)


@pytest.fixture(autouse=True)
def clean_registry():
    """Isolate registry state between tests."""
    original = dict(_REGISTRY)
    yield
    _REGISTRY.clear()
    _REGISTRY.update(original)


class TestRegisterDecorator:
    def test_decorator_registers_class(self):
        @register("test_provider_x")
        class FakeClient:
            name = "test_provider_x"
            model = "fake-1"

        assert "test_provider_x" in list_registered()
        assert get_class("test_provider_x") is FakeClient

    def test_list_registered_returns_all(self):
        @register("prov_a")
        class A:
            pass

        @register("prov_b")
        class B:
            pass

        names = list_registered()
        assert "prov_a" in names
        assert "prov_b" in names


class TestBuildActiveList:
    def _make_cache(self, healthy=True):
        """Return a mock CacheBackend that returns no cached health."""
        cache = MagicMock()
        cache.get.return_value = None  # no cached health -> probe
        cache.set.return_value = None
        return cache

    def test_filters_by_auth_ok(self):
        """build_active_list excludes providers whose health_check fails."""
        good_health = HealthStatus(
            auth_ok=True, tool_use_ok=True,
            last_checked=datetime.now(timezone.utc)
        )
        bad_health = HealthStatus(
            auth_ok=False, tool_use_ok=False,
            last_checked=datetime.now(timezone.utc)
        )

        @register("good_prov")
        class GoodClient:
            name = "good_prov"
            model = "good-1"
            def __init__(self, api_key): pass
            def health_check(self): return good_health
            def call(self, prompt, *, tool_use_schema=None, cache_key_inputs):
                return LLMResponse(verdict="ok", reasoning="")

        @register("bad_prov")
        class BadClient:
            name = "bad_prov"
            model = "bad-1"
            def __init__(self, api_key): pass
            def health_check(self): return bad_health
            def call(self, prompt, *, tool_use_schema=None, cache_key_inputs):
                return LLMResponse(verdict="ok", reasoning="")

        creds = MagicMock()
        creds.get_pool.side_effect = lambda p: ["fake-key"] if p in ("good_prov", "bad_prov") else []
        cache = self._make_cache()

        active = build_active_list(credentials=creds, cache=cache)
        active_names = [c.name for c in active]
        assert "good_prov" in active_names
        assert "bad_prov" not in active_names

    def test_skips_providers_without_credentials(self):
        @register("no_creds_prov")
        class NoCreds:
            name = "no_creds_prov"
            model = "nc-1"
            def __init__(self, api_key): pass
            def health_check(self): raise AssertionError("should not be called")
            def call(self, *a, **kw): ...

        creds = MagicMock()
        creds.get_pool.return_value = []  # no credentials
        cache = self._make_cache()

        active = build_active_list(credentials=creds, cache=cache)
        assert all(c.name != "no_creds_prov" for c in active)


class TestCachedHealth:
    def test_uses_cache_when_fresh(self):
        """If cache has a recent health entry, skip the probe."""
        now = datetime.now(timezone.utc)
        cache = MagicMock()
        cache.get.return_value = {
            "auth_ok": True,
            "tool_use_ok": True,
            "last_checked": now.isoformat(),
            "error": None,
        }

        client = MockClient(name="c", responses={})
        health = _cached_health(client, cache)
        assert health.auth_ok is True
        # Client.health_check was NOT called because cache was fresh
        # (MockClient.health_check always returns ok; we just verify
        # cache.set was NOT called since we used the cached value)
        cache.set.assert_not_called()

    def test_probes_when_cache_miss(self):
        """If no cached entry, call client.health_check and cache result."""
        cache = MagicMock()
        cache.get.return_value = None

        client = MockClient(name="c2", responses={})
        health = _cached_health(client, cache)
        assert health.auth_ok is True
        cache.set.assert_called_once()
