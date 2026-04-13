"""ContextBundle dataclass representing the assembled evidence bundle passed to an agent."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .enums import StepId
from .retrieved_chunk import RetrievedChunk


@dataclass(slots=True)
class ExcludedChunk:
    """A chunk that was retrieved but excluded from the admitted evidence set."""

    chunk: RetrievedChunk
    exclusion_reason: str

    def to_dict(self) -> dict[str, Any]:
        return {"chunk": self.chunk.to_dict(), "exclusion_reason": self.exclusion_reason}


@dataclass(slots=True)
class ContextBundle:
    """Structured evidence bundle assembled by the retrieval layer for a given step."""

    step_id: StepId
    """The pipeline step this bundle was assembled for."""

    admitted_evidence: list[RetrievedChunk] = field(default_factory=list)
    """Chunks that passed admissibility checks and are available to the agent."""

    excluded_evidence: list[ExcludedChunk] = field(default_factory=list)
    """Chunks that were retrieved but failed admissibility checks."""

    structured_fields: dict[str, Any] = field(default_factory=dict)
    """Structured key/value fields drawn from direct-structured sources."""

    source_provenance: list[dict[str, Any]] = field(default_factory=list)
    """Source-level provenance records describing which stores were queried."""

    admissibility_status: str = "PENDING"
    """Overall admissibility status of the bundle (``ADMISSIBLE``, ``PARTIAL``, ``INADMISSIBLE``)."""

    def to_dict(self) -> dict[str, Any]:
        return {
            "step_id": self.step_id.value,
            "admitted_evidence": [c.to_dict() for c in self.admitted_evidence],
            "excluded_evidence": [e.to_dict() for e in self.excluded_evidence],
            "structured_fields": self.structured_fields,
            "source_provenance": self.source_provenance,
            "admissibility_status": self.admissibility_status,
        }
