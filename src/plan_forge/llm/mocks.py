"""Deterministic mock LLM clients for unit tests.

MockClient returns canned responses keyed by prompt substrings.
No real API calls; no cache interaction (tests that need cache
behaviour use the real SqlAlchemyCacheBackend with a test DB).

Usage:
    client = MockClient(name="mock_a", responses={"PASS": pass_resp})
    result = client.call("...PASS...", cache_key_inputs={})
    # -> pass_resp
"""
from __future__ import annotations

from datetime import datetime, timezone

from plan_forge.llm.client import HealthStatus, LLMResponse


class MockClient:
    """Return deterministic responses based on prompt content.

    responses: mapping of substring -> LLMResponse.  First matching
    key wins.  Falls back to a default "unknown" response.
    """

    model = "mock-1"

    def __init__(
        self,
        name: str = "mock",
        responses: dict[str, LLMResponse] | None = None,
        health: HealthStatus | None = None,
    ) -> None:
        self.name = name
        self._responses: dict[str, LLMResponse] = responses or {}
        self._health = health or HealthStatus(
            auth_ok=True,
            tool_use_ok=True,
            last_checked=datetime.now(timezone.utc),
        )

    def health_check(self) -> HealthStatus:
        return self._health

    def call(
        self,
        prompt: str,
        *,
        tool_use_schema: dict | None = None,
        cache_key_inputs: dict,
    ) -> LLMResponse:
        for key, resp in self._responses.items():
            if key in prompt:
                return resp
        return LLMResponse(
            verdict="unknown",
            reasoning="no mock match",
            cited_instances=[],
            search_evidence=[],
            cost_usd=0.0,
            raw_response={},
        )
