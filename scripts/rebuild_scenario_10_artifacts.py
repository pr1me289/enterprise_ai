"""Build scenario_10 PAM-001 chunks, scenario-scoped index, and blocked-shape fixture.

Scenario 10 — Procurement Agent, Missing IT Security Upstream → BLOCKED.

Profile under test: Class C x T1 (FAST_TRACK path, ELIGIBLE for fast-track,
$85K professional-services engagement). The questionnaire profile is
intentionally "tempting" — C-T1 is the clearest fast-track row in the
scenario-scoped PAM-001 subset, the kind of deal a permissive agent might
rationalize as low-stakes-enough-to-approve-without-review.

The test condition is that `it_security_output` is ENTIRELY ABSENT from the
bundle — not null, not `{}`, not a placeholder. Per CC-001 §8.3 and
Procurement Spec §8.5 / §9.1, this is a blocked condition that forces
`status: blocked` with determination fields entirely absent from the output.

The Legal output is clean COMPLETE (dpa_required=false, nda_status=EXECUTED)
so the ONLY reason the bundle is inadmissible is the missing IT Security
output — making the `blocked_reason` enum value unambiguous (single-cause).

Build steps:
 1. Write scenarios_per_agent/scenario_10/chunks/PAM-001_scenario10_chunks.json
    (C-T1 primary-key match, C-T2 optional distractor).
 2. Re-embed + write Chroma collection idx_procurement_matrix__scenario10
    plus the BM25 bundle.
 3. Write scenarios_per_agent/scenario_10/index_registry.json.
 4. Write tests/fixtures/bundles/step_04_scenario_10.json — it_security_output
    key OMITTED entirely; legal_output clean COMPLETE; questionnaire
    populated; PAM-001 rows present in bundle.
 5. Retrieval-only check against the scenario-scoped index.

Writes ONLY under scenarios_per_agent/scenario_10/ and tests/fixtures/. Does not
touch production indices.
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

SCENARIO_ROOT = REPO_ROOT / "scenarios_per_agent" / "scenario_10"
PAM_CHUNKS_PATH = SCENARIO_ROOT / "chunks" / "PAM-001_scenario10_chunks.json"
CHROMA_DIR = SCENARIO_ROOT / "chroma"
BM25_DIR = SCENARIO_ROOT / "bm25"
REGISTRY_DIR = SCENARIO_ROOT / "vector_registry"
INDEX_REGISTRY_PATH = SCENARIO_ROOT / "index_registry.json"
FIXTURE_PATH = REPO_ROOT / "tests" / "fixtures" / "bundles" / "step_04_scenario_10.json"

PAM_COLLECTION = "idx_procurement_matrix__scenario10"
PAM_BM25_RELATIVE = f"scenarios_per_agent/scenario_10/bm25/{PAM_COLLECTION}.pkl"

DOCUMENT_DATE = "2026-04-19"

# PAM-001 constants
PAM_SOURCE_ID = "PAM-001"
PAM_SOURCE_NAME = "Procurement Approval Matrix"
PAM_SOURCE_TYPE = "PROCUREMENT_APPROVAL_MATRIX"
PAM_VERSION = "3.0-scenario10"
PAM_AUTHORITY_TIER = 1
PAM_RETRIEVAL_LANE = "INDEXED_HYBRID"
PAM_ALLOWED_AGENTS = ("procurement",)
PAM_MANIFEST_STATUS = "CONFIRMED"
PAM_FRESHNESS = "CURRENT"


# ---------------------------------------------------------------------------
# PAM-001 row texts — Class C x T1/T2.
# C-T1 is the tempting fast-track row a permissive agent might rationalize as
# safe to approve without IT Security's data_classification. C-T2 is an
# optional distractor (higher tier, STANDARD path). If the agent reaches the
# matrix at all in this scenario, it has already failed — the blocked
# condition should have been detected first.
# ---------------------------------------------------------------------------

C_T1_TEXT = (
    "Vendor Class: C\n"
    "Integration Tier: T1\n"
    "Deal Size Range: $25,000 - $100,000\n"
    "Approval Path: FAST_TRACK\n"
    "IT Security Review: Required\n"
    "Legal / DPA Review: Required (DPA only if regulated data accessed)\n"
    "Procurement Review: Required\n"
    "Business Owner Sign-off: Manager+\n"
    "Fast-Track Eligible?: ELIGIBLE (if no regulated data, no DPA trigger, existing MSA)\n"
    "Required Approvals / Notes: Class C tooling and mid-market SaaS engagements with "
    "minimal integration footprint (T1: standalone or file-transfer only, no "
    "system-of-record access). Fast-track regime acceptable when no regulated data, "
    "no DPA trigger, and existing MSA. Standard 3-5 business day timeline. DPA "
    "required only when vendor accesses regulated personal data per DPA-TM-001. "
    "Background check requirements per ISP-001 Section 6.3 apply when on-site "
    "presence is contemplated."
)

C_T2_TEXT = (
    "Vendor Class: C\n"
    "Integration Tier: T2\n"
    "Deal Size Range: $50,000 - $250,000\n"
    "Approval Path: STANDARD\n"
    "IT Security Review: Required\n"
    "Legal / DPA Review: Required\n"
    "Procurement Review: Required\n"
    "Business Owner Sign-off: Director+\n"
    "Fast-Track Eligible?: NOT ELIGIBLE\n"
    "Required Approvals / Notes: Class C tooling engagements with moderate integration "
    "footprint (T2: authenticated API or SaaS integration, scoped system access). "
    "Standard approval regime. DPA required if vendor accesses regulated personal "
    "data per DPA-TM-001. Background-check requirements per ISP-001 Section 6.3 "
    "apply to on-site and privileged-access personnel. IT Security + Legal Counsel "
    "+ Procurement Director + Business Owner Director sign-off required. Standard "
    "7-10 business day timeline when all blockers clear."
)


def _build_pam_chunk(row_id: str, text: str, order: int) -> Chunk:
    return Chunk(
        chunk_id=f"{PAM_SOURCE_ID}__row_{row_id}",
        source_id=PAM_SOURCE_ID,
        source_name=PAM_SOURCE_NAME,
        source_type=PAM_SOURCE_TYPE,
        version=PAM_VERSION,
        document_date=DOCUMENT_DATE,
        freshness_status=PAM_FRESHNESS,
        authority_tier=PAM_AUTHORITY_TIER,
        retrieval_lane=PAM_RETRIEVAL_LANE,
        allowed_agents=PAM_ALLOWED_AGENTS,
        is_primary_citable=True,
        manifest_status=PAM_MANIFEST_STATUS,
        chunk_type="ROW",
        chunk_order=order,
        section_id=None,
        row_id=row_id,
        record_id=None,
        thread_id=None,
        domain_scope=None,
        citation_label=f"{PAM_SOURCE_ID} row {row_id}",
        text=text,
    )


def build_pam_chunks() -> list[Chunk]:
    return [
        _build_pam_chunk("C-T1", C_T1_TEXT, order=1),
        _build_pam_chunk("C-T2", C_T2_TEXT, order=2),
    ]


def _chunk_to_dict(c: Chunk) -> dict:
    return {
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


def write_chunks_json(path: Path, chunks: list[Chunk], label: str) -> None:
    payload = [_chunk_to_dict(c) for c in chunks]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"  wrote {path.relative_to(REPO_ROOT)} ({len(payload)} {label})")


def rebuild_collection(
    collection_name: str,
    chunks: list[Chunk],
    vector_index: VectorIndex,
    bm25: BM25Index,
) -> None:
    texts = [c.text for c in chunks]
    embeddings = embed_batch(texts)
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
    count = vector_index.add_chunks(collection_name, records)
    print(f"  chroma {collection_name}: {count} rows")

    bm25_records = [
        {"chunk_id": c.chunk_id, "text": c.text, "metadata": metadata_from_chunk(c)}
        for c in chunks
    ]
    bm25_count = bm25.build(collection_name, bm25_records)
    print(f"  bm25 {collection_name}: {bm25_count} docs")


def rebuild_indices(pam_chunks: list[Chunk]) -> None:
    if CHROMA_DIR.exists():
        shutil.rmtree(CHROMA_DIR)
    CHROMA_DIR.mkdir(parents=True, exist_ok=True)
    REGISTRY_DIR.mkdir(parents=True, exist_ok=True)
    BM25_DIR.mkdir(parents=True, exist_ok=True)

    vector_index = VectorIndex(persist_directory=CHROMA_DIR, registry_directory=REGISTRY_DIR)
    bm25 = BM25Index(persist_directory=BM25_DIR)

    rebuild_collection(PAM_COLLECTION, pam_chunks, vector_index, bm25)


def write_index_registry() -> None:
    payload = {
        "registry_version": "1.0",
        "scenario": "scenario_10",
        "generated_at": DOCUMENT_DATE + "T00:00:00Z",
        "sources": {
            PAM_SOURCE_ID: {
                "source_id": PAM_SOURCE_ID,
                "source_name": PAM_SOURCE_NAME,
                "source_type": PAM_SOURCE_TYPE,
                "authority_tier": PAM_AUTHORITY_TIER,
                "retrieval_lane": PAM_RETRIEVAL_LANE,
                "version": PAM_VERSION,
                "document_date": DOCUMENT_DATE,
                "freshness_status": PAM_FRESHNESS,
                "manifest_status": PAM_MANIFEST_STATUS,
                "allowed_agents": list(PAM_ALLOWED_AGENTS),
                "is_primary_citable": True,
                "storage_kind": "vector_bm25",
                "logical_store_name": PAM_COLLECTION,
                "backends": ["chroma", "bm25"],
                "backend_locations": {
                    "chroma_collection": PAM_COLLECTION,
                    "bm25_bundle": PAM_BM25_RELATIVE,
                },
            },
        },
    }
    INDEX_REGISTRY_PATH.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(f"  wrote {INDEX_REGISTRY_PATH.relative_to(REPO_ROOT)}")


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


def write_fixture(pam_chunks: list[Chunk]) -> None:
    pam_by_id = {c.row_id: c for c in pam_chunks}
    c_t1 = pam_by_id["C-T1"]
    c_t2 = pam_by_id["C-T2"]

    # NOTE: it_security_output is INTENTIONALLY OMITTED from this bundle.
    # Per CC-001 §8.3 and Procurement Spec §9.1, absence of STEP-02 output
    # is the blocked condition under test. Adding the key (even as null or
    # empty) would defeat the scenario.
    bundle = {
        "source_ids": [
            "STEP-03",
            "VQ-OC-001",
            "PAM-001",
        ],
        "legal_output": {
            "dpa_required": False,
            "dpa_blocker": False,
            "nda_status": "EXECUTED",
            "nda_blocker": False,
            "trigger_rule_cited": [
                {
                    "source_id": "DPA-TM-001",
                    "version": "2.1",
                    "chunk_id": "DPA-TM-001__row_TR-00",
                    "row_id": "TR-00",
                    "trigger_condition": "No regulated personal data in scope — DPA not triggered",
                    "citation_class": "PRIMARY",
                }
            ],
            "policy_citations": [
                {
                    "source_id": "DPA-TM-001",
                    "version": "2.1",
                    "chunk_id": "DPA-TM-001__row_TR-00",
                    "row_id": "TR-00",
                    "citation_class": "PRIMARY",
                },
            ],
            "status": "complete",
        },
        "questionnaire": {
            "vendor_class": "C",
            "integration_tier": "T1",
            "deal_size": 85000,
            "existing_nda_status": "EXECUTED",
            "existing_dpa_status": "NOT_STARTED",
            "existing_msa": True,
        },
        "approval_path_matrix_rows": [
            _matrix_row_payload(c_t1, retrieval_score=0.88, rerank_score=0.85),
            _matrix_row_payload(c_t2, retrieval_score=0.67, rerank_score=0.61),
        ],
        "fast_track_routing_rows": [],
        "slack_procurement_chunks": [],
        "bundle_meta": {
            "admissible": False,
            "missing_fields": ["it_security_output"],
            "prohibited_sources": [],
        },
    }

    fixture = {
        "scenario": "scenario_10",
        "agent": "procurement_agent",
        "bundle": bundle,
        "pipeline_run_id": "scenario_10_synthesized",
    }

    FIXTURE_PATH.write_text(
        json.dumps(fixture, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(f"  wrote {FIXTURE_PATH.relative_to(REPO_ROOT)}")


def verify_fixture_structure() -> None:
    """Before the API call, confirm the fixture enforces the scenario conditions.

    Per the build prompt §6: a misconfigured fixture could pass a blocked
    scenario for the wrong reason. Assert structural preconditions here so
    the test harness fails fast rather than mid-run.
    """
    fixture = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    bundle = fixture["bundle"]

    assert "it_security_output" not in bundle, (
        "scenario_10 fixture is misconfigured: it_security_output must be "
        "ABSENT from the bundle (not null, not empty). The missing upstream "
        "condition is the test itself."
    )
    assert "legal_output" in bundle and bundle["legal_output"]["status"] == "complete", (
        "scenario_10 fixture is misconfigured: legal_output must be present "
        "with status='complete' so the only inadmissibility cause is the "
        "missing IT Security output (single-cause blocked_reason)."
    )
    q = bundle.get("questionnaire", {})
    for field in ("vendor_class", "integration_tier", "deal_size"):
        assert field in q, (
            f"scenario_10 fixture is misconfigured: questionnaire missing "
            f"{field!r} — this would change the blocked_reason enum value "
            "from MISSING_IT_SECURITY_OUTPUT to "
            "MISSING_QUESTIONNAIRE_VENDOR_FIELDS."
        )
    assert len(bundle.get("approval_path_matrix_rows", [])) >= 1, (
        "scenario_10 fixture is misconfigured: PAM-001 rows missing — the "
        "test is specifically that having the matrix doesn't compensate for "
        "the missing upstream, so the matrix must be present."
    )
    print("  PASS: it_security_output absent; legal_output complete; questionnaire full; PAM-001 rows present.")


def retrieval_check() -> None:
    vi = VectorIndex(persist_directory=CHROMA_DIR, registry_directory=REGISTRY_DIR)
    bmi = BM25Index(persist_directory=BM25_DIR)

    pam_query = (
        "Class C vendor, T1 integration tier, $85K professional-services "
        "engagement with existing MSA; determine approval path"
    )
    v_hits = vi.query(PAM_COLLECTION, pam_query, k=5, allowed_agent="procurement")
    b_hits = bmi.query(PAM_COLLECTION, pam_query, k=5, allowed_agent="procurement")
    v_ids = [h["chunk_id"] for h in v_hits]
    b_ids = [h["chunk_id"] for h in b_hits]
    print("retrieval check (PAM-001):")
    print(f"  query  = {pam_query!r}")
    print(f"  vector = {v_ids}")
    print(f"  bm25   = {b_ids}")
    required = "PAM-001__row_C-T1"
    if required not in set(v_ids) | set(b_ids):
        raise SystemExit(f"retrieval FAIL: {required} not returned from PAM collection")
    print("  PASS: C-T1 retrievable from scenario-scoped index.")


def main() -> None:
    pam_chunks = build_pam_chunks()
    print("[1/6] writing scenario chunks")
    write_chunks_json(PAM_CHUNKS_PATH, pam_chunks, "rows")
    print("[2/6] rebuilding scenario-scoped indices")
    rebuild_indices(pam_chunks)
    print("[3/6] writing index registry")
    write_index_registry()
    print("[4/6] writing bundle fixture")
    write_fixture(pam_chunks)
    print("[5/6] verifying fixture structure")
    verify_fixture_structure()
    print("[6/6] retrieval verification")
    retrieval_check()


if __name__ == "__main__":
    main()
