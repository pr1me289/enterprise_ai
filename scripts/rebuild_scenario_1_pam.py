"""Rebuild scenario_1 PAM-001 chunks + indices from the v2.0 CSV.

Usage:
    uv run python scripts/rebuild_scenario_1_pam.py

Overwrites:
    data/processed/scenario_1/chunks/PAM-001.json
    data/indexes/scenario_1/vector_registry/idx_procurement_matrix.json
    data/indexes/scenario_1/chroma/... (upsert into idx_procurement_matrix)
    data/bm25/scenario_1/idx_procurement_matrix.pkl
    data/indexes/scenario_1/index_registry.json  (PAM-001.version 3.0 -> 2.0)

Does not touch other sources (DPA, ISP, SLK, VQ, SHM).
"""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from chunking import Chunk  # noqa: E402
from indexing.build_bm25_index import BM25Index  # noqa: E402
from indexing.build_vector_index import VectorIndex  # noqa: E402
from indexing.embeddings import embed_batch  # noqa: E402
from indexing.metadata_schema import (  # noqa: E402
    chroma_metadata_from_chunk,
    metadata_from_chunk,
)

CSV_PATH = REPO_ROOT / "scenario_1_mock_documents" / "Procurement_Approval_Matrix_v2_0.csv"
CHUNKS_PATH = REPO_ROOT / "data" / "processed" / "scenario_1" / "chunks" / "PAM-001.json"
CHROMA_DIR = REPO_ROOT / "data" / "indexes" / "scenario_1" / "chroma"
VECTOR_REGISTRY_DIR = REPO_ROOT / "data" / "indexes" / "scenario_1" / "vector_registry"
BM25_DIR = REPO_ROOT / "data" / "bm25" / "scenario_1"
REGISTRY_PATH = REPO_ROOT / "data" / "indexes" / "scenario_1" / "index_registry.json"
COLLECTION_NAME = "idx_procurement_matrix"

SOURCE_ID = "PAM-001"
SOURCE_NAME = "Procurement Approval Matrix"
SOURCE_TYPE = "PROCUREMENT_APPROVAL_MATRIX"
VERSION = "2.0"
DOCUMENT_DATE = "2026-04-04"
FRESHNESS_STATUS = "CURRENT"
AUTHORITY_TIER = 1
RETRIEVAL_LANE = "INDEXED_HYBRID"
ALLOWED_AGENTS = ("procurement",)
MANIFEST_STATUS = "CONFIRMED"


def _row_text(row: dict[str, str]) -> str:
    return "\n".join([
        f"Class: {row['Class']}",
        f"Tier: {row['Tier']}",
        f"Approval Path: {row['Approval Path']}",
        f"IT Security Review: {row['IT Security Review']}",
        f"Legal / DPA Review: {row['Legal / DPA Review']}",
        f"Procurement Review: {row['Procurement Review']}",
        f"Business Owner Sign-off: {row['Business Owner Sign-off']}",
        f"Fast-Track Eligible?: {row['Fast-Track Eligible?']}",
        f"Required Approvals / Notes: {row['Required Approvals / Notes']}",
    ])


def build_chunks() -> list[Chunk]:
    with CSV_PATH.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        csv_rows = [row for row in reader if row.get("Class") and row.get("Tier")]

    chunks: list[Chunk] = []
    for order, row in enumerate(csv_rows, start=1):
        row_id = f"{row['Class']}-{row['Tier']}"
        chunk = Chunk(
            chunk_id=f"{SOURCE_ID}__row_{row_id}",
            source_id=SOURCE_ID,
            source_name=SOURCE_NAME,
            source_type=SOURCE_TYPE,
            version=VERSION,
            document_date=DOCUMENT_DATE,
            freshness_status=FRESHNESS_STATUS,
            authority_tier=AUTHORITY_TIER,
            retrieval_lane=RETRIEVAL_LANE,
            allowed_agents=ALLOWED_AGENTS,
            is_primary_citable=True,
            manifest_status=MANIFEST_STATUS,
            chunk_type="ROW",
            chunk_order=order,
            section_id=None,
            row_id=row_id,
            record_id=None,
            thread_id=None,
            domain_scope=None,
            citation_label=f"{SOURCE_ID} row {row_id}",
            text=_row_text(row),
        )
        chunks.append(chunk)
    return chunks


