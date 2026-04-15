"""STEP-04 Procurement step."""

from __future__ import annotations

from orchestration.models.contracts import GateDecision, RetrievalRequest, StepExecutionResult
from orchestration.models.enums import RetrievalLane, StepId, StepStatus
from orchestration.models.escalation import EscalationPayload
from orchestration.pipeline_state import PipelineState
from orchestration.steps.base import BaseStepHandler


class Step04ProcurementHandler(BaseStepHandler):
    def check_gate(self, state: PipelineState) -> GateDecision:
        step03_status = state.step_statuses[StepId.STEP_03]
        if step03_status not in {StepStatus.COMPLETE, StepStatus.ESCALATED}:
            return GateDecision(allowed=False, reason="STEP-03 must be terminal", resolution_owner="Legal")
        if not state.determinations["step_03_legal"]:
            return GateDecision(allowed=False, reason="STEP-03 output missing", resolution_owner="Legal")
        return GateDecision(allowed=True)

    def execute(self, state: PipelineState) -> StepExecutionResult:
        retrievals = {
            "it_security_output": self.router.route(
                RetrievalRequest(
                    request_id="R04-SQ-01",
                    lane=RetrievalLane.RUNTIME_READ,
                    source_id="STEP-02",
                    access_role=self.definition.access_role,
                    output_name="it_security_output",
                    runtime_target="determination:step_02_security_classification",
                    field_map={
                        "data_classification": ("data_classification",),
                        "fast_track_eligible": ("fast_track_eligible",),
                        "integration_tier": ("integration_tier",),
                        "security_followup_required": ("security_followup_required",),
                        "policy_citations": ("policy_citations",),
                        "status": ("status",),
                    },
                ),
                state=state,
            ),
            "legal_output": self.router.route(
                RetrievalRequest(
                    request_id="R04-SQ-02",
                    lane=RetrievalLane.RUNTIME_READ,
                    source_id="STEP-03",
                    access_role=self.definition.access_role,
                    output_name="legal_output",
                    runtime_target="determination:step_03_legal",
                    field_map={
                        "dpa_required": ("dpa_required",),
                        "dpa_blocker": ("dpa_blocker",),
                        "nda_status": ("nda_status",),
                        "nda_blocker": ("nda_blocker",),
                        "trigger_rule_cited": ("trigger_rule_cited",),
                        "policy_citations": ("policy_citations",),
                        "status": ("status",),
                    },
                ),
                state=state,
            ),
            "vendor_relationship": self.router.route(
                RetrievalRequest(
                    request_id="R04-SQ-03",
                    lane=RetrievalLane.DIRECT_STRUCTURED,
                    source_id="VQ-OC-001",
                    access_role=self.definition.access_role,
                    output_name="vendor_relationship",
                    field_map={
                        "vendor_class": ("contract_details.vendor_class_assigned",),
                        "deal_size": ("contract_details.annual_contract_value_usd",),
                        "existing_nda_status": ("legal_and_contractual_status.existing_nda_status",),
                        "existing_msa": ("legal_and_contractual_status.existing_msa",),
                    },
                ),
                state=state,
            ),
            "approval_matrix_rows": self.router.route(
                RetrievalRequest(
                    request_id="R04-SQ-04",
                    lane=RetrievalLane.INDEXED_HYBRID,
                    source_id="PAM-001",
                    access_role=self.definition.access_role,
                    output_name="approval_matrix_rows",
                    search_terms=("approval", "authority", "vendor class", "integration tier"),
                ),
                state=state,
            ),
            "fast_track_rows": self.router.route(
                RetrievalRequest(
                    request_id="R04-SQ-05",
                    lane=RetrievalLane.INDEXED_HYBRID,
                    source_id="PAM-001",
                    access_role=self.definition.access_role,
                    output_name="fast_track_rows",
                    search_terms=("fast track", "routing", "eligible", "unregulated"),
                ),
                state=state,
            ),
            "slack_procurement": self.router.route(
                RetrievalRequest(
                    request_id="R04-SQ-07",
                    lane=RetrievalLane.INDEXED_HYBRID,
                    source_id="SLK-001",
                    access_role=self.definition.access_role,
                    output_name="slack_procurement",
                    search_terms=("OptiChain", "vendor approval", "procurement", "onboarding"),
                ),
                state=state,
            ),
        }

        present_fields = {
            *retrievals["it_security_output"].payload.keys(),
            *retrievals["legal_output"].payload.keys(),
            *retrievals["vendor_relationship"].payload.keys(),
        }
        missing_fields = [
            *retrievals["it_security_output"].missing_fields,
            *retrievals["legal_output"].missing_fields,
            *retrievals["vendor_relationship"].missing_fields,
        ]
        validation = self.bundle_validator.validate(
            step_id=self.step_id.value,
            source_ids=["STEP-02", "STEP-03", "VQ-OC-001", "PAM-001", "SLK-001"],
            present_fields=present_fields,
            missing_fields=missing_fields,
        )
        bundle = self.bundle_assembler.assemble_step04(
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
                halt_reason="Invalid STEP-04 output",
            )
        escalation_payload = None
        if output["status"] == "escalated":
            escalation_payload = EscalationPayload(
                evidence_condition="Procurement routing inherited an unresolved constraint or lacked a matrix match.",
                resolution_owner="Procurement Director",
            )
        return StepExecutionResult(
            step_id=self.step_id,
            step_status=self._step_status_from_agent_status(output["status"]),
            output=output,
            bundle=bundle,
            retrieval_results=retrievals,
            agent_status=output["status"],
            escalation_payload=escalation_payload,
        )
