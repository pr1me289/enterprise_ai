"""Compatibility exports for the vector index wrapper."""

from .build_vector_index import (
    VectorIndex,
    build_vector_indices,
    persist_embeddings,
    vector_records_from_embeddings,
)
from .index_registry import DEFAULT_CHROMA_PERSIST_DIR, DEFAULT_VECTOR_REGISTRY_DIR

__all__ = [
    "DEFAULT_CHROMA_PERSIST_DIR",
    "DEFAULT_VECTOR_REGISTRY_DIR",
    "VectorIndex",
    "build_vector_indices",
    "persist_embeddings",
    "vector_records_from_embeddings",
]
