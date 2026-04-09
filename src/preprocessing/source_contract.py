"""Source contracts derived from the Context Contract."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .models import ManifestStatus, RetrievalLane, SourceType


@dataclass(frozen=True, slots=True)
class SourceContract:
    source_id: str
    source_type: SourceType
    source_name: str
    version: str
    authority_tier: int
    retrieval_lane: RetrievalLane
    allowed_agents: tuple[str, ...]
    manifest_status: ManifestStatus
    owner_role: str
    path_hints: tuple[str, ...]


SOURCE_CONTRACTS: tuple[SourceContract, ...] = (
    SourceContract(
        source_id="ISP-001",
        source_type=SourceType.POLICY,
        source_name="IT Security Policy",
        version="4.2",
        authority_tier=1,
        retrieval_lane=RetrievalLane.INDEXED_HYBRID,
        allowed_agents=("it_security", "legal", "procurement"),
        manifest_status=ManifestStatus.PROVISIONAL,
        owner_role="IT Security",
        path_hints=("it_security_policy",),
    ),
    SourceContract(
        source_id="DPA-TM-001",
        source_type=SourceType.MATRIX,
        source_name="DPA Legal Trigger Matrix",
        version="2.1",
        authority_tier=1,
        retrieval_lane=RetrievalLane.INDEXED_HYBRID,
        allowed_agents=("legal",),
        manifest_status=ManifestStatus.PROVISIONAL,
        owner_role="Legal",
        path_hints=("dpa_legal_trigger_matrix",),
    ),
    SourceContract(
        source_id="PAM-001",
        source_type=SourceType.MATRIX,
        source_name="Procurement Approval Matrix",
        version="3.0",
        authority_tier=1,
        retrieval_lane=RetrievalLane.INDEXED_HYBRID,
        allowed_agents=("procurement",),
        manifest_status=ManifestStatus.PROVISIONAL,
        owner_role="Procurement",
        path_hints=("procurement_approval_matrix",),
    ),
    SourceContract(
        source_id="VQ-OC-001",
        source_type=SourceType.QUESTIONNAIRE,
        source_name="OptiChain Vendor Questionnaire",
        version="Submission rev. 1",
        authority_tier=2,
        retrieval_lane=RetrievalLane.DIRECT_STRUCTURED,
        allowed_agents=(
            "it_security",
            "legal",
            "procurement",
            "checklist_assembler",
            "checkoff",
        ),
        manifest_status=ManifestStatus.PENDING,
        owner_role="Procurement",
        path_hints=("optichain_vsq", "vendor_questionnaire"),
    ),
    SourceContract(
        source_id="PVD-001",
        source_type=SourceType.PRECEDENT,
        source_name="Prior Vendor Decisions / Precedent Log",
        version="Current at init.",
        authority_tier=3,
        retrieval_lane=RetrievalLane.INDEXED_HYBRID,
        allowed_agents=("it_security", "legal", "procurement"),
        manifest_status=ManifestStatus.CONFIRMED,
        owner_role="IT Architecture / Platform",
        path_hints=("vendor_precedent_log", "precedent_log"),
    ),
    SourceContract(
        source_id="SLK-001",
        source_type=SourceType.SUPPLEMENTAL_NOTE,
        source_name="Slack / Meeting Thread Notes",
        version="Export at init.",
        authority_tier=4,
        retrieval_lane=RetrievalLane.INDEXED_HYBRID,
        allowed_agents=("procurement",),
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
