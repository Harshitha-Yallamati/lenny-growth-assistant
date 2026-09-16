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
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas import KnowledgeBaseStats, SourceDetailResponse, SourceExcerpt
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


@router.get("/stats", response_model=KnowledgeBaseStats)
async def knowledge_base_stats(db: AsyncSession = Depends(get_db)) -> KnowledgeBaseStats:
    """Corpus size for the status dashboard.

    Read-only counts over the same `chunks` table retrieval reads; it does not
    touch retrieval itself. Exposed here rather than folded into /api/health
    so the existing health contract stays exactly as it is.
    """
    total = await db.execute(select(func.count()).select_from(TranscriptChunk))
    titles = await db.execute(
        select(TranscriptChunk.source_title)
        .distinct()
        .order_by(TranscriptChunk.source_title)
    )
    source_titles = [row[0] for row in titles.all()]
    return KnowledgeBaseStats(
        chunk_count=total.scalar() or 0,
        source_count=len(source_titles),
        sources=source_titles,
    )
