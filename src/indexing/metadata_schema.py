"""Shared metadata schema helpers for storage and retrieval."""

from __future__ import annotations

import json
from typing import Any

from chunking import Chunk


CHROMA_WHERE_FILTER_FIELDS = {
    "source_id",
    "source_type",
    "authority_tier",
    "freshness_status",
    "manifest_status",
    "domain_scope",
    "version",
    "is_primary_citable",
}


def allowed_agents_str(allowed_agents: tuple[str, ...] | list[str]) -> str:
    values = list(allowed_agents)
    if not values:
        return "||"
    return "|" + "|".join(values) + "|"


def allowed_agents_json(allowed_agents: tuple[str, ...] | list[str]) -> str:
    return json.dumps(list(allowed_agents), ensure_ascii=True)


def metadata_from_chunk(chunk: Chunk) -> dict[str, Any]:
    return {
        "chunk_id": chunk.chunk_id,
        "source_id": chunk.source_id,
        "source_name": chunk.source_name,
        "source_type": chunk.source_type,
        "authority_tier": chunk.authority_tier,
        "retrieval_lane": chunk.retrieval_lane,
        "version": chunk.version,
        "document_date": chunk.document_date,
        "freshness_status": chunk.freshness_status,
        "allowed_agents": list(chunk.allowed_agents),
        "allowed_agents_str": allowed_agents_str(chunk.allowed_agents),
        "is_primary_citable": chunk.is_primary_citable,
        "manifest_status": chunk.manifest_status,
        "section_id": chunk.section_id,
        "row_id": chunk.row_id,
        "record_id": chunk.record_id,
        "thread_id": chunk.thread_id,
        "domain_scope": chunk.domain_scope,
        "text": chunk.text,
        "citation_label": chunk.citation_label,
        "chunk_type": chunk.chunk_type,
        "chunk_order": chunk.chunk_order,
    }


def chroma_metadata_from_chunk(chunk: Chunk) -> dict[str, str | int | bool]:
    metadata = {
        "chunk_id": chunk.chunk_id,
        "source_id": chunk.source_id,
        "source_name": chunk.source_name,
        "source_type": chunk.source_type,
        "authority_tier": chunk.authority_tier,
        "retrieval_lane": chunk.retrieval_lane,
        "version": chunk.version,
        "document_date": chunk.document_date or "",
        "freshness_status": chunk.freshness_status,
        "allowed_agents": allowed_agents_json(chunk.allowed_agents),
        "allowed_agents_str": allowed_agents_str(chunk.allowed_agents),
        "is_primary_citable": chunk.is_primary_citable,
        "manifest_status": chunk.manifest_status,
        "citation_label": chunk.citation_label,
        "chunk_type": chunk.chunk_type,
    }
    if chunk.section_id is not None:
        metadata["section_id"] = chunk.section_id
    if chunk.row_id is not None:
        metadata["row_id"] = chunk.row_id
    if chunk.record_id is not None:
        metadata["record_id"] = chunk.record_id
    if chunk.thread_id is not None:
        metadata["thread_id"] = chunk.thread_id
    if chunk.domain_scope is not None:
        metadata["domain_scope"] = chunk.domain_scope
    return metadata


def split_chroma_and_fallback_filters(
    metadata_filter: dict[str, Any] | None,
) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    if not metadata_filter:
        return None, {}

    chroma_filter = {
        key: value
        for key, value in metadata_filter.items()
        if key in CHROMA_WHERE_FILTER_FIELDS
    }
    fallback_filter = {
        key: value
        for key, value in metadata_filter.items()
        if key not in CHROMA_WHERE_FILTER_FIELDS
    }
    return chroma_filter or None, fallback_filter


def metadata_matches_filter(metadata: dict[str, Any], metadata_filter: dict[str, Any] | None) -> bool:
    if not metadata_filter:
        return True

    for key, expected in metadata_filter.items():
        actual = metadata.get(key)
        if key == "allowed_agents":
            allowed_agents = tuple(actual or ())
            if isinstance(expected, str):
                if expected not in allowed_agents:
                    return False
                continue
            if tuple(expected) != allowed_agents:
                return False
            continue
        if actual != expected:
            return False
    return True


def parse_allowed_agents(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item) for item in value]
    if isinstance(value, str):
        if value.startswith("["):
            return [str(item) for item in json.loads(value)]
        if value.startswith("|") and value.endswith("|"):
            return [item for item in value.strip("|").split("|") if item]
        return [value]
    return [str(value)]
