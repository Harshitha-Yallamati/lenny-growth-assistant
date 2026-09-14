"""Regression coverage for the provider fallback chokepoint (registry.py).

No automated test previously exercised resolve_provider() itself -- the
"falls back to Ollama when a cloud key is missing" behavior was only ever
checked manually (see README's "What was verified end-to-end" and this
audit's live curl tests), so a future change to this function could silently
break the core "flexible LLM configuration" fallback requirement.

Needs no database and no network: conftest.py defaults ANTHROPIC_API_KEY and
OPENAI_API_KEY to "" for the whole test process, so AnthropicProvider.is_
available()/OpenAIProvider.is_available() are already False here exactly as
they would be with no key configured in .env.
"""

import pytest

from app.core import runtime_state
from app.llm.registry import resolve_provider

pytestmark = pytest.mark.asyncio


async def test_resolve_provider_uses_ollama_directly_with_no_fallback_check():
    runtime_state.set_active_provider("ollama")
    resolved = await resolve_provider()
    assert resolved.provider.name == "ollama"
    assert resolved.requested == "ollama"
    assert resolved.fell_back is False


async def test_resolve_provider_falls_back_to_ollama_when_anthropic_key_missing():
    runtime_state.set_active_provider("anthropic")
    resolved = await resolve_provider()
    assert resolved.provider.name == "ollama", "no key configured -- must silently drop to Ollama"
    assert resolved.requested == "anthropic", "the UI needs to know what was actually requested"
    assert resolved.fell_back is True


async def test_resolve_provider_falls_back_to_ollama_when_openai_key_missing():
    runtime_state.set_active_provider("openai")
    resolved = await resolve_provider()
    assert resolved.provider.name == "ollama"
    assert resolved.requested == "openai"
    assert resolved.fell_back is True
