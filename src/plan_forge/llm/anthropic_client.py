"""Anthropic LLM client.

Uses the first-party anthropic SDK.  Web search is supported via the
built-in web_search_20250305 tool (no custom function-calling needed).

Cache key: SHA-256 of JSON(cache_key_inputs, sort_keys=True)
           + provider name + model + tool_use_schema fingerprint.

Health probe: minimal 3-token call to verify auth; tool_use probe sends
a single-message call with the web_search tool to verify acceptance.
"""
from __future__ import annotations

from datetime import datetime, timezone

import anthropic

from plan_forge.llm.cache import SqlAlchemyCacheBackend
from plan_forge.llm.client import (
    HealthStatus,
    LLMResponse,
    cache_key,
    parse_verdict_response,
)
from plan_forge.llm.credentials import base_url_for
from plan_forge.llm.registry import register
from plan_forge.llm.tool_use import ANTHROPIC_WEB_SEARCH_TOOL


@register("anthropic")
class AnthropicClient:
    """Anthropic provider client (claude-opus-4-7)."""

    name = "anthropic"
    model = "claude-opus-4-7"

    def __init__(self, api_key: str) -> None:
        kwargs: dict = {"api_key": api_key}
        resolved_url = base_url_for("anthropic", None)
        if resolved_url is not None:
            kwargs["base_url"] = resolved_url
        self._client = anthropic.Anthropic(**kwargs)
        self._cache = SqlAlchemyCacheBackend()

    def health_check(self) -> HealthStatus:
        now = datetime.now(timezone.utc)
        # Auth probe: minimal token call
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

        # Tool-use probe: send web_search tool
        tool_ok = True
        try:
            self._client.messages.create(
                model=self.model,
                max_tokens=5,
                tools=[ANTHROPIC_WEB_SEARCH_TOOL],
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
        key = cache_key(cache_key_inputs, self.name, self.model, tool_use_schema)
        cached = self._cache.get(key)
        if cached is not None:
            return LLMResponse(**cached)

        tools = []
        if tool_use_schema is not None:
            tools = [tool_use_schema]
        else:
            tools = [ANTHROPIC_WEB_SEARCH_TOOL]

        kwargs: dict = {
            "model": self.model,
            "max_tokens": 1024,
            "messages": [{"role": "user", "content": prompt}],
        }
        if tools:
            kwargs["tools"] = tools

        try:
            raw = self._client.messages.create(**kwargs)
        except Exception as exc:
            raise RuntimeError(f"anthropic call failed: {exc}") from exc

        raw_text = ""
        web_search_evidence: list[dict] = []
        for block in raw.content:
            if hasattr(block, "text"):
                raw_text = block.text
            elif hasattr(block, "type") and block.type == "web_search_result":
                web_search_evidence.append(
                    {"url": getattr(block, "url", ""), "text": getattr(block, "encrypted_content", "")}
                )

        verdict, reasoning, cited_instances, search_evidence = \
            parse_verdict_response(raw_text)
        # Merge any web_search_result blocks from Anthropic's built-in search
        search_evidence = search_evidence or web_search_evidence

        cost = 0.0
        if hasattr(raw, "usage"):
            cost = (raw.usage.input_tokens * 15 + raw.usage.output_tokens * 75) / 1_000_000

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
