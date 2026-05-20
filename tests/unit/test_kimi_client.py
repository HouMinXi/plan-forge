"""Tests for llm/kimi_client.py."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from plan_forge.llm.kimi_client import KimiClient


def _make_client(mock_cache=None):
    with patch("plan_forge.llm.kimi_client.openai.OpenAI"):
        c = KimiClient(api_key="fake-key")
    if mock_cache is not None:
        c._cache = mock_cache
    return c


def _stub_choice(content="PASS"):
    choice = MagicMock()
    choice.message.content = content
    raw = MagicMock()
    raw.choices = [choice]
    raw.usage.prompt_tokens = 10
    raw.usage.completion_tokens = 5
    raw.model_dump.return_value = {"stub": True}
    return raw


class TestKimiHealthCheckMock:
    def test_auth_ok(self):
        with patch("plan_forge.llm.kimi_client.openai.OpenAI") as mock_cls:
            sdk = MagicMock()
            mock_cls.return_value = sdk
            sdk.chat.completions.create.return_value = _stub_choice()
            c = KimiClient(api_key="fake")
            h = c.health_check()
            assert h.auth_ok is True

    def test_auth_fail(self):
        import openai as oa
        with patch("plan_forge.llm.kimi_client.openai.OpenAI") as mock_cls:
            sdk = MagicMock()
            mock_cls.return_value = sdk
            sdk.chat.completions.create.side_effect = oa.AuthenticationError(
                message="auth", response=MagicMock(), body={}
            )
            c = KimiClient(api_key="bad")
            h = c.health_check()
            assert h.auth_ok is False


class TestKimiCallCaches:
    def test_sdk_called_once_on_two_identical_calls(self):
        with patch("plan_forge.llm.kimi_client.openai.OpenAI") as mock_cls:
            sdk = MagicMock()
            mock_cls.return_value = sdk
            sdk.chat.completions.create.return_value = _stub_choice("PASS")

            cache = MagicMock()
            cache.get.side_effect = [None, {"verdict": "PASS", "reasoning": "",
                                             "cited_instances": [], "search_evidence": [],
                                             "cost_usd": 0.0, "raw_response": {}}]
            cache.set.return_value = None

            c = KimiClient(api_key="fake")
            c._cache = cache

            inputs = {"plan": "y", "ttl_class": "canonical", "prompt_version": "v0"}
            c.call("prompt", cache_key_inputs=inputs)
            r2 = c.call("prompt", cache_key_inputs=inputs)
            assert sdk.chat.completions.create.call_count == 1
            assert r2.verdict == "PASS"


class TestKimiJsonParse:
    """Verify parse_verdict_response is applied in call()."""

    def test_call_parses_json_verdict(self):
        json_body = '{"verdict": "VERIFIED", "reason": "ok", "cited_instances": [], "search_evidence": []}'
        raw = _stub_choice(json_body)
        with patch("plan_forge.llm.kimi_client.openai.OpenAI") as mock_cls:
            sdk = MagicMock()
            mock_cls.return_value = sdk
            sdk.chat.completions.create.return_value = raw
            cache = MagicMock()
            cache.get.return_value = None
            cache.set.return_value = None
            c = KimiClient(api_key="fake")
            c._cache = cache
            resp = c.call("prompt", cache_key_inputs={"t": "1"})
            assert resp.verdict == "VERIFIED"
            assert resp.reasoning == "ok"

    def test_call_non_json_fallback(self):
        raw = _stub_choice("hello")
        with patch("plan_forge.llm.kimi_client.openai.OpenAI") as mock_cls:
            sdk = MagicMock()
            mock_cls.return_value = sdk
            sdk.chat.completions.create.return_value = raw
            cache = MagicMock()
            cache.get.return_value = None
            cache.set.return_value = None
            c = KimiClient(api_key="fake")
            c._cache = cache
            resp = c.call("prompt", cache_key_inputs={"t": "2"})
            assert resp.verdict == "hello"

    def test_call_markdown_fenced_json(self):
        fenced = '```json\n{"verdict":"UNVERIFIED","reason":"bad","cited_instances":[],"search_evidence":[]}\n```'
        raw = _stub_choice(fenced)
        with patch("plan_forge.llm.kimi_client.openai.OpenAI") as mock_cls:
            sdk = MagicMock()
            mock_cls.return_value = sdk
            sdk.chat.completions.create.return_value = raw
            cache = MagicMock()
            cache.get.return_value = None
            cache.set.return_value = None
            c = KimiClient(api_key="fake")
            c._cache = cache
            resp = c.call("prompt", cache_key_inputs={"t": "3"})
            assert resp.verdict == "UNVERIFIED"
            assert resp.reasoning == "bad"


@pytest.mark.live
def test_kimi_call_live():
    import os
    key = os.environ.get("PLAN_FORGE_KIMI_API_KEY", "")
    if not key:
        pytest.skip("no kimi credentials")
    c = KimiClient(api_key=key)
    resp = c.call(
        "Say exactly one word: hello",
        cache_key_inputs={"test": "live", "ttl_class": "recent", "prompt_version": "v0"},
    )
    assert resp.verdict.strip() != ""
