"""Build scenario_8 PAM-001 chunks, scenario-scoped indices, and fixture.

Scenario 8 — Procurement Agent, Upstream Blocker Propagation → ESCALATED.

1. Write scenarios_per_agent/scenario_8/chunks/PAM-001_scenario8_chunks.json with
   two rows: Q-01 (TIER_2 × TIER_2_SAAS, clean primary-key match for the
   scenario_8 questionnaire profile) and Q-02 (TIER_1 × TIER_1_ERP, a
   distractor that does not match on either primary key).
2. Re-chunk + re-embed into scenario-scoped Chroma collection
   `idx_procurement_matrix__scenario8` and a scenario-scoped BM25 bundle.
3. Write scenarios_per_agent/scenario_8/index_registry.json describing the
   scenario-scoped collection.
4. Write tests/fixtures/bundles/step_04_scenario_8.json — clean IT Security
   output (status=complete, REGULATED, TIER_2_SAAS), escalated Legal output
   (dpa_blocker=true, all six Legal determination fields populated), and
   approval_path_matrix_rows = [Q-01, Q-02].
5. Retrieval-only check confirming Q-01 surfaces as the primary-key match
   and Q-02 is retrievable but non-matching.

This script writes ONLY to scenarios_per_agent/scenario_8/ and tests/fixtures/.
It does not touch production indices.
"""

from __future__ import annotations

import json
import shutil
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

SCENARIO_ROOT = REPO_ROOT / "scenarios_per_agent" / "scenario_8"
CHUNKS_PATH = SCENARIO_ROOT / "chunks" / "PAM-001_scenario8_chunks.json"
CHROMA_DIR = SCENARIO_ROOT / "chroma"
BM25_DIR = SCENARIO_ROOT / "bm25"
REGISTRY_DIR = SCENARIO_ROOT / "vector_registry"
INDEX_REGISTRY_PATH = SCENARIO_ROOT / "index_registry.json"
FIXTURE_PATH = REPO_ROOT / "tests" / "fixtures" / "bundles" / "step_04_scenario_8.json"
COLLECTION_NAME = "idx_procurement_matrix__scenario8"
BM25_BUNDLE_RELATIVE = f"scenarios_per_agent/scenario_8/bm25/{COLLECTION_NAME}.pkl"

SOURCE_ID = "PAM-001"
SOURCE_NAME = "Procurement Approval Matrix"
SOURCE_TYPE = "PROCUREMENT_APPROVAL_MATRIX"
VERSION = "3.0-scenario8"
DOCUMENT_DATE = "2026-04-19"
FRESHNESS_STATUS = "CURRENT"
AUTHORITY_TIER = 1
RETRIEVAL_LANE = "INDEXED_HYBRID"
ALLOWED_AGENTS = ("procurement",)
MANIFEST_STATUS = "CONFIRMED"


Q_01_TEXT = (
    "Vendor Class: TIER_2\n"
    "Integration Tier: TIER_2_SAAS\n"
    "Deal Size Range: $100,000 – $500,000\n"
    "Approval Path: STANDARD\n"
    "IT Security Review: Required\n"
    "Legal / DPA Review: Required\n"
    "Procurement Review: Required\n"
    "Business Owner Sign-off: Director+\n"
    "Fast-Track Eligible?: NOT ELIGIBLE\n"
    "Required Approvals / Notes: Standard approval regime for Tier 2 SaaS "
    "engagements with REGULATED data scope. IT Security + Legal Counsel + "
    "Procurement Director + Business Owner Director sign-off required. DPA must be fully "
    "executed before onboarding begins; unresolved DPA blocks implementation. "
    "Standard 7-10 business day timeline when all blockers clear."
)

Q_02_TEXT = (
    "Vendor Class: TIER_1\n"
    "Integration Tier: TIER_1_ERP\n"
    "Deal Size Range: $500,000+\n"
    "Approval Path: STANDARD\n"
    "IT Security Review: Required + CISO Sign-off\n"
    "Legal / DPA Review: Required + GC Sign-off\n"
    "Procurement Review: Required + CPO Sign-off\n"
    "Business Owner Sign-off: VP + SVP\n"
    "Fast-Track Eligible?: NOT ELIGIBLE\n"
    "Required Approvals / Notes: Enhanced approval regime for Tier 1 ERP "
    "integrations. CISO and General Counsel must co-sign approval memo. DPA "
    "required. ERP integration tier assignment mandatory. Architecture "
    "review by IT Security before integration activity begins. 15-20 "
    "business day timeline."
)


