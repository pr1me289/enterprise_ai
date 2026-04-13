"""Mock STEP-05 Checklist Assembler agent.

Bundle-aware deterministic agent.

Validates:
- upstream security, legal, and procurement agent outputs are all present
- pipeline_run_id and vendor_name are present
"""

from __future__ import annotations

from typing import Any

from orchestration.models.context_bundle import ContextBundle
from orchestration.models.escalation import EscalationPayload


def _validate_bundle(bundle: ContextBundle) -> None:
    sf = bundle.structured_fields

    for required_key in ("it_security_agent", "legal_agent", "procurement_agent"):
        if not sf.get(required_key):
            raise ValueError(
                f"STEP-05 mock agent: malformed bundle — '{required_key}' missing "
                f"from structured_fields. Keys: {list(sf.keys())!r}"
            )

    if not sf.get("pipeline_run_id"):
        raise ValueError(
            "STEP-05 mock agent: malformed bundle — 'pipeline_run_id' missing."
        )


def run(
    bundle: ContextBundle,
    scenario_name: str,
) -> tuple[dict[str, Any], str, EscalationPayload | None]:
    """Execute mock STEP-05 Checklist assembly."""
    _validate_bundle(bundle)

    sf = bundle.structured_fields
    pipeline_run_id: str = sf.get("pipeline_run_id", "")
    vendor_name: str = sf.get("vendor_name", "")

    output = {
        "pipeline_run_id": pipeline_run_id,
        "vendor_name": vendor_name,
        "overall_status": "COMPLETE",
        "data_classification": "UNREGULATED",
        "dpa_required": False,
        "fast_track_eligible": True,
        "required_security_actions": [],
        "approval_path": "FAST_TRACK",
        "required_approvals": [
            {
                "approver": "Procurement Manager",
                "domain": "procurement",
                "status": "PENDING",
                "blocker": False,
                "estimated_completion": "2 business days",
            }
        ],
        "blockers": [],
        "citations": [],
    }
    return output, "COMPLETE", None
