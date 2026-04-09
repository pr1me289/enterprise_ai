"""Explicit index definitions and source-to-endpoint mapping."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, UTC
from pathlib import Path
from typing import Any

from chunking import Chunk


DEFAULT_CHROMA_PERSIST_DIR = Path("data/indexes/chroma")
DEFAULT_VECTOR_REGISTRY_DIR = Path("data/indexes/vector_registry")
DEFAULT_INDEX_REGISTRY_PATH = Path("data/indexes/index_registry.json")
DEFAULT_BM25_PERSIST_DIR = Path("data/bm25")
DEFAULT_STRUCTURED_STORE_DIR = Path("data/structured")
DEFAULT_STRUCTURED_STORE_NAME = "vq_direct_access"


@dataclass(frozen=True, slots=True)
class IndexDefinition:
    index_name: str
    source_id: str
    source_type: str
    backends: tuple[str, ...]
    allowed_agents: tuple[str, ...]
    retrieval_lane: str


INDEX_CONFIG: dict[str, IndexDefinition] = {
    "idx_security_policy": IndexDefinition(
        index_name="idx_security_policy",
        source_id="ISP-001",
        source_type="POLICY",
        backends=("vector", "bm25"),
        allowed_agents=("it_security", "legal", "procurement"),
        retrieval_lane="INDEXED_HYBRID",
    ),
    "idx_dpa_matrix": IndexDefinition(
        index_name="idx_dpa_matrix",
        source_id="DPA-TM-001",
        source_type="MATRIX",
        backends=("vector", "bm25"),
        allowed_agents=("legal",),
        retrieval_lane="INDEXED_HYBRID",
    ),
    "idx_procurement_matrix": IndexDefinition(
        index_name="idx_procurement_matrix",
        source_id="PAM-001",
        source_type="MATRIX",
        backends=("vector", "bm25"),
        allowed_agents=("procurement",),
        retrieval_lane="INDEXED_HYBRID",
    ),
    "idx_precedents": IndexDefinition(
        index_name="idx_precedents",
        source_id="PVD-001",
        source_type="PRECEDENT",
        backends=("vector", "bm25"),
        allowed_agents=("it_security", "legal", "procurement"),
        retrieval_lane="INDEXED_HYBRID",
    ),
    "idx_slack_notes": IndexDefinition(
        index_name="idx_slack_notes",
        source_id="SLK-001",
        source_type="SUPPLEMENTAL_NOTE",
        backends=("vector", "bm25"),
        allowed_agents=("procurement",),
        retrieval_lane="INDEXED_HYBRID",
    ),
}

STRUCTURED_STORE_CONFIG = {
    DEFAULT_STRUCTURED_STORE_NAME: {
        "source_id": "VQ-OC-001",
        "source_type": "QUESTIONNAIRE",
        "allowed_agents": (
            "it_security",
            "legal",
            "procurement",
            "checklist_assembler",
            "checkoff",
        ),
        "retrieval_lane": "DIRECT_STRUCTURED",
    }
}

SOURCE_ID_TO_INDEX_NAME = {
    definition.source_id: index_name
    for index_name, definition in INDEX_CONFIG.items()
}

SOURCE_ID_TO_LOGICAL_STORE = {
    **SOURCE_ID_TO_INDEX_NAME,
    STRUCTURED_STORE_CONFIG[DEFAULT_STRUCTURED_STORE_NAME]["source_id"]: DEFAULT_STRUCTURED_STORE_NAME,
}

ACCESS_MATRIX = {
    index_name: definition.allowed_agents
    for index_name, definition in INDEX_CONFIG.items()
}


def index_name_for_source(source_id: str) -> str:
    if source_id not in SOURCE_ID_TO_LOGICAL_STORE:
        raise KeyError(f"Unsupported source id for indexing: {source_id}")
    return SOURCE_ID_TO_LOGICAL_STORE[source_id]


def index_definition_for_source(source_id: str) -> IndexDefinition:
    index_name = index_name_for_source(source_id)
    if index_name not in INDEX_CONFIG:
        raise KeyError(f"Source {source_id} is not mapped to a vector/BM25 index.")
    return INDEX_CONFIG[index_name]


def group_chunks_by_index_name(chunks: list[Chunk]) -> dict[str, list[Chunk]]:
    grouped: dict[str, list[Chunk]] = {index_name: [] for index_name in INDEX_CONFIG}
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
    embedding_model: str,
    structured_store_name: str = DEFAULT_STRUCTURED_STORE_NAME,
) -> dict[str, Any]:
    indices: dict[str, Any] = {}
    for index_name, chunks in sorted(chunk_groups.items()):
        definition = INDEX_CONFIG[index_name]
        first_chunk = chunks[0]
        indices[index_name] = {
            "index_name": index_name,
            "source_id": definition.source_id,
            "source_type": definition.source_type,
            "collection_name": index_name,
            "source_ids": sorted({chunk.source_id for chunk in chunks}),
            "versions": sorted({chunk.version for chunk in chunks}),
            "chunk_count": len(chunks),
            "build_timestamp": datetime.now(UTC).isoformat(),
            "embedding_model": embedding_model,
            "manifest_statuses": sorted({chunk.manifest_status for chunk in chunks}),
            "freshness_statuses": sorted({chunk.freshness_status for chunk in chunks}),
            "document_dates": sorted({date for date in {chunk.document_date for chunk in chunks} if date}),
            "allowed_agents": list(definition.allowed_agents),
            "retrieval_lane": first_chunk.retrieval_lane,
            "backends": list(definition.backends),
        }

    structured_definition = STRUCTURED_STORE_CONFIG[structured_store_name]
    return {
        "indices": indices,
        "structured_store": {
            "store_name": structured_store_name,
            "source_id": structured_definition["source_id"],
            "source_type": structured_definition["source_type"],
            "allowed_agents": list(structured_definition["allowed_agents"]),
            "retrieval_lane": structured_definition["retrieval_lane"],
        },
    }
