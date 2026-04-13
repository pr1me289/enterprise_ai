"""Runnable first-pass orchestration demo."""

from __future__ import annotations

import json
from pathlib import Path

from orchestration.supervisor import Supervisor


def run_demo() -> dict:
    repo_root = Path(__file__).resolve().parents[2]
    supervisor = Supervisor(
        repo_root=repo_root,
        questionnaire_path=repo_root / "mock_documents" / "OptiChain_VSQ_001_v2_1.json",
        questionnaire_overrides={
            "product_and_integration": {
                "erp_integration": {
                    "erp_type": "EXPORT_ONLY",
                    "integration_description": "Scheduled export-only transfer over SFTP. No service account and no persistent ERP session.",
                }
            },
            "data_handling": {
                "personal_data_in_scope": False,
                "data_categories_in_scope": ["Inventory position exports", "Demand forecast outputs"],
                "data_subjects": {
                    "eu_personal_data_flag": False,
                    "data_subjects_eu": False,
                },
            },
            "legal_and_contractual_status": {
                "existing_nda_status": "EXECUTED",
                "dpa_status": "EXECUTED",
                "dpa_required": False,
            },
        },
    )
    state = supervisor.run()
    return {
        "pipeline_run_id": state.pipeline_run_id,
        "overall_status": state.overall_status.value,
        "step_statuses": {step.value: status.value for step, status in state.step_statuses.items()},
        "final_output": state.determinations["step_06_guidance"] or state.determinations["step_05_checklist"],
        "audit_entry_count": len(supervisor.audit_logger.entries),
    }


if __name__ == "__main__":
    print(json.dumps(run_demo(), indent=2, sort_keys=True))
