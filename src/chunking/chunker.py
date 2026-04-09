"""Source-aware chunk creation from normalized sources."""

from __future__ import annotations

from preprocessing import NormalizedSource, SourceType

from .models import Chunk, ChunkType

PRECEDENT_DOMAIN_SCOPE_BY_RECORD_ID = {
    "PVD-001-REC-001": "legal",
    "PVD-001-REC-002": "security",
    "PVD-001-REC-003": "procurement",
    "PVD-001-REC-004": "procurement",
}


def chunk_source(source: NormalizedSource) -> list[Chunk]:
    if source.source_type is SourceType.POLICY:
        return _chunk_policy(source)
    if source.source_type is SourceType.MATRIX:
        return _chunk_matrix(source)
    if source.source_type is SourceType.PRECEDENT:
        return _chunk_precedent(source)
    if source.source_type is SourceType.SUPPLEMENTAL_NOTE:
        return _chunk_slack(source)
    if source.source_type is SourceType.QUESTIONNAIRE:
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


def _sanitize_identifier(value: str) -> str:
    return value.replace(" ", "_").replace(".", "_").replace("/", "_").replace("§", "")
