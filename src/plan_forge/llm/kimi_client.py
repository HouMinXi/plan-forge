"""Kimi LLM client (Moonshot AI).

Uses the OpenAI-compatible endpoint at https://api.moonshot.ai/v1.
Web search uses OpenAI-style function calling (KIMI_WEB_SEARCH_TOOL).

Known quirk (project memory reference_kimi_api.md): do NOT use
Anthropic cache_control headers -- they are not applicable here.

Model: moonshot-v1-32k (confirmed available 2026-04 per project memory).
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone

import openai

from plan_forge.llm.cache import SqlAlchemyCacheBackend
from plan_forge.llm.client import HealthStatus, LLMResponse, parse_verdict_response
from plan_forge.llm.registry import register
from plan_forge.llm.tool_use import KIMI_WEB_SEARCH_TOOL

_KIMI_BASE_URL = "https://api.moonshot.ai/v1"


def _cache_key(cache_key_inputs: dict, provider: str, model: str,
               tool_schema: dict | None) -> str:
    parts = json.dumps(cache_key_inputs, sort_keys=True)
    parts += provider + model
    parts += json.dumps(tool_schema, sort_keys=True) if tool_schema else "null"
    return hashlib.sha256(parts.encode()).hexdigest()


@register("kimi")
class KimiClient:
    """Kimi provider client (moonshot-v1-32k via OpenAI-compatible SDK)."""

    name = "kimi"
    model = "moonshot-v1-32k"

    def __init__(self, api_key: str) -> None:
        self._client = openai.OpenAI(
            api_key=api_key,
            base_url=_KIMI_BASE_URL,
        )
        self._cache = SqlAlchemyCacheBackend()

    def health_check(self) -> HealthStatus:
        now = datetime.now(timezone.utc)
        try:
            self._client.chat.completions.create(
                model=self.model,
                max_tokens=1,
                messages=[{"role": "user", "content": "ping"}],
            )
        except openai.AuthenticationError as exc:
            return HealthStatus(
                auth_ok=False, tool_use_ok=False,
                last_checked=now, error=str(exc)
            )
        except Exception as exc:
            return HealthStatus(
                auth_ok=False, tool_use_ok=False,
                last_checked=now, error=str(exc)
            )

        # Tool-use probe
        tool_ok = True
        try:
            self._client.chat.completions.create(
                model=self.model,
                max_tokens=5,
                tools=[KIMI_WEB_SEARCH_TOOL],
                messages=[{"role": "user", "content": "search: test"}],
            )
        except Exception:
            tool_ok = False

        return HealthStatus(
            auth_ok=True, tool_use_ok=tool_ok, last_checked=now
        )

    def call(
        self,
        prompt: str,
        *,
        tool_use_schema: dict | None = None,
        cache_key_inputs: dict,
    ) -> LLMResponse:
        key = _cache_key(cache_key_inputs, self.name, self.model, tool_use_schema)
        cached = self._cache.get(key)
        if cached is not None:
            return LLMResponse(**cached)

        schema = tool_use_schema if tool_use_schema is not None else KIMI_WEB_SEARCH_TOOL
        try:
            raw = self._client.chat.completions.create(
                model=self.model,
                max_tokens=1024,
                tools=[schema],
                messages=[{"role": "user", "content": prompt}],
            )
        except Exception as exc:
            raise RuntimeError(f"kimi call failed: {exc}") from exc

        choice = raw.choices[0] if raw.choices else None
        raw_text = ""
        if choice and choice.message and choice.message.content:
            raw_text = choice.message.content

        verdict, reasoning, cited_instances, search_evidence = \
            parse_verdict_response(raw_text)

        cost = 0.0
        if hasattr(raw, "usage") and raw.usage:
            cost = (
                raw.usage.prompt_tokens * 2 + raw.usage.completion_tokens * 8
            ) / 1_000_000

        resp = LLMResponse(
            verdict=verdict,
            reasoning=reasoning,
            cited_instances=cited_instances,
            search_evidence=search_evidence,
            cost_usd=cost,
            raw_response=raw.model_dump() if hasattr(raw, "model_dump") else {},
        )
        ttl = cache_key_inputs.get("ttl_class", "canonical")
        prompt_version = cache_key_inputs.get("prompt_version", "v0")
        self._cache.set(
            key, resp.__dict__,
            provider=self.name, model=self.model,
            prompt_version=prompt_version, ttl_class=ttl,
        )
        return resp
