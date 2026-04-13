"""Static step order for the orchestration state machine."""

from __future__ import annotations

from orchestration.models.contracts import StepDefinition
from orchestration.models.enums import StepId


STEP_ORDER: tuple[StepId, ...] = (
    StepId.STEP_01,
    StepId.STEP_02,
    StepId.STEP_03,
    StepId.STEP_04,
    StepId.STEP_05,
    StepId.STEP_06,
)


STEP_DEFINITIONS: dict[StepId, StepDefinition] = {
    StepId.STEP_01: StepDefinition(
        step_id=StepId.STEP_01,
        label="Intake Validation",
        assigned_agent="supervisor",
        access_role="supervisor",
        next_step=StepId.STEP_02,
    ),
    StepId.STEP_02: StepDefinition(
        step_id=StepId.STEP_02,
        label="Onboarding Path Classification and Fast-Track Determination",
        assigned_agent="it_security_agent",
        access_role="it_security",
        next_step=StepId.STEP_03,
    ),
    StepId.STEP_03: StepDefinition(
        step_id=StepId.STEP_03,
        label="Legal and Compliance Trigger Determination",
        assigned_agent="legal_agent",
        access_role="legal",
        next_step=StepId.STEP_04,
    ),
    StepId.STEP_04: StepDefinition(
        step_id=StepId.STEP_04,
        label="Approval Path Routing",
        assigned_agent="procurement_agent",
        access_role="procurement",
        next_step=StepId.STEP_05,
    ),
    StepId.STEP_05: StepDefinition(
        step_id=StepId.STEP_05,
        label="Approval Checklist Generation",
        assigned_agent="checklist_assembler",
        access_role="checklist_assembler",
        next_step=StepId.STEP_06,
    ),
    StepId.STEP_06: StepDefinition(
        step_id=StepId.STEP_06,
        label="Stakeholder Guidance and Checkoff Support",
        assigned_agent="checkoff_agent",
        access_role="checkoff",
        next_step=None,
    ),
}
