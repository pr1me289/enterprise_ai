"""FinalStateWriter: writes final_state.json and audit_log.json."""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from orchestration.audit.audit_logger import AuditLogger
from orchestration.pipeline_state import PipelineState


class FinalStateWriter:
    """Serialises PipelineState and audit entries to disk."""

    def __init__(self, run_dir: Path) -> None:
        self._run_dir = run_dir

    def write(self, state: PipelineState, audit_logger: AuditLogger) -> None:
        self._write_final_state(state)
        self._write_audit_log(audit_logger)

    def _write_final_state(self, state: PipelineState) -> None:
        data: dict[str, Any] = {
            "pipeline_run_id": state.pipeline_run_id,
            "vendor_name": state.vendor_name,
            "manifest_version": state.manifest_version,
            "initialized_at": state.initialized_at,
            "overall_status": state.overall_status.value,
            "current_step": state.current_step.value if state.current_step else None,
            "step_statuses": {k.value: v.value for k, v in state.step_statuses.items()},
            "determinations": state.determinations,
            "escalations": state.escalations,
            "audit_refs": state.audit_refs,
            "next_step_queue": [s.value for s in state.next_step_queue],
        }
        path = self._run_dir / "final_state.json"
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def _write_audit_log(self, audit_logger: AuditLogger) -> None:
        entries = [
            {
                "entry_id": e.entry_id,
                "pipeline_run_id": e.pipeline_run_id,
                "agent_id": e.agent_id,
                "event_type": e.event_type.value,
                "timestamp": e.timestamp,
                "source_queried": e.source_queried,
                "chunks_retrieved": e.chunks_retrieved,
                "details": e.details,
            }
            for e in audit_logger.entries
        ]
        path = self._run_dir / "audit_log.json"
        path.write_text(json.dumps(entries, indent=2), encoding="utf-8")
