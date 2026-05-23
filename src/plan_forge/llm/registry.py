"""Provider registry: plug-in registration and active-list construction.

Providers register at module import via the @register("name") decorator.
build_active_list() filters to providers with credentials AND passing
health check (auth_ok=True).

Health check results are cached in llm_cache with key
"health:<provider>:<model>" using ttl_class="never_expire".  The cache
entry is invalidated only by explicit invalidate() calls.  A staleness
check at read time triggers a fresh probe: 7 days for successful checks
(auth_ok=True), 1 hour for failed checks (auth_ok=False).

Note: _cached_health logic kept here (< 30 lines); no separate health.py.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Type

from plan_forge.llm.client import HealthStatus, LLMClient


_REGISTRY: dict[str, Type] = {}


def register(name: str):
    """Class decorator that registers a provider client class."""
    def deco(cls):
        _REGISTRY[name] = cls
        return cls
    return deco


def list_registered() -> list[str]:
    """Return names of all registered providers."""
    return list(_REGISTRY.keys())


def get_class(name: str) -> Type:
    """Return the class registered under name; raises KeyError if absent."""
    return _REGISTRY[name]


def build_active_list(
    credentials=None,
    cache=None,
) -> list[LLMClient]:
    """Instantiate clients for providers with credentials AND auth_ok=True.

    Providers with auth_ok=False are excluded from the active list.
    Providers with auth_ok=True but tool_use_ok=False are included; callers
    may tag their evidence as UNCLASSIFIED.

    credentials: CredentialResolver (default: pass -> env chain)
    cache: CacheBackend (default: SqlAlchemyCacheBackend)
    """
    from plan_forge.llm.credentials import default_resolver
    from plan_forge.llm.cache import SqlAlchemyCacheBackend

    creds = credentials if credentials is not None else default_resolver()
    backend = cache if cache is not None else SqlAlchemyCacheBackend()

    active: list[LLMClient] = []
    for name, cls in _REGISTRY.items():
        pool = creds.get_pool(name)
        if not pool:
            continue
        client = cls(api_key=pool[0])  # v0.1: first key; v0.2: round-robin
        health = _cached_health(client, backend)
        if health.auth_ok:
            active.append(client)
    return active


def _cached_health(client: LLMClient, cache) -> HealthStatus:
    """Return cached health status if still fresh; else probe and cache.

    Fresh window: 7 days for auth_ok=True, 1 hour for auth_ok=False.
    """
    key = f"health:{client.name}:{client.model}"
    cached = cache.get(key)
    if cached:
        last_str = cached.get("last_checked", "")
        try:
            last = datetime.fromisoformat(last_str)
        except (ValueError, TypeError):
            last = None
        if last is not None:
            # Normalise naive -> UTC (SQLite stores without tz)
            if last.tzinfo is None:
                last = last.replace(tzinfo=timezone.utc)
            max_age = (
                timedelta(days=7)
                if cached.get("auth_ok")
                else timedelta(hours=1)
            )
            if datetime.now(timezone.utc) - last < max_age:
                return HealthStatus(
                    auth_ok=cached["auth_ok"],
                    tool_use_ok=cached["tool_use_ok"],
                    last_checked=last,
                    error=cached.get("error"),
                )
    fresh = client.health_check()
    cache.set(
        key,
        {
            "auth_ok": fresh.auth_ok,
            "tool_use_ok": fresh.tool_use_ok,
            "last_checked": fresh.last_checked.isoformat(),
            "error": fresh.error,
        },
        provider=client.name,
        model=client.model,
        prompt_version="health_v1",
        ttl_class="never_expire",
    )
    return fresh
