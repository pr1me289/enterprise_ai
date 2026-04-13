"""Per-source BM25 index building and lexical query helpers."""

from __future__ import annotations

import pickle
import re
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from chunking import Chunk
from rank_bm25 import BM25Okapi

from .index_registry import DEFAULT_BM25_PERSIST_DIR
from .metadata_schema import metadata_from_chunk, metadata_matches_filter


TOKEN_RE = re.compile(r"[A-Za-z0-9§._/-]+")


def tokenize(text: str) -> list[str]:
    return [token.lower() for token in TOKEN_RE.findall(text)]


class BM25Index:
    """Serialized BM25 document registry plus lazy lexical querying."""

    def __init__(self, *, persist_directory: str | Path = DEFAULT_BM25_PERSIST_DIR) -> None:
        self.persist_directory = Path(persist_directory)
        self._bundle_cache: dict[str, dict[str, Any]] = {}

    def build(self, collection_name: str, chunk_records: Sequence[dict[str, Any]]) -> int:
        if not chunk_records:
            return 0

        self.persist_directory.mkdir(parents=True, exist_ok=True)
        docs = [record["text"] for record in chunk_records]
        doc_ids = [record["chunk_id"] for record in chunk_records]
        tokenized_docs = [tokenize(text) for text in docs]
        metadata_by_id = {
            record["chunk_id"]: record["metadata"]
            for record in chunk_records
        }
        bundle = {
            "bm25": BM25Okapi(tokenized_docs),
            "docs": docs,
            "doc_ids": doc_ids,
            "metadata_by_id": metadata_by_id,
            "tokenized_docs": tokenized_docs,
        }
        with (self.persist_directory / f"{collection_name}.pkl").open("wb") as file_handle:
            pickle.dump(bundle, file_handle)
        self._bundle_cache[collection_name] = bundle
        return len(chunk_records)

    def query(
        self,
        collection_name: str,
        query_text: str,
        *,
        k: int,
        metadata_filter: dict[str, Any] | None = None,
        allowed_agent: str | None = None,
    ) -> list[dict[str, Any]]:
        bundle = self._load_bundle(collection_name)
        candidate_ids = []
        candidate_docs = []
        candidate_tokens = []
        candidate_metadata = []

        for chunk_id, text, tokenized in zip(bundle["doc_ids"], bundle["docs"], bundle["tokenized_docs"], strict=True):
            metadata = dict(bundle["metadata_by_id"][chunk_id])
            if allowed_agent and allowed_agent not in metadata.get("allowed_agents", []):
                continue
            if not metadata_matches_filter(metadata, metadata_filter):
                continue
            candidate_ids.append(chunk_id)
            candidate_docs.append(text)
            candidate_tokens.append(tokenized)
            candidate_metadata.append(metadata)

        if not candidate_ids:
            return []

        bm25 = BM25Okapi(candidate_tokens)
        scores = bm25.get_scores(tokenize(query_text))
        ranked_indices = sorted(
            range(len(candidate_ids)),
            key=lambda index: float(scores[index]),
            reverse=True,
        )[:k]

        hits: list[dict[str, Any]] = []
        for index in ranked_indices:
            metadata = candidate_metadata[index]
            hits.append(
                {
                    "chunk_id": candidate_ids[index],
                    "text": candidate_docs[index],
                    "source_id": metadata["source_id"],
                    "source_type": metadata["source_type"],
                    "authority_tier": metadata["authority_tier"],
                    "freshness_status": metadata["freshness_status"],
                    "allowed_agents": metadata["allowed_agents"],
                    "backend": "bm25",
                    "score": float(scores[index]),
                    "metadata": metadata,
                }
            )
        return hits

    def get_by_ids(self, collection_name: str, ids: Sequence[str]) -> list[dict[str, Any]]:
        if not ids:
            return []
        bundle = self._load_bundle(collection_name)
        metadata_by_id = bundle["metadata_by_id"]
        doc_by_id = dict(zip(bundle["doc_ids"], bundle["docs"], strict=True))
        return [
            {
                "chunk_id": chunk_id,
                "text": doc_by_id[chunk_id],
                "metadata": metadata_by_id[chunk_id],
            }
            for chunk_id in ids
            if chunk_id in metadata_by_id and chunk_id in doc_by_id
        ]

    def _load_bundle(self, collection_name: str) -> dict[str, Any]:
        if collection_name not in self._bundle_cache:
            with (self.persist_directory / f"{collection_name}.pkl").open("rb") as file_handle:
                self._bundle_cache[collection_name] = pickle.load(file_handle)
        return self._bundle_cache[collection_name]


def build_bm25_indices(
    chunk_groups: dict[str, list[Chunk]],
    *,
    bm25_index: BM25Index,
) -> dict[str, int]:
    counts: dict[str, int] = {}
    for collection_name, chunks in sorted(chunk_groups.items()):
        records = [
            {
                "chunk_id": chunk.chunk_id,
                "text": chunk.text,
                "metadata": metadata_from_chunk(chunk),
            }
            for chunk in chunks
        ]
        counts[collection_name] = bm25_index.build(collection_name, records)
    return counts
