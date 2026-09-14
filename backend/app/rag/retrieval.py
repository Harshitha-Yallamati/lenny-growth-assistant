"""Retrieval over the transcript knowledge base using PostgreSQL's built-in
full-text search (tsvector/ts_rank) instead of a vector database.

Trade-off (documented in architecture.md): this trades semantic/paraphrase
recall for zero extra infrastructure -- no embedding model to download, no
pgvector extension, no dimension config, and it reuses the Postgres instance
we already need for persistence. Good enough for a small, curated corpus;
the natural upgrade path is pgvector + a local embedding model.
"""

from dataclasses import dataclass

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


@dataclass
class RetrievedChunk:
    source_title: str
    source_url: str
    content: str
    rank: float


async def retrieve(db: AsyncSession, query: str, top_k: int = 5) -> list[RetrievedChunk]:
    result = await db.execute(
        text(
            """
            SELECT source_title, source_url, content,
                   ts_rank(content_tsv, plainto_tsquery('english', :query)) AS rank
            FROM chunks
            WHERE content_tsv @@ plainto_tsquery('english', :query)
            ORDER BY rank DESC
            LIMIT :top_k
            """
        ),
        {"query": query, "top_k": top_k},
    )
    rows = result.mappings().all()
    return [
        RetrievedChunk(
            source_title=row["source_title"],
            source_url=row["source_url"],
            content=row["content"],
            rank=float(row["rank"]),
        )
        for row in rows
    ]


def format_context(chunks: list[RetrievedChunk]) -> str:
    if not chunks:
        return ""
    blocks = []
    for chunk in chunks:
        blocks.append(f"[Source: {chunk.source_title}]\n{chunk.content}")
    return "\n\n---\n\n".join(blocks)


def to_citations(chunks: list[RetrievedChunk]) -> list[dict]:
    seen = set()
    citations = []
    for chunk in chunks:
        if chunk.source_title in seen:
            continue
        seen.add(chunk.source_title)
        citations.append({"title": chunk.source_title, "url": chunk.source_url})
    return citations
