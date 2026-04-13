"""Per-step bundle assembly helpers."""

from __future__ import annotations

from typing import Any

from orchestration.models.contracts import RetrievalResult


class BundleAssembler:
    """Build narrowly scoped bundles for each step from routed evidence."""

    def assemble_step02(
        self,
        retrievals: dict[str, RetrievalResult],
        validation: dict[str, Any],
    ) -> dict[str, Any]:
        questionnaire = {}
        for key in ("integration_inputs", "classification_inputs", "eu_inputs", "nda_inputs"):
            questionnaire.update(retrievals[key].payload)
        return {
            "step_id": "STEP-02",
            "source_ids": ["VQ-OC-001", "ISP-001"],
            "questionnaire": questionnaire,
            "policy_chunks": {
                "erp_tier_policy_chunks": retrievals["erp_tier_policy_chunks"].payload,
                "classification_policy_chunks": retrievals["classification_policy_chunks"].payload,
                "fast_track_policy_chunks": retrievals["fast_track_policy_chunks"].payload,
                "nda_policy_chunks": retrievals["nda_policy_chunks"].payload,
            },
            "bundle_meta": validation,
        }

    def assemble_step03(
        self,
        retrievals: dict[str, RetrievalResult],
        validation: dict[str, Any],
    ) -> dict[str, Any]:
        return {
            "step_id": "STEP-03",
            "source_ids": ["STEP-02", "VQ-OC-001", "DPA-TM-001", "ISP-001"],
            "security_output": {
                "data_classification": retrievals["upstream_security"].payload.get("upstream_data_classification"),
                "status": retrievals["upstream_security"].payload.get("status"),
                "policy_citations": retrievals["upstream_security"].payload.get("policy_citations", []),
            },
            "questionnaire": {
                **retrievals["eu_inputs"].payload,
                **retrievals["nda_inputs"].payload,
                **retrievals["dpa_status"].payload,
            },
            "dpa_trigger_rows": retrievals["dpa_trigger_rows"].payload,
            "nda_clause_chunks": retrievals["nda_clause_chunks"].payload,
            "bundle_meta": validation,
        }

    def assemble_step04(
        self,
        retrievals: dict[str, RetrievalResult],
        validation: dict[str, Any],
    ) -> dict[str, Any]:
        return {
            "step_id": "STEP-04",
            "source_ids": ["STEP-02", "STEP-03", "VQ-OC-001", "PAM-001", "SLK-001"],
            "it_security_output": retrievals["it_security_output"].payload,
            "legal_output": retrievals["legal_output"].payload,
            "questionnaire": retrievals["vendor_relationship"].payload,
            "approval_path_matrix_rows": retrievals["approval_matrix_rows"].payload,
            "fast_track_routing_rows": retrievals["fast_track_rows"].payload,
            "slack_procurement_chunks": retrievals["slack_procurement"].payload,
            "bundle_meta": validation,
        }

    def assemble_step05(
        self,
        retrievals: dict[str, RetrievalResult],
        validation: dict[str, Any],
    ) -> dict[str, Any]:
        domain_outputs = retrievals["all_agent_outputs"].payload
        return {
            "step_id": "STEP-05",
            "source_ids": ["STEP-02", "STEP-03", "STEP-04", "AUDIT_LOG", "VQ-OC-001"],
            "pipeline_run_id": retrievals["pipeline_state"].payload.get("pipeline_run_id"),
            "vendor_name": retrievals["questionnaire_header"].payload.get("vendor_name"),
            "it_security_agent": domain_outputs.get("it_security_agent"),
            "legal_agent": domain_outputs.get("legal_agent"),
            "procurement_agent": domain_outputs.get("procurement_agent"),
            "audit_log_entries": retrievals["audit_log"].payload.get("entries", []),
            "bundle_meta": validation,
        }

    def assemble_step06(
        self,
        retrievals: dict[str, RetrievalResult],
        validation: dict[str, Any],
    ) -> dict[str, Any]:
        return {
            "step_id": "STEP-06",
            "source_ids": ["STEP-05", "PIPELINE_CONFIG", "STEP-02", "STEP-03", "STEP-04"],
            "finalized_checklist": retrievals["finalized_checklist"].payload,
            "stakeholder_map": retrievals["stakeholder_map"].payload,
            "domain_outputs": retrievals["domain_outputs"].payload,
            "bundle_meta": validation,
        }
