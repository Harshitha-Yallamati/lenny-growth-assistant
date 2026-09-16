"""Every error response keeps the {error: str, detail: str} shape.

architecture.md documents that contract, but FastAPI's default 422 handler
returns {"detail": [ {...} ]} -- no `error` key, and `detail` as a list of
objects. The frontend does `body.detail ?? statusText` and puts the result
straight into its error banner, so a validation failure rendered a
stringified object instead of a readable message.
"""

import pytest

pytestmark = pytest.mark.asyncio


async def test_not_found_uses_the_documented_shape(client):
    resp = await client.get("/api/sessions/00000000-0000-0000-0000-000000000000")
    assert resp.status_code == 404
    body = resp.json()
    assert body["error"] == "HTTPException"
    assert isinstance(body["detail"], str)


async def test_validation_error_uses_the_documented_shape(client):
    resp = await client.post("/api/chat", json={"session_id": "not-a-uuid", "message": "hi"})
    assert resp.status_code == 422
    body = resp.json()
    assert body["error"] == "ValidationError"
    assert isinstance(body["detail"], str), "a list here renders as junk in the UI banner"
    assert "session_id" in body["detail"]


async def test_invalid_provider_name_is_readable(client):
    resp = await client.post("/api/config", json={"provider": "gpt5"})
    assert resp.status_code == 422
    body = resp.json()
    assert isinstance(body["detail"], str)
    assert "provider" in body["detail"]


async def test_empty_message_is_rejected_readably(client):
    """message has min_length=1; the rejection still has to be legible."""
    resp = await client.post(
        "/api/chat",
        json={"session_id": "00000000-0000-0000-0000-000000000000", "message": ""},
    )
    assert resp.status_code == 422
    assert isinstance(resp.json()["detail"], str)
