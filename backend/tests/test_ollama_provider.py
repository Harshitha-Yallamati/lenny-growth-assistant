"""Regression coverage for the per-call timeout override (Case 3: Ship 30
essays need a longer Ollama timeout than ordinary QA turns, without raising
the shared default for every request). Fakes httpx.AsyncClient entirely --
no network, no real Ollama needed -- to isolate exactly which timeout value
reaches the client construction.
"""

import httpx
import pytest

from app.llm.ollama_provider import OllamaProvider

pytestmark = pytest.mark.asyncio


class _FakeResponse:
    def raise_for_status(self):
        pass

    def json(self):
        return {"message": {"content": "a response"}}


class _FakeAsyncClient:
    captured_timeouts: list[float] = []

    def __init__(self, timeout):
        _FakeAsyncClient.captured_timeouts.append(timeout)

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def post(self, *args, **kwargs):
        return _FakeResponse()


@pytest.fixture(autouse=True)
def _patch_httpx_client(monkeypatch):
    _FakeAsyncClient.captured_timeouts = []
    monkeypatch.setattr(httpx, "AsyncClient", _FakeAsyncClient)


async def test_complete_uses_the_providers_own_timeout_by_default():
    provider = OllamaProvider("http://fake:11434", "test-model", timeout_seconds=42.0)
    await provider.complete("system", [], "hi")
    assert _FakeAsyncClient.captured_timeouts == [42.0]


async def test_complete_uses_timeout_override_when_given():
    """This is what lets Ship 30 get a longer budget than QA without raising
    OLLAMA_TIMEOUT_SECONDS itself -- the orchestrator passes a distinct,
    larger value per call instead."""
    provider = OllamaProvider("http://fake:11434", "test-model", timeout_seconds=42.0)
    await provider.complete("system", [], "hi", timeout_override=1200.0)
    assert _FakeAsyncClient.captured_timeouts == [1200.0]
