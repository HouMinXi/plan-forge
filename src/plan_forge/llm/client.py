"""Abstract LLM client interface and shared dataclasses.

All provider clients (anthropic, kimi, deepseek, mimo) must satisfy
the LLMClient Protocol.  cache_key_inputs is a dict whose stable
JSON serialization (sort_keys=True) combined with provider + model +
tool_use schema version forms the SHA-256 cache key.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Protocol, runtime_checkable


@dataclass
class HealthStatus:
    """Result of a provider health-check probe."""
    auth_ok: bool
    tool_use_ok: bool
    last_checked: datetime
    error: str | None = None


@dataclass
class LLMResponse:
    """Normalised response from a single provider call."""
    verdict: str                    # provider-specific verdict text
    reasoning: str
    cited_instances: list[dict] = field(default_factory=list)
    search_evidence: list[dict] = field(default_factory=list)
    cost_usd: float = 0.0
    raw_response: dict = field(default_factory=dict)  # provider native, for debug


@runtime_checkable
class LLMClient(Protocol):
    """Protocol every provider client must satisfy."""

    name: str    # "anthropic" / "kimi" / "deepseek" / "mimo"
    model: str

    def health_check(self) -> HealthStatus: ...

    def call(
        self,
        prompt: str,
        *,
        tool_use_schema: dict | None = None,
        cache_key_inputs: dict,
    ) -> LLMResponse: ...
