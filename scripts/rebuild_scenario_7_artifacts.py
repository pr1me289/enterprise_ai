"""Rebuild scenario-7 PAM-001 artifacts end-to-end.

Scenario 7 — Procurement Agent, No-Matching-Row Escalation.

1. Write scenario_data/scenario_7/sources/PAM-001_scenario7.json as a
   deliberate subset of production PAM-001: rows A-T1, B-T1, C-T1 only.
   This leaves Classes D and E uncovered entirely so the scenario-7
   questionnaire profile (Class D — Technology Professional Services)
   has no matching row.
2. Re-chunk + re-embed into the scenario-scoped Chroma collection
   `idx_procurement_matrix__scenario7` and BM25 bundle
   `scenario_data/scenario_7/bm25/idx_procurement_matrix__scenario7.pkl`.
3. Regenerate tests/fixtures/bundles/step_04_scenario_7.json so
   approval_path_matrix_rows contains all three rows as the Supervisor-
   assembled candidate set.
4. Run a retrieval-only check confirming the three rows surface for a
   questionnaire-representative query and that none of them cleanly
   matches Class D × Tier 3.

This script writes ONLY to scenario_data/scenario_7/ and tests/fixtures/.
It does not touch production indices.
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

PROD_PAM_PATH = REPO_ROOT / "data" / "processed" / "scenario_1" / "chunks" / "PAM-001.json"
SCENARIO_ROOT = REPO_ROOT / "scenario_data" / "scenario_7"
SOURCE_PATH = SCENARIO_ROOT / "sources" / "PAM-001_scenario7.json"
CHROMA_DIR = SCENARIO_ROOT / "chroma"
BM25_DIR = SCENARIO_ROOT / "bm25"
REGISTRY_DIR = SCENARIO_ROOT / "vector_registry"
FIXTURE_PATH = REPO_ROOT / "tests" / "fixtures" / "bundles" / "step_04_scenario_7.json"
COLLECTION_NAME = "idx_procurement_matrix__scenario7"
SCENARIO_VERSION = "3.0-scenario7"

# The three rows preserved for scenario_7 — Classes A, B, C at Tier 1 only.
# Classes D and E are intentionally absent, leaving the scenario_7
# questionnaire profile (vendor_class "Class D — Technology Professional
# Services") uncovered. The model must not silently fall back to the
# nearest Class (A/B/C) row — it must escalate per §8.5 and §9.2 Example C.
KEEP_ROW_IDS = {"A-T1", "B-T1", "C-T1"}


def rebuild_source() -> list[dict]:
    """Write the scenario-7 PAM-001 subset (A-T1, B-T1, C-T1, re-versioned)."""
    prod_rows = json.loads(PROD_PAM_PATH.read_text(encoding="utf-8"))
    scenario_rows: list[dict] = []
    for row in prod_rows:
        if row.get("row_id") not in KEEP_ROW_IDS:
            continue
        new_row = dict(row)
        new_row["version"] = SCENARIO_VERSION
        scenario_rows.append(new_row)

    found = {row["row_id"] for row in scenario_rows}
    missing = KEEP_ROW_IDS - found
    if missing:
        raise SystemExit(f"scenario-7 source build FAIL: missing expected rows {sorted(missing)}")

    SOURCE_PATH.parent.mkdir(parents=True, exist_ok=True)
    SOURCE_PATH.write_text(
        json.dumps(scenario_rows, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"[1/4] wrote {SOURCE_PATH} ({len(scenario_rows)} rows: {sorted(found)})")
    return scenario_rows


def _chunks_from_rows(rows: list[dict]) -> list[Chunk]:
    return [Chunk.from_dict(row) for row in rows]


def rebuild_indices(rows: list[dict]) -> None:
    """Re-chunk + re-embed into scenario-scoped Chroma + BM25 indices."""
    chunks = _chunks_from_rows(rows)

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


def _matrix_row_payload(row: dict, *, retrieval_score: float, rerank_score: float) -> dict:
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
    """Write step_04_scenario_7.json with the three matrix rows as the
    Supervisor-assembled candidate set and a questionnaire profile that
    falls into the Class-D × Tier-3 gap."""
    rows_by_id = {row["row_id"]: row for row in rows if row.get("row_id")}
    a_t1 = rows_by_id["A-T1"]
    b_t1 = rows_by_id["B-T1"]
    c_t1 = rows_by_id["C-T1"]

    fixture = {
        "scenario": "scenario_7",
        "agent": "procurement_agent",
        "bundle": {
            "source_ids": ["STEP-02", "STEP-03", "VQ-OC-001", "PAM-001"],
            "it_security_output": {
                "data_classification": "UNREGULATED",
                "fast_track_eligible": True,
                "integration_tier": "TIER_1",
                "security_followup_required": False,
                "policy_citations": [
                    {
                        "source_id": "ISP-001",
                        "version": "4.2",
                        "chunk_id": "ISP-001__section_12",
                        "section_id": "12",
                        "citation_class": "PRIMARY",
                    }
                ],
                "status": "complete",
            },
            "legal_output": {
                "dpa_required": False,
                "dpa_blocker": False,
                "nda_status": "EXECUTED",
                "nda_blocker": False,
                "trigger_rule_cited": [],
                "policy_citations": [
                    {
                        "source_id": "ISP-001",
                        "version": "4.2",
                        "chunk_id": "ISP-001__section_12_1_4",
                        "section_id": "12.1.4",
                        "citation_class": "PRIMARY",
                    }
                ],
                "status": "complete",
            },
            "questionnaire": {
                "vendor_class": "Class D \u2014 Technology Professional Services",
                "deal_size": 85000,
                "existing_nda_status": "EXECUTED",
                "existing_msa": True,
            },
            "approval_path_matrix_rows": [
                _matrix_row_payload(a_t1, retrieval_score=0.71, rerank_score=0.68),
                _matrix_row_payload(b_t1, retrieval_score=0.69, rerank_score=0.66),
                _matrix_row_payload(c_t1, retrieval_score=0.67, rerank_score=0.64),
            ],
            "fast_track_routing_rows": [],
            "slack_procurement_chunks": [],
            "bundle_meta": {
                "admissible": True,
                "missing_fields": [],
                "prohibited_sources": [],
            },
        },
        "pipeline_run_id": "scenario_7_synthesized",
    }

    FIXTURE_PATH.write_text(
        json.dumps(fixture, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"[3/4] wrote {FIXTURE_PATH} (approval_path_matrix_rows = [A-T1, B-T1, C-T1])")


def retrieval_check() -> None:
    """Query the scenario-scoped index and confirm the candidate set surfaces
    while none of the rows cleanly matches Class D × Tier 3."""
    query_text = (
        "Technology professional services vendor engagement; Class D vendor profile; "
        "integration tier TIER_1; fast-track eligible; non-regulated data; "
        "$85K annual contract value; determine approval path"
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

    required = {
        "PAM-001__row_A-T1",
        "PAM-001__row_B-T1",
        "PAM-001__row_C-T1",
    }
    missing = required - combined
    if missing:
        raise SystemExit(
            f"retrieval FAIL: missing from combined candidate set: {sorted(missing)}"
        )

    # Gap assertion: no row in the subset covers Class D. The scenario
    # relies on this single-axis gap — the questionnaire vendor_class is
    # Class D and no matrix row in the subset matches Class D.
    for hit_id in combined:
        row_id = hit_id.rsplit("__row_", 1)[-1]
        row_class, _row_tier = row_id.split("-T")
        if row_class == "D":
            raise SystemExit(
                f"gap assertion FAIL: row {row_id!r} would cover Class D — "
                "the scenario requires Class D absent from the matrix subset"
            )

    print(f"  PASS: all three candidate rows surface (combined union includes {sorted(required)})")
    print(f"  PASS: no row in the subset covers Class D (gap confirmed)")


def main() -> None:
    rows = rebuild_source()
    rebuild_indices(rows)
    rebuild_fixture(rows)
    retrieval_check()


if __name__ == "__main__":
    main()
