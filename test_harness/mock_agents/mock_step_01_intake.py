"""Mock STEP-01 intake agent.

Validates the questionnaire bundle and returns a deterministic
Step01IntakeDetermination-shaped dict.

For scenario_blocked_missing_questionnaire the questionnaire structured
fields will be absent, so the agent returns BLOCKED.
"""

from __future__ import annotations

from typing import Any

from orchestration.models.context_bundle import ContextBundle
from orchestration.models.escalation import EscalationPayload


def run(
    bundle: ContextBundle,
    scenario_name: str,
) -> tuple[dict[str, Any], str, EscalationPayload | None]:
    """Execute mock STEP-01 intake validation.

    Returns:
        (output_dict, step_status_str, escalation_payload_or_none)
    """
    # STEP-01 uses direct structured retrieval — the structured_fields
    # dict is used by the actual Step01IntakeHandler before mock agent
    # involvement.  Our mock agent re-validates based on what would have
    # been populated.  In the harness we call the real step handler, so
    # this mock is only invoked by the result_assertions tests directly.

    sf = bundle.structured_fields

    vendor_name: str = sf.get("vendor_name") or ""

    if scenario_name == "scenario_blocked_missing_questionnaire":
        # Questionnaire absent — gate blocked
        return (
            {
                "questionnaire_valid": False,
                "vendor_name": "",
                "status": "BLOCKED",
                "notes": ["Questionnaire document VQ-OC-001 could not be retrieved."],
            },
            "BLOCKED",
            None,
        )

    # For all other scenarios validate that vendor_name is present
    if not vendor_name:
        raise ValueError(
            "STEP-01 mock agent: malformed bundle — 'vendor_name' missing from "
            f"structured_fields. Keys present: {list(sf.keys())!r}"
        )

    return (
        {
            "questionnaire_valid": True,
            "vendor_name": vendor_name,
            "status": "COMPLETE",
            "notes": [],
        },
        "COMPLETE",
        None,
    )
