"""Embedding helpers for finalized chunk records."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Any

from chunking import Chunk

from .models import EmbeddingRecord


DEFAULT_EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
DEFAULT_EMBED_BATCH_SIZE = 32

EmbedTextsFn = Callable[[Sequence[str]], Sequence[Sequence[float]]]

_MODEL_CACHE: dict[str, Any] = {}


def should_embed(chunk: Chunk) -> bool:
    """Return True only for chunks in the indexed semantic lane."""

    return chunk.retrieval_lane == "INDEXED_HYBRID"


def build_embeddings(
    chunks: Sequence[Chunk],
    *,
    embed_texts: EmbedTextsFn | None = None,
    model_name: str = DEFAULT_EMBEDDING_MODEL,
    batch_size: int = DEFAULT_EMBED_BATCH_SIZE,
) -> list[EmbeddingRecord]:
    """Embed eligible chunks in deterministic order and return vector records."""

    eligible_chunks = sorted(
        (chunk for chunk in chunks if should_embed(chunk)),
        key=lambda chunk: (chunk.source_id, chunk.chunk_order, chunk.chunk_id),
    )
    if not eligible_chunks:
        return []

    texts = [chunk.text for chunk in eligible_chunks]
    raw_embeddings = (
        embed_texts(texts)
        if embed_texts is not None
        else embed_batch(texts, model_name=model_name, batch_size=batch_size)
    )
    embeddings = [list(vector) for vector in raw_embeddings]
    if len(embeddings) != len(eligible_chunks):
        raise ValueError("Embedding count does not match eligible chunk count.")

    return [
        EmbeddingRecord.from_chunk(chunk, embedding)
        for chunk, embedding in zip(eligible_chunks, embeddings, strict=True)
    ]


def embed_batch(
    texts: Sequence[str],
    *,
    model_name: str = DEFAULT_EMBEDDING_MODEL,
    batch_size: int = DEFAULT_EMBED_BATCH_SIZE,
    model: Any | None = None,
) -> list[list[float]]:
    """Embed a batch of texts with the configured sentence-transformer model."""

    if not texts:
        return []

    encoder = model or _load_embedding_model(model_name)
    embeddings = encoder.encode(
        list(texts),
        batch_size=batch_size,
        show_progress_bar=False,
        convert_to_numpy=True,
    )
    return embeddings.tolist()


def _load_embedding_model(model_name: str) -> Any:
    if model_name not in _MODEL_CACHE:
        from sentence_transformers import SentenceTransformer

        _MODEL_CACHE[model_name] = SentenceTransformer(model_name)
    return _MODEL_CACHE[model_name]
