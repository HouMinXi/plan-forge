"""Web search tool_use schemas per provider.

Each provider uses a different tool_use protocol:
  - Anthropic: first-party web_search_20250305 tool (built-in)
  - Kimi: OpenAI-compatible function calling
  - DeepSeek: OpenAI-compatible function calling (tool_use has known bugs;
    health_check probes at startup and sets tool_use_ok=False if broken)
  - Mimo: tool_use support unconfirmed; health_check probes; if absent,
    all Mimo evidence is tagged UNCLASSIFIED (no_search_judgment tier)

MIMO_WEB_SEARCH_TOOL is None because Mimo's tool_use support was not
confirmed; mimo_client health_check probes at startup and sets
tool_use_ok accordingly.
"""
from __future__ import annotations

# Anthropic built-in web search tool (2025-03-05 version).
# Passed as a tool entry in the tools list; Anthropic executes the
# search internally and injects results into the assistant turn.
ANTHROPIC_WEB_SEARCH_TOOL: dict = {
    "type": "web_search_20250305",
    "name": "web_search",
    "max_uses": 3,
}

# Kimi uses OpenAI-compatible function calling for web search.
# Model decides when to invoke; caller must handle tool_call turns.
KIMI_WEB_SEARCH_TOOL: dict = {
    "type": "function",
    "function": {
        "name": "web_search",
        "description": "Search the web for current information.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
            },
            "required": ["query"],
        },
    },
}

# DeepSeek uses OpenAI-compatible function calling.
# Known limitation per project memory: tool_use protocol has conversion
# bugs with multi-turn alternation; health_check probes and may set
# tool_use_ok=False, degrading provider to no_search_judgment tier.
DEEPSEEK_WEB_SEARCH_TOOL: dict = {
    "type": "function",
    "function": {
        "name": "web_search",
        "description": "Search the web.",
        "parameters": {
            "type": "object",
            "properties": {"query": {"type": "string"}},
            "required": ["query"],
        },
    },
}

# Mimo tool_use schema is unconfirmed.  Placeholder; health_check will
# attempt a probe and update tool_use_ok in HealthStatus accordingly.
# If tool_use_ok=False at startup, downstream search_vote tags Mimo
# evidence as UNCLASSIFIED (no_search_judgment fallback).
MIMO_WEB_SEARCH_TOOL: dict | None = None
