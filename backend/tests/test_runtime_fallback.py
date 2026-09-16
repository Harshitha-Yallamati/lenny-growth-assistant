"""The cloud->Ollama fallback when a request fails *in flight*.

registry.resolve_provider() only pre-checks configuration, which for the
cloud providers means "is a key set at all". A key that exists but is
expired, revoked, rate-limited, or paired with a wrong model name passes that
check and only fails once the request is running -- and that is the most
likely real cloud failure. Before this, the user got an apology instead of an
answer, contradicting the documented behavior in the README ("if the key is
missing *or a request fails* ... automatically falls back to Ollama").

These use fake providers rather than real keys, so they need no network.
"""

import pytest

from app.agent.orchestrator import _complete_with_runtime_fallback
from app.llm.base import LLMProvider, ProviderResult, ProviderTimeoutError, ProviderUnavailableError
from app.llm.registry import ResolvedProvider


class _FailingCloudProvider(LLMProvider):
    """Configured (a key is present) but every live request fails."""

    name = "anthropic"

    def __init__(self, exc: Exception):
        self.exc = exc
        self.calls = 0

    async def is_available(self) -> bool:
        return True  # the key exists -- that's all the pre-check can know

    async def complete(self, system_prompt, history, user_message, **kwargs):
        self.calls += 1
        raise self.exc


class _WorkingOllama(LLMProvider):
    name = "ollama"

    def __init__(self):
        self.calls = 0

    async def is_available(self) -> bool:
        return True

    async def complete(self, system_prompt, history, user_message, **kwargs):
        self.calls += 1
        return ProviderResult(text="local answer", provider="ollama", model="llama3.1")


class _FailingOllama(LLMProvider):
    name = "ollama"

    async def is_available(self) -> bool:
        return False

    async def complete(self, system_prompt, history, user_message, **kwargs):
        raise ProviderUnavailableError("Ollama is down")


@pytest.mark.asyncio
async def test_invalid_cloud_key_falls_back_to_ollama_mid_request(monkeypatch):
    cloud = _FailingCloudProvider(ProviderUnavailableError("401 invalid x-api-key"))
    ollama = _WorkingOllama()
    monkeypatch.setattr("app.agent.orchestrator.get_provider", lambda name: ollama)

    resolved = ResolvedProvider(provider=cloud, requested="anthropic", fell_back=False)
    call = await _complete_with_runtime_fallback(resolved, "sys", [], "hello")

    assert call.result.text == "local answer"
    assert call.provider.name == "ollama"
    assert call.fell_back is True, "the UI banner depends on this flag"
    assert cloud.calls == 1 and ollama.calls == 1


@pytest.mark.asyncio
async def test_cloud_timeout_also_falls_back(monkeypatch):
    cloud = _FailingCloudProvider(ProviderTimeoutError("cloud timed out"))
    ollama = _WorkingOllama()
    monkeypatch.setattr("app.agent.orchestrator.get_provider", lambda name: ollama)

    resolved = ResolvedProvider(provider=cloud, requested="anthropic", fell_back=False)
    call = await _complete_with_runtime_fallback(resolved, "sys", [], "hello")
    assert call.fell_back is True
    assert call.result.provider == "ollama"


@pytest.mark.asyncio
async def test_ollama_failure_propagates_rather_than_looping():
    """Ollama has nothing to fall back to -- its failure must reach the
    caller's error handling, not retry itself forever."""
    resolved = ResolvedProvider(provider=_FailingOllama(), requested="ollama", fell_back=False)
    with pytest.raises(ProviderUnavailableError, match="Ollama is down"):
        await _complete_with_runtime_fallback(resolved, "sys", [], "hello")


@pytest.mark.asyncio
async def test_successful_cloud_call_preserves_the_pre_check_fallback_flag():
    """A provider that works must not be reported as having fallen back."""

    class _WorkingCloud(LLMProvider):
        name = "anthropic"

        async def is_available(self) -> bool:
            return True

        async def complete(self, system_prompt, history, user_message, **kwargs):
            return ProviderResult(text="cloud answer", provider="anthropic", model="claude-opus-5")

    resolved = ResolvedProvider(provider=_WorkingCloud(), requested="anthropic", fell_back=False)
    call = await _complete_with_runtime_fallback(resolved, "sys", [], "hello")
    assert call.fell_back is False
    assert call.result.text == "cloud answer"
