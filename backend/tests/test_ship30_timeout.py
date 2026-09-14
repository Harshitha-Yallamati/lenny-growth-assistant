"""Regression coverage that the orchestrator actually wires the Ship 30
timeout through (Case 3) -- test_ollama_provider.py proves the provider
honors timeout_override when given one; this proves the orchestrator gives
it one for ship30 and not for qa, so ordinary QA requests keep the shorter
default rather than waiting as long as an essay is allowed to.
"""

import pytest

from app.agent.orchestrator import run_turn
from app.core.config import get_settings
from app.llm.base import ProviderResult
from app.llm.ollama_provider import OllamaProvider

pytestmark = pytest.mark.asyncio

# A query unlikely to match anything in the corpus, so both skills hit their
# "no chunks retrieved" branch -- for ship30 that's still a single
# provider.complete() call (the honest-refusal one), which is all this test
# needs to observe which timeout was requested.
_UNMATCHED_QUERY = "xyzzyqux nonsense string matching nothing in the corpus"


async def test_ship30_requests_the_longer_essay_timeout(db_session, monkeypatch):
    captured = []

    async def fake_complete(self, system_prompt, history, user_message, max_tokens=1500, timeout_override=None):
        captured.append(timeout_override)
        return ProviderResult(text="a refusal", provider="ollama", model="test-model")

    monkeypatch.setattr(OllamaProvider, "complete", fake_complete)

    await run_turn(db_session, _UNMATCHED_QUERY, history=[], requested_skill="ship30")

    settings = get_settings()
    assert captured, "provider.complete should have been called"
    assert all(t == settings.ollama_ship30_timeout_seconds for t in captured)


async def test_qa_does_not_request_a_timeout_override(db_session, monkeypatch):
    captured = []

    async def fake_complete(self, system_prompt, history, user_message, max_tokens=1500, timeout_override=None):
        captured.append(timeout_override)
        return ProviderResult(text="an answer", provider="ollama", model="test-model")

    monkeypatch.setattr(OllamaProvider, "complete", fake_complete)

    await run_turn(db_session, _UNMATCHED_QUERY, history=[], requested_skill="qa")

    assert captured == [None], "QA must keep using the provider's own (shorter) default timeout"
