"""Phase 6 CLI: ingests rag_corpus/*.md into the pgvector-backed rag_chunks
table.

Usage:
    uv run python scripts/ingest_rag_docs.py
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.data.postgis_repo import async_session_factory  # noqa: E402
from src.rag.ingest import ingest_corpus_dir  # noqa: E402


async def main() -> None:
    async with async_session_factory() as session:
        total = await ingest_corpus_dir(session, "rag_corpus")
    print(f"total chunks ingested: {total}")


if __name__ == "__main__":
    asyncio.run(main())
