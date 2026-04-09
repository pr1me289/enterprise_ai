"""Source-aware endpoint routing for retrieval."""

from __future__ import annotations

from indexing.index_registry import SOURCE_ID_TO_LOGICAL_STORE, index_definition_for_source


def route_source(source_id: str) -> str:
    if source_id not in SOURCE_ID_TO_LOGICAL_STORE:
        raise KeyError(f"Unsupported source routing request: {source_id}")
    return SOURCE_ID_TO_LOGICAL_STORE[source_id]


def route_index_endpoint(source_id: str) -> str:
    return index_definition_for_source(source_id).index_name
