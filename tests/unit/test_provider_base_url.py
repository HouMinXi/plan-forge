"""Tests for env-configurable provider base_url (credentials.base_url_for).

Covers:
- base_url_for: env set -> env value; unset/blank -> default.
- Per-client: with PLAN_FORGE_<P>_BASE_URL set, the SDK client is
  constructed with that override; unset -> the hardcoded default.
- anthropic special case: unset -> base_url NOT passed to the SDK;
  set -> base_url IS passed.
- Back-compat: full suite green with no env set (verified by running
  tests without any PLAN_FORGE_*_BASE_URL variables in the environment).
"""
from __future__ import annotations

from unittest.mock import patch


class TestBaseUrlFor:
    def test_env_set_returns_env_value(self, monkeypatch):
        monkeypatch.setenv("PLAN_FORGE_KIMI_BASE_URL", "https://proxy.example.com/v1")
        from plan_forge.llm.credentials import base_url_for
        assert base_url_for("kimi", "https://default.example.com") == \
            "https://proxy.example.com/v1"

    def test_env_unset_returns_default(self, monkeypatch):
        monkeypatch.delenv("PLAN_FORGE_KIMI_BASE_URL", raising=False)
        from plan_forge.llm.credentials import base_url_for
        assert base_url_for("kimi", "https://default.example.com") == \
            "https://default.example.com"

    def test_env_blank_returns_default(self, monkeypatch):
        monkeypatch.setenv("PLAN_FORGE_KIMI_BASE_URL", "   ")
        from plan_forge.llm.credentials import base_url_for
        assert base_url_for("kimi", "https://default.example.com") == \
            "https://default.example.com"

    def test_env_blank_with_none_default_returns_none(self, monkeypatch):
        monkeypatch.setenv("PLAN_FORGE_ANTHROPIC_BASE_URL", "")
        from plan_forge.llm.credentials import base_url_for
        assert base_url_for("anthropic", None) is None

    def test_provider_name_lowercased_in_input(self, monkeypatch):
        monkeypatch.setenv(
            "PLAN_FORGE_DEEPSEEK_BASE_URL", "https://proxy.ds.com"
        )
        from plan_forge.llm.credentials import base_url_for
        # Input is lowercase; env var name is uppercased internally.
        assert base_url_for("deepseek", "https://api.deepseek.com") == \
            "https://proxy.ds.com"

    def test_env_set_returns_stripped_value(self, monkeypatch):
        monkeypatch.setenv(
            "PLAN_FORGE_MIMO_BASE_URL", "  https://proxy.mimo.com  "
        )
        from plan_forge.llm.credentials import base_url_for
        assert base_url_for("mimo", "https://default.mimo.com") == \
            "https://proxy.mimo.com"



class TestKimiBaseUrlOverride:
    def test_override_propagates_to_sdk(self, monkeypatch):
        monkeypatch.setenv(
            "PLAN_FORGE_KIMI_BASE_URL", "https://proxy.kimi.example.com/v1"
        )
        with patch("plan_forge.llm.kimi_client.openai.OpenAI") as mock_cls:
            from plan_forge.llm.kimi_client import KimiClient
            KimiClient(api_key="fake-key")
            _, kwargs = mock_cls.call_args
            assert kwargs["base_url"] == \
                "https://proxy.kimi.example.com/v1"

    def test_unset_uses_default(self, monkeypatch):
        monkeypatch.delenv("PLAN_FORGE_KIMI_BASE_URL", raising=False)
        with patch("plan_forge.llm.kimi_client.openai.OpenAI") as mock_cls:
            from plan_forge.llm.kimi_client import KimiClient
            KimiClient(api_key="fake-key")
            _, kwargs = mock_cls.call_args
            assert kwargs["base_url"] == "https://api.moonshot.ai/v1"


class TestDeepSeekBaseUrlOverride:
    def test_override_propagates_to_sdk(self, monkeypatch):
        monkeypatch.setenv(
            "PLAN_FORGE_DEEPSEEK_BASE_URL", "https://proxy.ds.example.com"
        )
        with patch("plan_forge.llm.deepseek_client.openai.OpenAI") as mock_cls:
            from plan_forge.llm.deepseek_client import DeepSeekClient
            DeepSeekClient(api_key="fake-key")
            _, kwargs = mock_cls.call_args
            assert kwargs["base_url"] == "https://proxy.ds.example.com"

    def test_unset_uses_default(self, monkeypatch):
        monkeypatch.delenv("PLAN_FORGE_DEEPSEEK_BASE_URL", raising=False)
        with patch("plan_forge.llm.deepseek_client.openai.OpenAI") as mock_cls:
            from plan_forge.llm.deepseek_client import DeepSeekClient
            DeepSeekClient(api_key="fake-key")
            _, kwargs = mock_cls.call_args
            assert kwargs["base_url"] == "https://api.deepseek.com"


class TestMimoBaseUrlOverride:
    def test_override_propagates_to_sdk(self, monkeypatch):
        monkeypatch.setenv(
            "PLAN_FORGE_MIMO_BASE_URL", "https://proxy.mimo.example.com"
        )
        with patch(
            "plan_forge.llm.mimo_client.anthropic.Anthropic"
        ) as mock_cls:
            from plan_forge.llm.mimo_client import MimoClient
            MimoClient(api_key="fake-key")
            _, kwargs = mock_cls.call_args
            assert kwargs["base_url"] == "https://proxy.mimo.example.com"

    def test_unset_uses_default(self, monkeypatch):
        monkeypatch.delenv("PLAN_FORGE_MIMO_BASE_URL", raising=False)
        with patch(
            "plan_forge.llm.mimo_client.anthropic.Anthropic"
        ) as mock_cls:
            from plan_forge.llm.mimo_client import MimoClient
            MimoClient(api_key="fake-key")
            _, kwargs = mock_cls.call_args
            assert kwargs["base_url"] == \
                "https://token-plan-cn.xiaomimimo.com/anthropic"


class TestAnthropicBaseUrlOverride:
    def test_override_propagates_to_sdk(self, monkeypatch):
        monkeypatch.setenv(
            "PLAN_FORGE_ANTHROPIC_BASE_URL",
            "https://proxy.anthropic.example.com",
        )
        with patch(
            "plan_forge.llm.anthropic_client.anthropic.Anthropic"
        ) as mock_cls:
            from plan_forge.llm.anthropic_client import AnthropicClient
            AnthropicClient(api_key="fake-key")
            _, kwargs = mock_cls.call_args
            assert kwargs.get("base_url") == \
                "https://proxy.anthropic.example.com"

    def test_unset_does_not_pass_base_url(self, monkeypatch):
        """When no env override, base_url must not appear in the SDK call."""
        monkeypatch.delenv("PLAN_FORGE_ANTHROPIC_BASE_URL", raising=False)
        with patch(
            "plan_forge.llm.anthropic_client.anthropic.Anthropic"
        ) as mock_cls:
            from plan_forge.llm.anthropic_client import AnthropicClient
            AnthropicClient(api_key="fake-key")
            _, kwargs = mock_cls.call_args
            assert "base_url" not in kwargs, (
                "base_url must not be passed to the Anthropic SDK "
                "when PLAN_FORGE_ANTHROPIC_BASE_URL is unset"
            )
