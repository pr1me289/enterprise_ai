"""STEP-06 Checkoff step."""

from __future__ import annotations

from orchestration.models.contracts import GateDecision, RetrievalRequest, StepExecutionResult
from orchestration.models.enums import RetrievalLane, StepId, StepStatus
from orchestration.pipeline_state import PipelineState
from orchestration.steps.base import BaseStepHandler


class Step06CheckoffHandler(BaseStepHandler):
    def check_gate(self, state: PipelineState) -> GateDecision:
        if state.step_statuses[StepId.STEP_05] is not StepStatus.COMPLETE:
            return GateDecision(allowed=False, reason="STEP-05 must be COMPLETE", resolution_owner="Checklist Assembler")
        return GateDecision(allowed=True)

    def execute(self, state: PipelineState) -> StepExecutionResult:
        retrievals = {
            "finalized_checklist": self.router.route(
                RetrievalRequest(
                    request_id="R06-SQ-01",
                    lane=RetrievalLane.RUNTIME_READ,
                    source_id="STEP-05",
                    access_role=self.definition.access_role,
                    output_name="finalized_checklist",
                    runtime_target="determination:step_05_checklist",
                    field_map={
                        "overall_status": ("overall_status",),
                        "blockers": ("blockers",),
                        "required_approvals": ("required_approvals",),
                        "required_security_actions": ("required_security_actions",),
                        "citations": ("citations",),
                        "data_classification": ("data_classification",),
                        "approval_path": ("approval_path",),
                    },
                ),
                state=state,
            ),
            "stakeholder_map": self.router.route(
                RetrievalRequest(
                    request_id="R06-SQ-02",
                    lane=RetrievalLane.RUNTIME_READ,
                    source_id="PIPELINE_CONFIG",
                    access_role=self.definition.access_role,
                    output_name="stakeholder_map",
                    runtime_target="pipeline_config",
                    field_map={
                        "stakeholder_map": ("stakeholder_map",),
                        "approver_contacts": ("approver_contacts",),
                        "escalation_owners": ("escalation_owners",),
                    },
                ),
                state=state,
            ),
            "domain_outputs": self.router.route(
                RetrievalRequest(
                    request_id="R06-SQ-03",
                    lane=RetrievalLane.RUNTIME_READ,
                    source_id="PIPELINE_STATE",
                    access_role=self.definition.access_role,
                    output_name="domain_outputs",
                    runtime_target="pipeline_state",
                    field_map={
                        "step_02": ("determinations.step_02_security_classification",),
                        "step_03": ("determinations.step_03_legal",),
                        "step_04": ("determinations.step_04_procurement",),
                    },
                ),
                state=state,
            ),
            "escalations": self.router.route(
                RetrievalRequest(
                    request_id="R06-SQ-04",
                    lane=RetrievalLane.RUNTIME_READ,
                    source_id="PIPELINE_STATE",
                    access_role=self.definition.access_role,
                    output_name="escalations",
                    runtime_target="pipeline_state",
                    field_map={"escalations": ("escalations",)},
                ),
                state=state,
            ),
        }

        present_fields = {
            "finalized_checklist",
            "stakeholder_map",
        }
        if retrievals["stakeholder_map"].payload.get("approver_contacts") is not None:
            present_fields.add("approver_contacts")
        if retrievals["stakeholder_map"].payload.get("escalation_owners") is not None:
            present_fields.add("escalation_owners")
        missing_fields = list(retrievals["finalized_checklist"].missing_fields)
        validation = self.bundle_validator.validate(
            step_id=self.step_id.value,
            source_ids=["STEP-05", "PIPELINE_CONFIG", "STEP-02", "STEP-03", "STEP-04"],
            present_fields=present_fields,
            missing_fields=missing_fields,
        )
        bundle = self.bundle_assembler.assemble_step06(
            retrievals,
            {
                "admissible": validation.admissible,
                "missing_fields": validation.missing_fields,
                "prohibited_sources": validation.prohibited_sources,
            },
        )
        output = self.agent_runner.run(
            agent_name=self.definition.assigned_agent,
            bundle=bundle,
            step_metadata={"step_id": self.step_id.value},
        )
        validated = self.output_validator.validate(step_id=self.step_id.value, output=output)
        if not validated.valid:
            return StepExecutionResult(
                step_id=self.step_id,
                step_status=StepStatus.BLOCKED,
                output={"status": "blocked"},
                bundle=bundle,
                retrieval_results=retrievals,
                halt_reason="Invalid STEP-06 output",
            )
        return StepExecutionResult(
            step_id=self.step_id,
            step_status=self._step_status_from_agent_status(output["status"]),
            output=output,
            bundle=bundle,
            retrieval_results=retrievals,
            agent_status=output["status"],
        )
