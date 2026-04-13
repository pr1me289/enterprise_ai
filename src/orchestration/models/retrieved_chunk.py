"""RetrievedChunk dataclass representing a single admitted or excluded evidence chunk."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class RetrievedChunk:
    """A single chunk of evidence retrieved from a source during a pipeline step."""

    source_id: str
    """Logical source identifier (e.g. ``ISP-001``, ``SLK-001``)."""

    source_name: str
    """Human-readable source name."""

    source_type: str
    """Source classification (e.g. ``POLICY_DOCUMENT``, ``STRUCTURED_TABLE``)."""

    chunk_id: str
    """Unique chunk identifier within the source."""

    authority_tier: int
    """Numeric authority tier (1 = highest, 3 = lowest)."""

    retrieval_lane: str
    """The retrieval lane used to fetch this chunk (``direct_structured``, ``indexed_hybrid``, ``runtime_read``)."""

    is_primary_citable: bool
    """Whether this chunk qualifies as a primary citation."""

    text: str
    """Chunk body text."""

    citation_label: str
    """Short human-readable citation label (e.g. ``ISP-001 §12``)."""

    extra_metadata: dict[str, Any] = field(default_factory=dict)
    """Any additional source-specific metadata fields."""

    def to_dict(self) -> dict[str, Any]:
        """Serialise to a plain dict."""
        result: dict[str, Any] = {
            "source_id": self.source_id,
            "source_name": self.source_name,
            "source_type": self.source_type,
            "chunk_id": self.chunk_id,
            "authority_tier": self.authority_tier,
            "retrieval_lane": self.retrieval_lane,
            "is_primary_citable": self.is_primary_citable,
            "text": self.text,
            "citation_label": self.citation_label,
        }
        if self.extra_metadata:
            result["extra_metadata"] = self.extra_metadata
        return result
