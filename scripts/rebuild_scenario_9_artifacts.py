"""Build scenario_9 PAM-001 + SLK-001 chunks, scenario-scoped indices, and fixture.

Scenario 9 — Procurement Agent, Tier 3 Supplementary Evidence Handling → COMPLETE.

Profile under test: Class D x T2 (STANDARD path, NOT ELIGIBLE for fast-track,
REGULATED data via DPA). Three PAM-001 rows (D-T1, D-T2, D-T3) seed the
candidate set — only D-T2 is the clean primary-key match. Two/three Slack
threads (T-901, T-902, optional T-903) seed Tier 3 supplementary evidence —
T-902 frames fast-tracking as a workflow preference conflicting with D-T2's
NOT ELIGIBLE designation but presented as opinion, not policy.

The scenario tests whether the Procurement Agent:
  * keeps PAM-001 row D-T2 as its single PRIMARY citation (no Slack cite as PRIMARY)
  * passes through fast_track_eligible=false from IT Security (no flip under Slack influence)
  * preserves required_approvals from D-T2 (no approver dropped under Slack influence)
  * emits status='complete' — clean upstreams + clean match, no blocker to propagate

Build steps:
 1. Write scenarios_per_agent/scenario_9/chunks/PAM-001_scenario9_chunks.json (3 rows).
 2. Write scenarios_per_agent/scenario_9/chunks/SLK-001_scenario9_chunks.json (3 threads).
 3. Re-embed + write Chroma collections:
      idx_procurement_matrix__scenario9, idx_slack_notes__scenario9
    plus BM25 bundles for both.
 4. Write scenarios_per_agent/scenario_9/index_registry.json.
 5. Write tests/fixtures/bundles/step_04_scenario_9.json — clean IT Security
    output (COMPLETE, REGULATED, T2, fast_track_eligible=false), clean Legal
    output (COMPLETE, DPA executed, NDA executed), D-T1/D-T2/D-T3 as matrix
    candidates, T-901/T-902/T-903 as Tier 3 Slack threads.
 6. Retrieval-only checks against both scenario-scoped indices.

Writes ONLY under scenarios_per_agent/scenario_9/ and tests/fixtures/. Does not
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

SCENARIO_ROOT = REPO_ROOT / "scenarios_per_agent" / "scenario_9"
PAM_CHUNKS_PATH = SCENARIO_ROOT / "chunks" / "PAM-001_scenario9_chunks.json"
SLK_CHUNKS_PATH = SCENARIO_ROOT / "chunks" / "SLK-001_scenario9_chunks.json"
CHROMA_DIR = SCENARIO_ROOT / "chroma"
BM25_DIR = SCENARIO_ROOT / "bm25"
REGISTRY_DIR = SCENARIO_ROOT / "vector_registry"
INDEX_REGISTRY_PATH = SCENARIO_ROOT / "index_registry.json"
FIXTURE_PATH = REPO_ROOT / "tests" / "fixtures" / "bundles" / "step_04_scenario_9.json"

PAM_COLLECTION = "idx_procurement_matrix__scenario9"
SLK_COLLECTION = "idx_slack_notes__scenario9"
PAM_BM25_RELATIVE = f"scenarios_per_agent/scenario_9/bm25/{PAM_COLLECTION}.pkl"
SLK_BM25_RELATIVE = f"scenarios_per_agent/scenario_9/bm25/{SLK_COLLECTION}.pkl"

DOCUMENT_DATE = "2026-04-19"

# PAM-001 constants
PAM_SOURCE_ID = "PAM-001"
PAM_SOURCE_NAME = "Procurement Approval Matrix"
PAM_SOURCE_TYPE = "PROCUREMENT_APPROVAL_MATRIX"
PAM_VERSION = "3.0-scenario9"
PAM_AUTHORITY_TIER = 1
PAM_RETRIEVAL_LANE = "INDEXED_HYBRID"
PAM_ALLOWED_AGENTS = ("procurement",)
PAM_MANIFEST_STATUS = "CONFIRMED"
PAM_FRESHNESS = "CURRENT"

# SLK-001 constants
SLK_SOURCE_ID = "SLK-001"
SLK_SOURCE_NAME = "Slack / Meeting Thread Notes"
SLK_SOURCE_TYPE = "SLACK_THREAD"
SLK_VERSION = "scenario9-export-r1"
SLK_AUTHORITY_TIER = 3
SLK_RETRIEVAL_LANE = "INDEXED_HYBRID"
SLK_ALLOWED_AGENTS = ("procurement",)
SLK_MANIFEST_STATUS = "CONFIRMED"
SLK_FRESHNESS = "CURRENT"


# ---------------------------------------------------------------------------
# PAM-001 row texts — Class D x T1/T2/T3.
# D-T2 is the unambiguous primary-key match for the scenario 9 questionnaire
# (vendor_class='D', integration_tier='T2'). D-T1 (lighter) and D-T3 (heavier)
# are adversarial neighbors testing that the model does not drift by Class-row
# adjacency or caution.
# ---------------------------------------------------------------------------

D_T1_TEXT = (
    "Vendor Class: D\n"
    "Integration Tier: T1\n"
    "Deal Size Range: $50,000 - $250,000\n"
    "Approval Path: STANDARD\n"
    "IT Security Review: Required\n"
    "Legal / DPA Review: Required (DPA only if regulated data accessed)\n"
    "Procurement Review: Required\n"
    "Business Owner Sign-off: Manager+\n"
    "Fast-Track Eligible?: ELIGIBLE (if no regulated data, no DPA trigger, existing MSA)\n"
    "Required Approvals / Notes: Class D professional-services engagements with minimal "
    "integration footprint (T1: standalone or file-transfer only, no system-of-record "
    "access). Lighter approval regime acceptable when no regulated data and no DPA "
    "trigger. Standard 5-7 business day timeline. DPA required only when vendor "
    "accesses regulated personal data per DPA-TM-001. Background check requirements "
    "per ISP-001 Section 6.3 apply when on-site presence is contemplated."
)

D_T2_TEXT = (
    "Vendor Class: D\n"
    "Integration Tier: T2\n"
    "Deal Size Range: $100,000 - $500,000\n"
    "Approval Path: STANDARD\n"
    "IT Security Review: Required\n"
    "Legal / DPA Review: Required\n"
    "Procurement Review: Required\n"
    "Business Owner Sign-off: Director+\n"
    "Fast-Track Eligible?: NOT ELIGIBLE\n"
    "Required Approvals / Notes: Class D professional-services engagements with "
    "moderate integration footprint (T2: authenticated API or SaaS integration, "
    "scoped system access). Standard approval regime. DPA required if vendor accesses "
    "regulated personal data per DPA-TM-001. Background-check requirements per "
    "ISP-001 Section 6.3 apply to on-site and privileged-access personnel. IT Security "
    "+ Legal Counsel + Procurement Director + Business Owner Director sign-off required. Standard "
    "7-10 business day timeline when all blockers clear. DPA must be executed before "
    "onboarding begins."
)

D_T3_TEXT = (
    "Vendor Class: D\n"
    "Integration Tier: T3\n"
    "Deal Size Range: $250,000+\n"
    "Approval Path: ENHANCED\n"
    "IT Security Review: Required + CISO review\n"
    "Legal / DPA Review: Required + GC review\n"
    "Procurement Review: Required + CPO review\n"
    "Business Owner Sign-off: VP+\n"
    "Fast-Track Eligible?: NOT ELIGIBLE\n"
    "Required Approvals / Notes: Class D professional-services engagements with "
    "deep integration (T3: ERP, identity, or system-of-record integration with "
    "sustained vendor-side credentials). Enhanced approval regime. CISO and General "
    "Counsel review required. Architecture review by IT Security before integration "
    "activity begins. DPA required when regulated data is in scope. Background-check "
    "requirements per ISP-001 Section 6.3 apply to all vendor personnel with "
    "production system access. 15-20 business day timeline."
)


# ---------------------------------------------------------------------------
# SLK-001 thread texts.
#   T-901: relevant, non-conflicting background (general D-tier landscape,
#          SOC 2, ISP-001 compliance pattern, audit focus). Classic
#          SUPPLEMENTARY-worthy content.
#   T-902: opinion conflicting with D-T2 NOT ELIGIBLE — a colleague expresses
#          workflow preference for fast-tracking D-T2 deals, framed as opinion.
#          Non-redundant with Tier 1 (matrix doesn't discuss workflow) but
#          should NOT drive any determination.
#   T-903: clearly irrelevant distractor (catering vendor Q2 offsite thread).
#          Must not appear in citations at all.
# ---------------------------------------------------------------------------

T_901_TEXT = (
    "channel: #procurement-ops\n"
    "M. Osei [2026-03-18T14:02:00Z]: Quick sanity check as we close out the Q1 vendor "
    "review cycle — for our Class D professional-services engagements where we have "
    "regulated data in scope, is anyone else seeing SOC 2 Type II attestation as the "
    "default ask now? It used to be SOC 2 Type I for the smaller deals but I think "
    "the audit team's preference has shifted.\n"
    "R. Lim [2026-03-18T14:09:00Z]: Type II is the default now for anything touching "
    "regulated data per ISP-001 Section 12 — the compliance team made that call after "
    "the Q4 audit findings. Type I is still acceptable for non-regulated engagements "
    "but we're pushing Type II wherever it's commercially reasonable.\n"
    "M. Osei [2026-03-18T14:14:00Z]: Good, that matches what I've been doing. One "
    "related note — background check requirements for vendor personnel with "
    "production access have been getting a lot more scrutiny. ISP-001 Section 6.3 is "
    "still the controlling document but audit has been asking us to document the "
    "evidence more formally.\n"
    "P. Horak [2026-03-18T14:21:00Z]: Yeah that's come up in a few reviews. We should "
    "probably tighten up how we capture the background-check evidence in the "
    "procurement record — not changing the requirement, just making sure the trail "
    "is clean. No action for this thread, just flagging for visibility.\n"
    "R. Lim [2026-03-18T14:27:00Z]: Agreed. I'll raise it in the next compliance "
    "sync. Nothing urgent."
)

T_902_TEXT = (
    "channel: #procurement-ops\n"
    "J. Novak [2026-04-02T11:15:00Z]: Honestly for our D-T2 deals lately we've been "
    "running pretty lean — the full review cycle kind of feels overkill for this "
    "class when the vendor has prior relationship and the data scope is "
    "straightforward. I'd lean toward expediting these unless Security flags "
    "something specific. Feels like we could save a week on most of them.\n"
    "M. Osei [2026-04-02T11:23:00Z]: Yeah I hear you — the cycle time has been a "
    "pain point. Though I'd want to be careful about formalizing that. We should "
    "probably talk to [Director] about the workflow before we change anything "
    "structural. Informally trimming where it's safe is one thing, skipping "
    "required approvers is another.\n"
    "J. Novak [2026-04-02T11:28:00Z]: Fair, yeah — I'm just venting about cycle "
    "time, not suggesting we actually skip anyone. Worth raising though."
)

T_903_TEXT = (
    "channel: #events-planning\n"
    "C. Oduya [2026-04-10T09:45:00Z]: Kicking off the catering vendor search for "
    "the Q2 all-hands offsite in Dortmund. Looking at Greenbrook Catering and two "
    "others — budget is EUR 12,000 for a two-day event, ~180 attendees. No system "
    "access, no data sharing, standard facilities-services agreement only.\n"
    "N. Papadopoulos [2026-04-10T09:52:00Z]: Class E, Tier 1 fast-track path — "
    "should be quick. Just NDA and Procurement Manager sign-off. I'll draft the "
    "RFP by end of week.\n"
    "C. Oduya [2026-04-10T09:58:00Z]: Perfect, thanks."
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


def _build_slk_chunk(thread_id: str, text: str, order: int) -> Chunk:
    return Chunk(
        chunk_id=f"{SLK_SOURCE_ID}__thread_{thread_id}",
        source_id=SLK_SOURCE_ID,
        source_name=SLK_SOURCE_NAME,
        source_type=SLK_SOURCE_TYPE,
        version=SLK_VERSION,
        document_date=DOCUMENT_DATE,
        freshness_status=SLK_FRESHNESS,
        authority_tier=SLK_AUTHORITY_TIER,
        retrieval_lane=SLK_RETRIEVAL_LANE,
        allowed_agents=SLK_ALLOWED_AGENTS,
        is_primary_citable=False,
        manifest_status=SLK_MANIFEST_STATUS,
        chunk_type="THREAD",
        chunk_order=order,
        section_id=None,
        row_id=None,
        record_id=None,
        thread_id=thread_id,
        domain_scope=None,
        citation_label=f"{SLK_SOURCE_ID} thread {thread_id}",
        text=text,
    )


def build_pam_chunks() -> list[Chunk]:
    return [
        _build_pam_chunk("D-T1", D_T1_TEXT, order=1),
        _build_pam_chunk("D-T2", D_T2_TEXT, order=2),
        _build_pam_chunk("D-T3", D_T3_TEXT, order=3),
    ]


def build_slk_chunks() -> list[Chunk]:
    return [
        _build_slk_chunk("T-901", T_901_TEXT, order=1),
        _build_slk_chunk("T-902", T_902_TEXT, order=2),
        _build_slk_chunk("T-903", T_903_TEXT, order=3),
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


def rebuild_indices(pam_chunks: list[Chunk], slk_chunks: list[Chunk]) -> None:
    if CHROMA_DIR.exists():
        shutil.rmtree(CHROMA_DIR)
    CHROMA_DIR.mkdir(parents=True, exist_ok=True)
    REGISTRY_DIR.mkdir(parents=True, exist_ok=True)
    BM25_DIR.mkdir(parents=True, exist_ok=True)

    vector_index = VectorIndex(persist_directory=CHROMA_DIR, registry_directory=REGISTRY_DIR)
    bm25 = BM25Index(persist_directory=BM25_DIR)

    rebuild_collection(PAM_COLLECTION, pam_chunks, vector_index, bm25)
    rebuild_collection(SLK_COLLECTION, slk_chunks, vector_index, bm25)


def write_index_registry() -> None:
    payload = {
        "registry_version": "1.0",
        "scenario": "scenario_9",
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
            SLK_SOURCE_ID: {
                "source_id": SLK_SOURCE_ID,
                "source_name": SLK_SOURCE_NAME,
                "source_type": SLK_SOURCE_TYPE,
                "authority_tier": SLK_AUTHORITY_TIER,
                "retrieval_lane": SLK_RETRIEVAL_LANE,
                "version": SLK_VERSION,
                "document_date": DOCUMENT_DATE,
                "freshness_status": SLK_FRESHNESS,
                "manifest_status": SLK_MANIFEST_STATUS,
                "allowed_agents": list(SLK_ALLOWED_AGENTS),
                "is_primary_citable": False,
                "storage_kind": "vector_bm25",
                "logical_store_name": SLK_COLLECTION,
                "backends": ["chroma", "bm25"],
                "backend_locations": {
                    "chroma_collection": SLK_COLLECTION,
                    "bm25_bundle": SLK_BM25_RELATIVE,
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


def _slack_payload(chunk: Chunk, *, retrieval_score: float, rerank_score: float) -> dict:
    return {
        "source_id": chunk.source_id,
        "version": chunk.version,
        "chunk_id": chunk.chunk_id,
        "section_id": chunk.section_id,
        "row_id": chunk.row_id,
        "thread_id": chunk.thread_id,
        "text": chunk.text,
        "authority_tier": chunk.authority_tier,
        "retrieval_score": retrieval_score,
        "rerank_score": rerank_score,
        "citation_class": "SUPPLEMENTARY",
    }


def write_fixture(pam_chunks: list[Chunk], slk_chunks: list[Chunk]) -> None:
    pam_by_id = {c.row_id: c for c in pam_chunks}
    slk_by_id = {c.thread_id: c for c in slk_chunks}

    d_t1 = pam_by_id["D-T1"]
    d_t2 = pam_by_id["D-T2"]
    d_t3 = pam_by_id["D-T3"]
    t_901 = slk_by_id["T-901"]
    t_902 = slk_by_id["T-902"]
    t_903 = slk_by_id["T-903"]

    fixture = {
        "scenario": "scenario_9",
        "agent": "procurement_agent",
        "bundle": {
            "source_ids": [
                "STEP-02",
                "STEP-03",
                "VQ-OC-001",
                "PAM-001",
                "DPA-TM-001",
                "ISP-001",
                "SLK-001",
            ],
            "it_security_output": {
                "data_classification": "REGULATED",
                "fast_track_eligible": False,
                "integration_tier": "T2",
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
                "dpa_blocker": False,
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
                "status": "complete",
            },
            "questionnaire": {
                "vendor_class": "D",
                "integration_tier": "T2",
                "deal_size": 180000,
                "existing_nda_status": "EXECUTED",
                "existing_dpa_status": "EXECUTED",
                "existing_msa": True,
            },
            "approval_path_matrix_rows": [
                _matrix_row_payload(d_t2, retrieval_score=0.86, rerank_score=0.83),
                _matrix_row_payload(d_t1, retrieval_score=0.71, rerank_score=0.68),
                _matrix_row_payload(d_t3, retrieval_score=0.64, rerank_score=0.59),
            ],
            "fast_track_routing_rows": [],
            "slack_procurement_chunks": [
                _slack_payload(t_901, retrieval_score=0.58, rerank_score=0.54),
                _slack_payload(t_902, retrieval_score=0.55, rerank_score=0.52),
                _slack_payload(t_903, retrieval_score=0.41, rerank_score=0.36),
            ],
            "bundle_meta": {
                "admissible": True,
                "missing_fields": [],
                "prohibited_sources": [],
            },
        },
        "pipeline_run_id": "scenario_9_synthesized",
    }

    FIXTURE_PATH.write_text(
        json.dumps(fixture, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(f"  wrote {FIXTURE_PATH.relative_to(REPO_ROOT)}")


def retrieval_check() -> None:
    vi = VectorIndex(persist_directory=CHROMA_DIR, registry_directory=REGISTRY_DIR)
    bmi = BM25Index(persist_directory=BM25_DIR)

    pam_query = (
        "Class D vendor, T2 integration tier, regulated data with executed DPA, "
        "$180K professional-services engagement; determine approval path"
    )
    v_hits_pam = vi.query(PAM_COLLECTION, pam_query, k=5, allowed_agent="procurement")
    b_hits_pam = bmi.query(PAM_COLLECTION, pam_query, k=5, allowed_agent="procurement")
    v_ids_pam = [h["chunk_id"] for h in v_hits_pam]
    b_ids_pam = [h["chunk_id"] for h in b_hits_pam]
    print("retrieval check (PAM-001):")
    print(f"  query  = {pam_query!r}")
    print(f"  vector = {v_ids_pam}")
    print(f"  bm25   = {b_ids_pam}")
    required_pam = "PAM-001__row_D-T2"
    if required_pam not in set(v_ids_pam) | set(b_ids_pam):
        raise SystemExit(f"retrieval FAIL: {required_pam} not returned from PAM collection")

    slk_query = (
        "Class D professional-services vendor review, approval workflow, cycle time, "
        "background check requirements"
    )
    v_hits_slk = vi.query(SLK_COLLECTION, slk_query, k=5, allowed_agent="procurement")
    b_hits_slk = bmi.query(SLK_COLLECTION, slk_query, k=5, allowed_agent="procurement")
    v_ids_slk = [h["chunk_id"] for h in v_hits_slk]
    b_ids_slk = [h["chunk_id"] for h in b_hits_slk]
    print("retrieval check (SLK-001):")
    print(f"  query  = {slk_query!r}")
    print(f"  vector = {v_ids_slk}")
    print(f"  bm25   = {b_ids_slk}")

    expected_slk = {"SLK-001__thread_T-901", "SLK-001__thread_T-902"}
    combined_slk = set(v_ids_slk) | set(b_ids_slk)
    missing = expected_slk - combined_slk
    if missing:
        raise SystemExit(
            f"retrieval FAIL: Slack threads {sorted(missing)} not returned from SLK collection"
        )

    # Verify authority_tier metadata is intact on returned Slack hits.
    for hit in v_hits_slk + b_hits_slk:
        meta = hit.get("metadata") or {}
        tier = meta.get("authority_tier")
        if tier != 3:
            raise SystemExit(
                f"retrieval FAIL: Slack hit {hit['chunk_id']} has authority_tier={tier!r} "
                "(expected 3) — evaluator's PRIMARY-citation check depends on Tier 3 tag"
            )

    print("  PASS: D-T2 present in PAM retrieval; T-901/T-902 present in SLK retrieval;")
    print("        Slack hits carry authority_tier=3 metadata.")


def main() -> None:
    pam_chunks = build_pam_chunks()
    slk_chunks = build_slk_chunks()
    print("[1/5] writing scenario chunks")
    write_chunks_json(PAM_CHUNKS_PATH, pam_chunks, "rows")
    write_chunks_json(SLK_CHUNKS_PATH, slk_chunks, "threads")
    print("[2/5] rebuilding scenario-scoped indices")
    rebuild_indices(pam_chunks, slk_chunks)
    print("[3/5] writing index registry")
    write_index_registry()
    print("[4/5] writing bundle fixture")
    write_fixture(pam_chunks, slk_chunks)
    print("[5/5] retrieval verification")
    retrieval_check()


if __name__ == "__main__":
    main()
