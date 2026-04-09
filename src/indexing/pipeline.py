"""Pipeline entrypoints for building and persisting embeddings from chunk artifacts."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from chunking import Chunk
from chunking.artifacts import DEFAULT_CHUNK_ARTIFACT_DIR

from .chroma_store import (
    DEFAULT_CHROMA_COLLECTION_NAME,
    DEFAULT_CHROMA_PERSIST_DIR,
    persist_embeddings,
)
from .embeddings import DEFAULT_EMBED_BATCH_SIZE, DEFAULT_EMBEDDING_MODEL, build_embeddings
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
    collection_name: str = DEFAULT_CHROMA_COLLECTION_NAME,
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
        collection_name=collection_name,
        client=client,
    )
    return records


def build_and_persist_embeddings_from_chunk_dir(
    artifact_dir: str | Path = DEFAULT_CHUNK_ARTIFACT_DIR,
    *,
    persist_directory: str | Path = DEFAULT_CHROMA_PERSIST_DIR,
    collection_name: str = DEFAULT_CHROMA_COLLECTION_NAME,
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
        collection_name=collection_name,
        model_name=model_name,
        batch_size=batch_size,
        embed_texts=embed_texts,
        client=client,
    )
