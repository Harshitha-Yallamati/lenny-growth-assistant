import pytest

from app.llm.base import ProviderResult

pytestmark = pytest.mark.asyncio


async def test_create_and_fetch_session(client):
    create_resp = await client.post("/api/sessions", json={"user_metadata": {"client": "pytest"}})
    assert create_resp.status_code == 201
    session_id = create_resp.json()["id"]

    get_resp = await client.get(f"/api/sessions/{session_id}")
    assert get_resp.status_code == 200
    body = get_resp.json()
    assert body["id"] == session_id
    assert body["messages"] == []


async def test_get_missing_session_returns_404(client):
    resp = await client.get("/api/sessions/00000000-0000-0000-0000-000000000000")
    assert resp.status_code == 404
    assert resp.json()["error"] == "HTTPException"


async def test_chat_persists_user_and_assistant_messages(client, monkeypatch):
    async def fake_complete(self, system_prompt, history, user_message, max_tokens=1500):
        return ProviderResult(text="Mocked grounded answer.", provider="ollama", model="test-model")

    monkeypatch.setattr("app.llm.ollama_provider.OllamaProvider.complete", fake_complete)

    create_resp = await client.post("/api/sessions", json={})
    session_id = create_resp.json()["id"]

    chat_resp = await client.post(
        "/api/chat",
        json={"session_id": session_id, "message": "How do I find product-market fit?"},
    )
    assert chat_resp.status_code == 200
    body = chat_resp.json()
    assert body["message"]["role"] == "assistant"
    assert body["message"]["content"] == "Mocked grounded answer."
    assert body["message"]["skill"] == "qa"

    detail_resp = await client.get(f"/api/sessions/{session_id}")
    messages = detail_resp.json()["messages"]
    assert [m["role"] for m in messages] == ["user", "assistant"]
    assert messages[0]["content"] == "How do I find product-market fit?"
