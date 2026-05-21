"""Tests for llm/credentials.py."""
from __future__ import annotations

import subprocess
from unittest.mock import MagicMock, patch


from plan_forge.llm.credentials import (
    ChainedCredentialResolver,
    EnvCredentialResolver,
    PassCredentialResolver,
)


class TestPassCredentialResolver:
    def test_no_pass_binary_returns_empty(self):
        """FileNotFoundError when pass not installed -> empty pool."""
        with patch("subprocess.run", side_effect=FileNotFoundError):
            r = PassCredentialResolver()
            assert r.get_pool("anthropic") == []

    def test_pass_nonzero_exit_returns_empty(self):
        mock = MagicMock()
        mock.returncode = 1
        with patch("subprocess.run", return_value=mock):
            r = PassCredentialResolver()
            assert r.get_pool("anthropic") == []

    def test_timeout_returns_empty(self):
        with patch(
            "subprocess.run",
            side_effect=subprocess.TimeoutExpired(cmd="pass", timeout=5),
        ):
            r = PassCredentialResolver()
            assert r.get_pool("anthropic") == []

    def test_pass_returns_keys(self):
        """When pass ls returns keyN entries and pass show succeeds."""
        ls_mock = MagicMock()
        ls_mock.returncode = 0
        ls_mock.stdout = "plan-forge/anthropic\n  key1\n  key2\n"

        show_mock = MagicMock()
        show_mock.returncode = 0
        show_mock.stdout = "sk-ant-test\n"

        def side_effect(args, **kwargs):
            if args[0] == "pass" and args[1] == "ls":
                return ls_mock
            return show_mock

        with patch("subprocess.run", side_effect=side_effect):
            r = PassCredentialResolver()
            pool = r.get_pool("anthropic")
            assert len(pool) == 2
            assert pool[0] == "sk-ant-test"


class TestEnvCredentialResolver:
    def test_env_set_returns_list(self, monkeypatch):
        monkeypatch.setenv("PLAN_FORGE_ANTHROPIC_API_KEY", "test-key-123")
        r = EnvCredentialResolver()
        assert r.get_pool("anthropic") == ["test-key-123"]

    def test_env_unset_returns_empty(self, monkeypatch):
        monkeypatch.delenv("PLAN_FORGE_ANTHROPIC_API_KEY", raising=False)
        r = EnvCredentialResolver()
        assert r.get_pool("anthropic") == []

    def test_env_whitespace_only_returns_empty(self, monkeypatch):
        monkeypatch.setenv("PLAN_FORGE_ANTHROPIC_API_KEY", "   ")
        r = EnvCredentialResolver()
        assert r.get_pool("anthropic") == []

    def test_env_provider_name_uppercased(self, monkeypatch):
        monkeypatch.setenv("PLAN_FORGE_KIMI_API_KEY", "kimi-key")
        r = EnvCredentialResolver()
        assert r.get_pool("kimi") == ["kimi-key"]


class TestChainedCredentialResolver:
    def test_fallback_to_second_resolver(self):
        """First resolver returns empty -> falls back to second."""
        empty = MagicMock()
        empty.get_pool.return_value = []
        has_key = MagicMock()
        has_key.get_pool.return_value = ["key-from-second"]
        chained = ChainedCredentialResolver([empty, has_key])
        pool = chained.get_pool("test")
        assert pool == ["key-from-second"]
        empty.get_pool.assert_called_once_with("test")
        has_key.get_pool.assert_called_once_with("test")

    def test_stops_at_first_non_empty(self):
        """First resolver has keys -> second never called."""
        has_key = MagicMock()
        has_key.get_pool.return_value = ["key-from-first"]
        never = MagicMock()
        never.get_pool.return_value = ["key-from-second"]
        chained = ChainedCredentialResolver([has_key, never])
        pool = chained.get_pool("test")
        assert pool == ["key-from-first"]
        never.get_pool.assert_not_called()

    def test_all_empty_returns_empty(self):
        r1 = MagicMock()
        r1.get_pool.return_value = []
        r2 = MagicMock()
        r2.get_pool.return_value = []
        chained = ChainedCredentialResolver([r1, r2])
        assert chained.get_pool("test") == []
