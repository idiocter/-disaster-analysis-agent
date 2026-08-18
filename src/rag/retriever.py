"""Similarity search against the rag_chunks pgvector table."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.data.models import RagChunk
from src.rag.embeddings import embed_query


async def rag_retrieve(session: AsyncSession, query: str, k: int = 5) -> list[str]:
    query_vector = embed_query(query)
    result = await session.execute(
        select(RagChunk).order_by(RagChunk.embedding.cosine_distance(query_vector)).limit(k)
    )
    return [row.chunk_text for row in result.scalars().all()]
