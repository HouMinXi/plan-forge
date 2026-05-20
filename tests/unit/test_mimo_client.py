"""Tests for llm/mimo_client.py."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from plan_forge.llm.mimo_client import MimoClient


def _stub_messages_response(content="PASS"):
    block = MagicMock()
    block.text = content
    raw = MagicMock()
    raw.content = [block]
    raw.usage.input_tokens = 10
    raw.usage.output_tokens = 5
    raw.model_dump.return_value = {"stub": True}
    return raw


class TestMimoHealthCheckMock:
    def test_auth_ok_tool_use_ok(self):
        """Both probes succeed -> auth_ok=True, tool_use_ok=True."""
        with patch("plan_forge.llm.mimo_client.anthropic.Anthropic") as mock_cls:
            sdk = MagicMock()
            mock_cls.return_value = sdk
            sdk.messages.create.return_value = _stub_messages_response()
            c = MimoClient(api_key="fake")
            h = c.health_check()
            assert h.auth_ok is True
            assert h.tool_use_ok is True

    def test_tool_use_fail_still_auth_ok(self):
        """Auth probe ok, tool_use probe fails -> auth_ok=True, tool_use_ok=False."""
        with patch("plan_forge.llm.mimo_client.anthropic.Anthropic") as mock_cls:
            sdk = MagicMock()
            mock_cls.return_value = sdk
            sdk.messages.create.side_effect = [
                _stub_messages_response(),  # auth probe
                Exception("no tool_use support"),  # tool probe
            ]
            c = MimoClient(api_key="fake")
            h = c.health_check()
            assert h.auth_ok is True
            assert h.tool_use_ok is False

    def test_auth_fail(self):
        import anthropic as ant
        with patch("plan_forge.llm.mimo_client.anthropic.Anthropic") as mock_cls:
            sdk = MagicMock()
            mock_cls.return_value = sdk
            sdk.messages.create.side_effect = ant.AuthenticationError(
                message="auth", response=MagicMock(), body={}
            )
            c = MimoClient(api_key="bad")
            h = c.health_check()
            assert h.auth_ok is False


class TestMimoCallCaches:
    def test_sdk_called_once_on_cache_hit(self):
        with patch("plan_forge.llm.mimo_client.anthropic.Anthropic") as mock_cls:
            sdk = MagicMock()
            mock_cls.return_value = sdk
            sdk.messages.create.return_value = _stub_messages_response("PASS")

            cache = MagicMock()
            cache.get.side_effect = [None, {"verdict": "PASS", "reasoning": "",
                                             "cited_instances": [], "search_evidence": [],
                                             "cost_usd": 0.0, "raw_response": {}}]
            cache.set.return_value = None

            c = MimoClient(api_key="fake")
            c._cache = cache

            inputs = {"plan": "m", "ttl_class": "canonical", "prompt_version": "v0"}
            c.call("prompt", cache_key_inputs=inputs)
            r2 = c.call("prompt", cache_key_inputs=inputs)
            assert sdk.messages.create.call_count == 1
            assert r2.verdict == "PASS"


@pytest.mark.live
def test_mimo_call_live():
    import os
    key = os.environ.get("PLAN_FORGE_MIMO_API_KEY", "")
    if not key:
        pytest.skip("no mimo credentials")
    c = MimoClient(api_key=key)
    resp = c.call(
        "Say exactly one word: hello",
        cache_key_inputs={"test": "live", "ttl_class": "recent", "prompt_version": "v0"},
    )
    assert resp.verdict.strip() != ""
