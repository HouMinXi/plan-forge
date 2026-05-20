"""Mimo LLM client (Xiaomi MiMo-V2.5-Pro).

Uses an Anthropic-compatible endpoint:
  https://token-plan-cn.xiaomimimo.com/anthropic

Tool_use support is unconfirmed at spec time.  health_check probes;
if tool_use_ok=False, all Mimo evidence is tagged UNCLASSIFIED by
downstream search_vote / T11+ callers (no_search_judgment fallback
per PLAN SC-27 and SUBSPEC 6.4).

Credential path (pass): api/mimo
Env fallback: PLAN_FORGE_MIMO_API_KEY
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone

import anthropic

from plan_forge.llm.cache import SqlAlchemyCacheBackend
from plan_forge.llm.client import HealthStatus, LLMResponse
from plan_forge.llm.registry import register
from plan_forge.llm.tool_use import MIMO_WEB_SEARCH_TOOL

_MIMO_BASE_URL = "https://token-plan-cn.xiaomimimo.com/anthropic"
_MIMO_MODEL = "mimo-v2.5-pro"


def _cache_key(cache_key_inputs: dict, provider: str, model: str,
               tool_schema: dict | None) -> str:
    parts = json.dumps(cache_key_inputs, sort_keys=True)
    parts += provider + model
    parts += json.dumps(tool_schema, sort_keys=True) if tool_schema else "null"
    return hashlib.sha256(parts.encode()).hexdigest()


@register("mimo")
class MimoClient:
    """Mimo provider client (Xiaomi MiMo-V2.5-Pro via Anthropic-compatible SDK).

    Tool_use support probed at health_check time.  If tool_use_ok=False,
    caller should tag evidence as UNCLASSIFIED (no_search_judgment tier).
    """

    name = "mimo"
    model = _MIMO_MODEL

    def __init__(self, api_key: str) -> None:
        # SUBSPEC interpretation: Mimo uses Anthropic-compatible endpoint;
        # discovered from bashrc claude_mimo() function (see env setup notes).
        self._client = anthropic.Anthropic(
            api_key=api_key,
            base_url=_MIMO_BASE_URL,
        )
        self._cache = SqlAlchemyCacheBackend()

    def health_check(self) -> HealthStatus:
        now = datetime.now(timezone.utc)
        try:
            self._client.messages.create(
                model=self.model,
                max_tokens=1,
                messages=[{"role": "user", "content": "ping"}],
            )
        except anthropic.AuthenticationError as exc:
            return HealthStatus(
                auth_ok=False, tool_use_ok=False,
                last_checked=now, error=str(exc)
            )
        except Exception as exc:
            return HealthStatus(
                auth_ok=False, tool_use_ok=False,
                last_checked=now, error=str(exc)
            )

        # Tool-use probe: Mimo may not support tool_use natively.
        # If unsupported, health_check returns auth_ok=True, tool_use_ok=False.
        tool_ok = False  # conservative default; upgraded if probe succeeds
        tool_schema = MIMO_WEB_SEARCH_TOOL or {
            "type": "function",
            "function": {
                "name": "web_search",
                "description": "Search the web.",
                "parameters": {
                    "type": "object",
                    "properties": {"query": {"type": "string"}},
                    "required": ["query"],
                },
            },
        }
        try:
            # Mimo endpoint is Anthropic-compatible but may not recognise
            # function-calling; attempt with a minimal tool schema.
            self._client.messages.create(
                model=self.model,
                max_tokens=5,
                tools=[tool_schema],
                messages=[{"role": "user", "content": "search: test"}],
            )
            tool_ok = True
        except Exception:
            pass

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

        kwargs: dict = {
            "model": self.model,
            "max_tokens": 1024,
            "messages": [{"role": "user", "content": prompt}],
        }
        if tool_use_schema is not None:
            kwargs["tools"] = [tool_use_schema]

        try:
            raw = self._client.messages.create(**kwargs)
        except Exception as exc:
            raise RuntimeError(f"mimo call failed: {exc}") from exc

        verdict = ""
        for block in raw.content:
            if hasattr(block, "text"):
                verdict = block.text
                break

        cost = 0.0
        if hasattr(raw, "usage"):
            cost = (raw.usage.input_tokens * 3 + raw.usage.output_tokens * 15) / 1_000_000

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
