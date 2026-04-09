"""Per-source Chroma collection building and query helpers."""

from __future__ import annotations

import json
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from chunking import Chunk

from .embeddings import DEFAULT_EMBEDDING_MODEL, embed_batch
from .index_registry import DEFAULT_CHROMA_PERSIST_DIR, DEFAULT_VECTOR_REGISTRY_DIR
from .metadata_schema import (
    chroma_metadata_from_chunk,
    metadata_from_chunk,
    metadata_matches_filter,
    parse_allowed_agents,
    split_chroma_and_fallback_filters,
)


class VectorIndex:
    """Thin wrapper around Chroma collections for per-source vector search."""

    def __init__(
        self,
        *,
        persist_directory: str | Path = DEFAULT_CHROMA_PERSIST_DIR,
        registry_directory: str | Path = DEFAULT_VECTOR_REGISTRY_DIR,
        model_name: str = DEFAULT_EMBEDDING_MODEL,
        client: Any | None = None,
    ) -> None:
        self.persist_directory = Path(persist_directory)
        self.registry_directory = Path(registry_directory)
        self.model_name = model_name
        self._client = client
        self._registry_cache: dict[str, dict[str, dict[str, Any]]] = {}

    @property
    def client(self) -> Any:
        if self._client is None:
            from chromadb import PersistentClient

            self.persist_directory.mkdir(parents=True, exist_ok=True)
            self._client = PersistentClient(path=str(self.persist_directory))
        return self._client

    def add_chunks(self, collection_name: str, records: Sequence[dict[str, Any]]) -> int:
        if not records:
            return 0

        collection = self.client.get_or_create_collection(name=collection_name)
        collection.upsert(
            ids=[record["chunk_id"] for record in records],
            documents=[record["text"] for record in records],
            embeddings=[record["embedding"] for record in records],
            metadatas=[record["metadata"] for record in records],
        )
        self._write_registry(collection_name, records)
        return len(records)

    def query(
        self,
        collection_name: str,
        query_text: str,
        *,
        k: int,
        where: dict[str, Any] | None = None,
        allowed_agent: str | None = None,
    ) -> list[dict[str, Any]]:
        chroma_where, fallback_filter = split_chroma_and_fallback_filters(where)
        n_results = max(k * 3, k)
        query_embedding = embed_batch([query_text], model_name=self.model_name)[0]
        collection = self.client.get_collection(name=collection_name)
        response = collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            where=chroma_where,
        )

        ids = response.get("ids", [[]])[0]
        documents = response.get("documents", [[]])[0]
        metadatas = response.get("metadatas", [[]])[0]
        distances = response.get("distances", [[]])[0]

        hits: list[dict[str, Any]] = []
        for chunk_id, document, metadata, distance in zip(ids, documents, metadatas, distances, strict=False):
            normalized_metadata = self._normalize_metadata(metadata, document)
            if allowed_agent and allowed_agent not in normalized_metadata["allowed_agents"]:
                continue
            if not metadata_matches_filter(normalized_metadata, fallback_filter):
                continue
            hits.append(
                {
                    "chunk_id": chunk_id,
                    "text": document,
                    "source_id": normalized_metadata["source_id"],
                    "source_type": normalized_metadata["source_type"],
                    "authority_tier": normalized_metadata["authority_tier"],
                    "freshness_status": normalized_metadata["freshness_status"],
                    "allowed_agents": normalized_metadata["allowed_agents"],
                    "backend": "vector",
                    "score": 1.0 / (1.0 + float(distance)),
                    "metadata": normalized_metadata,
                }
            )
            if len(hits) == k:
                break
        return hits

    def get_by_ids(self, collection_name: str, ids: Sequence[str]) -> list[dict[str, Any]]:
        if not ids:
            return []
        registry = self._load_registry(collection_name)
        return [registry[chunk_id] for chunk_id in ids if chunk_id in registry]

    def _write_registry(self, collection_name: str, records: Sequence[dict[str, Any]]) -> None:
        self.registry_directory.mkdir(parents=True, exist_ok=True)
        registry_payload = [
            {
                "chunk_id": record["chunk_id"],
                "text": record["text"],
                "metadata": record["registry_metadata"],
            }
            for record in records
        ]
        (self.registry_directory / f"{collection_name}.json").write_text(
            json.dumps(registry_payload, indent=2, ensure_ascii=True) + "\n",
            encoding="utf-8",
        )
        self._registry_cache.pop(collection_name, None)

    def _load_registry(self, collection_name: str) -> dict[str, dict[str, Any]]:
        if collection_name not in self._registry_cache:
            registry_path = self.registry_directory / f"{collection_name}.json"
            payload = json.loads(registry_path.read_text(encoding="utf-8"))
            self._registry_cache[collection_name] = {
                item["chunk_id"]: item for item in payload
            }
        return self._registry_cache[collection_name]

    def _normalize_metadata(self, metadata: dict[str, Any], text: str) -> dict[str, Any]:
        normalized = dict(metadata)
        normalized["allowed_agents"] = parse_allowed_agents(metadata.get("allowed_agents"))
        normalized["text"] = text
        return normalized


def build_vector_indices(
    chunk_records: dict[str, list[dict[str, Any]]],
    *,
    vector_index: VectorIndex,
) -> dict[str, int]:
    return {
        collection_name: vector_index.add_chunks(collection_name, records)
        for collection_name, records in sorted(chunk_records.items())
    }


def persist_embeddings(
    records: Sequence[Any],
    *,
    persist_directory: str | Path = DEFAULT_CHROMA_PERSIST_DIR,
    registry_directory: str | Path = DEFAULT_VECTOR_REGISTRY_DIR,
    collection_name: str = "enterprise_ai_chunks",
    client: Any | None = None,
) -> int:
    vector_index = VectorIndex(
        persist_directory=persist_directory,
        registry_directory=registry_directory,
        client=client,
    )
    payload = [
        {
            "chunk_id": record.chunk_id,
            "text": record.text,
            "embedding": record.embedding,
            "metadata": record.metadata(),
            "registry_metadata": {
                key: value
                for key, value in record.to_dict().items()
                if key != "embedding"
            },
        }
        for record in records
    ]
    return vector_index.add_chunks(collection_name, payload)


def vector_records_from_embeddings(
    chunks: Sequence[Chunk],
    embeddings_by_chunk_id: dict[str, list[float]],
) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for chunk in chunks:
        if chunk.chunk_id not in embeddings_by_chunk_id:
            continue
        records.append(
            {
                "chunk_id": chunk.chunk_id,
                "text": chunk.text,
                "embedding": embeddings_by_chunk_id[chunk.chunk_id],
                "metadata": chroma_metadata_from_chunk(chunk),
                "registry_metadata": metadata_from_chunk(chunk),
            }
        )
    return records
