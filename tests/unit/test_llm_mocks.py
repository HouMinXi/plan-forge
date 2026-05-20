"""Tests for llm/mocks.py."""
from __future__ import annotations

from datetime import datetime, timezone

from plan_forge.llm.client import LLMResponse, HealthStatus
from plan_forge.llm.mocks import MockClient


class TestMockClient:
    def test_returns_canned_response_on_keyword_match(self):
        resp = LLMResponse(verdict="PASS", reasoning="looks good")
        client = MockClient(name="mock_test", responses={"PASS": resp})
        result = client.call("this plan PASS criteria", cache_key_inputs={})
        assert result.verdict == "PASS"
        assert result.reasoning == "looks good"

    def test_returns_default_when_no_match(self):
        client = MockClient(name="mock_test", responses={"PASS": LLMResponse(
            verdict="PASS", reasoning=""
        )})
        result = client.call("unrelated prompt", cache_key_inputs={})
        assert result.verdict == "unknown"

    def test_health_check_returns_ok(self):
        client = MockClient()
        h = client.health_check()
        assert h.auth_ok is True
        assert h.tool_use_ok is True

    def test_custom_health_status(self):
        bad = HealthStatus(
            auth_ok=False,
            tool_use_ok=False,
            last_checked=datetime.now(timezone.utc),
            error="test error",
        )
        client = MockClient(health=bad)
        assert client.health_check().auth_ok is False

    def test_default_name(self):
        client = MockClient()
        assert client.name == "mock"

    def test_custom_name(self):
        client = MockClient(name="custom_mock")
        assert client.name == "custom_mock"

    def test_call_ignores_tool_use_schema(self):
        resp = LLMResponse(verdict="ok", reasoning="")
        client = MockClient(responses={"ok": resp})
        result = client.call(
            "ok prompt",
            tool_use_schema={"type": "function"},
            cache_key_inputs={"plan": "x"},
        )
        assert result.verdict == "ok"
