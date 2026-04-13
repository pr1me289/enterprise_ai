"""Audit-entry dataclasses."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from orchestration.models.enums import AuditEventType


@dataclass(slots=True)
class AuditEntry:
    entry_id: str
    pipeline_run_id: str
    agent_id: str
    event_type: AuditEventType
    timestamp: str
    source_queried: str | None = None
    chunks_retrieved: list[dict[str, Any]] = field(default_factory=list)
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["event_type"] = self.event_type.value
        return payload
