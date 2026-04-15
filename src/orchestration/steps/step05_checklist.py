"""STEP-05 Checklist Assembler step."""

from __future__ import annotations

from orchestration.models.contracts import GateDecision, RetrievalRequest, StepExecutionResult
from orchestration.models.enums import RetrievalLane, StepId, StepStatus
from orchestration.pipeline_state import PipelineState
from orchestration.steps.base import BaseStepHandler


class Step05ChecklistHandler(BaseStepHandler):
    def check_gate(self, state: PipelineState) -> GateDecision:
        required_steps = (StepId.STEP_01, StepId.STEP_02, StepId.STEP_03, StepId.STEP_04)
        if not all(state.step_statuses[step] in {StepStatus.COMPLETE, StepStatus.ESCALATED} for step in required_steps):
            return GateDecision(allowed=False, reason="STEP-01 through STEP-04 must be terminal", resolution_owner="Supervisor")
        return GateDecision(allowed=True)

    def execute(self, state: PipelineState) -> StepExecutionResult:
        retrievals = {
            "all_agent_outputs": self.router.route(
                RetrievalRequest(
                    request_id="R05-SQ-00",
                    lane=RetrievalLane.RUNTIME_READ,
                    source_id="PIPELINE_STATE",
                    access_role=self.definition.access_role,
                    output_name="all_agent_outputs",
                    runtime_target="pipeline_state",
                    field_map={
                        "it_security_agent": ("determinations.step_02_security_classification",),
                        "legal_agent": ("determinations.step_03_legal",),
                        "procurement_agent": ("determinations.step_04_procurement",),
                    },
                ),
                state=state,
            ),
            "audit_log": self.router.route(
                RetrievalRequest(
                    request_id="R05-SQ-01",
                    lane=RetrievalLane.RUNTIME_READ,
                    source_id="AUDIT_LOG",
                    access_role=self.definition.access_role,
                    output_name="audit_log",
                    runtime_target="audit_log",
                    field_map={"entries": ("entries",)},
                ),
                state=state,
            ),
            "pipeline_state": self.router.route(
                RetrievalRequest(
                    request_id="R05-SQ-02",
                    lane=RetrievalLane.RUNTIME_READ,
                    source_id="PIPELINE_STATE",
                    access_role=self.definition.access_role,
                    output_name="pipeline_state",
                    runtime_target="pipeline_state",
                    field_map={
                        "pipeline_run_id": ("pipeline_run_id",),
                        "vendor_name": ("vendor_name",),
                    },
                ),
                state=state,
            ),
        }

        present_fields = {
            key for key, value in retrievals["all_agent_outputs"].payload.items() if value is not None
        }
        validation = self.bundle_validator.validate(
            step_id=self.step_id.value,
            source_ids=["STEP-02", "STEP-03", "STEP-04", "AUDIT_LOG", "PIPELINE_STATE"],
            present_fields=present_fields,
            missing_fields=retrievals["all_agent_outputs"].missing_fields,
        )
        bundle = self.bundle_assembler.assemble_step05(
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
                output={"pipeline_run_id": state.pipeline_run_id, "vendor_name": state.vendor_name, "overall_status": "BLOCKED"},
                bundle=bundle,
                retrieval_results=retrievals,
                halt_reason="Invalid STEP-05 output",
            )
        overall_status = output["overall_status"]
        step_status = StepStatus[overall_status]
        return StepExecutionResult(
            step_id=self.step_id,
            step_status=step_status,
            output=output,
            bundle=bundle,
            retrieval_results=retrievals,
        )
