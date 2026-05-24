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


class TestMimoJsonParse:
    """Verify parse_verdict_response is applied in call()."""

    def test_call_parses_json_verdict(self):
        json_body = '{"verdict": "VERIFIED", "reason": "ok", "cited_instances": [], "search_evidence": []}'
        raw = _stub_messages_response(json_body)
        with patch("plan_forge.llm.mimo_client.anthropic.Anthropic") as mock_cls:
            sdk = MagicMock()
            mock_cls.return_value = sdk
            sdk.messages.create.return_value = raw
            cache = MagicMock()
            cache.get.return_value = None
            cache.set.return_value = None
            c = MimoClient(api_key="fake")
            c._cache = cache
            resp = c.call("prompt", cache_key_inputs={"t": "1"})
            assert resp.verdict == "VERIFIED"
            assert resp.reasoning == "ok"

    def test_call_non_json_fallback(self):
        raw = _stub_messages_response("hello")
        with patch("plan_forge.llm.mimo_client.anthropic.Anthropic") as mock_cls:
            sdk = MagicMock()
            mock_cls.return_value = sdk
            sdk.messages.create.return_value = raw
            cache = MagicMock()
            cache.get.return_value = None
            cache.set.return_value = None
            c = MimoClient(api_key="fake")
            c._cache = cache
            resp = c.call("prompt", cache_key_inputs={"t": "2"})
            assert resp.verdict == "hello"

    def test_call_markdown_fenced_json(self):
        fenced = '```json\n{"verdict":"UNVERIFIED","reason":"bad","cited_instances":[],"search_evidence":[]}\n```'
        raw = _stub_messages_response(fenced)
        with patch("plan_forge.llm.mimo_client.anthropic.Anthropic") as mock_cls:
            sdk = MagicMock()
            mock_cls.return_value = sdk
            sdk.messages.create.return_value = raw
            cache = MagicMock()
            cache.get.return_value = None
            cache.set.return_value = None
            c = MimoClient(api_key="fake")
            c._cache = cache
            resp = c.call("prompt", cache_key_inputs={"t": "3"})
            assert resp.verdict == "UNVERIFIED"
            assert resp.reasoning == "bad"


class TestMimoThinkingControl:
    """Lock the disable_thinking flag and max_tokens=4096 behavior."""

    def test_default_no_thinking_kwarg(self):
        """Default instance: SDK create() kwargs must NOT contain thinking."""
        with patch("plan_forge.llm.mimo_client.anthropic.Anthropic") as m_cls:
            sdk = MagicMock()
            m_cls.return_value = sdk
            sdk.messages.create.return_value = _stub_messages_response()
            cache = MagicMock()
            cache.get.return_value = None
            cache.set.return_value = None
            c = MimoClient(api_key="fake")
            c._cache = cache
            c.call("test", cache_key_inputs={"t": "1"})
            kwargs = sdk.messages.create.call_args.kwargs
            assert "thinking" not in kwargs

    def test_disable_thinking_true_injects_kwarg(self):
        """disable_thinking=True: SDK create() gets thinking disabled."""
        with patch("plan_forge.llm.mimo_client.anthropic.Anthropic") as m_cls:
            sdk = MagicMock()
            m_cls.return_value = sdk
            sdk.messages.create.return_value = _stub_messages_response()
            cache = MagicMock()
            cache.get.return_value = None
            cache.set.return_value = None
            c = MimoClient(api_key="fake", disable_thinking=True)
            c._cache = cache
            c.call("test", cache_key_inputs={"t": "2"})
            kwargs = sdk.messages.create.call_args.kwargs
            assert kwargs["thinking"] == {"type": "disabled"}

    def test_max_tokens_4096(self):
        """All instances: SDK create() uses max_tokens=4096."""
        with patch("plan_forge.llm.mimo_client.anthropic.Anthropic") as m_cls:
            sdk = MagicMock()
            m_cls.return_value = sdk
            sdk.messages.create.return_value = _stub_messages_response()
            cache = MagicMock()
            cache.get.return_value = None
            cache.set.return_value = None
            c = MimoClient(api_key="fake")
            c._cache = cache
            c.call("test", cache_key_inputs={"t": "3"})
            kwargs = sdk.messages.create.call_args.kwargs
            assert kwargs["max_tokens"] == 4096

    def test_cache_key_isolation(self):
        """disable_thinking flag must isolate cache keys."""
        with patch("plan_forge.llm.mimo_client.anthropic.Anthropic") as m_cls:
            sdk = MagicMock()
            m_cls.return_value = sdk
            sdk.messages.create.return_value = _stub_messages_response()

            cache_default = MagicMock()
            cache_default.get.return_value = None
            cache_default.set.return_value = None
            cache_disabled = MagicMock()
            cache_disabled.get.return_value = None
            cache_disabled.set.return_value = None

            inst_default = MimoClient(api_key="x")
            inst_default._cache = cache_default
            inst_disabled = MimoClient(api_key="x", disable_thinking=True)
            inst_disabled._cache = cache_disabled

            inputs = {"plan": "same", "ttl_class": "canonical",
                      "prompt_version": "v0"}
            inst_default.call("test", cache_key_inputs=inputs)
            inst_disabled.call("test", cache_key_inputs=inputs)

            key_default = cache_default.get.call_args.args[0]
            key_disabled = cache_disabled.get.call_args.args[0]
            assert key_default != key_disabled


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
