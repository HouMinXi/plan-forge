"""Tests for llm/anthropic_client.py."""
from __future__ import annotations

from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from plan_forge.llm.anthropic_client import AnthropicClient


def _make_client(mock_cache=None):
    """Return an AnthropicClient with mocked SDK and optional mock cache."""
    with patch("plan_forge.llm.anthropic_client.anthropic.Anthropic"):
        c = AnthropicClient(api_key="fake-key")
    if mock_cache is not None:
        c._cache = mock_cache
    return c


def _stub_messages_response(content="PASS verdict", input_tokens=10, output_tokens=5):
    """Build a minimal anthropic messages response stub."""
    block = MagicMock()
    block.text = content
    raw = MagicMock()
    raw.content = [block]
    raw.usage.input_tokens = input_tokens
    raw.usage.output_tokens = output_tokens
    raw.model_dump.return_value = {"stub": True}
    return raw


class TestAnthropicHealthCheckMock:
    def test_auth_ok_and_tool_use_ok(self):
        """Mock both probes succeeding -> auth_ok=True, tool_use_ok=True."""
        with patch("plan_forge.llm.anthropic_client.anthropic.Anthropic") as mock_cls:
            mock_sdk = MagicMock()
            mock_cls.return_value = mock_sdk
            mock_sdk.messages.create.return_value = MagicMock()

            c = AnthropicClient(api_key="fake")
            h = c.health_check()
            assert h.auth_ok is True
            assert h.tool_use_ok is True
            assert isinstance(h.last_checked, datetime)

    def test_auth_fail_returns_auth_ok_false(self):
        import anthropic as ant
        with patch("plan_forge.llm.anthropic_client.anthropic.Anthropic") as mock_cls:
            mock_sdk = MagicMock()
            mock_cls.return_value = mock_sdk
            mock_sdk.messages.create.side_effect = ant.AuthenticationError(
                message="auth failed", response=MagicMock(), body={}
            )

            c = AnthropicClient(api_key="bad")
            h = c.health_check()
            assert h.auth_ok is False
            assert h.error is not None


class TestAnthropicCallCaches:
    def test_call_uses_cache_on_second_call(self):
        """Second call with same inputs returns cached result; SDK called once."""

        raw = _stub_messages_response("PASS")

        with patch("plan_forge.llm.anthropic_client.anthropic.Anthropic") as mock_cls:
            mock_sdk = MagicMock()
            mock_cls.return_value = mock_sdk
            mock_sdk.messages.create.return_value = raw

            cache = MagicMock()
            cache.get.side_effect = [None, {"verdict": "PASS", "reasoning": "",
                                             "cited_instances": [], "search_evidence": [],
                                             "cost_usd": 0.0, "raw_response": {}}]
            cache.set.return_value = None

            c = AnthropicClient(api_key="fake")
            c._cache = cache

            inputs = {"plan": "x", "ttl_class": "canonical", "prompt_version": "v0"}
            c.call("prompt", cache_key_inputs=inputs)
            r2 = c.call("prompt", cache_key_inputs=inputs)

            assert mock_sdk.messages.create.call_count == 1  # only first call hit SDK
            assert r2.verdict == "PASS"


@pytest.mark.live
def test_anthropic_call_live():
    """Smoke test: real Anthropic call.  Skipped without credentials."""
    import os
    key = os.environ.get("PLAN_FORGE_ANTHROPIC_API_KEY", "")
    if not key:
        pytest.skip("no anthropic credentials")
    c = AnthropicClient(api_key=key)
    resp = c.call(
        "Say exactly one word: hello",
        cache_key_inputs={"test": "live", "ttl_class": "recent", "prompt_version": "v0"},
    )
    assert resp.verdict.strip() != ""
