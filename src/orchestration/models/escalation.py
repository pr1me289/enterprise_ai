"""EscalationPayload dataclass for step escalation data."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class EscalationPayload:
    """Structured payload emitted when a step transitions to ESCALATED status."""

    evidence_condition: str
    """Human-readable description of why the escalation was triggered."""

    resolution_owner: str
    """The role or team responsible for resolving this escalation."""

    additional_context: dict[str, Any] = field(default_factory=dict)
    """Optional extra key/value context that step handlers may attach."""

    def to_dict(self) -> dict[str, Any]:
        """Serialise to a plain dict suitable for audit-log spreading."""
        result: dict[str, Any] = {
            "evidence_condition": self.evidence_condition,
            "resolution_owner": self.resolution_owner,
        }
        if self.additional_context:
            result.update(self.additional_context)
        return result
