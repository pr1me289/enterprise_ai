"""Rebuild scenario-5 DPA artifacts end-to-end.

1. Rebuild scenario_data/scenario_5/sources/DPA-TM-001_scenario5.json by copying
   the production v2.1 row set and appending row A-07 (same fact pattern as
   A-01, opposite outcome grounded in Art. 6(1)(f) legitimate interest /
   controller-to-controller allocation, no factual carve-outs).
2. Re-chunk + re-embed the scenario-5 source into the scenario-scoped Chroma
   collection `idx_dpa_matrix__scenario5` and BM25 bundle
   `scenario_data/scenario_5/bm25/idx_dpa_matrix__scenario5.pkl`.
3. Regenerate tests/fixtures/bundles/step_03_scenario_5.json so
   dpa_trigger_rows contains A-01 + A-07.
4. Run a retrieval-only check against the scenario-scoped indices to confirm
   both A-01 and A-07 surface.

This script writes ONLY to scenario_data/scenario_5/, tests/fixtures/, and the
scenario-scoped chroma/bm25 directories. It does not touch production indices.
"""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(REPO_ROOT))

from chunking import Chunk  # noqa: E402
from indexing.build_bm25_index import BM25Index  # noqa: E402
from indexing.build_vector_index import VectorIndex  # noqa: E402
from indexing.embeddings import embed_batch  # noqa: E402
from indexing.metadata_schema import (  # noqa: E402
    chroma_metadata_from_chunk,
    metadata_from_chunk,
)

PROD_DPA_PATH = REPO_ROOT / "data" / "processed" / "scenario_2" / "chunks" / "DPA-TM-001.json"
SCENARIO_ROOT = REPO_ROOT / "scenario_data" / "scenario_5"
SOURCE_PATH = SCENARIO_ROOT / "sources" / "DPA-TM-001_scenario5.json"
CHROMA_DIR = SCENARIO_ROOT / "chroma"
BM25_DIR = SCENARIO_ROOT / "bm25"
REGISTRY_DIR = SCENARIO_ROOT / "vector_registry"
FIXTURE_PATH = REPO_ROOT / "tests" / "fixtures" / "bundles" / "step_03_scenario_5.json"
COLLECTION_NAME = "idx_dpa_matrix__scenario5"
SCENARIO_VERSION = "2.1-scenario5"

A_07_ROW = {
    "chunk_id": "DPA-TM-001__row_A-07",
    "source_id": "DPA-TM-001",
    "source_name": "DPA Legal Trigger Matrix",
    "source_type": "LEGAL_TRIGGER_MATRIX",
    "version": SCENARIO_VERSION,
    "document_date": "2026-04-04",
    "freshness_status": "CURRENT",
    "authority_tier": 1,
    "retrieval_lane": "INDEXED_HYBRID",
    "allowed_agents": ["legal"],
    "is_primary_citable": True,
    "manifest_status": "CONFIRMED",
    "chunk_type": "ROW",
    "chunk_order": 28,
    "citation_label": "DPA-TM-001 row A-07",
    "text": (
        "ID: A-07\n"
        "Trigger Condition: Vendor will process personal data of EU/EEA data subjects "
        "in connection with Lichen's internal workforce-adjacent analytics "
        "(e.g., employee scheduling, operational efficiency, workforce planning), "
        "where Lichen has a documented legitimate interest under GDPR Art. 6(1)(f) "
        "and the vendor is engaged under a controller-to-controller allocation "
        "rather than as an Art. 28 processor\n"
        "Data Types Involved: Personal data of EU/EEA employees or contractors used "
        "for workforce-adjacent analytics (name, email, employee ID, behavioral "
        "telemetry, device identifiers, shift/scheduling data)\n"
        "Regulations Triggered: GDPR Art. 6(1)(f) (legitimate interest); Recital 47; "
        "EDPB Guidelines 07/2020 on controller-processor concepts (controller-to-"
        "controller allocation)\n"
        "DPA Required?: NOT REQUIRED\n"
        "Required DPA / Contract Clauses: No GDPR Art. 28 DPA required where the "
        "vendor is engaged under a controller-to-controller allocation for Lichen's "
        "internal workforce-adjacent analytics and the processing relies on "
        "Art. 6(1)(f) legitimate interest. A signed Legitimate Interest Assessment "
        "(LIA) memorializing the Art. 6(1)(f) balancing test is sufficient. "
        "Standard NDA and confidentiality provisions cover confidentiality "
        "obligations. Controller-to-controller relationship must be explicit in the "
        "commercial agreement.\n"
        "Additional Obligations: Privacy Team completes and retains an LIA "
        "documenting purpose, necessity, and the Art. 6(1)(f) balancing test before "
        "processing begins. Controller-to-controller allocation must be stated in "
        "writing in the commercial agreement. Vendor privacy notice must align with "
        "Lichen's Art. 13/14 disclosures to data subjects.\n"
        "Lichen Action / Owner: Owner: Privacy Team (LIA) / Legal (controller-to-"
        "controller allocation)"
    ),
    "section_id": None,
    "row_id": "A-07",
    "record_id": None,
    "thread_id": None,
    "domain_scope": None,
}


