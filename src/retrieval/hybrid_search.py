"""Hybrid retrieval over per-source vector and BM25 indices."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from .authority_reranker import authority_rerank
from .permission_guard import assert_endpoint_access
from .retrieval_manifest import RetrievalManifestEntry


def reciprocal_rank_fusion(
    vector_hits: Sequence[dict[str, Any]],
    bm25_hits: Sequence[dict[str, Any]],
    *,
    k_constant: int = 60,
) -> list[dict[str, Any]]:
    merged: dict[str, dict[str, Any]] = {}
    for backend_hits in (vector_hits, bm25_hits):
        for rank, hit in enumerate(backend_hits, start=1):
            if hit["chunk_id"] not in merged:
                merged[hit["chunk_id"]] = dict(hit)
                merged[hit["chunk_id"]]["backend"] = "hybrid"
                merged[hit["chunk_id"]]["score"] = 0.0
            merged[hit["chunk_id"]]["score"] += 1.0 / (k_constant + rank)
    return sorted(merged.values(), key=lambda item: item["score"], reverse=True)


def hybrid_search(
    agent_name: str,
    index_name: str,
    query_text: str,
    *,
    vector_index: Any,
    bm25_index: Any,
    filters: dict[str, Any] | None = None,
    k: int = 5,
    k_vector: int | None = None,
    k_bm25: int | None = None,
) -> tuple[list[dict[str, Any]], RetrievalManifestEntry]:
    assert_endpoint_access(agent_name, index_name)

    metadata_filter = dict(filters or {})
    vector_hits = vector_index.query(
        index_name,
        query_text,
        k=k_vector or k,
        where=metadata_filter,
        allowed_agent=agent_name,
    )
    bm25_hits = bm25_index.query(
        index_name,
        query_text,
        k=k_bm25 or k,
        metadata_filter=metadata_filter,
        allowed_agent=agent_name,
    )

    fused = reciprocal_rank_fusion(vector_hits, bm25_hits)
    reranked = authority_rerank(fused)[:k]
    manifest = RetrievalManifestEntry(
        agent_name=agent_name,
        index_name=index_name,
        query_text=query_text,
        filters=metadata_filter,
        returned_chunks=reranked,
        suppressed_chunks=[],
    )
    return reranked, manifest
