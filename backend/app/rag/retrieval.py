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


async def retrieve(
    db: AsyncSession, query: str, top_k: int = 5, min_rank: float = 0.03
) -> list[RetrievedChunk]:
    """Rank chunks against a natural-language question.

    `plainto_tsquery` ANDs every lexeme together, which is wrong for
    conversational RAG: "how do I know if I have product-market fit" would
    require the word "know" to appear in a chunk alongside the actual topic,
    so most real questions returned nothing and the assistant claimed the
    knowledge base didn't cover them. We keep plainto_tsquery for its safe
    parsing/stemming/stopword handling, then rewrite its `&` operators to `|`
    so partial matches are allowed and `ts_rank` decides what's actually
    relevant. `min_rank` then filters the long tail of chunks that share only
    an incidental common word -- measured on this corpus, a genuine topical
    question tops out around 0.08 while an off-topic one ("weather in Tokyo")
    scrapes ~0.02, so the floor is what keeps "not grounded" honest.
    """
    result = await db.execute(
        text(
            """
            WITH q AS (
                SELECT replace(plainto_tsquery('english', :query)::text, '&', '|')::tsquery AS tsq
            )
            SELECT source_title, source_url, content,
                   ts_rank(content_tsv, q.tsq) AS rank
            FROM chunks, q
            WHERE content_tsv @@ q.tsq
              AND ts_rank(content_tsv, q.tsq) >= :min_rank
            ORDER BY rank DESC
            LIMIT :top_k
            """
        ),
        {"query": query, "top_k": top_k, "min_rank": min_rank},
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
