"""BundleTraceWriter: writes per-step bundle summaries to bundle_trace.json."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from orchestration.models.context_bundle import ContextBundle


class BundleTraceWriter:
    """Accumulates per-step bundle summaries and writes bundle_trace.json."""

    def __init__(self, run_dir: Path) -> None:
        self._run_dir = run_dir
        self._traces: list[dict[str, Any]] = []

    def record(self, step_id: str, bundle: ContextBundle) -> None:
        """Record a step's bundle summary."""
        trace: dict[str, Any] = {
            "step_id": step_id,
            "admissibility_status": bundle.admissibility_status,
            "admitted_count": len(bundle.admitted_evidence),
            "excluded_count": len(bundle.excluded_evidence),
            "admitted_chunks": [
                {
                    "source_id": c.source_id,
                    "chunk_id": c.chunk_id,
                    "authority_tier": c.authority_tier,
                    "is_primary_citable": c.is_primary_citable,
                    "citation_label": c.citation_label,
                }
                for c in bundle.admitted_evidence
            ],
            "excluded_chunks": [
                {
                    "source_id": e.chunk.source_id,
                    "chunk_id": e.chunk.chunk_id,
                    "exclusion_reason": e.exclusion_reason,
                }
                for e in bundle.excluded_evidence
            ],
            "structured_fields_keys": list(bundle.structured_fields.keys()),
            "source_provenance": bundle.source_provenance,
        }
        self._traces.append(trace)

    def write(self) -> None:
        path = self._run_dir / "bundle_trace.json"
        path.write_text(json.dumps(self._traces, indent=2), encoding="utf-8")

    @property
    def traces(self) -> list[dict[str, Any]]:
        return list(self._traces)
