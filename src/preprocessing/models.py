"""Core models for the preprocessing layer."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any


class SourceType(str, Enum):
    POLICY_DOCUMENT = "POLICY_DOCUMENT"
    LEGAL_TRIGGER_MATRIX = "LEGAL_TRIGGER_MATRIX"
    PROCUREMENT_APPROVAL_MATRIX = "PROCUREMENT_APPROVAL_MATRIX"
    VENDOR_QUESTIONNAIRE = "VENDOR_QUESTIONNAIRE"
    VENDOR_PRECEDENT = "VENDOR_PRECEDENT"
    SLACK_THREAD = "SLACK_THREAD"


class RetrievalLane(str, Enum):
    INDEXED_HYBRID = "INDEXED_HYBRID"
    DIRECT_STRUCTURED = "DIRECT_STRUCTURED"


class ManifestStatus(str, Enum):
    CONFIRMED = "CONFIRMED"
    PROVISIONAL = "PROVISIONAL"
    PENDING = "PENDING"


@dataclass(slots=True)
class PolicySection:
    section_id: str
    heading: str
    text: str
    order: int
    level: int | None = None


@dataclass(slots=True)
class MatrixRow:
    row_id: str
    values: dict[str, Any]
    text: str
    order: int


@dataclass(slots=True)
class PrecedentRecord:
    record_id: str
    text: str
    order: int
    fields: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class SlackMessage:
    timestamp: str
    author: str
    text: str
    order: int


@dataclass(slots=True)
class SlackThread:
    thread_id: str
    text: str
    order: int
    channel: str | None = None
    export_date: str | None = None
    message_count: int | None = None
    messages: list[SlackMessage] = field(default_factory=list)


@dataclass(slots=True)
class NormalizedSource:
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
    source_path: Path
    raw_text: str
    structured_data: Any | None = None
    sections: list[PolicySection] = field(default_factory=list)
    rows: list[MatrixRow] = field(default_factory=list)
    records: list[PrecedentRecord] = field(default_factory=list)
    threads: list[SlackThread] = field(default_factory=list)
    document_id: str | None = None
    detected_version: str | None = None
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["source_path"] = str(self.source_path)
        payload["source_type"] = self.source_type.value
        payload["retrieval_lane"] = self.retrieval_lane.value
        payload["manifest_status"] = self.manifest_status.value
        return payload
