"""Minimal structured-output validation for step results."""

from __future__ import annotations

from orchestration.models.contracts import OutputValidationResult


REQUIRED_OUTPUT_FIELDS = {
    "STEP-02": {
        "integration_type_normalized",
        "integration_tier",
        "data_classification",
        "eu_personal_data_present",
        "fast_track_eligible",
        "fast_track_rationale",
        "security_followup_required",
        "nda_status_from_questionnaire",
        "required_security_actions",
        "policy_citations",
        "status",
    },
    "STEP-03": {
        "dpa_required",
        "dpa_blocker",
        "nda_status",
        "nda_blocker",
        "trigger_rule_cited",
        "policy_citations",
        "status",
    },
    "STEP-04": {
        "fast_track_eligible",
        "required_approvals",
        "estimated_timeline",
        "policy_citations",
        "status",
    },
    "STEP-05": {
        "pipeline_run_id",
        "vendor_name",
        "overall_status",
    },
    "STEP-06": {
        "status",
    },
}

LOWERCASE_STATUS_STEPS = {"STEP-02", "STEP-03", "STEP-04", "STEP-06"}


class OutputValidator:
    def validate(self, *, step_id: str, output: dict | None) -> OutputValidationResult:
        if output is None:
            return OutputValidationResult(valid=False, errors=["missing output"])

        required_fields = REQUIRED_OUTPUT_FIELDS.get(step_id, set())
        missing = [field for field in required_fields if field not in output]
        errors = list(missing)
        if step_id in LOWERCASE_STATUS_STEPS:
            status = output.get("status")
            if status not in {"complete", "escalated", "blocked"}:
                errors.append(f"invalid status: {status}")
        if step_id == "STEP-05":
            status = output.get("overall_status")
            if status not in {"COMPLETE", "ESCALATED", "BLOCKED"}:
                errors.append(f"invalid overall_status: {status}")
        return OutputValidationResult(valid=not errors, errors=errors)
