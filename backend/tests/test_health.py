import pytest

pytestmark = pytest.mark.asyncio


async def test_health_reports_database_and_providers(client):
    resp = await client.get("/api/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["components"]["database"] == "ok"
    assert "providers" in body["components"]
    assert "ollama" in body["components"]["providers"]
