"""STEP-03 Legal step."""

from __future__ import annotations

from orchestration.models.contracts import GateDecision, RetrievalRequest, StepExecutionResult
from orchestration.models.enums import RetrievalLane, StepId, StepStatus
from orchestration.pipeline_state import PipelineState
from orchestration.steps.base import BaseStepHandler


class Step03LegalHandler(BaseStepHandler):
    def check_gate(self, state: PipelineState) -> GateDecision:
        if state.step_statuses[StepId.STEP_02] is not StepStatus.COMPLETE:
            return GateDecision(allowed=False, reason="STEP-02 must be COMPLETE", resolution_owner="IT Security")
        return GateDecision(allowed=True)

    def execute(self, state: PipelineState) -> StepExecutionResult:
        retrievals = {
            "upstream_security": self.router.route(
                RetrievalRequest(
                    request_id="R03-SQ-01",
                    lane=RetrievalLane.RUNTIME_READ,
                    source_id="STEP-02",
                    access_role=self.definition.access_role,
                    output_name="upstream_security",
                    runtime_target="determination:step_02_security_classification",
                    field_map={
                        "upstream_data_classification": ("data_classification",),
                        "status": ("status",),
                        "policy_citations": ("policy_citations",),
                    },
                ),
                state=state,
            ),
            "eu_inputs": self.router.route(
                RetrievalRequest(
                    request_id="R03-SQ-02",
                    lane=RetrievalLane.DIRECT_STRUCTURED,
                    source_id="VQ-OC-001",
                    access_role=self.definition.access_role,
                    output_name="eu_inputs",
                    field_map={
                        "eu_personal_data_flag": ("data_handling.data_subjects.eu_personal_data_flag",),
                        "data_subjects_eu": ("data_handling.data_subjects.data_subjects_eu",),
                    },
                ),
                state=state,
            ),
            "nda_inputs": self.router.route(
                RetrievalRequest(
                    request_id="R03-SQ-03",
                    lane=RetrievalLane.DIRECT_STRUCTURED,
                    source_id="VQ-OC-001",
                    access_role=self.definition.access_role,
                    output_name="nda_inputs",
                    field_map={"existing_nda_status": ("legal_and_contractual_status.existing_nda_status",)},
                ),
                state=state,
            ),
            "dpa_status": self.router.route(
                RetrievalRequest(
                    request_id="R03-SQ-03B",
                    lane=RetrievalLane.DIRECT_STRUCTURED,
                    source_id="VQ-OC-001",
                    access_role=self.definition.access_role,
                    output_name="dpa_status",
                    field_map={"dpa_status_raw": ("legal_and_contractual_status.dpa_status",)},
                ),
                state=state,
            ),
            "dpa_trigger_rows": self.router.route(
                RetrievalRequest(
                    request_id="R03-SQ-04",
                    lane=RetrievalLane.INDEXED_HYBRID,
                    source_id="DPA-TM-001",
                    access_role=self.definition.access_role,
                    output_name="dpa_trigger_rows",
                    search_terms=("EU personal data", "GDPR", "Art. 28", "employee data"),
                ),
                state=state,
            ),
            "nda_clause_chunks": self.router.route(
                RetrievalRequest(
                    request_id="R03-SQ-06",
                    lane=RetrievalLane.INDEXED_HYBRID,
                    source_id="ISP-001",
                    access_role=self.definition.access_role,
                    output_name="nda_clause_chunks",
                    search_terms=("NDA", "12.1.4", "information exchange", "non-disclosure"),
                ),
                state=state,
            ),
        }

        present_fields = {
            *retrievals["upstream_security"].payload.keys(),
            *retrievals["eu_inputs"].payload.keys(),
            *retrievals["nda_inputs"].payload.keys(),
            *retrievals["dpa_status"].payload.keys(),
        }
        missing_fields = [
            *retrievals["upstream_security"].missing_fields,
            *retrievals["eu_inputs"].missing_fields,
            *retrievals["nda_inputs"].missing_fields,
            *retrievals["dpa_status"].missing_fields,
        ]
        validation = self.bundle_validator.validate(
            step_id=self.step_id.value,
            source_ids=["STEP-02", "VQ-OC-001", "DPA-TM-001", "ISP-001"],
            present_fields=present_fields,
            missing_fields=missing_fields,
        )
        bundle = self.bundle_assembler.assemble_step03(
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
                output={"status": "blocked", "errors": validated.errors},
                bundle=bundle,
                retrieval_results=retrievals,
                halt_reason="Invalid STEP-03 output",
            )
        escalation_payload = None
        if output["status"] == "escalated":
            escalation_payload = {
                "evidence_condition": "Legal blocker or missing citation evidence requires human action.",
                "resolution_owner": "Legal (General Counsel)",
            }
        return StepExecutionResult(
            step_id=self.step_id,
            step_status=self._step_status_from_agent_status(output["status"]),
            output=output,
            bundle=bundle,
            retrieval_results=retrievals,
            agent_status=output["status"],
            escalation_payload=escalation_payload,
        )
