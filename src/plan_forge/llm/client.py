"""Abstract LLM client interface and shared dataclasses.

All provider clients (anthropic, kimi, deepseek, mimo) must satisfy
the LLMClient Protocol.  cache_key_inputs is a dict whose stable
JSON serialization (sort_keys=True) combined with provider + model +
tool_use schema version forms the SHA-256 cache key.
"""
from __future__ import annotations

import hashlib
import json
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


def parse_verdict_response(raw_text: str) -> tuple[str, str, list, list]:
    """Parse the unified JSON verdict convention from LLM output.

    Returns (verdict, reasoning, cited_instances, search_evidence).
    Falls back to (raw_text, "", [], []) if the text is not the
    expected JSON object (back-compat for non-judge prompts).
    """
    text = raw_text.strip()
    # Strip a markdown code fence if the model wrapped its JSON.
    if text.startswith("```"):
        lines = [ln for ln in text.split("\n")
                 if not ln.strip().startswith("```")]
        text = "\n".join(lines).strip()
    try:
        data = json.loads(text)
    except (json.JSONDecodeError, ValueError):
        return raw_text, "", [], []
    if not isinstance(data, dict) or "verdict" not in data:
        return raw_text, "", [], []
    return (
        str(data["verdict"]),
        str(data.get("reason", "")),
        list(data.get("cited_instances") or []),
        list(data.get("search_evidence") or []),
    )


def cache_key(cache_key_inputs: dict, provider: str, model: str,
              tool_schema: dict | None) -> str:
    """Return a 64-char SHA-256 hex cache key for an LLM call.

    Shared by all provider clients so the key algorithm has one source
    of truth.  Stable JSON serialization (sort_keys) of the inputs is
    combined with provider, model, and tool schema.
    """
    parts = json.dumps(cache_key_inputs, sort_keys=True)
    parts += provider + model
    parts += json.dumps(tool_schema, sort_keys=True) if tool_schema else "null"
    return hashlib.sha256(parts.encode()).hexdigest()


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
