"""The citation-preview lookup.

Read-only and additive: it does not touch retrieval, so these tests assert
the endpoint's contract rather than any ranking behavior.
"""

import pytest
from sqlalchemy import delete

from app.db.models import TranscriptChunk

pytestmark = pytest.mark.asyncio

SEEDED_TITLE = "Source Preview Test Episode"


@pytest.fixture(autouse=True)
async def _seed(db_session):
    db_session.add_all(
        [
            TranscriptChunk(
                source_title=SEEDED_TITLE,
                source_url="https://example.local/preview",
                chunk_index=i,
                content=f"Excerpt number {i} about activation and onboarding.",
            )
            for i in range(3)
        ]
    )
    await db_session.commit()
    yield
    await db_session.execute(
        delete(TranscriptChunk).where(TranscriptChunk.source_title == SEEDED_TITLE)
    )
    await db_session.commit()


async def test_returns_excerpts_in_chunk_order(client):
    resp = await client.get("/api/sources", params={"title": SEEDED_TITLE})
    assert resp.status_code == 200
    body = resp.json()
    assert body["title"] == SEEDED_TITLE
    assert body["url"] == "https://example.local/preview"
    assert [e["chunk_index"] for e in body["excerpts"]] == [0, 1, 2]
    assert "activation" in body["excerpts"][0]["content"]


async def test_limit_is_respected(client):
    resp = await client.get("/api/sources", params={"title": SEEDED_TITLE, "limit": 2})
    assert resp.status_code == 200
    assert len(resp.json()["excerpts"]) == 2


async def test_unknown_title_degrades_instead_of_erroring(client):
    """A citation can outlive a corpus edit; a side panel shouldn't throw."""
    resp = await client.get("/api/sources", params={"title": "No Such Episode"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["excerpts"] == []
    assert body["url"] is None


async def test_missing_title_is_a_validation_error(client):
    resp = await client.get("/api/sources")
    assert resp.status_code == 422
    assert isinstance(resp.json()["detail"], str)
