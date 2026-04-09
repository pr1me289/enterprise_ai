"""Core models for the chunking layer."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any


class ChunkType(str, Enum):
    SECTION = "SECTION"
    ROW = "ROW"
    RECORD = "RECORD"
    THREAD = "THREAD"


@dataclass(slots=True)
class Chunk:
    chunk_id: str
    source_id: str
    source_name: str
    source_type: str
    version: str
    authority_tier: int
    retrieval_lane: str
    allowed_agents: tuple[str, ...]
    manifest_status: str
    chunk_type: str
    chunk_order: int
    citation_label: str
    text: str
    section_id: str | None = None
    row_id: str | None = None
    record_id: str | None = None
    thread_id: str | None = None

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "Chunk":
        normalized_payload = dict(payload)
        normalized_payload["allowed_agents"] = tuple(payload.get("allowed_agents", []))
        return cls(**normalized_payload)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["allowed_agents"] = list(self.allowed_agents)
        return payload
