"""Structured-store persistence for direct-structured sources outside retrieval indices."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from preprocessing import load_source

from .index_registry import (
    DEFAULT_STRUCTURED_STORE_DIR,
    DEFAULT_STRUCTURED_STORE_NAME,
    SOURCE_STORE_CONFIG,
)


class StructuredStore:
    """Plain JSON direct-access store for direct-structured source data."""

    def __init__(self, *, output_dir: str | Path = DEFAULT_STRUCTURED_STORE_DIR) -> None:
        self.output_dir = Path(output_dir)

    def build(self, store_name: str, payload: dict[str, Any]) -> Path:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        output_path = self.output_dir / f"{store_name}.json"
        output_path.write_text(
            json.dumps(payload, indent=2, ensure_ascii=True) + "\n",
            encoding="utf-8",
        )
        return output_path

    def load(self, store_name: str) -> dict[str, Any]:
        return json.loads((self.output_dir / f"{store_name}.json").read_text(encoding="utf-8"))

    def get_field(self, store_name: str, field_path: str) -> Any:
        payload = self.load(store_name)
        current: Any = payload["data"]
        for key in field_path.split("."):
            current = current[key]
        return current


def build_structured_store(
    source_path: str | Path,
    *,
    store: StructuredStore | None = None,
    store_name: str | None = None,
) -> Path:
    source = load_source(source_path)
    if source.retrieval_lane.value != "DIRECT_STRUCTURED":
        raise ValueError("Structured store build expects a direct-structured source.")
    if source.source_id not in SOURCE_STORE_CONFIG:
        raise ValueError(f"Unsupported direct-structured source for store build: {source.source_id}")

    resolved_store_name = store_name or SOURCE_STORE_CONFIG[source.source_id].logical_store_name

    payload = {
        "store_name": resolved_store_name,
        "source_id": source.source_id,
        "source_name": source.source_name,
        "source_type": source.source_type.value,
        "authority_tier": source.authority_tier,
        "retrieval_lane": source.retrieval_lane.value,
        "version": source.version,
        "document_date": source.document_date,
        "freshness_status": source.freshness_status,
        "allowed_agents": list(source.allowed_agents),
        "is_primary_citable": source.is_primary_citable,
        "manifest_status": source.manifest_status.value,
        "data": source.structured_data,
    }
    structured_store = store or StructuredStore()
    return structured_store.build(resolved_store_name, payload)


def build_structured_stores(
    source_paths: list[str | Path],
    *,
    store: StructuredStore | None = None,
) -> dict[str, Path]:
    structured_store = store or StructuredStore()
    built_paths: dict[str, Path] = {}
    for source_path in source_paths:
        path = build_structured_store(source_path, store=structured_store)
        payload = structured_store.load(path.stem)
        built_paths[payload["source_id"]] = path
    return built_paths