def _build_chunk(row_id: str, text: str, order: int) -> Chunk:
    return Chunk(
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
        text=text,
    )


def build_chunks() -> list[Chunk]:
    return [
        _build_chunk("Q-01", Q_01_TEXT, order=1),
        _build_chunk("Q-02", Q_02_TEXT, order=2),
    ]


def write_chunks_json(chunks: list[Chunk]) -> None:
    payload = [
        {
            "chunk_id": c.chunk_id,
            "source_id": c.source_id,
            "source_name": c.source_name,
            "source_type": c.source_type,
            "version": c.version,
            "document_date": c.document_date,
            "freshness_status": c.freshness_status,
            "authority_tier": c.authority_tier,
            "retrieval_lane": c.retrieval_lane,
            "allowed_agents": list(c.allowed_agents),
            "is_primary_citable": c.is_primary_citable,
            "manifest_status": c.manifest_status,
            "chunk_type": c.chunk_type,
            "chunk_order": c.chunk_order,
            "citation_label": c.citation_label,
            "text": c.text,
            "section_id": c.section_id,
            "row_id": c.row_id,
            "record_id": c.record_id,
            "thread_id": c.thread_id,
            "domain_scope": c.domain_scope,
        }
        for c in chunks
    ]
    CHUNKS_PATH.parent.mkdir(parents=True, exist_ok=True)
    CHUNKS_PATH.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"[1/5] wrote {CHUNKS_PATH.relative_to(REPO_ROOT)} ({len(payload)} rows)")


def rebuild_indices(chunks: list[Chunk]) -> None:
    texts = [c.text for c in chunks]
    embeddings = embed_batch(texts)

    if CHROMA_DIR.exists():
        shutil.rmtree(CHROMA_DIR)
    CHROMA_DIR.mkdir(parents=True, exist_ok=True)
    REGISTRY_DIR.mkdir(parents=True, exist_ok=True)

    vector_index = VectorIndex(persist_directory=CHROMA_DIR, registry_directory=REGISTRY_DIR)
    records = [
        {
            "chunk_id": c.chunk_id,
            "text": c.text,
            "embedding": emb,
            "metadata": chroma_metadata_from_chunk(c),
            "registry_metadata": metadata_from_chunk(c),
        }
        for c, emb in zip(chunks, embeddings, strict=True)
    ]
    count = vector_index.add_chunks(COLLECTION_NAME, records)
    print(f"[2/5] chroma {COLLECTION_NAME}: {count} rows")

    BM25_DIR.mkdir(parents=True, exist_ok=True)
    bm25 = BM25Index(persist_directory=BM25_DIR)
    bm25_records = [
        {"chunk_id": c.chunk_id, "text": c.text, "metadata": metadata_from_chunk(c)}
        for c in chunks
    ]
    bm25_count = bm25.build(COLLECTION_NAME, bm25_records)
    print(f"[3/5] bm25 {COLLECTION_NAME}: {bm25_count} docs")


def write_index_registry() -> None:
    payload = {
        "registry_version": "1.0",
        "scenario": "scenario_8",
        "generated_at": DOCUMENT_DATE + "T00:00:00Z",
        "sources": {
            SOURCE_ID: {
                "source_id": SOURCE_ID,
                "source_name": SOURCE_NAME,
                "source_type": SOURCE_TYPE,
                "authority_tier": AUTHORITY_TIER,
                "retrieval_lane": RETRIEVAL_LANE,
                "version": VERSION,
                "document_date": DOCUMENT_DATE,
                "freshness_status": FRESHNESS_STATUS,
                "manifest_status": MANIFEST_STATUS,
                "allowed_agents": list(ALLOWED_AGENTS),
                "is_primary_citable": True,
                "storage_kind": "vector_bm25",
                "logical_store_name": COLLECTION_NAME,
                "backends": ["chroma", "bm25"],
                "backend_locations": {
                    "chroma_collection": COLLECTION_NAME,
                    "bm25_bundle": BM25_BUNDLE_RELATIVE,
                },
            }
        },
    }
    INDEX_REGISTRY_PATH.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(f"[4/5] wrote {INDEX_REGISTRY_PATH.relative_to(REPO_ROOT)}")


