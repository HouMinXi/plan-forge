"""Tests for llm/deepseek_client.py."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from plan_forge.llm.deepseek_client import DeepSeekClient


def _stub_choice(content="PASS"):
    choice = MagicMock()
    choice.message.content = content
    raw = MagicMock()
    raw.choices = [choice]
    raw.usage.prompt_tokens = 10
    raw.usage.completion_tokens = 5
    raw.model_dump.return_value = {"stub": True}
    return raw


class TestDeepSeekHealthCheckMock:
    def test_auth_ok(self):
        with patch("plan_forge.llm.deepseek_client.openai.OpenAI") as mock_cls:
            sdk = MagicMock()
            mock_cls.return_value = sdk
            sdk.chat.completions.create.return_value = _stub_choice()
            c = DeepSeekClient(api_key="fake")
            h = c.health_check()
            assert h.auth_ok is True

    def test_tool_use_fail_still_auth_ok(self):
        """If tool_use probe fails, auth_ok stays True; tool_use_ok=False."""
        with patch("plan_forge.llm.deepseek_client.openai.OpenAI") as mock_cls:
            sdk = MagicMock()
            mock_cls.return_value = sdk
            # First call (auth probe) succeeds; second (tool_use probe) fails
            sdk.chat.completions.create.side_effect = [
                _stub_choice(),  # auth probe OK
                Exception("tool_use bug"),  # tool probe fails
            ]
            c = DeepSeekClient(api_key="fake")
            h = c.health_check()
            assert h.auth_ok is True
            assert h.tool_use_ok is False

    def test_auth_fail(self):
        import openai as oa
        with patch("plan_forge.llm.deepseek_client.openai.OpenAI") as mock_cls:
            sdk = MagicMock()
            mock_cls.return_value = sdk
            sdk.chat.completions.create.side_effect = oa.AuthenticationError(
                message="auth", response=MagicMock(), body={}
            )
            c = DeepSeekClient(api_key="bad")
            h = c.health_check()
            assert h.auth_ok is False


class TestDeepSeekCallCaches:
    def test_sdk_called_once_on_cache_hit(self):
        with patch("plan_forge.llm.deepseek_client.openai.OpenAI") as mock_cls:
            sdk = MagicMock()
            mock_cls.return_value = sdk
            sdk.chat.completions.create.return_value = _stub_choice("PASS")

            cache = MagicMock()
            cache.get.side_effect = [None, {"verdict": "PASS", "reasoning": "",
                                             "cited_instances": [], "search_evidence": [],
                                             "cost_usd": 0.0, "raw_response": {}}]
            cache.set.return_value = None

            c = DeepSeekClient(api_key="fake")
            c._cache = cache

            inputs = {"plan": "z", "ttl_class": "canonical", "prompt_version": "v0"}
            c.call("prompt", cache_key_inputs=inputs)
            r2 = c.call("prompt", cache_key_inputs=inputs)
            assert r2.verdict == "PASS"


@pytest.mark.live
def test_deepseek_call_live():
    import os
    key = os.environ.get("PLAN_FORGE_DEEPSEEK_API_KEY", "")
    if not key:
        pytest.skip("no deepseek credentials")
    c = DeepSeekClient(api_key=key)
    resp = c.call(
        "Say exactly one word: hello",
        cache_key_inputs={"test": "live", "ttl_class": "recent", "prompt_version": "v0"},
    )
    assert resp.verdict.strip() != ""
