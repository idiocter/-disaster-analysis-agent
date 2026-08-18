"""Local embedding model -- no API key needed, runs fully offline. Same
model choice as autonomous-dev-agent's RAG for consistency; swap via
EMBEDDING_PROVIDER in config.py for a hosted alternative (Voyage/OpenAI)
later. Must match src/data/models.py's EMBEDDING_DIM (384).
"""

from sentence_transformers import SentenceTransformer

EMBEDDING_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"

_model: SentenceTransformer | None = None


def get_model() -> SentenceTransformer:
    global _model
    if _model is None:
        _model = SentenceTransformer(EMBEDDING_MODEL_NAME)
    return _model


def embed_texts(texts: list[str]) -> list[list[float]]:
    if not texts:
        return []
    model = get_model()
    vectors = model.encode(texts, convert_to_numpy=True, show_progress_bar=False)
    return vectors.tolist()


def embed_query(text: str) -> list[float]:
    return embed_texts([text])[0]
