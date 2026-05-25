"""Credential resolvers for LLM provider API keys.

Primary source: pass (Unix password-store) under plan-forge/<provider>/keyN.
Fallback: PLAN_FORGE_<PROVIDER>_API_KEY env var.

ChainedCredentialResolver tries each resolver in order and returns the
first non-empty pool.  FileNotFoundError (pass binary absent) is caught
and treated as empty pool so code works in CI without pass installed.
"""
from __future__ import annotations

import os
import subprocess
from typing import Protocol


class CredentialResolver(Protocol):
    def get_pool(self, provider: str) -> list[str]: ...


class PassCredentialResolver:
    """Read API keys from Unix password-store (pass).

    Expects entries at plan-forge/<provider>/key1, key2, ...
    Returns empty list if pass is not installed or the path is absent.
    """

    def get_pool(self, provider: str) -> list[str]:
        try:
            out = subprocess.run(
                ["pass", "ls", f"plan-forge/{provider}"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if out.returncode != 0:
                return []
            keys: list[str] = []
            for line in out.stdout.splitlines():
                entry = line.strip().lstrip("`- |").strip()
                if entry.startswith("key"):
                    val = subprocess.run(
                        ["pass", "show", f"plan-forge/{provider}/{entry}"],
                        capture_output=True,
                        text=True,
                        timeout=5,
                    )
                    if val.returncode == 0:
                        first_line = val.stdout.strip().splitlines()
                        if first_line:
                            keys.append(first_line[0])
            return keys
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return []


class EnvCredentialResolver:
    """Read a single API key from PLAN_FORGE_<PROVIDER>_API_KEY env var."""

    def get_pool(self, provider: str) -> list[str]:
        envvar = f"PLAN_FORGE_{provider.upper()}_API_KEY"
        val = os.environ.get(envvar, "").strip()
        return [val] if val else []


class ChainedCredentialResolver:
    """Try resolvers in order; return first non-empty pool."""

    def __init__(self, resolvers: list[CredentialResolver]) -> None:
        self.resolvers = resolvers

    def get_pool(self, provider: str) -> list[str]:
        for resolver in self.resolvers:
            pool = resolver.get_pool(provider)
            if pool:
                return pool
        return []


def default_resolver() -> ChainedCredentialResolver:
    """Return the default credential resolver (pass -> env fallback)."""
    return ChainedCredentialResolver(
        [PassCredentialResolver(), EnvCredentialResolver()]
    )


def base_url_for(provider: str, default: str | None) -> str | None:
    """Return PLAN_FORGE_<PROVIDER>_BASE_URL if set, else default.

    An unset or blank env var leaves the caller's default unchanged,
    so existing setups with no override are byte-identical to today.
    """
    v = os.environ.get(
        f"PLAN_FORGE_{provider.upper()}_BASE_URL", ""
    ).strip()
    return v or default
