"""Embedding and vector persistence layer for indexed chunk artifacts."""

from .chroma_store import (
    DEFAULT_CHROMA_COLLECTION_NAME,
    DEFAULT_CHROMA_PERSIST_DIR,
    persist_embeddings,
)
from .embeddings import (
    DEFAULT_EMBED_BATCH_SIZE,
    DEFAULT_EMBEDDING_MODEL,
    build_embeddings,
    embed_batch,
    should_embed,
)
from .models import EmbeddingRecord
from .pipeline import (
    build_and_persist_embeddings_from_chunk_dir,
    build_and_persist_embeddings_from_chunk_paths,
    load_chunk_artifacts,
    load_chunk_artifacts_from_dir,
)

__all__ = [
    "DEFAULT_CHROMA_COLLECTION_NAME",
    "DEFAULT_CHROMA_PERSIST_DIR",
    "DEFAULT_EMBED_BATCH_SIZE",
    "DEFAULT_EMBEDDING_MODEL",
    "EmbeddingRecord",
    "build_and_persist_embeddings_from_chunk_dir",
    "build_and_persist_embeddings_from_chunk_paths",
    "build_embeddings",
    "embed_batch",
    "load_chunk_artifacts",
    "load_chunk_artifacts_from_dir",
    "persist_embeddings",
    "should_embed",
]
