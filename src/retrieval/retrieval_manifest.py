"""Manifest objects for reconstructable retrieval events."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(slots=True)
class RetrievalManifestEntry:
    agent_name: str
    index_name: str
    query_text: str
    filters: dict[str, Any]
    returned_chunks: list[dict[str, Any]] = field(default_factory=list)
    suppressed_chunks: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
