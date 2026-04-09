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
    DEFAULT_BM25_PERSIST_DIR,
    DEFAULT_INDEX_REGISTRY_PATH,
    DEFAULT_STRUCTURED_STORE_DIR,
    INDEX_CONFIG,
    SOURCE_ID_TO_LOGICAL_STORE,
    SOURCE_STORE_CONFIG,
    SOURCE_ID_TO_INDEX_NAME,
    build_index_registry_payload,
    group_chunks_by_index_name,
    index_name_for_source,
    write_index_registry,
)
from .load_index_registry import (
    get_allowed_agents,
    get_backends,
    get_entry_by_logical_store_name,
    get_logical_store_name,
    get_registry_entry,
    is_indexed_source,
    is_structured_source,
    list_indexed_sources,
    list_structured_sources,
    load_index_registry,
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
    "SOURCE_ID_TO_LOGICAL_STORE",
    "SOURCE_STORE_CONFIG",
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
    "get_allowed_agents",
    "get_backends",
    "get_entry_by_logical_store_name",
    "get_logical_store_name",
    "get_registry_entry",
    "group_chunks_by_index_name",
    "index_name_for_source",
    "is_indexed_source",
    "is_structured_source",
    "list_indexed_sources",
    "list_structured_sources",
    "load_chunk_artifacts",
    "load_chunk_artifacts_from_dir",
    "load_index_registry",
    "metadata_from_chunk",
    "should_embed",
    "tokenize",
    "vector_records_from_embeddings",
    "write_index_registry",
]