def rebuild_source() -> list[dict]:
    """Copy all production v2.1 rows, re-version them, and append A-07."""

    prod_rows = json.loads(PROD_DPA_PATH.read_text(encoding="utf-8"))
    scenario_rows: list[dict] = []
    for row in prod_rows:
        new_row = dict(row)
        new_row["version"] = SCENARIO_VERSION
        scenario_rows.append(new_row)

    scenario_rows.append(A_07_ROW)

    SOURCE_PATH.parent.mkdir(parents=True, exist_ok=True)
    SOURCE_PATH.write_text(
        json.dumps(scenario_rows, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"[1/4] wrote {SOURCE_PATH} ({len(scenario_rows)} rows)")
    return scenario_rows


def _chunks_from_rows(rows: list[dict]) -> list[Chunk]:
    return [Chunk.from_dict(row) for row in rows]


def rebuild_indices(rows: list[dict]) -> None:
    """Re-chunk + re-embed into scenario-scoped Chroma + BM25 indices."""

    chunks = _chunks_from_rows(rows)

    # Fresh chroma dir so no stale embeddings remain.
    if CHROMA_DIR.exists():
        shutil.rmtree(CHROMA_DIR)
    CHROMA_DIR.mkdir(parents=True, exist_ok=True)

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

    REGISTRY_DIR.mkdir(parents=True, exist_ok=True)
    vector_index = VectorIndex(
        persist_directory=CHROMA_DIR,
        registry_directory=REGISTRY_DIR,
    )
    vector_count = vector_index.add_chunks(COLLECTION_NAME, vector_records)

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

    print(
        f"[2/4] indexed {vector_count} vectors into {CHROMA_DIR} ({COLLECTION_NAME}); "
        f"{bm25_count} docs into {BM25_DIR / f'{COLLECTION_NAME}.pkl'}"
    )


def _trigger_row_payload(row: dict, *, retrieval_score: float, rerank_score: float) -> dict:
    return {
        "source_id": row["source_id"],
        "version": row["version"],
        "chunk_id": row["chunk_id"],
        "section_id": row.get("section_id"),
        "row_id": row.get("row_id"),
        "thread_id": row.get("thread_id"),
        "text": row["text"],
        "retrieval_score": retrieval_score,
        "rerank_score": rerank_score,
        "citation_class": "PRIMARY",
    }


def rebuild_fixture(rows: list[dict]) -> None:
    """Regenerate step_03_scenario_5.json with A-01 + A-07 in dpa_trigger_rows."""

    rows_by_id = {row["row_id"]: row for row in rows if row.get("row_id")}
    a01 = rows_by_id["A-01"]
    a07 = rows_by_id["A-07"]

    fixture = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    fixture["bundle"]["dpa_trigger_rows"] = [
        _trigger_row_payload(a01, retrieval_score=0.94, rerank_score=0.92),
        _trigger_row_payload(a07, retrieval_score=0.91, rerank_score=0.89),
    ]

    FIXTURE_PATH.write_text(
        json.dumps(fixture, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"[3/4] wrote {FIXTURE_PATH} (dpa_trigger_rows = [A-01, A-07])")


def retrieval_check() -> None:
    """Query the scenario-scoped indices and confirm both A-01 and A-07 surface."""

    query_text = (
        "SaaS vendor processing personal data of EU/EEA employees for internal "
        "workforce-adjacent analytics (scheduling, operational efficiency); "
        "determine whether an Art. 28 DPA is required"
    )

    vector_index = VectorIndex(
        persist_directory=CHROMA_DIR,
        registry_directory=REGISTRY_DIR,
    )
    vector_hits = vector_index.query(COLLECTION_NAME, query_text, k=8)
    vector_ids = [hit["chunk_id"] for hit in vector_hits]

    bm25_index = BM25Index(persist_directory=BM25_DIR)
    bm25_hits = bm25_index.query(COLLECTION_NAME, query_text, k=8)
    bm25_ids = [hit["chunk_id"] for hit in bm25_hits]

    combined = set(vector_ids) | set(bm25_ids)

    print("[4/4] retrieval check:")
    print(f"  query = {query_text!r}")
    print(f"  vector top-8: {vector_ids}")
    print(f"  bm25   top-8: {bm25_ids}")

    required = {"DPA-TM-001__row_A-01", "DPA-TM-001__row_A-07"}
    missing = required - combined
    if missing:
        raise SystemExit(
            f"retrieval FAIL: missing from combined candidate set: {sorted(missing)}"
        )
    print(f"  PASS: both A-01 and A-07 surface (combined union = {sorted(required)})")


def main() -> None:
    rows = rebuild_source()
    rebuild_indices(rows)
    rebuild_fixture(rows)
    retrieval_check()


if __name__ == "__main__":
    main()
