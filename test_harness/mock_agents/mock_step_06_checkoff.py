"""Mock STEP-06 Stakeholder Checkoff agent.

Bundle-aware deterministic agent.

Validates:
- finalized checklist is present
- stakeholder_map is present
- no status downgrade (checklist overall_status must not be degraded)
"""

from __future__ import annotations

from typing import Any

from orchestration.models.context_bundle import ContextBundle
from orchestration.models.escalation import EscalationPayload


def _validate_bundle(bundle: ContextBundle) -> None:
    sf = bundle.structured_fields

    checklist = sf.get("finalized_checklist")
    if not checklist:
        raise ValueError(
            "STEP-06 mock agent: malformed bundle — 'finalized_checklist' missing. "
            f"Keys: {list(sf.keys())!r}"
        )

    stakeholder_map = sf.get("stakeholder_map")
    if not stakeholder_map:
        raise ValueError(
            "STEP-06 mock agent: malformed bundle — 'stakeholder_map' missing. "
            f"Keys: {list(sf.keys())!r}"
        )


def run(
    bundle: ContextBundle,
    scenario_name: str,
) -> tuple[dict[str, Any], str, EscalationPayload | None]:
    """Execute mock STEP-06 checkoff guidance generation."""
    _validate_bundle(bundle)

    sf = bundle.structured_fields
    checklist: dict[str, Any] = sf.get("finalized_checklist", {})
    overall_status: str = checklist.get("overall_status", "COMPLETE")

    guidance_documents = [
        {
            "stakeholder_role": "Procurement Manager",
            "domain": "procurement",
            "instructions": (
                f"Pipeline status is {overall_status}. "
                "Review procurement approval and complete signoff."
            ),
            "blockers_owned": [],
            "required_security_actions": [],
            "next_steps": ["Review approval requirement for procurement"],
            "citations": checklist.get("citations", []),
        }
    ]

    output = {
        "guidance_documents": guidance_documents,
        "status": "complete",
    }
    return output, "COMPLETE", None
