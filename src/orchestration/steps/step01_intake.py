"""STEP-01 intake validation."""

from __future__ import annotations

from orchestration.models.contracts import GateDecision, RetrievalRequest, StepExecutionResult
from orchestration.models.enums import RetrievalLane, StepStatus
from orchestration.pipeline_state import PipelineState
from orchestration.steps.base import BaseStepHandler


class Step01IntakeHandler(BaseStepHandler):
    def check_gate(self, state: PipelineState) -> GateDecision:
        del state
        return GateDecision(allowed=True)

    def execute(self, state: PipelineState) -> StepExecutionResult:
        existence = self.router.route(
            RetrievalRequest(
                request_id="R01-SQ-01",
                lane=RetrievalLane.DIRECT_STRUCTURED,
                source_id="VQ-OC-001",
                access_role=self.definition.access_role,
                output_name="questionnaire_exists",
                field_map={
                    "document_id": ("document_id",),
                    "submission_date": ("submission_date",),
                    "vendor_name": ("vendor_profile.vendor_legal_name",),
                },
            ),
            state=state,
        )
        completeness = self.router.route(
            RetrievalRequest(
                request_id="R01-SQ-02",
                lane=RetrievalLane.DIRECT_STRUCTURED,
                source_id="VQ-OC-001",
                access_role=self.definition.access_role,
                output_name="questionnaire_complete",
                field_map={
                    "vendor_name": ("vendor_profile.vendor_legal_name",),
                    "integration_details.erp_type": ("product_and_integration.erp_integration.erp_type",),
                    "data_classification_self_reported": ("data_handling.personal_data_in_scope",),
                    "regulated_data_types": ("data_handling.data_categories_in_scope",),
                    "eu_personal_data_flag": ("data_handling.data_subjects.eu_personal_data_flag",),
                    "data_subjects_eu": ("data_handling.data_subjects.data_subjects_eu",),
                    "existing_nda_status": ("legal_and_contractual_status.existing_nda_status",),
                    "existing_msa": ("legal_and_contractual_status.existing_msa",),
                    "vendor_class": ("contract_details.vendor_class_assigned",),
                    "contract_value_annual": ("contract_details.annual_contract_value_usd",),
                },
            ),
            state=state,
        )
        version_check = self.router.route(
            RetrievalRequest(
                request_id="R01-SQ-03",
                lane=RetrievalLane.DIRECT_STRUCTURED,
                source_id="VQ-OC-001",
                access_role=self.definition.access_role,
                output_name="version_conflict_detected",
                field_map={
                    "document_id": ("document_id",),
                    "submission_version": ("version",),
                },
            ),
            state=state,
        )

        questionnaire_exists = not existence.missing_fields
        missing_fields = list(completeness.missing_fields)
        version_conflict_detected = False
        output = {
            "questionnaire_exists": questionnaire_exists,
            "questionnaire_complete": not missing_fields,
            "version_conflict_detected": version_conflict_detected,
            "missing_fields": missing_fields,
        }
        state.vendor_name = existence.payload.get("vendor_name")

        if not questionnaire_exists:
            step_status = StepStatus.BLOCKED
        elif missing_fields:
            step_status = StepStatus.BLOCKED
        elif version_conflict_detected:
            step_status = StepStatus.BLOCKED
        else:
            step_status = StepStatus.COMPLETE

        return StepExecutionResult(
            step_id=self.step_id,
            step_status=step_status,
            output=output,
            retrieval_results={
                "existence": existence,
                "completeness": completeness,
                "version_check": version_check,
            },
            halt_reason="Missing questionnaire fields" if step_status is StepStatus.BLOCKED else None,
        )
