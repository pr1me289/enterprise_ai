"""Authority- and freshness-aware reranking for hybrid candidates."""

from __future__ import annotations

from collections.abc import Sequence


AUTHORITY_WEIGHTS = {
    1: 1.0,
    2: 0.9,
    3: 0.75,
}

MANIFEST_STATUS_WEIGHTS = {
    "CONFIRMED": 1.0,
    "PENDING": 0.9,
}

FRESHNESS_WEIGHTS = {
    "CURRENT": 1.0,
    "CONFIRMED": 1.0,
}


def authority_rerank(candidates: Sequence[dict]) -> list[dict]:
    reranked: list[dict] = []
    for candidate in candidates:
        metadata = candidate.get("metadata", {})
        authority_weight = AUTHORITY_WEIGHTS.get(int(candidate["authority_tier"]), 0.5)
        manifest_weight = MANIFEST_STATUS_WEIGHTS.get(str(metadata.get("manifest_status", "")), 1.0)
        freshness_weight = FRESHNESS_WEIGHTS.get(str(candidate.get("freshness_status", "")), 0.95)
        reranked_candidate = dict(candidate)
        reranked_candidate["score"] = candidate["score"] * authority_weight * manifest_weight * freshness_weight
        reranked.append(reranked_candidate)
    return sorted(reranked, key=lambda item: item["score"], reverse=True)
