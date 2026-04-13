"""Pipeline-state model for the static orchestration state machine."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, UTC
from uuid import uuid4

from orchestration.config.step_definitions import STEP_ORDER
from orchestration.models.enums import RunStatus, StepId, StepStatus


def utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


@dataclass(slots=True)
class PipelineState:
    pipeline_run_id: str
    vendor_name: str | None
    manifest_version: str
    initialized_at: str
    overall_status: RunStatus
    current_step: StepId | None
    active_steps: list[StepId]
    step_statuses: dict[StepId, StepStatus]
    determinations: dict[str, dict | None]
    escalations: list[dict]
    audit_refs: list[str]
    next_step_queue: list[StepId]

    @classmethod
    def initialize(cls, manifest_version: str) -> "PipelineState":
        return cls(
            pipeline_run_id=f"run_{uuid4().hex[:10]}",
            vendor_name=None,
            manifest_version=manifest_version,
            initialized_at=utc_now(),
            overall_status=RunStatus.IN_PROGRESS,
            current_step=StepId.STEP_01,
            active_steps=[],
            step_statuses={step_id: StepStatus.PENDING for step_id in STEP_ORDER},
            determinations={
                "step_01_intake": None,
                "step_02_security_classification": None,
                "step_03_legal": None,
                "step_04_procurement": None,
                "step_05_checklist": None,
                "step_06_guidance": None,
            },
            escalations=[],
            audit_refs=[],
            next_step_queue=[StepId.STEP_01],
        )

    def set_current_step(self, step_id: StepId) -> None:
        self.current_step = step_id
        self.active_steps = [step_id]

    def complete_step(self, step_id: StepId, status: StepStatus) -> None:
        self.step_statuses[step_id] = status
        self.active_steps = []

    def enqueue(self, step_id: StepId | None) -> None:
        if step_id is not None and step_id not in self.next_step_queue:
            self.next_step_queue.append(step_id)

    def dequeue(self) -> StepId | None:
        if not self.next_step_queue:
            return None
        return self.next_step_queue.pop(0)
