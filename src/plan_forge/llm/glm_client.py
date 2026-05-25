"""GLM (Zhipu) LLM client.

Uses an Anthropic-compatible endpoint:
  https://open.bigmodel.cn/api/anthropic

Override the endpoint via PLAN_FORGE_GLM_BASE_URL (e.g. to point at the
local 429-retry proxy on :18889). The credential is PLAN_FORGE_GLM_API_KEY;
the user sources it from pass at api/zhipu/api-key.

Tool_use is not sent: the Zhipu Anthropic-compatible endpoint does not
expose a web-search tool, matching the existing MiMo client behavior.
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

_GLM_DEFAULT_BASE_URL = "https://open.bigmodel.cn/api/anthropic"
_GLM_MODEL = "glm-5.1"


@register("glm")
class GlmClient:
    """GLM provider client (Zhipu GLM-5.1 via Anthropic-compatible SDK).

    No web-search tool is declared: the Zhipu Anthropic endpoint does
    not support web search, so all GLM evidence is tagged UNCLASSIFIED
    (no_search_judgment fallback) when a search verdict would be expected.
    """

    name = "glm"
    model = _GLM_MODEL

    def __init__(self, api_key: str) -> None:
        self._client = anthropic.Anthropic(
            api_key=api_key,
            base_url=base_url_for("glm", _GLM_DEFAULT_BASE_URL),
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
                last_checked=now, error=str(exc),
            )
        except Exception as exc:
            return HealthStatus(
                auth_ok=False, tool_use_ok=False,
                last_checked=now, error=str(exc),
            )

        # No tool-use probe: the endpoint does not support web_search.
        return HealthStatus(
            auth_ok=True, tool_use_ok=False, last_checked=now
        )

    def call(
        self,
        prompt: str,
        *,
        tool_use_schema: dict | None = None,
        cache_key_inputs: dict,
    ) -> LLMResponse:
        key = cache_key(
            cache_key_inputs, self.name, self.model, tool_use_schema
        )
        cached = self._cache.get(key)
        if cached is not None:
            return LLMResponse(**cached)

        kwargs: dict = {
            "model": self.model,
            "max_tokens": 4096,
            "messages": [{"role": "user", "content": prompt}],
        }
        # tool_use_schema is accepted for interface compatibility but not
        # forwarded: the endpoint does not support web_search.

        try:
            raw = self._client.messages.create(**kwargs)
        except Exception as exc:
            raise RuntimeError(f"glm call failed: {exc}") from exc

        raw_text = ""
        for block in raw.content:
            if hasattr(block, "text"):
                raw_text = block.text
                break

        verdict, reasoning, cited_instances, search_evidence = \
            parse_verdict_response(raw_text)

        cost = 0.0
        if hasattr(raw, "usage"):
            cost = (
                raw.usage.input_tokens * 3
                + raw.usage.output_tokens * 15
            ) / 1_000_000

        resp = LLMResponse(
            verdict=verdict,
            reasoning=reasoning,
            cited_instances=cited_instances,
            search_evidence=search_evidence,
            cost_usd=cost,
            raw_response=(
                raw.model_dump() if hasattr(raw, "model_dump") else {}
            ),
        )
        ttl = cache_key_inputs.get("ttl_class", "canonical")
        prompt_version = cache_key_inputs.get("prompt_version", "v0")
        self._cache.set(
            key, resp.__dict__,
            provider=self.name, model=self.model,
            prompt_version=prompt_version, ttl_class=ttl,
        )
        return resp
