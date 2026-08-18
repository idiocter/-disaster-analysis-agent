"""Ingests documents from rag_corpus/ into the pgvector-backed rag_chunks
table -- historical/reference environmental and disaster-risk docs that
ground the narrative agent's explanations. Chunking is simple
paragraph-based (good enough for short prose reference docs); the
AST-aware chunking autonomous-dev-agent uses for code isn't relevant here.
"""

import re
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from src.data.models import RagChunk, RagDocument
from src.rag.embeddings import embed_texts

_MIN_CHUNK_CHARS = 100


def chunk_text(text: str) -> list[str]:
    """Splits on blank lines (paragraphs/headings), merging short fragments
    forward so each chunk carries enough context to be independently
    useful as a retrieval result.
    """
    raw_parts = re.split(r"\n\s*\n", text.strip())
    chunks: list[str] = []
    buffer = ""
    for part in raw_parts:
        part = part.strip()
        if not part:
            continue
        buffer = f"{buffer}\n\n{part}" if buffer else part
        if len(buffer) >= _MIN_CHUNK_CHARS:
            chunks.append(buffer)
            buffer = ""
    if buffer:
        chunks.append(buffer)
    return chunks


async def ingest_document(session: AsyncSession, *, title: str, source_type: str, file_path: str) -> int:
    text = Path(file_path).read_text(encoding="utf-8")
    chunks = chunk_text(text)
    if not chunks:
        return 0

    doc = RagDocument(source_title=title, source_type=source_type)
    session.add(doc)
    await session.flush()  # need doc.id before building the FK'd chunk rows

    embeddings = embed_texts(chunks)
    for chunk, vector in zip(chunks, embeddings):
        session.add(
            RagChunk(
                document_id=doc.id,
                chunk_text=chunk,
                embedding=vector,
                metadata_json={"source_file": file_path},
            )
        )
    await session.commit()
    return len(chunks)


async def ingest_corpus_dir(session: AsyncSession, corpus_dir: str) -> int:
    total = 0
    for path in sorted(Path(corpus_dir).glob("*.md")):
        count = await ingest_document(
            session,
            title=path.stem.replace("_", " ").title(),
            source_type="reference_doc",
            file_path=str(path),
        )
        total += count
        print(f"ingested {count} chunks from {path.name}")
    return total
