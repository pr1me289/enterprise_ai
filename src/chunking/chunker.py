"""Source-aware chunk creation from normalized sources."""

from __future__ import annotations

from preprocessing import NormalizedSource, SourceType
from preprocessing.text_utils import flatten_json_to_text, normalize_text

from .models import Chunk, ChunkType

PRECEDENT_DOMAIN_SCOPE_BY_RECORD_ID = {
    "PVD-001-REC-001": "legal",
    "PVD-001-REC-002": "security",
    "PVD-001-REC-003": "legal",
    "PVD-001-REC-004": "procurement",
}


def chunk_source(source: NormalizedSource) -> list[Chunk]:
    if source.source_type is SourceType.POLICY_DOCUMENT:
        return _chunk_policy(source)
    if source.source_type in {
        SourceType.LEGAL_TRIGGER_MATRIX,
        SourceType.PROCUREMENT_APPROVAL_MATRIX,
    }:
        return _chunk_matrix(source)
    if source.source_type is SourceType.VENDOR_PRECEDENT:
        return _chunk_precedent(source)
    if source.source_type is SourceType.SLACK_THREAD:
        return _chunk_slack(source)
    if source.source_type is SourceType.STAKEHOLDER_MAP:
        return _chunk_stakeholder_map(source)
    if source.source_type is SourceType.VENDOR_QUESTIONNAIRE:
        return []
    raise ValueError(f"Unsupported source type for chunking: {source.source_type}")


def chunk_sources(sources: list[NormalizedSource]) -> dict[str, list[Chunk]]:
    return {source.source_id: chunk_source(source) for source in sources}


def _chunk_policy(source: NormalizedSource) -> list[Chunk]:
    return [
        _build_chunk(
            source,
            chunk_type=ChunkType.SECTION,
            chunk_order=section.order,
            text=section.text,
            citation_label=_policy_citation_label(source.source_id, section.section_id),
            section_id=section.section_id,
            suffix=f"section_{_sanitize_identifier(section.section_id)}",
        )
        for section in source.sections
    ]


def _chunk_matrix(source: NormalizedSource) -> list[Chunk]:
    return [
        _build_chunk(
            source,
            chunk_type=ChunkType.ROW,
            chunk_order=row.order,
            text=row.text,
            citation_label=f"{source.source_id} row {row.row_id}",
            row_id=row.row_id,
            suffix=f"row_{_sanitize_identifier(row.row_id)}",
        )
        for row in source.rows
    ]


def _chunk_precedent(source: NormalizedSource) -> list[Chunk]:
    return [
        _build_chunk(
            source,
            chunk_type=ChunkType.RECORD,
            chunk_order=record.order,
            text=record.text,
            citation_label=f"{source.source_id} record {record.record_id}",
            record_id=record.record_id,
            domain_scope=PRECEDENT_DOMAIN_SCOPE_BY_RECORD_ID.get(record.record_id),
            suffix=f"record_{_sanitize_identifier(record.record_id)}",
        )
        for record in source.records
    ]


def _chunk_slack(source: NormalizedSource) -> list[Chunk]:
    return [
        _build_chunk(
            source,
            chunk_type=ChunkType.THREAD,
            chunk_order=thread.order,
            text=thread.text,
            citation_label=f"{source.source_id} thread {thread.thread_id}",
            thread_id=thread.thread_id,
            suffix=f"thread_{_sanitize_identifier(thread.thread_id)}",
        )
        for thread in source.threads
    ]


