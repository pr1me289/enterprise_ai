from __future__ import annotations

import pytest

from retrieval.authority_reranker import authority_rerank
from retrieval.hybrid_search import hybrid_search, reciprocal_rank_fusion
from retrieval.permission_guard import UnauthorizedRetrieval, assert_endpoint_access
from retrieval.source_router import route_index_endpoint, route_source


class FakeVectorIndex:
    def query(self, *args, **kwargs):
        return [
            {
                "chunk_id": "chunk-1",
                "text": "policy clause",
                "source_id": "ISP-001",
                "source_type": "POLICY_DOCUMENT",
                "authority_tier": 1,
                "freshness_status": "CURRENT",
                "allowed_agents": ["legal"],
                "backend": "vector",
                "score": 0.8,
                "metadata": {"manifest_status": "PROVISIONAL"},
            }
        ]


class FakeBM25Index:
    def query(self, *args, **kwargs):
        return [
            {
                "chunk_id": "chunk-1",
                "text": "policy clause",
                "source_id": "ISP-001",
                "source_type": "POLICY_DOCUMENT",
                "authority_tier": 1,
                "freshness_status": "CURRENT",
                "allowed_agents": ["legal"],
                "backend": "bm25",
                "score": 12.0,
                "metadata": {"manifest_status": "PROVISIONAL"},
            },
            {
                "chunk_id": "chunk-2",
                "text": "slack note",
                "source_id": "SLK-001",
                "source_type": "SLACK_THREAD",
                "authority_tier": 4,
                "freshness_status": "CURRENT",
                "allowed_agents": ["legal"],
                "backend": "bm25",
                "score": 11.0,
                "metadata": {"manifest_status": "CONFIRMED"},
            },
        ]


def test_permission_guard_fails_closed_for_unauthorized_endpoint() -> None:
    with pytest.raises(UnauthorizedRetrieval):
        assert_endpoint_access("checkoff", "idx_dpa_matrix")


def test_source_router_uses_explicit_storage_mapping() -> None:
    assert route_source("VQ-OC-001") == "vq_direct_access"
    assert route_index_endpoint("ISP-001") == "idx_security_policy"


def test_reciprocal_rank_fusion_merges_by_chunk_id() -> None:
    fused = reciprocal_rank_fusion(
        [{"chunk_id": "chunk-1", "score": 1.0}],
        [{"chunk_id": "chunk-1", "score": 2.0}, {"chunk_id": "chunk-2", "score": 1.5}],
    )

    assert fused[0]["chunk_id"] == "chunk-1"
    assert {item["chunk_id"] for item in fused} == {"chunk-1", "chunk-2"}


def test_authority_rerank_caps_lower_authority_candidates() -> None:
    reranked = authority_rerank(
        [
            {
                "chunk_id": "tier-1",
                "authority_tier": 1,
                "freshness_status": "CURRENT",
                "score": 1.0,
                "metadata": {"manifest_status": "CONFIRMED"},
            },
            {
                "chunk_id": "tier-4",
                "authority_tier": 4,
                "freshness_status": "CURRENT",
                "score": 1.1,
                "metadata": {"manifest_status": "CONFIRMED"},
            },
        ]
    )

    assert reranked[0]["chunk_id"] == "tier-1"


def test_hybrid_search_returns_manifest_and_reranked_hits() -> None:
    results, manifest = hybrid_search(
        "legal",
        "idx_security_policy",
        "NDA status",
        vector_index=FakeVectorIndex(),
        bm25_index=FakeBM25Index(),
        filters={"source_id": "ISP-001"},
        k=2,
    )

    assert results[0]["chunk_id"] == "chunk-1"
    assert manifest.index_name == "idx_security_policy"
    assert manifest.filters == {"source_id": "ISP-001"}
