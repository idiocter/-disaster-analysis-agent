"""Exercises the real ingest -> pgvector -> retriever pipeline against the
live PostGIS container and the local sentence-transformers embedding model
(no external API key needed for either). Uses temp .md files rather than
the actual rag_corpus/ docs so tests don't depend on that corpus's content
or leave permanent rows behind from re-running against the same files.
"""

import uuid

from sqlalchemy import select

from src.data.models import RagChunk, RagDocument
from src.data.postgis_repo import async_session_factory
from src.rag.ingest import chunk_text, ingest_document
from src.rag.retriever import rag_retrieve


def test_chunk_text_merges_short_paragraphs_forward():
    text = "Short.\n\nAlso short.\n\n" + ("B" * 150) + "\n\n" + ("C" * 150)
    chunks = chunk_text(text)

    # The two short paragraphs (under the min-chars threshold on their own)
    # get absorbed into the buffer along with the next paragraph until the
    # combined length crosses the threshold, THEN flush as one chunk --
    # never emitted as their own tiny fragments.
    assert len(chunks) == 2
    assert "Short." in chunks[0]
    assert "Also short." in chunks[0]
    assert "B" * 150 in chunks[0]
    assert chunks[1] == "C" * 150


async def test_ingest_document_creates_document_and_chunks(tmp_path):
    title = f"Test Doc {uuid.uuid4().hex[:8]}"
    doc_path = tmp_path / "test_doc.md"
    doc_path.write_text(
        "# Test Doc\n\n" + ("Paragraph one about landslide risk. " * 10) + "\n\n" + ("Paragraph two about rainfall. " * 10)
    )

    async with async_session_factory() as session:
        count = await ingest_document(session, title=title, source_type="reference_doc", file_path=str(doc_path))
        assert count > 0

        doc_result = await session.execute(select(RagDocument).where(RagDocument.source_title == title))
        docs = doc_result.scalars().all()
        assert len(docs) == 1

        chunk_result = await session.execute(select(RagChunk).where(RagChunk.document_id == docs[0].id))
        chunks = chunk_result.scalars().all()
        assert len(chunks) == count


async def test_retrieval_finds_semantically_relevant_chunk(tmp_path):
    unique_marker = uuid.uuid4().hex[:8]
    doc_path = tmp_path / "landslide_doc.md"
    doc_path.write_text(
        f"# Landslide Risk {unique_marker}\n\n"
        + "Deforestation on steep slopes reduces root cohesion and increases landslide "
        "risk during intense monsoon rainfall in mountainous terrain. " * 5
        + "\n\n"
        + "Unrelated paragraph about database indexing performance tuning strategies. " * 5
    )

    async with async_session_factory() as session:
        await ingest_document(
            session, title=f"Landslide Doc {unique_marker}", source_type="reference_doc", file_path=str(doc_path)
        )
        results = await rag_retrieve(session, "why does cutting down trees on hillsides cause landslides", k=1)

    assert len(results) == 1
    assert "root cohesion" in results[0] or "landslide" in results[0].lower()
