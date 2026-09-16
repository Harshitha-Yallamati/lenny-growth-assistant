"""Conversation search, rename, and knowledge-base stats.

All three are additive read/write endpoints for the user's own chat history
and corpus size. None of them touch retrieval, the orchestrator or the
skills.
"""

import pytest

pytestmark = pytest.mark.asyncio


async def _session_with_message(client, message: str) -> str:
    """Create a session and give it one persisted user message.

    Goes through /api/chat with a mocked provider would need the LLM, so we
    instead rely on the title being set from the first message -- but for
    body-search coverage we need a real message row, so tests that need one
    patch the provider at the call site.
    """
    resp = await client.post("/api/sessions", json={})
    return resp.json()["id"]


async def test_rename_updates_the_title(client):
    session_id = await _session_with_message(client, "unused")
    resp = await client.patch(f"/api/sessions/{session_id}", json={"title": "Pricing research"})
    assert resp.status_code == 200
    assert resp.json()["title"] == "Pricing research"

    # and it persists
    detail = await client.get(f"/api/sessions/{session_id}")
    assert detail.json()["title"] == "Pricing research"


async def test_rename_trims_whitespace(client):
    session_id = await _session_with_message(client, "unused")
    resp = await client.patch(f"/api/sessions/{session_id}", json={"title": "  Padded  "})
    assert resp.json()["title"] == "Padded"


async def test_rename_rejects_a_whitespace_only_title(client):
    """min_length=1 lets "   " past validation; without an explicit guard it
    would blank the sidebar entry instead of renaming it."""
    session_id = await _session_with_message(client, "unused")
    resp = await client.patch(f"/api/sessions/{session_id}", json={"title": "   "})
    assert resp.status_code == 422
    assert "blank" in resp.json()["detail"].lower()


async def test_rename_missing_session_is_404(client):
    resp = await client.patch(
        "/api/sessions/00000000-0000-0000-0000-000000000000", json={"title": "x"}
    )
    assert resp.status_code == 404
    assert resp.json()["error"] == "HTTPException"


async def test_search_matches_session_title(client):
    session_id = await _session_with_message(client, "unused")
    await client.patch(f"/api/sessions/{session_id}", json={"title": "Zebra onboarding notes"})

    resp = await client.get("/api/sessions/search", params={"q": "zebra"})
    assert resp.status_code == 200
    hits = resp.json()
    assert any(h["id"] == session_id and h["matched_in"] == "title" for h in hits)


async def test_search_is_case_insensitive(client):
    session_id = await _session_with_message(client, "unused")
    await client.patch(f"/api/sessions/{session_id}", json={"title": "Quokka Metrics"})

    for q in ("quokka", "QUOKKA", "QuOkKa"):
        hits = (await client.get("/api/sessions/search", params={"q": q})).json()
        assert any(h["id"] == session_id for h in hits), f"no match for {q}"


async def test_search_route_is_not_shadowed_by_the_session_id_route(client):
    """/search must be declared before /{session_id}, or FastAPI tries to
    parse the literal "search" as a UUID and 422s."""
    resp = await client.get("/api/sessions/search", params={"q": "anything"})
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


async def test_search_requires_a_query(client):
    resp = await client.get("/api/sessions/search")
    assert resp.status_code == 422
    assert isinstance(resp.json()["detail"], str)


async def test_knowledge_base_stats_reports_the_corpus(client):
    resp = await client.get("/api/sources/stats")
    assert resp.status_code == 200
    body = resp.json()
    assert body["chunk_count"] >= 0
    assert body["source_count"] == len(body["sources"])
