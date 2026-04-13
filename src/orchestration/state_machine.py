"""Explicit state-transition helpers for the Supervisor."""

from __future__ import annotations

from orchestration.models.enums import RunStatus, StepId, StepStatus
from orchestration.pipeline_state import PipelineState


class StateMachine:
    """Small deterministic transition helper for the sequential pipeline."""

    @staticmethod
    def derive_overall_status(state: PipelineState) -> RunStatus:
        statuses = tuple(state.step_statuses.values())
        if StepStatus.BLOCKED in statuses:
            return RunStatus.BLOCKED
        if StepStatus.ESCALATED in statuses:
            return RunStatus.ESCALATED
        if state.step_statuses[StepId.STEP_05] is StepStatus.COMPLETE:
            return RunStatus.COMPLETE
        return RunStatus.IN_PROGRESS

    @staticmethod
    def determine_next_step(
        state: PipelineState,
        just_completed: StepId,
        step_status: StepStatus,
        output: dict | None,
    ) -> StepId | None:
        if just_completed is StepId.STEP_01:
            return StepId.STEP_02 if step_status is StepStatus.COMPLETE else None
        if just_completed is StepId.STEP_02:
            return StepId.STEP_03 if step_status is StepStatus.COMPLETE else None
        if just_completed is StepId.STEP_03:
            return StepId.STEP_04 if step_status in {StepStatus.COMPLETE, StepStatus.ESCALATED} else None
        if just_completed is StepId.STEP_04:
            return StepId.STEP_05 if step_status in {StepStatus.COMPLETE, StepStatus.ESCALATED} else None
        if just_completed is StepId.STEP_05:
            if step_status is StepStatus.COMPLETE and output and output.get("overall_status") == "COMPLETE":
                return StepId.STEP_06
            return None
        return None
