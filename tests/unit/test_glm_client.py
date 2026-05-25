"""Tests for llm/glm_client.py."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from plan_forge.llm.glm_client import GlmClient, _GLM_DEFAULT_BASE_URL


def _stub_messages_response(content="PASS"):
    block = MagicMock()
    block.text = content
    raw = MagicMock()
    raw.content = [block]
    raw.usage.input_tokens = 10
    raw.usage.output_tokens = 5
    raw.model_dump.return_value = {"stub": True}
    return raw


class TestGlmBaseUrlOverride:
    """base_url_for propagates correctly to the Anthropic SDK constructor."""

    def test_override_propagates_to_sdk(self, monkeypatch):
        monkeypatch.setenv(
            "PLAN_FORGE_GLM_BASE_URL",
            "http://127.0.0.1:18889/api/anthropic",
        )
        with patch(
            "plan_forge.llm.glm_client.anthropic.Anthropic"
        ) as mock_cls:
            GlmClient(api_key="fake-key")
            _, kwargs = mock_cls.call_args
            assert kwargs["base_url"] == "http://127.0.0.1:18889/api/anthropic"

    def test_unset_uses_default(self, monkeypatch):
        monkeypatch.delenv("PLAN_FORGE_GLM_BASE_URL", raising=False)
        with patch(
            "plan_forge.llm.glm_client.anthropic.Anthropic"
        ) as mock_cls:
            GlmClient(api_key="fake-key")
            _, kwargs = mock_cls.call_args
            assert kwargs["base_url"] == _GLM_DEFAULT_BASE_URL


class TestGlmRegistration:
    """@register("glm") makes the provider discoverable."""

    def test_glm_in_registry(self):
        from plan_forge.llm.registry import _REGISTRY
        assert "glm" in _REGISTRY

    def test_build_active_list_includes_glm(self):
        with patch(
            "plan_forge.llm.glm_client.anthropic.Anthropic"
        ) as mock_cls:
            sdk = MagicMock()
            mock_cls.return_value = sdk
            sdk.messages.create.return_value = _stub_messages_response()

            creds = MagicMock()
            creds.get_pool.side_effect = (
                lambda p: ["fake-glm-key"] if p == "glm" else []
            )
            cache = MagicMock()
            cache.get.return_value = None
            cache.set.return_value = None

            from plan_forge.llm.registry import build_active_list
            active = build_active_list(credentials=creds, cache=cache)
            names = [c.name for c in active]
            assert "glm" in names

    def test_build_active_list_excludes_glm_on_auth_failure(self):
        import anthropic as ant
        with patch(
            "plan_forge.llm.glm_client.anthropic.Anthropic"
        ) as mock_cls:
            sdk = MagicMock()
            mock_cls.return_value = sdk
            sdk.messages.create.side_effect = ant.AuthenticationError(
                message="auth", response=MagicMock(), body={}
            )

            creds = MagicMock()
            creds.get_pool.side_effect = (
                lambda p: ["bad-key"] if p == "glm" else []
            )
            cache = MagicMock()
            cache.get.return_value = None
            cache.set.return_value = None

            from plan_forge.llm.registry import build_active_list
            active = build_active_list(credentials=creds, cache=cache)
            names = [c.name for c in active]
            assert "glm" not in names


class TestGlmNoWebSearchTool:
    """GLM must not send a tool_use_schema to the Anthropic SDK."""

    def test_call_without_tool_schema(self):
        with patch(
            "plan_forge.llm.glm_client.anthropic.Anthropic"
        ) as mock_cls:
            sdk = MagicMock()
            mock_cls.return_value = sdk
            sdk.messages.create.return_value = _stub_messages_response()
            cache = MagicMock()
            cache.get.return_value = None
            cache.set.return_value = None
            c = GlmClient(api_key="fake")
            c._cache = cache
            c.call("prompt", cache_key_inputs={"t": "1"})
            kwargs = sdk.messages.create.call_args.kwargs
            assert "tools" not in kwargs

    def test_call_with_tool_schema_still_omits_tools(self):
        """Even when caller passes tool_use_schema, GLM must not forward it."""
        with patch(
            "plan_forge.llm.glm_client.anthropic.Anthropic"
        ) as mock_cls:
            sdk = MagicMock()
            mock_cls.return_value = sdk
            sdk.messages.create.return_value = _stub_messages_response()
            cache = MagicMock()
            cache.get.return_value = None
            cache.set.return_value = None
            c = GlmClient(api_key="fake")
            c._cache = cache
            tool = {"name": "web_search", "input_schema": {}}
            c.call("prompt", tool_use_schema=tool, cache_key_inputs={"t": "2"})
            kwargs = sdk.messages.create.call_args.kwargs
            assert "tools" not in kwargs

    def test_health_check_tool_use_ok_false(self):
        """health_check always returns tool_use_ok=False for GLM."""
        with patch(
            "plan_forge.llm.glm_client.anthropic.Anthropic"
        ) as mock_cls:
            sdk = MagicMock()
            mock_cls.return_value = sdk
            sdk.messages.create.return_value = _stub_messages_response()
            c = GlmClient(api_key="fake")
            h = c.health_check()
            assert h.auth_ok is True
            assert h.tool_use_ok is False


class TestGlmHealthCheck:
    def test_auth_fail(self):
        import anthropic as ant
        with patch(
            "plan_forge.llm.glm_client.anthropic.Anthropic"
        ) as mock_cls:
            sdk = MagicMock()
            mock_cls.return_value = sdk
            sdk.messages.create.side_effect = ant.AuthenticationError(
                message="auth", response=MagicMock(), body={}
            )
            c = GlmClient(api_key="bad")
            h = c.health_check()
            assert h.auth_ok is False
            assert h.tool_use_ok is False

    def test_generic_exception_returns_auth_false(self):
        with patch(
            "plan_forge.llm.glm_client.anthropic.Anthropic"
        ) as mock_cls:
            sdk = MagicMock()
            mock_cls.return_value = sdk
            sdk.messages.create.side_effect = RuntimeError("timeout")
            c = GlmClient(api_key="fake")
            h = c.health_check()
            assert h.auth_ok is False


class TestGlmCallCaches:
    def test_sdk_called_once_on_cache_hit(self):
        with patch(
            "plan_forge.llm.glm_client.anthropic.Anthropic"
        ) as mock_cls:
            sdk = MagicMock()
            mock_cls.return_value = sdk
            sdk.messages.create.return_value = _stub_messages_response("PASS")

            cache = MagicMock()
            cache.get.side_effect = [
                None,
                {
                    "verdict": "PASS", "reasoning": "",
                    "cited_instances": [], "search_evidence": [],
                    "cost_usd": 0.0, "raw_response": {},
                },
            ]
            cache.set.return_value = None

            c = GlmClient(api_key="fake")
            c._cache = cache

            inputs = {
                "plan": "m", "ttl_class": "canonical", "prompt_version": "v0"
            }
            c.call("prompt", cache_key_inputs=inputs)
            r2 = c.call("prompt", cache_key_inputs=inputs)
            assert sdk.messages.create.call_count == 1
            assert r2.verdict == "PASS"


class TestGlmJsonParse:
    def test_call_parses_json_verdict(self):
        body = (
            '{"verdict": "VERIFIED", "reason": "ok",'
            ' "cited_instances": [], "search_evidence": []}'
        )
        raw = _stub_messages_response(body)
        with patch(
            "plan_forge.llm.glm_client.anthropic.Anthropic"
        ) as mock_cls:
            sdk = MagicMock()
            mock_cls.return_value = sdk
            sdk.messages.create.return_value = raw
            cache = MagicMock()
            cache.get.return_value = None
            cache.set.return_value = None
            c = GlmClient(api_key="fake")
            c._cache = cache
            resp = c.call("prompt", cache_key_inputs={"t": "1"})
            assert resp.verdict == "VERIFIED"
            assert resp.reasoning == "ok"

    def test_call_non_json_fallback(self):
        raw = _stub_messages_response("hello")
        with patch(
            "plan_forge.llm.glm_client.anthropic.Anthropic"
        ) as mock_cls:
            sdk = MagicMock()
            mock_cls.return_value = sdk
            sdk.messages.create.return_value = raw
            cache = MagicMock()
            cache.get.return_value = None
            cache.set.return_value = None
            c = GlmClient(api_key="fake")
            c._cache = cache
            resp = c.call("prompt", cache_key_inputs={"t": "2"})
            assert resp.verdict == "hello"


class TestGlmMaxTokens:
    def test_call_uses_max_tokens_4096(self):
        with patch(
            "plan_forge.llm.glm_client.anthropic.Anthropic"
        ) as mock_cls:
            sdk = MagicMock()
            mock_cls.return_value = sdk
            sdk.messages.create.return_value = _stub_messages_response()
            cache = MagicMock()
            cache.get.return_value = None
            cache.set.return_value = None
            c = GlmClient(api_key="fake")
            c._cache = cache
            c.call("test", cache_key_inputs={"t": "1"})
            kwargs = sdk.messages.create.call_args.kwargs
            assert kwargs["max_tokens"] == 4096


@pytest.mark.live
def test_glm_call_live():
    import os
    key = os.environ.get("PLAN_FORGE_GLM_API_KEY", "")
    if not key:
        pytest.skip("no glm credentials")
    c = GlmClient(api_key=key)
    resp = c.call(
        "Say exactly one word: hello",
        cache_key_inputs={
            "test": "live", "ttl_class": "recent", "prompt_version": "v0"
        },
    )
    assert resp.verdict.strip() != ""
