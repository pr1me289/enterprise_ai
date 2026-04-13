"""Canonical source-to-store registry generation for Step 8."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from chunking import Chunk


DEFAULT_INDEX_ROOT = Path("data/indexes")
DEFAULT_BM25_ROOT = Path("data/bm25")
DEFAULT_STRUCTURED_ROOT = Path("data/structured")
DEFAULT_CHROMA_PERSIST_DIR = DEFAULT_INDEX_ROOT / "chroma"
DEFAULT_VECTOR_REGISTRY_DIR = DEFAULT_INDEX_ROOT / "vector_registry"
DEFAULT_INDEX_REGISTRY_PATH = DEFAULT_INDEX_ROOT / "index_registry.json"
DEFAULT_BM25_PERSIST_DIR = DEFAULT_BM25_ROOT
DEFAULT_STRUCTURED_STORE_DIR = DEFAULT_STRUCTURED_ROOT
DEFAULT_STRUCTURED_STORE_NAME = "vq_direct_access"
DEFAULT_STAKEHOLDER_STORE_NAME = "stakeholder_map_direct_access"
REGISTRY_VERSION = "1.0"


@dataclass(frozen=True, slots=True)
class SourceStoreDefinition:
    source_id: str
    logical_store_name: str
    storage_kind: str
    backends: tuple[str, ...]


SOURCE_STORE_CONFIG: dict[str, SourceStoreDefinition] = {
    "ISP-001": SourceStoreDefinition(
        source_id="ISP-001",
        logical_store_name="idx_security_policy",
        storage_kind="vector_bm25",
        backends=("chroma", "bm25"),
    ),
    "DPA-TM-001": SourceStoreDefinition(
        source_id="DPA-TM-001",
        logical_store_name="dpa_matrix_direct",
        storage_kind="structured_direct",
        backends=("structured_json",),
    ),
    "PAM-001": SourceStoreDefinition(
        source_id="PAM-001",
        logical_store_name="procurement_matrix_direct",
        storage_kind="structured_direct",
        backends=("structured_json",),
    ),
    "PVD-001": SourceStoreDefinition(
        source_id="PVD-001",
        logical_store_name="idx_precedents",
        storage_kind="vector_bm25",
        backends=("chroma", "bm25"),
    ),
    "SLK-001": SourceStoreDefinition(
        source_id="SLK-001",
        logical_store_name="idx_slack_notes",
        storage_kind="vector_bm25",
        backends=("chroma", "bm25"),
    ),
    "VQ-OC-001": SourceStoreDefinition(
        source_id="VQ-OC-001",
        logical_store_name=DEFAULT_STRUCTURED_STORE_NAME,
        storage_kind="structured_direct",
        backends=("structured_json",),
    ),
    "SHM-001": SourceStoreDefinition(
        source_id="SHM-001",
        logical_store_name=DEFAULT_STAKEHOLDER_STORE_NAME,
        storage_kind="structured_direct",
        backends=("structured_json",),
    ),
}

SOURCE_ID_TO_LOGICAL_STORE = {
    source_id: definition.logical_store_name
    for source_id, definition in SOURCE_STORE_CONFIG.items()
}

SOURCE_ID_TO_INDEX_NAME = {
    source_id: definition.logical_store_name
    for source_id, definition in SOURCE_STORE_CONFIG.items()
    if definition.storage_kind == "vector_bm25"
}

INDEX_CONFIG = {
    definition.logical_store_name: definition
    for definition in SOURCE_STORE_CONFIG.values()
    if definition.storage_kind == "vector_bm25"
}


def scenario_chroma_persist_directory(scenario_name: str) -> Path:
    return DEFAULT_INDEX_ROOT / scenario_name / "chroma"


def scenario_vector_registry_directory(scenario_name: str) -> Path:
    return DEFAULT_INDEX_ROOT / scenario_name / "vector_registry"


def scenario_index_registry_path(scenario_name: str) -> Path:
    return DEFAULT_INDEX_ROOT / scenario_name / "index_registry.json"


def scenario_bm25_persist_directory(scenario_name: str) -> Path:
    return DEFAULT_BM25_ROOT / scenario_name


def scenario_structured_store_directory(scenario_name: str) -> Path:
    return DEFAULT_STRUCTURED_ROOT / scenario_name


def index_name_for_source(source_id: str) -> str:
    if source_id not in SOURCE_ID_TO_LOGICAL_STORE:
        raise KeyError(f"Unsupported source id for indexing: {source_id}")
    return SOURCE_ID_TO_LOGICAL_STORE[source_id]


def is_indexed_source(source_id: str) -> bool:
    return SOURCE_STORE_CONFIG[source_id].storage_kind == "vector_bm25"


def is_structured_source(source_id: str) -> bool:
    return SOURCE_STORE_CONFIG[source_id].storage_kind == "structured_direct"


def group_chunks_by_index_name(chunks: list[Chunk]) -> dict[str, list[Chunk]]:
    grouped: dict[str, list[Chunk]] = {
        definition.logical_store_name: []
        for definition in SOURCE_STORE_CONFIG.values()
        if definition.storage_kind == "vector_bm25"
    }
    for chunk in chunks:
        if chunk.source_id not in SOURCE_ID_TO_INDEX_NAME:
            continue
        grouped[SOURCE_ID_TO_INDEX_NAME[chunk.source_id]].append(chunk)
    return {
        index_name: sorted(records, key=lambda chunk: (chunk.chunk_order, chunk.chunk_id))
        for index_name, records in grouped.items()
        if records
    }


def build_index_registry_payload(
    *,
    chunk_groups: dict[str, list[Chunk]],
    structured_store_path: str | Path | None = None,
    structured_store_paths: list[str | Path] | None = None,
    bm25_persist_directory: str | Path = DEFAULT_BM25_PERSIST_DIR,
    generated_at: datetime | None = None,
) -> dict[str, Any]:
    sources: dict[str, Any] = {}

    for logical_store_name, chunks in sorted(chunk_groups.items()):
        if logical_store_name not in INDEX_CONFIG:
            continue
        definition = INDEX_CONFIG[logical_store_name]
        sources[definition.source_id] = _build_indexed_source_entry(
            definition=definition,
            chunks=chunks,
            bm25_persist_directory=bm25_persist_directory,
        )

    all_structured_store_paths: list[str | Path] = []
    if structured_store_path is not None:
        all_structured_store_paths.append(structured_store_path)
    if structured_store_paths is not None:
        all_structured_store_paths.extend(structured_store_paths)

    for path in all_structured_store_paths:
        structured_payload = json.loads(Path(path).read_text(encoding="utf-8"))
        structured_source_id = structured_payload["source_id"]
        sources[structured_source_id] = _build_structured_source_entry(
            definition=SOURCE_STORE_CONFIG[structured_source_id],
            payload=structured_payload,
            structured_store_path=path,
        )

    return {
        "registry_version": REGISTRY_VERSION,
        "generated_at": (generated_at or datetime.now(UTC)).isoformat().replace("+00:00", "Z"),
        "sources": sources,
    }


def write_index_registry(
    payload: dict[str, Any],
    *,
    path: str | Path = DEFAULT_INDEX_REGISTRY_PATH,
) -> Path:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )
    return output_path


def _build_indexed_source_entry(
    *,
    definition: SourceStoreDefinition,
    chunks: list[Chunk],
    bm25_persist_directory: str | Path,
) -> dict[str, Any]:
    first_chunk = chunks[0]
    _assert_homogeneous_source_metadata(first_chunk.source_id, chunks)

    return {
        "source_id": first_chunk.source_id,
        "source_name": first_chunk.source_name,
        "source_type": first_chunk.source_type,
        "authority_tier": first_chunk.authority_tier,
        "retrieval_lane": first_chunk.retrieval_lane,
        "version": first_chunk.version,
        "document_date": first_chunk.document_date,
        "freshness_status": first_chunk.freshness_status,
        "manifest_status": first_chunk.manifest_status,
        "allowed_agents": list(first_chunk.allowed_agents),
        "is_primary_citable": first_chunk.is_primary_citable,
        "storage_kind": definition.storage_kind,
        "logical_store_name": definition.logical_store_name,
        "backends": list(definition.backends),
        "backend_locations": {
            "chroma_collection": definition.logical_store_name,
            "bm25_bundle": str(Path(bm25_persist_directory) / f"{definition.logical_store_name}.pkl"),
        },
    }


def _build_structured_source_entry(
    *,
    definition: SourceStoreDefinition,
    payload: dict[str, Any],
    structured_store_path: str | Path,
) -> dict[str, Any]:
    return {
        "source_id": payload["source_id"],
        "source_name": payload["source_name"],
        "source_type": payload["source_type"],
        "authority_tier": payload["authority_tier"],
        "retrieval_lane": payload["retrieval_lane"],
        "version": payload["version"],
        "document_date": payload["document_date"],
        "freshness_status": payload["freshness_status"],
        "manifest_status": payload["manifest_status"],
        "allowed_agents": list(payload["allowed_agents"]),
        "is_primary_citable": payload["is_primary_citable"],
        "storage_kind": definition.storage_kind,
        "logical_store_name": definition.logical_store_name,
        "backends": list(definition.backends),
        "backend_locations": {
            "structured_store": str(Path(structured_store_path)),
        },
    }


def _assert_homogeneous_source_metadata(source_id: str, chunks: list[Chunk]) -> None:
    first_chunk = chunks[0]
    expected = (
        first_chunk.source_name,
        first_chunk.source_type,
        first_chunk.authority_tier,
        first_chunk.retrieval_lane,
        first_chunk.version,
        first_chunk.document_date,
        first_chunk.freshness_status,
        first_chunk.manifest_status,
        first_chunk.allowed_agents,
        first_chunk.is_primary_citable,
    )
    for chunk in chunks[1:]:
        current = (
            chunk.source_name,
            chunk.source_type,
            chunk.authority_tier,
            chunk.retrieval_lane,
            chunk.version,
            chunk.document_date,
            chunk.freshness_status,
            chunk.manifest_status,
            chunk.allowed_agents,
            chunk.is_primary_citable,
        )
        if current != expected:
            raise ValueError(f"Indexed source {source_id} is not homogeneous at the source-metadata level.")
