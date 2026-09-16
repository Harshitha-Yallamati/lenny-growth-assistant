"""Read-only lookup of a source's transcript excerpts, for the UI's citation
preview.

Purely additive: retrieval, the orchestrator and the skills are untouched,
and `to_citations()` still emits the same `{title, url}` shape it always has.
Doing it this way (rather than fattening the citation payload) means the
preview also works for messages that were persisted before this endpoint
existed -- their citations already carry the title, which is all the lookup
needs.
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas import SourceDetailResponse, SourceExcerpt
from app.db.models import TranscriptChunk
from app.db.session import get_db

router = APIRouter(prefix="/api/sources", tags=["sources"])


@router.get("", response_model=SourceDetailResponse)
async def get_source(
    title: str = Query(..., description="Exact source_title as it appears in a citation"),
    limit: int = Query(6, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
) -> SourceDetailResponse:
    result = await db.execute(
        select(TranscriptChunk)
        .where(TranscriptChunk.source_title == title)
        .order_by(TranscriptChunk.chunk_index)
        .limit(limit)
    )
    chunks = list(result.scalars().all())

    # An unknown title isn't an error worth a 404 here -- a citation can
    # outlive a corpus edit, and the viewer should degrade to "no excerpts"
    # rather than throwing inside a side panel.
    return SourceDetailResponse(
        title=title,
        url=chunks[0].source_url if chunks else None,
        total_chunks=len(chunks),
        excerpts=[
            SourceExcerpt(chunk_index=c.chunk_index, content=c.content) for c in chunks
        ],
    )
