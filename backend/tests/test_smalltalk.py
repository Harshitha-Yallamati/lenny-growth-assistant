"""End-to-end coverage for the smalltalk short-circuit, through the real
/api/chat endpoint -- not just the detector function in isolation. Confirms
the observable contract the frontend depends on: grounded=false, no
citations, skill="smalltalk", and (via a provider mock that raises if
called) that no Ollama generation happens at all.
"""

import pytest

from app.llm.ollama_provider import OllamaProvider

pytestmark = pytest.mark.asyncio


async def _never_call_the_provider(*args, **kwargs):
    raise AssertionError("smalltalk must not call the LLM provider")


async def test_greeting_gets_a_deterministic_response_with_no_grounding(client, monkeypatch):
    monkeypatch.setattr(OllamaProvider, "complete", _never_call_the_provider)

    create_resp = await client.post("/api/sessions", json={})
    session_id = create_resp.json()["id"]

    chat_resp = await client.post("/api/chat", json={"session_id": session_id, "message": "hey"})
    assert chat_resp.status_code == 200

    body = chat_resp.json()["message"]
    assert body["skill"] == "smalltalk"
    assert body["grounded"] is False
    assert not body["citations"]
    assert body["artifact"] is None
    assert "Lenny Growth Assistant" in body["content"]


async def test_thanks_gets_a_deterministic_response_too(client, monkeypatch):
    monkeypatch.setattr(OllamaProvider, "complete", _never_call_the_provider)

    create_resp = await client.post("/api/sessions", json={})
    session_id = create_resp.json()["id"]

    chat_resp = await client.post("/api/chat", json={"session_id": session_id, "message": "thank you!"})
    assert chat_resp.status_code == 200

    body = chat_resp.json()["message"]
    assert body["skill"] == "smalltalk"
    assert body["grounded"] is False
    assert not body["citations"]


async def test_a_real_question_still_reaches_the_provider(client, monkeypatch):
    """Sanity check that the mock itself is meaningful: an ordinary question
    must still hit the (mocked) provider, proving the smalltalk short-circuit
    isn't accidentally swallowing real questions too."""
    monkeypatch.setattr(OllamaProvider, "complete", _never_call_the_provider)

    create_resp = await client.post("/api/sessions", json={})
    session_id = create_resp.json()["id"]

    chat_resp = await client.post(
        "/api/chat", json={"session_id": session_id, "message": "what are retention curves"}
    )
    assert chat_resp.status_code == 502, "the mocked provider raises, which chat.py maps to a 502"
