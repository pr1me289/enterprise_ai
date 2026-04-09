"""Source-aware endpoint routing for retrieval."""

from __future__ import annotations

from pathlib import Path

from indexing.load_index_registry import get_logical_store_name, get_registry_entry


def route_source(source_id: str, registry_path: str | Path | None = None) -> str:
    return get_logical_store_name(source_id, path=registry_path) if registry_path else get_logical_store_name(source_id)


def route_index_endpoint(source_id: str, registry_path: str | Path | None = None) -> str:
    entry = get_registry_entry(source_id, path=registry_path) if registry_path else get_registry_entry(source_id)
    if entry["storage_kind"] != "vector_bm25":
        raise KeyError(f"Source {source_id} is not mapped to a vector/BM25 index.")
    return str(entry["logical_store_name"])
