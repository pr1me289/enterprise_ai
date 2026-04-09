"""Persistence helpers for storing embedding records in Chroma."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import Any

from .models import EmbeddingRecord


DEFAULT_CHROMA_PERSIST_DIR = Path("data/indexes/chroma")
DEFAULT_CHROMA_COLLECTION_NAME = "enterprise_ai_chunks"


def persist_embeddings(
    records: Sequence[EmbeddingRecord],
    *,
    persist_directory: str | Path = DEFAULT_CHROMA_PERSIST_DIR,
    collection_name: str = DEFAULT_CHROMA_COLLECTION_NAME,
    client: Any | None = None,
) -> int:
    """Persist embedding records into a Chroma collection."""

    if not records:
        return 0

    chroma_client = client or _build_persistent_client(persist_directory)
    collection = chroma_client.get_or_create_collection(name=collection_name)
    collection.upsert(
        ids=[record.chunk_id for record in records],
        embeddings=[record.embedding for record in records],
        metadatas=[record.metadata() for record in records],
        documents=[record.text for record in records],
    )
    return len(records)


def _build_persistent_client(persist_directory: str | Path) -> Any:
    from chromadb import PersistentClient

    persist_path = Path(persist_directory)
    persist_path.mkdir(parents=True, exist_ok=True)
    return PersistentClient(path=str(persist_path))
