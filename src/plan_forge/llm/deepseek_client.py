"""DeepSeek LLM client.

Uses the OpenAI-compatible endpoint at https://api.deepseek.com.
Model: deepseek-chat (maps to deepseek-v3 on the API side).

Known limitations (project memory reference_deepseek_compact.md):
  - tool_use has protocol conversion bugs; health_check probes
    at startup and sets tool_use_ok=False if the probe fails.
  - cache_control is ignored (every request retransmits full context).
  - Do NOT use reasoning models with tool_use.

If tool_use_ok=False after health_check, callers
treats DeepSeek evidence as UNCLASSIFIED (no_search_judgment tier).
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone

import openai

from plan_forge.llm.cache import SqlAlchemyCacheBackend
from plan_forge.llm.client import HealthStatus, LLMResponse
from plan_forge.llm.registry import register
from plan_forge.llm.tool_use import DEEPSEEK_WEB_SEARCH_TOOL

_DEEPSEEK_BASE_URL = "https://api.deepseek.com"
_DEEPSEEK_MODEL = "deepseek-chat"


def _cache_key(cache_key_inputs: dict, provider: str, model: str,
               tool_schema: dict | None) -> str:
    parts = json.dumps(cache_key_inputs, sort_keys=True)
    parts += provider + model
    parts += json.dumps(tool_schema, sort_keys=True) if tool_schema else "null"
    return hashlib.sha256(parts.encode()).hexdigest()


@register("deepseek")
class DeepSeekClient:
    """DeepSeek provider client (deepseek-chat via OpenAI-compatible SDK).

    tool_use_ok=False is expected in production due to known protocol bugs;
    health_check documents this at startup so callers can degrade gracefully.
    """

    name = "deepseek"
    model = _DEEPSEEK_MODEL

    def __init__(self, api_key: str) -> None:
        self._client = openai.OpenAI(
            api_key=api_key,
            base_url=_DEEPSEEK_BASE_URL,
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

        # Tool-use probe: expected to fail per project memory.
        # If it passes, great; if not, auth_ok remains True, tool_use_ok=False.
        tool_ok = True
        try:
            self._client.chat.completions.create(
                model=self.model,
                max_tokens=5,
                tools=[DEEPSEEK_WEB_SEARCH_TOOL],
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

        # Attempt tool_use if a schema is given; fall back to plain chat on error.
        messages = [{"role": "user", "content": prompt}]
        raw = None
        if tool_use_schema is not None:
            try:
                raw = self._client.chat.completions.create(
                    model=self.model,
                    max_tokens=1024,
                    tools=[tool_use_schema],
                    messages=messages,
                )
            except Exception:
                raw = None  # fall through to plain chat

        if raw is None:
            try:
                raw = self._client.chat.completions.create(
                    model=self.model,
                    max_tokens=1024,
                    messages=messages,
                )
            except Exception as exc:
                raise RuntimeError(f"deepseek call failed: {exc}") from exc

        choice = raw.choices[0] if raw.choices else None
        verdict = ""
        if choice and choice.message and choice.message.content:
            verdict = choice.message.content

        cost = 0.0
        if hasattr(raw, "usage") and raw.usage:
            cost = (
                raw.usage.prompt_tokens * 1 + raw.usage.completion_tokens * 3
            ) / 1_000_000

        resp = LLMResponse(
            verdict=verdict,
            reasoning="",
            cited_instances=[],
            search_evidence=[],
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
