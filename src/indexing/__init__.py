"""Embedding, storage, and indexing layer for governed retrieval artifacts."""

from .build_bm25_index import BM25Index, build_bm25_indices, tokenize
from .build_structured_store import (
    DEFAULT_STRUCTURED_STORE_NAME,
    StructuredStore,
    build_structured_store,
)
from .build_vector_index import (
    DEFAULT_CHROMA_PERSIST_DIR,
    DEFAULT_VECTOR_REGISTRY_DIR,
    VectorIndex,
    build_vector_indices,
    vector_records_from_embeddings,
)
from .embeddings import (
    DEFAULT_EMBED_BATCH_SIZE,
    DEFAULT_EMBEDDING_MODEL,
    build_embeddings,
    embed_batch,
    should_embed,
)
from .index_registry import (
    ACCESS_MATRIX,
    DEFAULT_BM25_PERSIST_DIR,
    DEFAULT_INDEX_REGISTRY_PATH,
    DEFAULT_STRUCTURED_STORE_DIR,
    INDEX_CONFIG,
    SOURCE_ID_TO_INDEX_NAME,
    build_index_registry_payload,
    index_name_for_source,
)
from .metadata_schema import metadata_from_chunk
from .models import EmbeddingRecord
from .pipeline import (
    build_and_persist_embeddings_from_chunk_dir,
    build_and_persist_embeddings_from_chunk_paths,
    build_storage_indices,
    load_chunk_artifacts,
    load_chunk_artifacts_from_dir,
)

__all__ = [
    "ACCESS_MATRIX",
    "BM25Index",
    "DEFAULT_BM25_PERSIST_DIR",
    "DEFAULT_CHROMA_PERSIST_DIR",
    "DEFAULT_EMBED_BATCH_SIZE",
    "DEFAULT_EMBEDDING_MODEL",
    "DEFAULT_INDEX_REGISTRY_PATH",
    "DEFAULT_STRUCTURED_STORE_DIR",
    "DEFAULT_STRUCTURED_STORE_NAME",
    "DEFAULT_VECTOR_REGISTRY_DIR",
    "EmbeddingRecord",
    "INDEX_CONFIG",
    "SOURCE_ID_TO_INDEX_NAME",
    "StructuredStore",
    "VectorIndex",
    "build_and_persist_embeddings_from_chunk_dir",
    "build_and_persist_embeddings_from_chunk_paths",
    "build_embeddings",
    "build_bm25_indices",
    "build_index_registry_payload",
    "build_storage_indices",
    "build_structured_store",
    "build_vector_indices",
    "embed_batch",
    "index_name_for_source",
    "load_chunk_artifacts",
    "load_chunk_artifacts_from_dir",
    "metadata_from_chunk",
    "should_embed",
    "tokenize",
    "vector_records_from_embeddings",
]