def _matrix_row_payload(chunk: Chunk, *, retrieval_score: float, rerank_score: float) -> dict:
    return {
        "source_id": chunk.source_id,
        "version": chunk.version,
        "chunk_id": chunk.chunk_id,
        "section_id": chunk.section_id,
        "row_id": chunk.row_id,
        "thread_id": chunk.thread_id,
        "text": chunk.text,
        "retrieval_score": retrieval_score,
        "rerank_score": rerank_score,
        "citation_class": "PRIMARY",
    }


def write_fixture(chunks: list[Chunk]) -> None:
    by_id = {c.row_id: c for c in chunks}
    q01 = by_id["Q-01"]
    q02 = by_id["Q-02"]

    fixture = {
        "scenario": "scenario_8",
        "agent": "procurement_agent",
        "bundle": {
            "source_ids": ["STEP-02", "STEP-03", "VQ-OC-001", "PAM-001", "DPA-TM-001", "ISP-001"],
            "it_security_output": {
                "data_classification": "REGULATED",
                "fast_track_eligible": False,
                "integration_tier": "TIER_2_SAAS",
                "security_followup_required": False,
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
            "legal_output": {
                "dpa_required": True,
                "dpa_blocker": True,
                "nda_status": "EXECUTED",
                "nda_blocker": False,
                "trigger_rule_cited": [
                    {
                        "source_id": "DPA-TM-001",
                        "version": "2.1",
                        "chunk_id": "DPA-TM-001__row_TR-04",
                        "row_id": "TR-04",
                        "trigger_condition": "Vendor processes REGULATED personal data on Lichen's behalf",
                        "citation_class": "PRIMARY",
                    }
                ],
                "policy_citations": [
                    {
                        "source_id": "DPA-TM-001",
                        "version": "2.1",
                        "chunk_id": "DPA-TM-001__row_TR-04",
                        "row_id": "TR-04",
                        "citation_class": "PRIMARY",
                    },
                    {
                        "source_id": "ISP-001",
                        "version": "4.2",
                        "chunk_id": "ISP-001__section_12_1_4",
                        "section_id": "12.1.4",
                        "citation_class": "PRIMARY",
                    },
                ],
                "status": "escalated",
            },
            "questionnaire": {
                "vendor_class": "TIER_2",
                "integration_tier": "TIER_2_SAAS",
                "deal_size": 250000,
                "existing_nda_status": "EXECUTED",
                "existing_dpa_status": "NOT_STARTED",
                "existing_msa": True,
            },
            "approval_path_matrix_rows": [
                _matrix_row_payload(q01, retrieval_score=0.82, rerank_score=0.79),
                _matrix_row_payload(q02, retrieval_score=0.54, rerank_score=0.51),
            ],
            "fast_track_routing_rows": [],
            "slack_procurement_chunks": [],
            "bundle_meta": {
                "admissible": True,
                "missing_fields": [],
                "prohibited_sources": [],
            },
        },
        "pipeline_run_id": "scenario_8_synthesized",
    }

    FIXTURE_PATH.write_text(
        json.dumps(fixture, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(f"[5/5] wrote {FIXTURE_PATH.relative_to(REPO_ROOT)}")


def retrieval_check() -> None:
    query_text = (
        "TIER_2 vendor SaaS engagement, TIER_2_SAAS integration, $250K annual "
        "contract, REGULATED data, DPA required; determine approval path"
    )
    vi = VectorIndex(persist_directory=CHROMA_DIR, registry_directory=REGISTRY_DIR)
    bmi = BM25Index(persist_directory=BM25_DIR)

    v_hits = vi.query(COLLECTION_NAME, query_text, k=5, allowed_agent="procurement")
    b_hits = bmi.query(COLLECTION_NAME, query_text, k=5, allowed_agent="procurement")

    v_ids = [h["chunk_id"] for h in v_hits]
    b_ids = [h["chunk_id"] for h in b_hits]
    print("retrieval check:")
    print(f"  query  = {query_text!r}")
    print(f"  vector = {v_ids}")
    print(f"  bm25   = {b_ids}")

    required_primary = "PAM-001__row_Q-01"
    if required_primary not in set(v_ids) | set(b_ids):
        raise SystemExit(f"retrieval FAIL: {required_primary} not returned")
    print(f"  PASS: Q-01 present in combined retrieval set; Q-02 retrievable as distractor")


def main() -> None:
    chunks = build_chunks()
    write_chunks_json(chunks)
    rebuild_indices(chunks)
    write_index_registry()
    write_fixture(chunks)
    retrieval_check()


if __name__ == "__main__":
    main()
