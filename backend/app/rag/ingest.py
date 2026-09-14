"""Loads the curated transcript corpus from /app/data into the `chunks` table.

Idempotent: re-running clears and re-inserts chunks per source, so it's safe
to call on every startup (cheap for a corpus this small) and to re-run after
editing data/sources.json.
"""

import json
import logging
from pathlib import Path

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.models import TranscriptChunk

logger = logging.getLogger(__name__)

TARGET_WORDS_PER_CHUNK = 180


def _data_dir() -> Path:
    return Path(get_settings().data_dir)


def _chunk_text(text: str, target_words: int = TARGET_WORDS_PER_CHUNK) -> list[str]:
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    chunks: list[str] = []
    current: list[str] = []
    current_words = 0

    for para in paragraphs:
        para_words = len(para.split())
        if current and current_words + para_words > target_words:
            chunks.append("\n\n".join(current))
            current, current_words = [], 0
        current.append(para)
        current_words += para_words

    if current:
        chunks.append("\n\n".join(current))
    return chunks


async def ingest_transcripts(db: AsyncSession) -> int:
    data_dir = _data_dir()
    manifest_path = data_dir / "sources.json"
    if not manifest_path.exists():
        logger.warning("ingest_no_manifest", extra={"event": "ingest_no_manifest"})
        return 0

    sources = json.loads(manifest_path.read_text(encoding="utf-8"))
    total_chunks = 0

    for source in sources:
        title = source["title"]
        url = source["url"]
        transcript_path = data_dir / "transcripts" / source["file"]
        if not transcript_path.exists():
            logger.warning(
                "ingest_missing_file",
                extra={"event": "ingest_missing_file", "provider": source["file"]},
            )
            continue

        text = transcript_path.read_text(encoding="utf-8")
        pieces = _chunk_text(text)

        await db.execute(delete(TranscriptChunk).where(TranscriptChunk.source_title == title))
        for idx, piece in enumerate(pieces):
            db.add(
                TranscriptChunk(
                    source_title=title,
                    source_url=url,
                    chunk_index=idx,
                    content=piece,
                )
            )
        total_chunks += len(pieces)

    await db.commit()
    logger.info("ingest_complete", extra={"event": "ingest_complete"})
    return total_chunks


async def needs_ingestion(db: AsyncSession) -> bool:
    result = await db.execute(select(func.count()).select_from(TranscriptChunk))
    return (result.scalar() or 0) == 0
