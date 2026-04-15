"""Bundle admissibility and contamination checks."""

from __future__ import annotations

from orchestration.models.contracts import BundleValidationResult


ALLOWED_SOURCES = {
    "STEP-02": {"VQ-OC-001", "ISP-001"},
    "STEP-03": {"STEP-02", "VQ-OC-001", "DPA-TM-001", "ISP-001"},
    "STEP-04": {"STEP-02", "STEP-03", "VQ-OC-001", "PAM-001", "SLK-001"},
    "STEP-05": {"STEP-02", "STEP-03", "STEP-04", "AUDIT_LOG", "PIPELINE_STATE"},
    "STEP-06": {
        "STEP-05",
        "PIPELINE_CONFIG",
        "PIPELINE_STATE",
        "STEP-02",
        "STEP-03",
        "STEP-04",
    },
}

REQUIRED_FIELDS = {
    "STEP-02": {
        "integration_details.erp_type",
        "data_classification_self_reported",
        "regulated_data_types",
        "eu_personal_data_flag",
        "data_subjects_eu",
        "existing_nda_status",
    },
    "STEP-03": {
        "upstream_data_classification",
        "eu_personal_data_flag",
        "data_subjects_eu",
        "existing_nda_status",
    },
    "STEP-04": {
        "data_classification",
        "fast_track_eligible",
        "integration_tier",
        "dpa_required",
        "dpa_blocker",
        "nda_status",
        "nda_blocker",
        "vendor_class",
        "deal_size",
    },
    "STEP-05": {
        "it_security_agent",
        "legal_agent",
        "procurement_agent",
    },
    "STEP-06": {
        "finalized_checklist",
        "stakeholder_map",
    },
}


class BundleValidator:
    def validate(self, *, step_id: str, source_ids: list[str], present_fields: set[str], missing_fields: list[str]) -> BundleValidationResult:
        prohibited_sources = sorted(set(source_ids) - ALLOWED_SOURCES.get(step_id, set()))
        required = REQUIRED_FIELDS.get(step_id, set())
        missing_required = sorted(set(missing_fields) | (required - present_fields))
        # Prohibited sources indicate an authority-governance violation: the bundle
        # cannot be used until the prohibited source is removed or the step's allowed
        # sources are updated.  This requires escalation rather than a simple partial
        # status.
        escalation_required = bool(prohibited_sources)
        admissible = not prohibited_sources and not missing_required
        return BundleValidationResult(
            admissible=admissible,
            missing_fields=missing_required,
            prohibited_sources=prohibited_sources,
            escalation_required=escalation_required,
        )
