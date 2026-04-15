"""Required-field presence check for each agent output contract.

Per the LLM call layer spec: on failure, log the missing fields but
still return whatever the model produced. The validator does not mutate
or discard the output; it only reports which required fields are
missing or null so callers can log them.
"""

from __future__ import annotations

from typing import Any

# Required fields come from each agent's spec output contract and match
# the orchestration layer's OutputValidator. Kept in sync intentionally
# so the call-layer check mirrors the downstream gate.
REQUIRED_FIELDS: dict[str, tuple[str, ...]] = {
    "it_security_agent": (
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
    ),
    "legal_agent": (
        "dpa_required",
        "dpa_blocker",
        "nda_status",
        "nda_blocker",
        "trigger_rule_cited",
        "policy_citations",
        "status",
    ),
    "procurement_agent": (
        "fast_track_eligible",
        "required_approvals",
        "estimated_timeline",
        "policy_citations",
        "status",
    ),
    "checklist_assembler": (
        "pipeline_run_id",
        "vendor_name",
        "overall_status",
    ),
    "checkoff_agent": (
        "status",
    ),
}


def find_missing_fields(agent_name: str, output: dict[str, Any] | None) -> list[str]:
    """Return the list of required fields that are absent or null.

    Never raises. An unknown agent name returns an empty list so a
    future addition does not break the pipeline until the contract is
    registered here.
    """
    if output is None:
        return list(REQUIRED_FIELDS.get(agent_name, ()))
    required = REQUIRED_FIELDS.get(agent_name, ())
    return [field for field in required if output.get(field) is None]
