"""Helpers for consuming the generated source-to-store registry."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .index_registry import DEFAULT_INDEX_REGISTRY_PATH


def load_index_registry(path: str | Path = DEFAULT_INDEX_REGISTRY_PATH) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def get_registry_entry(source_id: str, path: str | Path = DEFAULT_INDEX_REGISTRY_PATH) -> dict[str, Any]:
    payload = load_index_registry(path)
    try:
        return payload["sources"][source_id]
    except KeyError as exc:
        raise KeyError(f"Unsupported source id for registry lookup: {source_id}") from exc


def get_entry_by_logical_store_name(
    logical_store_name: str,
    path: str | Path = DEFAULT_INDEX_REGISTRY_PATH,
) -> dict[str, Any]:
    payload = load_index_registry(path)
    for entry in payload["sources"].values():
        if entry["logical_store_name"] == logical_store_name:
            return entry
    raise KeyError(f"Unsupported logical store name for registry lookup: {logical_store_name}")


def get_logical_store_name(source_id: str, path: str | Path = DEFAULT_INDEX_REGISTRY_PATH) -> str:
    return str(get_registry_entry(source_id, path)["logical_store_name"])


def get_backends(source_id: str, path: str | Path = DEFAULT_INDEX_REGISTRY_PATH) -> list[str]:
    return list(get_registry_entry(source_id, path)["backends"])


def get_allowed_agents(source_id: str, path: str | Path = DEFAULT_INDEX_REGISTRY_PATH) -> list[str]:
    return list(get_registry_entry(source_id, path)["allowed_agents"])


def is_indexed_source(source_id: str, path: str | Path = DEFAULT_INDEX_REGISTRY_PATH) -> bool:
    return get_registry_entry(source_id, path)["storage_kind"] == "vector_bm25"


def is_structured_source(source_id: str, path: str | Path = DEFAULT_INDEX_REGISTRY_PATH) -> bool:
    return get_registry_entry(source_id, path)["storage_kind"] == "structured_direct"


def list_indexed_sources(path: str | Path = DEFAULT_INDEX_REGISTRY_PATH) -> list[str]:
    payload = load_index_registry(path)
    return sorted(
        source_id
        for source_id, entry in payload["sources"].items()
        if entry["storage_kind"] == "vector_bm25"
    )


def list_structured_sources(path: str | Path = DEFAULT_INDEX_REGISTRY_PATH) -> list[str]:
    payload = load_index_registry(path)
    return sorted(
        source_id
        for source_id, entry in payload["sources"].items()
        if entry["storage_kind"] == "structured_direct"
    )