def write_chunks_json(chunks: list[Chunk]) -> None:
    payload = [
        {
            "chunk_id": chunk.chunk_id,
            "source_id": chunk.source_id,
            "source_name": chunk.source_name,
            "source_type": chunk.source_type,
            "version": chunk.version,
            "document_date": chunk.document_date,
            "freshness_status": chunk.freshness_status,
            "authority_tier": chunk.authority_tier,
            "retrieval_lane": chunk.retrieval_lane,
            "allowed_agents": list(chunk.allowed_agents),
            "is_primary_citable": chunk.is_primary_citable,
            "manifest_status": chunk.manifest_status,
            "chunk_type": chunk.chunk_type,
            "chunk_order": chunk.chunk_order,
            "citation_label": chunk.citation_label,
            "text": chunk.text,
            "section_id": chunk.section_id,
            "row_id": chunk.row_id,
            "record_id": chunk.record_id,
            "thread_id": chunk.thread_id,
            "domain_scope": chunk.domain_scope,
        }
        for chunk in chunks
    ]
    CHUNKS_PATH.parent.mkdir(parents=True, exist_ok=True)
    CHUNKS_PATH.write_text(json.dumps(payload, indent=2, ensure_ascii=True))
    print(f"[1/4] wrote {CHUNKS_PATH.relative_to(REPO_ROOT)} ({len(payload)} rows)")


def rebuild_indices(chunks: list[Chunk]) -> None:
    texts = [chunk.text for chunk in chunks]
    embeddings = embed_batch(texts)

    vector_records = [
        {
            "chunk_id": chunk.chunk_id,
            "text": chunk.text,
            "embedding": embedding,
            "metadata": chroma_metadata_from_chunk(chunk),
            "registry_metadata": metadata_from_chunk(chunk),
        }
        for chunk, embedding in zip(chunks, embeddings, strict=True)
    ]

    VECTOR_REGISTRY_DIR.mkdir(parents=True, exist_ok=True)
    CHROMA_DIR.mkdir(parents=True, exist_ok=True)
    vector_index = VectorIndex(
        persist_directory=CHROMA_DIR,
        registry_directory=VECTOR_REGISTRY_DIR,
    )
    from chromadb import PersistentClient
    client = PersistentClient(path=str(CHROMA_DIR))
    existing = {c.name for c in client.list_collections()}
    if COLLECTION_NAME in existing:
        client.delete_collection(name=COLLECTION_NAME)
    vector_index._client = client
    count = vector_index.add_chunks(COLLECTION_NAME, vector_records)
    print(f"[2/4] chroma {COLLECTION_NAME}: {count} rows upserted")

    BM25_DIR.mkdir(parents=True, exist_ok=True)
    bm25_index = BM25Index(persist_directory=BM25_DIR)
    bm25_records = [
        {
            "chunk_id": chunk.chunk_id,
            "text": chunk.text,
            "metadata": metadata_from_chunk(chunk),
        }
        for chunk in chunks
    ]
    bm25_count = bm25_index.build(COLLECTION_NAME, bm25_records)
    print(f"[3/4] bm25 {COLLECTION_NAME}: {bm25_count} docs")


def update_registry_version() -> None:
    registry = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    pam_entry = registry["sources"].get(SOURCE_ID)
    if pam_entry is None:
        raise SystemExit("PAM-001 missing from index registry")
    old_version = pam_entry.get("version")
    pam_entry["version"] = VERSION
    REGISTRY_PATH.write_text(json.dumps(registry, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    print(f"[4/4] index_registry PAM-001.version {old_version} -> {VERSION}")


def main() -> None:
    chunks = build_chunks()
    write_chunks_json(chunks)
    rebuild_indices(chunks)
    update_registry_version()


if __name__ == "__main__":
    main()
