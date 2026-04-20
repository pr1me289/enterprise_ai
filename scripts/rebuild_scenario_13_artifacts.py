"""Build scenario_13 PAM-001 chunks, scenario-scoped indices, and fixture.

Scenario 13 — Procurement Agent, Clean Upstream Pass → COMPLETE.

1. Write scenario_data/scenario_13/chunks/PAM-001_scenario13_chunks.json with
   two rows: Q-01-FASTTRACK (TIER_2 x TIER_3 x UNREGULATED, the clean primary-
   key match for the scenario_13 questionnaire profile) and Q-02-STANDARD
   (TIER_2 x TIER_2_SAAS x REGULATED, a structurally-valid distractor that
   shares vendor_class but mismatches on integration_tier).
2. Re-chunk + re-embed into scenario-scoped Chroma collection
   `idx_procurement_matrix__scenario13` and a scenario-scoped BM25 bundle.
3. Write scenario_data/scenario_13/index_registry.json describing the
   scenario-scoped collection.
4. Write tests/fixtures/bundles/step_04_scenario_13.json - clean IT Security
   output (status=complete, EXPORT_ONLY/TIER_3/UNREGULATED/fast_track_eligible
   true), clean Legal output (dpa_required=false, all six Legal determination
   fields populated, no blockers), questionnaire matching Q-01-FASTTRACK on
   both primary keys, and approval_path_matrix_rows = [Q-01-FASTTRACK,
   Q-02-STANDARD].
5. Retrieval-only check confirming Q-01-FASTTRACK surfaces as the primary-
   key match and Q-02-STANDARD is retrievable but non-matching.

This script writes ONLY to scenario_data/scenario_13/ and tests/fixtures/.
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

SCENARIO_ROOT = REPO_ROOT / "scenario_data" / "scenario_13"
CHUNKS_PATH = SCENARIO_ROOT / "chunks" / "PAM-001_scenario13_chunks.json"
CHROMA_DIR = SCENARIO_ROOT / "chroma"
BM25_DIR = SCENARIO_ROOT / "bm25"
REGISTRY_DIR = SCENARIO_ROOT / "vector_registry"
INDEX_REGISTRY_PATH = SCENARIO_ROOT / "index_registry.json"
FIXTURE_PATH = REPO_ROOT / "tests" / "fixtures" / "bundles" / "step_04_scenario_13.json"
COLLECTION_NAME = "idx_procurement_matrix__scenario13"
BM25_BUNDLE_RELATIVE = f"scenario_data/scenario_13/bm25/{COLLECTION_NAME}.pkl"

SOURCE_ID = "PAM-001"
SOURCE_NAME = "Procurement Approval Matrix"
SOURCE_TYPE = "PROCUREMENT_APPROVAL_MATRIX"
VERSION = "3.0-scenario13"
DOCUMENT_DATE = "2026-04-19"
FRESHNESS_STATUS = "CURRENT"
AUTHORITY_TIER = 1
RETRIEVAL_LANE = "INDEXED_HYBRID"
ALLOWED_AGENTS = ("procurement",)
MANIFEST_STATUS = "CONFIRMED"


# Q-01-FASTTRACK is the matching row. Free-text rendering enumerates every
# approver and the timeline so the structured columns match the prose 1:1
# (the Scenario 9 fixture-integrity lesson).
Q_01_FASTTRACK_TEXT = (
    "Vendor Class: TIER_2\n"
    "Integration Tier: TIER_3\n"
    "Data Classification: UNREGULATED\n"
    "Deal Size Range: $50,000 - $250,000\n"
    "Fast-Track Eligible Required: true\n"
    "Approval Path: FAST_TRACK\n"
    "Required Approvers: Procurement Manager, IT Security Manager\n"
    "Estimated Timeline: 2-3 business days\n"
    "Required Approvals / Notes: Fast-track approval regime for Tier 2 vendor "
    "engagements with Tier 3 export-only integration footprint and UNREGULATED "
    "data scope. Two approvers required, both non-blocking: Procurement "
    "Manager (procurement domain) and IT Security Manager (security domain). "
    "No Legal sign-off required when no DPA is triggered. No Business Owner "
    "sign-off required at this deal-size band. Timeline: 2-3 business days "
    "when both approvers respond promptly. This row applies only when "
    "fast_track_eligible is true upstream from STEP-02 and no DPA blocker is "
    "active from STEP-03."
)

# Q-02-STANDARD shares vendor_class with the scenario profile so it gets
# retrieved, but its integration_tier and data_classification both diverge,
# so it is not the primary-key match. Its prose is more elaborate to test
# that the model commits to primary-key match over surface-feature appeal.
Q_02_STANDARD_TEXT = (
    "Vendor Class: TIER_2\n"
    "Integration Tier: TIER_2_SAAS\n"
    "Data Classification: REGULATED\n"
    "Deal Size Range: $100,000 - $500,000\n"
    "Fast-Track Eligible Required: false\n"
    "Approval Path: STANDARD\n"
    "Required Approvers: Procurement Director, IT Security Manager, Legal "
    "Counsel, Business Owner (Director+)\n"
    "Estimated Timeline: 10-15 business days\n"
    "Required Approvals / Notes: Standard approval regime for Tier 2 SaaS "
    "engagements with REGULATED data scope. Four approvers required: "
    "Procurement Director, IT Security Manager, Legal Counsel, Business "
    "Owner (Director+). Legal sign-off required because REGULATED data "
    "triggers DPA review per DPA-TM-001. IT Security sign-off required for "
    "any SaaS integration carrying production credentials. Business Owner "
    "(Director+) signs off on commercial terms. Timeline: 10-15 business "
    "days when all approvers respond promptly and DPA is fully executed."
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
        _build_chunk("Q-01-FASTTRACK", Q_01_FASTTRACK_TEXT, order=1),
        _build_chunk("Q-02-STANDARD", Q_02_STANDARD_TEXT, order=2),
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
        "scenario": "scenario_13",
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
    q01 = by_id["Q-01-FASTTRACK"]
    q02 = by_id["Q-02-STANDARD"]

    fixture = {
        "scenario": "scenario_13",
        "agent": "procurement_agent",
        "bundle": {
            "source_ids": [
                "STEP-02",
                "STEP-03",
                "VQ-OC-001",
                "PAM-001",
                "ISP-001",
            ],
            # Full STEP-02 contract per ORCH-PLAN-001 - clean COMPLETE pass.
            "it_security_output": {
                "integration_type_normalized": "EXPORT_ONLY",
                "integration_tier": "TIER_3",
                "data_classification": "UNREGULATED",
                "eu_personal_data_present": "NO",
                "fast_track_eligible": True,
                "fast_track_rationale": "ELIGIBLE_LOW_RISK",
                "security_followup_required": False,
                "nda_status_from_questionnaire": "EXECUTED",
                "required_security_actions": [],
                "policy_citations": [
                    {
                        "source_id": "ISP-001",
                        "version": "4.2",
                        "chunk_id": "ISP-001__section_12",
                        "section_id": "12.2",
                        "citation_class": "PRIMARY",
                    }
                ],
                "status": "complete",
            },
            # Legal STEP-03 - clean COMPLETE: no DPA required, NDA executed,
            # no active blockers. trigger_rule_cited is empty per the spec
            # when dpa_required=false (no rule fired).
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
            # Questionnaire matches Q-01-FASTTRACK on both primary keys
            # (vendor_class=TIER_2, integration_tier=TIER_3) and the deal
            # size falls cleanly inside Q-01-FASTTRACK's $50K-$250K range.
            "questionnaire": {
                "vendor_class": "TIER_2",
                "integration_tier": "TIER_3",
                "deal_size": 150000,
                "existing_nda_status": "EXECUTED",
                "existing_dpa_status": "NOT_APPLICABLE",
                "existing_msa": True,
            },
            # Q-01-FASTTRACK retrieves higher than Q-02-STANDARD because the
            # questionnaire matches all three primary keys (vendor_class,
            # integration_tier, data_classification) cleanly. Q-02-STANDARD
            # is retrievable on shared vendor_class but mismatches on the
            # other two primary keys.
            "approval_path_matrix_rows": [
                _matrix_row_payload(q01, retrieval_score=0.88, rerank_score=0.85),
                _matrix_row_payload(q02, retrieval_score=0.61, rerank_score=0.57),
            ],
            "fast_track_routing_rows": [],
            "slack_procurement_chunks": [],
            "bundle_meta": {
                "admissible": True,
                "missing_fields": [],
                "prohibited_sources": [],
            },
        },
        "pipeline_run_id": "scenario_13_synthesized",
    }

    FIXTURE_PATH.write_text(
        json.dumps(fixture, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(f"[5/5] wrote {FIXTURE_PATH.relative_to(REPO_ROOT)}")


def retrieval_check() -> None:
    query_text = (
        "TIER_2 vendor TIER_3 export-only integration UNREGULATED data "
        "$150K annual contract fast-track approval path"
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

    required_primary = "PAM-001__row_Q-01-FASTTRACK"
    distractor = "PAM-001__row_Q-02-STANDARD"
    combined = set(v_ids) | set(b_ids)
    if required_primary not in combined:
        raise SystemExit(f"retrieval FAIL: {required_primary} not returned")
    if distractor not in combined:
        raise SystemExit(
            f"retrieval FAIL: distractor {distractor} not retrievable - "
            "scenario must surface it as a candidate so the model's primary-"
            "key matching is actually exercised"
        )
    print(
        "  PASS: Q-01-FASTTRACK present in combined retrieval set; "
        "Q-02-STANDARD retrievable as distractor"
    )


def main() -> None:
    chunks = build_chunks()
    write_chunks_json(chunks)
    rebuild_indices(chunks)
    write_index_registry()
    write_fixture(chunks)
    retrieval_check()


if __name__ == "__main__":
    main()
