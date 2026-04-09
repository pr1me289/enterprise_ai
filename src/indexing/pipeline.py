"""Pipeline entrypoints for building and persisting embeddings from chunk artifacts."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from chunking import Chunk
from chunking.artifacts import DEFAULT_CHUNK_ARTIFACT_DIR

from .build_bm25_index import BM25Index, build_bm25_indices
from .build_structured_store import DEFAULT_STRUCTURED_STORE_NAME, StructuredStore, build_structured_store
from .build_vector_index import persist_embeddings
from .build_vector_index import VectorIndex, build_vector_indices, vector_records_from_embeddings
from .embeddings import DEFAULT_EMBED_BATCH_SIZE, DEFAULT_EMBEDDING_MODEL, build_embeddings
from .index_registry import (
    DEFAULT_BM25_PERSIST_DIR,
    DEFAULT_CHROMA_PERSIST_DIR,
    DEFAULT_INDEX_REGISTRY_PATH,
    DEFAULT_STRUCTURED_STORE_DIR,
    DEFAULT_VECTOR_REGISTRY_DIR,
    build_index_registry_payload,
    group_chunks_by_index_name,
    write_index_registry,
)
from .models import EmbeddingRecord


def load_chunk_artifacts(paths: list[str | Path]) -> list[Chunk]:
    """Load chunk artifacts from JSON files into canonical Chunk objects."""

    chunks: list[Chunk] = []
    for artifact_path in sorted(Path(path) for path in paths):
        payload = json.loads(artifact_path.read_text(encoding="utf-8"))
        file_chunks = [Chunk.from_dict(item) for item in payload]
        file_chunks.sort(key=lambda chunk: (chunk.chunk_order, chunk.chunk_id))
        chunks.extend(file_chunks)
    return chunks


def load_chunk_artifacts_from_dir(
    artifact_dir: str | Path = DEFAULT_CHUNK_ARTIFACT_DIR,
) -> list[Chunk]:
    """Load all chunk artifacts from the default artifact directory."""

    artifact_paths = sorted(Path(artifact_dir).glob("*.json"))
    return load_chunk_artifacts(list(artifact_paths))


def build_and_persist_embeddings_from_chunk_paths(
    paths: list[str | Path],
    *,
    persist_directory: str | Path = DEFAULT_CHROMA_PERSIST_DIR,
    registry_directory: str | Path = DEFAULT_VECTOR_REGISTRY_DIR,
    collection_name: str = "enterprise_ai_chunks",
    model_name: str = DEFAULT_EMBEDDING_MODEL,
    batch_size: int = DEFAULT_EMBED_BATCH_SIZE,
    embed_texts: Any | None = None,
    client: Any | None = None,
) -> list[EmbeddingRecord]:
    """Load finalized chunk artifacts, embed eligible chunks, and persist them to Chroma."""

    chunks = load_chunk_artifacts(paths)
    records = build_embeddings(
        chunks,
        embed_texts=embed_texts,
        model_name=model_name,
        batch_size=batch_size,
    )
    persist_embeddings(
        records,
        persist_directory=persist_directory,
        registry_directory=registry_directory,
        collection_name=collection_name,
        client=client,
    )
    return records


def build_and_persist_embeddings_from_chunk_dir(
    artifact_dir: str | Path = DEFAULT_CHUNK_ARTIFACT_DIR,
    *,
    persist_directory: str | Path = DEFAULT_CHROMA_PERSIST_DIR,
    registry_directory: str | Path = DEFAULT_VECTOR_REGISTRY_DIR,
    collection_name: str = "enterprise_ai_chunks",
    model_name: str = DEFAULT_EMBEDDING_MODEL,
    batch_size: int = DEFAULT_EMBED_BATCH_SIZE,
    embed_texts: Any | None = None,
    client: Any | None = None,
) -> list[EmbeddingRecord]:
    """Embed every chunk artifact in the default artifact directory and persist them."""

    artifact_paths = sorted(Path(artifact_dir).glob("*.json"))
    return build_and_persist_embeddings_from_chunk_paths(
        list(artifact_paths),
        persist_directory=persist_directory,
        registry_directory=registry_directory,
        collection_name=collection_name,
        model_name=model_name,
        batch_size=batch_size,
        embed_texts=embed_texts,
        client=client,
    )


def build_storage_indices(
    *,
    chunk_artifact_dir: str | Path = DEFAULT_CHUNK_ARTIFACT_DIR,
    questionnaire_path: str | Path,
    chroma_persist_directory: str | Path = DEFAULT_CHROMA_PERSIST_DIR,
    vector_registry_directory: str | Path = DEFAULT_VECTOR_REGISTRY_DIR,
    bm25_persist_directory: str | Path = DEFAULT_BM25_PERSIST_DIR,
    structured_store_directory: str | Path = DEFAULT_STRUCTURED_STORE_DIR,
    index_registry_path: str | Path = DEFAULT_INDEX_REGISTRY_PATH,
    model_name: str = DEFAULT_EMBEDDING_MODEL,
    batch_size: int = DEFAULT_EMBED_BATCH_SIZE,
    embed_texts: Any | None = None,
) -> dict[str, Any]:
    chunks = load_chunk_artifacts_from_dir(chunk_artifact_dir)
    chunk_groups = group_chunks_by_index_name(chunks)

    embedding_records = build_embeddings(
        chunks,
        embed_texts=embed_texts,
        model_name=model_name,
        batch_size=batch_size,
    )
    embeddings_by_chunk_id = {
        record.chunk_id: record.embedding
        for record in embedding_records
    }

    vector_records = {
        index_name: vector_records_from_embeddings(grouped_chunks, embeddings_by_chunk_id)
        for index_name, grouped_chunks in chunk_groups.items()
    }
    vector_index = VectorIndex(
        persist_directory=chroma_persist_directory,
        registry_directory=vector_registry_directory,
        model_name=model_name,
    )
    vector_counts = build_vector_indices(vector_records, vector_index=vector_index)

    bm25_index = BM25Index(persist_directory=bm25_persist_directory)
    bm25_counts = build_bm25_indices(chunk_groups, bm25_index=bm25_index)

    structured_store = StructuredStore(output_dir=structured_store_directory)
    structured_store_path = build_structured_store(
        questionnaire_path,
        store=structured_store,
        store_name=DEFAULT_STRUCTURED_STORE_NAME,
    )

    registry_payload = build_index_registry_payload(
        chunk_groups=chunk_groups,
        structured_store_path=structured_store_path,
        bm25_persist_directory=bm25_persist_directory,
    )
    registry_path = write_index_registry(registry_payload, path=index_registry_path)

    return {
        "vector_counts": vector_counts,
        "bm25_counts": bm25_counts,
        "structured_store_path": Path(structured_store_path),
        "index_registry_path": registry_path,
    }
