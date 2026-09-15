"""Tests for the Claude Agent SDK path.

What these can and can't cover: the SDK drives the `claude` CLI against the
live Anthropic API, and no API key was available for this build, so the
network round-trip is NOT exercised here. What is covered is everything that
decides whether that path is even entered, plus the response parsing -- i.e.
the logic that protects the mandatory Ollama demo path from a half-configured
Anthropic setup.
"""

import pytest

from app.llm import claude_agent_provider
from app.llm.base import ProviderUnavailableError
from app.llm.claude_agent_provider import QUALIFIED_TOOL, ClaudeAgentSDKProvider

# No module-level asyncio mark: pytest.ini runs asyncio_mode=auto, and marking
# the sync tests below would emit a warning for each.


async def test_unavailable_without_api_key(monkeypatch):
    monkeypatch.setattr(claude_agent_provider, "sdk_available", lambda: True)
    provider = ClaudeAgentSDKProvider(api_key="", model="claude-opus-5")
    assert await provider.is_available() is False


async def test_unavailable_when_cli_missing(monkeypatch):
    """The pip package alone isn't enough -- without the `claude` binary the
    SDK can't run, and reporting available would strand the request."""
    monkeypatch.setattr(claude_agent_provider.shutil, "which", lambda _: None)
    provider = ClaudeAgentSDKProvider(api_key="sk-test", model="claude-opus-5")
    assert await provider.is_available() is False


async def test_complete_without_key_raises_provider_unavailable():
    provider = ClaudeAgentSDKProvider(api_key="", model="claude-opus-5")
    with pytest.raises(ProviderUnavailableError, match="ANTHROPIC_API_KEY"):
        await provider.complete("system", [], "hello")


async def test_complete_without_cli_names_the_missing_dependency(monkeypatch):
    monkeypatch.setattr(claude_agent_provider, "sdk_available", lambda: False)
    provider = ClaudeAgentSDKProvider(api_key="sk-test", model="claude-opus-5")
    with pytest.raises(ProviderUnavailableError, match="Claude Code CLI"):
        await provider.complete("system", [], "hello")


def test_tool_is_namespaced_for_the_allow_list():
    """The allow-list entry must match the SDK's mcp__<server>__<tool> form,
    or the agent silently gets no tools at all."""
    assert QUALIFIED_TOOL == "mcp__lenny_kb__search_transcripts"


def test_history_is_flattened_into_the_prompt():
    from app.llm.base import ChatTurn

    prompt = claude_agent_provider._flatten_history(
        [ChatTurn(role="user", content="What is PMF?"),
         ChatTurn(role="assistant", content="Retention that flattens.")],
        "How do I measure it?",
    )
    assert "What is PMF?" in prompt
    assert "Retention that flattens." in prompt
    assert prompt.endswith("How do I measure it?")


def test_no_history_passes_the_message_through_unchanged():
    assert claude_agent_provider._flatten_history([], "Just this") == "Just this"
