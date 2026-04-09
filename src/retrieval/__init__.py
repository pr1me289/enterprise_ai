"""Governed retrieval helpers for hybrid search over explicit logical indices."""

from .authority_reranker import authority_rerank
from .hybrid_search import hybrid_search, reciprocal_rank_fusion
from .permission_guard import UnauthorizedRetrieval, assert_endpoint_access
from .retrieval_manifest import RetrievalManifestEntry
from .source_router import route_index_endpoint, route_source

__all__ = [
    "RetrievalManifestEntry",
    "UnauthorizedRetrieval",
    "assert_endpoint_access",
    "authority_rerank",
    "hybrid_search",
    "reciprocal_rank_fusion",
    "route_index_endpoint",
    "route_source",
]