def _chunk_stakeholder_map(source: NormalizedSource) -> list[Chunk]:
    data = source.structured_data or {}
    chunks: list[Chunk] = []
    chunk_order = 1

    summary_payload = {
        "document_id": data.get("document_id"),
        "vendor": data.get("vendor"),
        "procurement_reference": data.get("procurement_reference"),
        "pipeline_run_scope": data.get("pipeline_run_scope"),
        "source_references": data.get("source_references"),
        "checkoff_agent_note": data.get("checkoff_agent_note"),
    }
    chunks.append(
        _build_chunk(
            source,
            chunk_type=ChunkType.RECORD,
            chunk_order=chunk_order,
            text=normalize_text(flatten_json_to_text(summary_payload, "stakeholder_map")),
            citation_label=f"{source.source_id} summary",
            record_id="SUMMARY",
            suffix="record_summary",
        )
    )
    chunk_order += 1

    for role in data.get("roles", []):
        role_id = str(role.get("role_id") or f"ROLE-{chunk_order:03d}")
        role_label = str(role.get("role_label") or role_id)
        chunks.append(
            _build_chunk(
                source,
                chunk_type=ChunkType.RECORD,
                chunk_order=chunk_order,
                text=_stakeholder_chunk_text(role_label, role, prefix="role"),
                citation_label=f"{source.source_id} role {role_id}",
                record_id=role_id,
                suffix=f"record_{_sanitize_identifier(role_id)}",
            )
        )
        chunk_order += 1

    for index, approval in enumerate(data.get("optichain_required_approvals", []), start=1):
        approval_id = f"APPROVAL-{index:02d}"
        approver_role = str(approval.get("approver_role") or approval_id)
        chunks.append(
            _build_chunk(
                source,
                chunk_type=ChunkType.RECORD,
                chunk_order=chunk_order,
                text=_stakeholder_chunk_text(approver_role, approval, prefix="approval"),
                citation_label=f"{source.source_id} approval {approver_role}",
                record_id=approval_id,
                suffix=f"record_{_sanitize_identifier(approval_id)}",
            )
        )
        chunk_order += 1

    for escalation in data.get("optichain_escalation_routing", []):
        escalation_id = str(escalation.get("escalation_id") or f"ESC-{chunk_order:03d}")
        condition = str(escalation.get("condition") or escalation_id)
        chunks.append(
            _build_chunk(
                source,
                chunk_type=ChunkType.RECORD,
                chunk_order=chunk_order,
                text=_stakeholder_chunk_text(condition, escalation, prefix="escalation"),
                citation_label=f"{source.source_id} escalation {escalation_id}",
                record_id=escalation_id,
                suffix=f"record_{_sanitize_identifier(escalation_id)}",
            )
        )
        chunk_order += 1

    vendor_contact = data.get("vendor_contact")
    if vendor_contact:
        chunks.append(
            _build_chunk(
                source,
                chunk_type=ChunkType.RECORD,
                chunk_order=chunk_order,
                text=_stakeholder_chunk_text("vendor_contact", vendor_contact, prefix="vendor_contact"),
                citation_label=f"{source.source_id} vendor contact",
                record_id="VENDOR-CONTACT",
                suffix="record_vendor_contact",
            )
        )

    return chunks


def _build_chunk(
    source: NormalizedSource,
    *,
    chunk_type: ChunkType,
    chunk_order: int,
    text: str,
    citation_label: str,
    suffix: str,
    section_id: str | None = None,
    row_id: str | None = None,
    record_id: str | None = None,
    thread_id: str | None = None,
    domain_scope: str | None = None,
) -> Chunk:
    return Chunk(
        chunk_id=f"{source.source_id}__{suffix}",
        source_id=source.source_id,
        source_name=source.source_name,
        source_type=source.source_type.value,
        version=source.version,
        document_date=source.document_date,
        freshness_status=source.freshness_status,
        authority_tier=source.authority_tier,
        retrieval_lane=source.retrieval_lane.value,
        allowed_agents=source.allowed_agents,
        is_primary_citable=source.is_primary_citable,
        manifest_status=source.manifest_status.value,
        chunk_type=chunk_type.value,
        chunk_order=chunk_order,
        section_id=section_id,
        row_id=row_id,
        record_id=record_id,
        thread_id=thread_id,
        domain_scope=domain_scope,
        citation_label=citation_label,
        text=text,
    )


def _policy_citation_label(source_id: str, section_id: str) -> str:
    if section_id and section_id != "document":
        return f"{source_id} §{section_id}"
    return source_id


def _stakeholder_chunk_text(title: str, payload: object, *, prefix: str) -> str:
    return normalize_text(f"{prefix}_title: {title}\n{flatten_json_to_text(payload, prefix)}")


def _sanitize_identifier(value: str) -> str:
    return value.replace(" ", "_").replace(".", "_").replace("/", "_").replace("§", "")
