"""Source contracts derived from the Context Contract."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .models import ManifestStatus, RetrievalLane, SourceType

DEMO_DOCUMENT_DATE = "2026-04-04"
DEMO_FRESHNESS_STATUS = "CURRENT"


@dataclass(frozen=True, slots=True)
class SourceContract:
    source_id: str
    source_type: SourceType
    source_name: str
    version: str
    document_date: str | None
    freshness_status: str
    authority_tier: int
    retrieval_lane: RetrievalLane
    allowed_agents: tuple[str, ...]
    is_primary_citable: bool
    manifest_status: ManifestStatus
    owner_role: str
    path_hints: tuple[str, ...]


SOURCE_CONTRACTS: tuple[SourceContract, ...] = (
    SourceContract(
        source_id="ISP-001",
        source_type=SourceType.POLICY_DOCUMENT,
        source_name="IT Security Policy",
        version="4.2",
        document_date=DEMO_DOCUMENT_DATE,
        freshness_status=DEMO_FRESHNESS_STATUS,
        authority_tier=1,
        retrieval_lane=RetrievalLane.INDEXED_HYBRID,
        allowed_agents=("it_security", "legal", "procurement"),
        is_primary_citable=True,
        manifest_status=ManifestStatus.PROVISIONAL,
        owner_role="IT Security",
        path_hints=("it_security_policy",),
    ),
    SourceContract(
        source_id="DPA-TM-001",
        source_type=SourceType.LEGAL_TRIGGER_MATRIX,
        source_name="DPA Legal Trigger Matrix",
        version="2.1",
        document_date=DEMO_DOCUMENT_DATE,
        freshness_status=DEMO_FRESHNESS_STATUS,
        authority_tier=1,
        retrieval_lane=RetrievalLane.INDEXED_HYBRID,
        allowed_agents=("legal",),
        is_primary_citable=True,
        manifest_status=ManifestStatus.PROVISIONAL,
        owner_role="Legal",
        path_hints=("dpa_legal_trigger_matrix",),
    ),
    SourceContract(
        source_id="PAM-001",
        source_type=SourceType.PROCUREMENT_APPROVAL_MATRIX,
        source_name="Procurement Approval Matrix",
        version="3.0",
        document_date=DEMO_DOCUMENT_DATE,
        freshness_status=DEMO_FRESHNESS_STATUS,
        authority_tier=1,
        retrieval_lane=RetrievalLane.INDEXED_HYBRID,
        allowed_agents=("procurement",),
        is_primary_citable=True,
        manifest_status=ManifestStatus.PROVISIONAL,
        owner_role="Procurement",
        path_hints=("procurement_approval_matrix",),
    ),
    SourceContract(
        source_id="VQ-OC-001",
        source_type=SourceType.VENDOR_QUESTIONNAIRE,
        source_name="OptiChain Vendor Questionnaire",
        version="Submission rev. 1",
        document_date=DEMO_DOCUMENT_DATE,
        freshness_status=DEMO_FRESHNESS_STATUS,
        authority_tier=2,
        retrieval_lane=RetrievalLane.DIRECT_STRUCTURED,
        allowed_agents=(
            "it_security",
            "legal",
            "procurement",
            "checklist_assembler",
            "checkoff",
        ),
        is_primary_citable=True,
        manifest_status=ManifestStatus.PENDING,
        owner_role="Procurement",
        path_hints=("optichain_vsq", "vendor_questionnaire"),
    ),
    SourceContract(
        source_id="PVD-001",
        source_type=SourceType.VENDOR_PRECEDENT,
        source_name="Prior Vendor Decisions / Precedent Log",
        version="Current at init.",
        document_date=DEMO_DOCUMENT_DATE,
        freshness_status=DEMO_FRESHNESS_STATUS,
        authority_tier=3,
        retrieval_lane=RetrievalLane.INDEXED_HYBRID,
        allowed_agents=("it_security", "legal", "procurement"),
        is_primary_citable=False,
        manifest_status=ManifestStatus.CONFIRMED,
        owner_role="IT Architecture / Platform",
        path_hints=("vendor_precedent_log", "precedent_log"),
    ),
    SourceContract(
        source_id="SLK-001",
        source_type=SourceType.SLACK_THREAD,
        source_name="Slack / Meeting Thread Notes",
        version="Export at init.",
        document_date=DEMO_DOCUMENT_DATE,
        freshness_status=DEMO_FRESHNESS_STATUS,
        authority_tier=4,
        retrieval_lane=RetrievalLane.INDEXED_HYBRID,
        allowed_agents=("procurement",),
        is_primary_citable=False,
        manifest_status=ManifestStatus.CONFIRMED,
        owner_role="Procurement",
        path_hints=("slack_thread_export", "meeting_thread"),
    ),
)

SOURCE_CONTRACTS_BY_ID = {contract.source_id: contract for contract in SOURCE_CONTRACTS}


def resolve_contract_for_path(path: str | Path) -> SourceContract:
    """Resolve a contract using the file name and known source hints."""

    normalized_name = Path(path).name.lower()
    for contract in SOURCE_CONTRACTS:
        if any(hint in normalized_name for hint in contract.path_hints):
            return contract
    raise ValueError(f"Unsupported source file: {path}")
