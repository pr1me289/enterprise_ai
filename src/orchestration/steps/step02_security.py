"""STEP-02 IT Security step."""

from __future__ import annotations

from orchestration.models.contracts import GateDecision, RetrievalRequest, StepExecutionResult
from orchestration.models.enums import RetrievalLane, StepId, StepStatus
from orchestration.models.escalation import EscalationPayload
from orchestration.pipeline_state import PipelineState
from orchestration.steps.base import BaseStepHandler


class Step02SecurityHandler(BaseStepHandler):
    def check_gate(self, state: PipelineState) -> GateDecision:
        if state.step_statuses[StepId.STEP_01] is not StepStatus.COMPLETE:
            return GateDecision(allowed=False, reason="STEP-01 must be COMPLETE", resolution_owner="Procurement")
        return GateDecision(allowed=True)

    def execute(self, state: PipelineState) -> StepExecutionResult:
        retrievals = {
            "integration_inputs": self.router.route(
                RetrievalRequest(
                    request_id="R02-SQ-01",
                    lane=RetrievalLane.DIRECT_STRUCTURED,
                    source_id="VQ-OC-001",
                    access_role=self.definition.access_role,
                    output_name="integration_inputs",
                    field_map={
                        "integration_details.erp_type": ("product_and_integration.erp_integration.erp_type",),
                        "integration_details.erp_system": ("product_and_integration.erp_integration.erp_system",),
                        "integration_details.integration_description": ("product_and_integration.erp_integration.integration_description",),
                    },
                ),
                state=state,
            ),
            "classification_inputs": self.router.route(
                RetrievalRequest(
                    request_id="R02-SQ-02",
                    lane=RetrievalLane.DIRECT_STRUCTURED,
                    source_id="VQ-OC-001",
                    access_role=self.definition.access_role,
                    output_name="classification_inputs",
                    field_map={
                        "data_classification_self_reported": ("data_handling.personal_data_in_scope",),
                        "regulated_data_types": ("data_handling.data_categories_in_scope",),
                    },
                ),
                state=state,
            ),
            "eu_inputs": self.router.route(
                RetrievalRequest(
                    request_id="R02-SQ-03",
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
            "erp_tier_policy_chunks": self.router.route(
                RetrievalRequest(
                    request_id="R02-SQ-04",
                    lane=RetrievalLane.INDEXED_HYBRID,
                    source_id="ISP-001",
                    access_role=self.definition.access_role,
                    output_name="erp_tier_policy_chunks",
                    search_terms=("ERP integration tier", "12.2", "integration classification", "tier"),
                ),
                state=state,
            ),
            "classification_policy_chunks": self.router.route(
                RetrievalRequest(
                    request_id="R02-SQ-05",
                    lane=RetrievalLane.INDEXED_HYBRID,
                    source_id="ISP-001",
                    access_role=self.definition.access_role,
                    output_name="classification_policy_chunks",
                    search_terms=("regulated data", "data classification", "third-party access", "12"),
                ),
                state=state,
            ),
            "fast_track_policy_chunks": self.router.route(
                RetrievalRequest(
                    request_id="R02-SQ-06",
                    lane=RetrievalLane.INDEXED_HYBRID,
                    source_id="ISP-001",
                    access_role=self.definition.access_role,
                    output_name="fast_track_policy_chunks",
                    search_terms=("fast track", "manual review", "regulated data", "third-party risk"),
                ),
                state=state,
            ),
            "nda_inputs": self.router.route(
                RetrievalRequest(
                    request_id="R02-SQ-07A",
                    lane=RetrievalLane.DIRECT_STRUCTURED,
                    source_id="VQ-OC-001",
                    access_role=self.definition.access_role,
                    output_name="nda_inputs",
                    field_map={"existing_nda_status": ("legal_and_contractual_status.existing_nda_status",)},
                ),
                state=state,
            ),
            "nda_policy_chunks": self.router.route(
                RetrievalRequest(
                    request_id="R02-SQ-07",
                    lane=RetrievalLane.INDEXED_HYBRID,
                    source_id="ISP-001",
                    access_role=self.definition.access_role,
                    output_name="nda_policy_chunks",
                    search_terms=("NDA", "12.1.4", "information exchange", "non-disclosure"),
                ),
                state=state,
            ),
        }

        present_fields = {
            *retrievals["integration_inputs"].payload.keys(),
            *retrievals["classification_inputs"].payload.keys(),
            *retrievals["eu_inputs"].payload.keys(),
            *retrievals["nda_inputs"].payload.keys(),
        }
        missing_fields = [
            *retrievals["integration_inputs"].missing_fields,
            *retrievals["classification_inputs"].missing_fields,
            *retrievals["eu_inputs"].missing_fields,
            *retrievals["nda_inputs"].missing_fields,
        ]
        validation = self.bundle_validator.validate(
            step_id=self.step_id.value,
            source_ids=["VQ-OC-001", "ISP-001"],
            present_fields=present_fields,
            missing_fields=missing_fields,
        )
        bundle = self.bundle_assembler.assemble_step02(
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
                halt_reason="Invalid STEP-02 output",
            )
        agent_status = output["status"]
        escalation_payload = None
        if agent_status == "escalated":
            escalation_payload = EscalationPayload(
                evidence_condition="Security classification requires review before downstream execution.",
                resolution_owner="IT Security",
            )
        return StepExecutionResult(
            step_id=self.step_id,
            step_status=self._step_status_from_agent_status(agent_status),
            output=output,
            bundle=bundle,
            retrieval_results=retrievals,
            agent_status=agent_status,
            escalation_payload=escalation_payload,
        )
