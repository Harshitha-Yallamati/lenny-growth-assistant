"""Manual re-ingestion entrypoint. The backend also auto-ingests on startup
if the `chunks` table is empty; run this directly after editing
data/sources.json or a transcript file to refresh the knowledge base without
restarting the server.

Usage (inside the backend container or a matching local venv):
    python -m scripts.ingest_transcripts
"""

import asyncio

from app.db.session import AsyncSessionLocal
from app.rag.ingest import ingest_transcripts


async def main() -> None:
    async with AsyncSessionLocal() as db:
        count = await ingest_transcripts(db)
        print(f"Ingested {count} chunks.")


if __name__ == "__main__":
    asyncio.run(main())
