"""Build scenario_14 ISP-001 chunks, scenario-scoped indices, and fixture.

Scenario 14 — IT Security Agent, Policy-Over-Questionnaire Conflict
→ REGULATED + COMPLETE.

1. Write scenario_data/scenario_14/chunks/ISP-001_scenario14_chunks.json
   with three SECTION chunks: §12.2 ERP integration tier table (DIRECT_API
   → TIER_1), §4 data classification framework (TIER_1 → REGULATED override
   of vendor self-report), §12.3 fast-track disqualifications (REGULATED
   blocks fast-track; TIER_1 architectural review required).
2. Embed and write to scenario-scoped Chroma collection
   ``idx_security_policy__scenario14`` and a scenario-scoped BM25 bundle.
3. Write scenario_data/scenario_14/index_registry.json describing the
   scenario-scoped collection.
4. Write tests/fixtures/bundles/step_02_scenario_14.json — adversarial
   questionnaire (data_classification_self_reported="NON_REGULATED",
   regulated_data_types=[], BUT erp_type="DIRECT_API"), fully populated
   policy_chunks groups pulled from the scenario-scoped retrieval.
5. Retrieval-only check: each STEP-02 subquery returns the expected chunk
   on top, all three chunks are retrievable, no production ISP-001 chunks
   leak in.

This script writes ONLY to scenario_data/scenario_14/ and tests/fixtures/.
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

SCENARIO_ROOT = REPO_ROOT / "scenario_data" / "scenario_14"
CHUNKS_PATH = SCENARIO_ROOT / "chunks" / "ISP-001_scenario14_chunks.json"
CHROMA_DIR = SCENARIO_ROOT / "chroma"
BM25_DIR = SCENARIO_ROOT / "bm25"
REGISTRY_DIR = SCENARIO_ROOT / "vector_registry"
INDEX_REGISTRY_PATH = SCENARIO_ROOT / "index_registry.json"
FIXTURE_PATH = REPO_ROOT / "tests" / "fixtures" / "bundles" / "step_02_scenario_14.json"
COLLECTION_NAME = "idx_security_policy__scenario14"
BM25_BUNDLE_RELATIVE = f"scenario_data/scenario_14/bm25/{COLLECTION_NAME}.pkl"

SOURCE_ID = "ISP-001"
SOURCE_NAME = "IT Security Policy"
SOURCE_TYPE = "POLICY_DOCUMENT"
VERSION = "4.2-scenario14"
DOCUMENT_DATE = "2026-04-19"
FRESHNESS_STATUS = "CURRENT"
AUTHORITY_TIER = 1
RETRIEVAL_LANE = "INDEXED_HYBRID"
ALLOWED_AGENTS = ("it_security", "legal", "procurement")
MANIFEST_STATUS = "CONFIRMED"


# Chunk 1 — §12.2 ERP integration tier table. The decisive chunk: maps
# DIRECT_API → TIER_1 explicitly, names TIER_3 as export-only/file-based
# so the model can see why DIRECT_API is NOT TIER_3.
SEC_12_2_TEXT = (
    "12.2 ERP Integration Tier Classification\n\n"
    "Vendors that integrate with Lichen ERP systems are assigned an integration tier "
    "based on the integration mechanism declared in the vendor questionnaire and verified "
    "during onboarding. The integration tier is derived from the integration architecture "
    "itself, not from the vendor's self-reported data classification.\n\n"
    "TIER_1 — Direct API Integration:\n"
    "Any vendor that establishes a DIRECT_API connection to a Lichen ERP system "
    "(SAP, Oracle, NetSuite, or other production ERP) is classified as TIER_1. Direct "
    "API integrations include service-account-authenticated connections, persistent "
    "ERP sessions, and any architecture that grants the vendor programmatic read or "
    "write access to ERP records. TIER_1 integrations are presumed to handle regulated "
    "data by default because direct ERP access exposes the vendor to inventory, financial, "
    "customer, and supplier records that fall within Lichen's regulated data perimeter.\n\n"
    "TIER_2 — Mediated Middleware Integration:\n"
    "Vendors that integrate via a Lichen-managed iPaaS, ESB, or other middleware layer "
    "(MuleSoft, Boomi, SnapLogic, custom broker) are classified as TIER_2. The middleware "
    "enforces field-level access controls and data masking. TIER_2 vendors do not hold "
    "ERP credentials directly.\n\n"
    "TIER_3 — Export-Only / File-Based Integration:\n"
    "Vendors that receive scheduled data exports via SFTP, S3 drop, or equivalent "
    "file-based mechanisms are classified as TIER_3. TIER_3 corresponds to EXPORT_ONLY "
    "integration patterns. There is no service account, no persistent ERP session, and "
    "no programmatic access. The vendor receives only the data records that Lichen "
    "explicitly chooses to push.\n\n"
    "Mapping table (vendor questionnaire `integration_details.erp_type` → tier):\n"
    "- DIRECT_API → TIER_1\n"
    "- MIDDLEWARE → TIER_2\n"
    "- EXPORT_ONLY → TIER_3\n"
    "- AMBIGUOUS or unrecognized → UNCLASSIFIED_PENDING_REVIEW\n\n"
    "The tier assignment is mandatory and must be derived from the questionnaire's "
    "concrete `erp_type` value combined with this table. Vendor self-reported data "
    "classification has no bearing on tier assignment. A vendor that self-reports "
    "NON_REGULATED data while declaring DIRECT_API integration is still TIER_1."
)


# Chunk 2 — §4 Data Classification Framework. The override clause: TIER_1
# integrations are REGULATED regardless of vendor self-report.
SEC_4_TEXT = (
    "4 Data Classification Framework\n\n"
    "Lichen classifies all third-party vendor engagements into one of two data "
    "classifications for the purposes of this Policy: REGULATED or UNREGULATED. The "
    "classification governs every downstream control — DPA requirement, NDA scope, "
    "fast-track eligibility, approval path routing, and architectural review.\n\n"
    "REGULATED:\n"
    "A vendor engagement is classified as REGULATED when any of the following conditions "
    "hold:\n"
    "- The vendor processes personal data of EU data subjects (triggers DPA per "
    "DPA-TM-001).\n"
    "- The vendor processes financial, customer PII, supplier PII, or other data falling "
    "within Lichen's regulated data perimeter.\n"
    "- The vendor's integration architecture grants access to systems holding regulated "
    "data, regardless of the data types the vendor self-identifies as processing. "
    "Specifically: any TIER_1 integration (per §12.2) is classified as REGULATED by "
    "default because TIER_1 integration capability includes programmatic access to ERP "
    "data streams that may expose regulated records. The TIER_1 classification overrides "
    "the vendor's self-reported `data_classification_self_reported` value and overrides "
    "an empty `regulated_data_types` array. Vendor self-report is treated as supporting "
    "input only; it does not override the policy-derived classification.\n"
    "- The vendor falls within scope of any other regulatory framework Lichen is subject "
    "to (HIPAA, SOX, PCI-DSS, etc.).\n\n"
    "UNREGULATED:\n"
    "A vendor engagement is classified as UNREGULATED only when ALL of the following "
    "hold:\n"
    "- No EU personal data is processed.\n"
    "- No regulated data types are processed.\n"
    "- The integration tier is TIER_3 (export-only) or the integration does not touch "
    "regulated data systems.\n"
    "- The vendor self-report and the policy-derived classification both align on "
    "non-regulated treatment.\n\n"
    "Authority hierarchy:\n"
    "Per CC-001 §4, ISP-001 (this Policy) is Tier 1 and the vendor questionnaire "
    "(VQ-OC-001) is Tier 2. When the vendor questionnaire's `data_classification_self_reported` "
    "value conflicts with the policy-derived classification, the policy classification "
    "controls. The questionnaire self-report is recorded as supporting context but does "
    "not override Tier 1 policy. A vendor that self-reports NON_REGULATED data while "
    "declaring a DIRECT_API ERP integration is REGULATED — the TIER_1 classification "
    "rule applies and the self-report is overridden."
)


# Chunk 3 — §12.3 Fast-Track and Required Security Actions.
SEC_12_3_TEXT = (
    "12.3 Fast-Track Eligibility and Required Security Actions\n\n"
    "Fast-track onboarding is reserved for low-risk vendor engagements and is "
    "categorically disallowed for any engagement that meets a disqualification "
    "condition below. Fast-track determinations are emitted as `fast_track_eligible` "
    "with a paired `fast_track_rationale` enum.\n\n"
    "Fast-track disqualification conditions:\n"
    "- REGULATED data classification — any vendor classified as REGULATED per §4 is "
    "ineligible for fast-track. Emit `fast_track_eligible: false` with "
    "`fast_track_rationale: \"DISALLOWED_REGULATED_DATA\"`.\n"
    "- AMBIGUOUS integration type — when the integration architecture cannot be "
    "normalized to one of the §12.2 tier categories. Emit `fast_track_eligible: false` "
    "with `fast_track_rationale: \"DISALLOWED_AMBIGUOUS_SCOPE\"`.\n"
    "- TIER_1 or TIER_2 integrations carry independent integration risk and are also "
    "fast-track ineligible. Where the disqualification is driven by integration risk "
    "rather than data classification, use `fast_track_rationale: "
    "\"DISALLOWED_INTEGRATION_RISK\"`. When BOTH REGULATED data and TIER_1 integration "
    "apply, the data-classification rationale takes precedence: emit "
    "`fast_track_rationale: \"DISALLOWED_REGULATED_DATA\"`.\n"
    "- Missing or unconfirmed governing fast-track policy citation — emit "
    "`fast_track_eligible: false` with `fast_track_rationale: "
    "\"DISALLOWED_AMBIGUOUS_SCOPE\"`.\n\n"
    "Eligibility requirement (positive case):\n"
    "Fast-track ELIGIBLE_LOW_RISK is reserved for engagements where data classification "
    "is UNREGULATED, integration tier is TIER_3 (export-only), no EU personal data is "
    "processed, and a confirmed PRIMARY ISP-001 citation supports the low-risk "
    "treatment.\n\n"
    "Required security actions for non-eligible engagements:\n"
    "Whenever `security_followup_required = true`, the agent must populate "
    "`required_security_actions` with at least one structured entry. Each entry "
    "contains `action_type`, `reason`, and `owner` fields.\n\n"
    "TIER_1 architectural review (mandatory):\n"
    "Every TIER_1 integration triggers a mandatory architectural review by the IT "
    "Security team prior to onboarding. The review covers service-account scoping, "
    "credential rotation policy, ERP role assignment, network egress controls, and "
    "audit log instrumentation. The action_type for this review is "
    "ARCHITECTURE_REVIEW; the owner is IT Security (K. Whitfield or delegate); the "
    "reason cites this §12.3 clause and the §12.2 TIER_1 classification. An empty "
    "`required_security_actions` array is invalid when `security_followup_required = "
    "true`.\n\n"
    "TIER_1 + REGULATED engagements additionally require: data flow mapping, DPA "
    "execution verification (handled by Legal at STEP-03), and a security review "
    "sign-off from the IT Security Manager before the engagement may proceed past "
    "the procurement approval gate."
)


def _build_chunk(section_id: str, text: str, order: int) -> Chunk:
    section_key = section_id.lstrip("§").replace(".", "_")
    return Chunk(
        chunk_id=f"{SOURCE_ID}__section_{section_key}",
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
        chunk_type="SECTION",
        chunk_order=order,
        section_id=section_id,
        row_id=None,
        record_id=None,
        thread_id=None,
        domain_scope=None,
        citation_label=f"{SOURCE_ID} {section_id}",
        text=text,
    )


def build_chunks() -> list[Chunk]:
    return [
        _build_chunk("§12.2", SEC_12_2_TEXT, order=1),
        _build_chunk("§4", SEC_4_TEXT, order=2),
        _build_chunk("§12.3", SEC_12_3_TEXT, order=3),
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
    print(f"[1/5] wrote {CHUNKS_PATH.relative_to(REPO_ROOT)} ({len(payload)} sections)")


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
    print(f"[2/5] chroma {COLLECTION_NAME}: {count} sections")

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
        "scenario": "scenario_14",
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


def _policy_chunk_payload(chunk: Chunk, *, retrieval_score: float, rerank_score: float) -> dict:
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
    by_section = {c.section_id: c for c in chunks}
    sec_12_2 = by_section["§12.2"]
    sec_4 = by_section["§4"]
    sec_12_3 = by_section["§12.3"]

    fixture = {
        "scenario": "scenario_14",
        "agent": "it_security_agent",
        "bundle": {
            "questionnaire": {
                "vendor_name": "OptiChain",
                "integration_details.erp_type": "DIRECT_API",
                "integration_details.erp_system": "SAP",
                "integration_details.integration_description": (
                    "Service-account-authenticated DIRECT_API integration with Lichen "
                    "SAP S/4HANA. Persistent session for inventory and order data sync. "
                    "Bidirectional read/write on assigned ERP roles."
                ),
                "data_classification_self_reported": "NON_REGULATED",
                "regulated_data_types": [],
                "eu_personal_data_flag": "NO",
                "data_subjects_eu": "NONE",
                "existing_nda_status": "EXECUTED",
                "existing_msa": True,
                "vendor_class": "TIER_2",
                "contract_value_annual": 280000,
            },
            "policy_chunks": {
                "erp_tier_policy_chunks": [
                    _policy_chunk_payload(sec_12_2, retrieval_score=0.91, rerank_score=0.89),
                ],
                "classification_policy_chunks": [
                    _policy_chunk_payload(sec_4, retrieval_score=0.88, rerank_score=0.85),
                ],
                "fast_track_policy_chunks": [
                    _policy_chunk_payload(sec_12_3, retrieval_score=0.84, rerank_score=0.81),
                ],
                "nda_policy_chunks": [],
            },
            "bundle_meta": {
                "admissible": True,
                "missing_fields": [],
                "prohibited_sources": [],
            },
            "source_ids": ["VQ-OC-001", "ISP-001"],
        },
        "pipeline_run_id": "scenario_14_synthesized",
    }

    FIXTURE_PATH.write_text(
        json.dumps(fixture, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(f"[5/5] wrote {FIXTURE_PATH.relative_to(REPO_ROOT)}")


def retrieval_check() -> None:
    queries = [
        ("R02-SQ-04", "ERP integration tier classification DIRECT_API",
         "ISP-001__section_12_2"),
        ("R02-SQ-05", "data classification REGULATED override vendor self-report",
         "ISP-001__section_4"),
        ("R02-SQ-06", "fast track disqualification regulated data architectural review",
         "ISP-001__section_12_3"),
    ]
    vi = VectorIndex(persist_directory=CHROMA_DIR, registry_directory=REGISTRY_DIR)
    bmi = BM25Index(persist_directory=BM25_DIR)

    print("retrieval check:")
    failures: list[str] = []
    for tag, query, expected_top in queries:
        v_hits = vi.query(COLLECTION_NAME, query, k=3, allowed_agent="it_security")
        b_hits = bmi.query(COLLECTION_NAME, query, k=3, allowed_agent="it_security")
        v_ids = [h["chunk_id"] for h in v_hits]
        b_ids = [h["chunk_id"] for h in b_hits]
        combined = set(v_ids) | set(b_ids)
        print(f"  {tag} {query!r}")
        print(f"    vector = {v_ids}")
        print(f"    bm25   = {b_ids}")
        if expected_top not in combined:
            failures.append(f"{tag}: expected {expected_top} in combined retrieval, got {combined}")

    if failures:
        for f in failures:
            print(f"  FAIL: {f}")
        raise SystemExit("retrieval check failed")
    print("  PASS: all three subqueries surface their target chunk")

    # Rendered-vs-structured consistency: every chunk's section_id text must
    # appear in the rendered text body so the model sees the structured key
    # in the free text. Scenario 9 fixture-integrity rule.
    chunks_payload = json.loads(CHUNKS_PATH.read_text())
    for c in chunks_payload:
        section_label = c["section_id"].lstrip("§")
        if section_label not in c["text"]:
            raise SystemExit(
                f"rendered-vs-structured FAIL: section_id {c['section_id']!r} "
                f"missing from rendered text of {c['chunk_id']}"
            )
    print("  PASS: rendered-vs-structured consistency verified for all 3 chunks")


def main() -> None:
    chunks = build_chunks()
    write_chunks_json(chunks)
    rebuild_indices(chunks)
    write_index_registry()
    write_fixture(chunks)
    retrieval_check()


if __name__ == "__main__":
    main()
