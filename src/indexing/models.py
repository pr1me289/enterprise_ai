"""Core models for the embedding and vector persistence layer."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from typing import Any

from chunking import Chunk


@dataclass(slots=True)
class EmbeddingRecord:
    chunk_id: str
    text: str
    embedding: list[float]
    source_id: str
    source_name: str
    source_type: str
    version: str
    document_date: str | None
    freshness_status: str
    authority_tier: int
    retrieval_lane: str
    allowed_agents: tuple[str, ...]
    is_primary_citable: bool
    manifest_status: str
    chunk_type: str
    citation_label: str
    section_id: str | None = None
    row_id: str | None = None
    record_id: str | None = None
    thread_id: str | None = None
    domain_scope: str | None = None

    @classmethod
    def from_chunk(cls, chunk: Chunk, embedding: list[float]) -> "EmbeddingRecord":
        return cls(
            chunk_id=chunk.chunk_id,
            text=chunk.text,
            embedding=embedding,
            source_id=chunk.source_id,
            source_name=chunk.source_name,
            source_type=chunk.source_type,
            version=chunk.version,
            document_date=chunk.document_date,
            freshness_status=chunk.freshness_status,
            authority_tier=chunk.authority_tier,
            retrieval_lane=chunk.retrieval_lane,
            allowed_agents=chunk.allowed_agents,
            is_primary_citable=chunk.is_primary_citable,
            manifest_status=chunk.manifest_status,
            chunk_type=chunk.chunk_type,
            citation_label=chunk.citation_label,
            section_id=chunk.section_id,
            row_id=chunk.row_id,
            record_id=chunk.record_id,
            thread_id=chunk.thread_id,
            domain_scope=chunk.domain_scope,
        )

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["allowed_agents"] = list(self.allowed_agents)
        return payload

    def metadata(self) -> dict[str, str | int]:
        metadata: dict[str, str | int] = {
            "chunk_id": self.chunk_id,
            "source_id": self.source_id,
            "source_name": self.source_name,
            "source_type": self.source_type,
            "version": self.version,
            "document_date": self.document_date or "",
            "freshness_status": self.freshness_status,
            "authority_tier": self.authority_tier,
            "retrieval_lane": self.retrieval_lane,
            "allowed_agents": json.dumps(list(self.allowed_agents), ensure_ascii=True),
            "is_primary_citable": self.is_primary_citable,
            "manifest_status": self.manifest_status,
            "chunk_type": self.chunk_type,
            "citation_label": self.citation_label,
        }
        if self.section_id is not None:
            metadata["section_id"] = self.section_id
        if self.row_id is not None:
            metadata["row_id"] = self.row_id
        if self.record_id is not None:
            metadata["record_id"] = self.record_id
        if self.thread_id is not None:
            metadata["thread_id"] = self.thread_id
        if self.domain_scope is not None:
            metadata["domain_scope"] = self.domain_scope
        return metadata
