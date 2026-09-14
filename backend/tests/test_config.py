import pytest

pytestmark = pytest.mark.asyncio


async def test_get_config_reports_defaults(client):
    resp = await client.get("/api/config")
    assert resp.status_code == 200
    body = resp.json()
    assert body["configured_default"] == "ollama"
    assert body["active_provider"] == "ollama"
    assert set(body["provider_status"].keys()) == {"ollama", "anthropic", "openai"}
    assert body["ollama_model"] and body["anthropic_model"] and body["openai_model"]


async def test_post_config_switches_active_provider(client):
    resp = await client.post("/api/config", json={"provider": "anthropic"})
    assert resp.status_code == 200
    assert resp.json()["active_provider"] == "anthropic"

    # the switch is live -- a subsequent GET reflects it, not the .env default
    resp2 = await client.get("/api/config")
    assert resp2.json()["active_provider"] == "anthropic"
    assert resp2.json()["configured_default"] == "ollama"


async def test_post_config_rejects_an_unknown_provider(client):
    resp = await client.post("/api/config", json={"provider": "not-a-real-provider"})
    assert resp.status_code == 422
