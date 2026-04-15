"""Mock STEP-02 IT Security agent.

Bundle-aware deterministic agent.

Validates:
- required structured fields from questionnaire exist
- ISP-001 policy chunks are present in admitted_evidence or structured_fields
- Slack (SLK-001) is NOT admitted as primary evidence
- Thread 4 Slack chunk is NOT admitted

Returns scenario-appropriate security determination.
"""

from __future__ import annotations

from typing import Any

from orchestration.models.context_bundle import ContextBundle
from orchestration.models.escalation import EscalationPayload

_REQUIRED_STRUCTURED_FIELDS = (
    "integration_details.erp_type",
    "eu_personal_data_flag",
    "existing_nda_status",
)

_COMPLETE_OUTPUT = {
    "integration_type_normalized": "EXPORT_ONLY",
    "integration_tier": "TIER_3",
    "data_classification": "UNREGULATED",
    "eu_personal_data_present": "NO",
    "fast_track_eligible": True,
    "fast_track_rationale": "ELIGIBLE_LOW_RISK",
    "security_followup_required": False,
    "nda_status_from_questionnaire": "EXECUTED",
    "required_security_actions": [],
    "policy_citations": [
        {
            "source_id": "ISP-001",
            "version": "4.2",
            "chunk_id": "ISP-001__section_12",
            "section_id": "12",
            "citation_class": "PRIMARY",
        }
    ],
    "status": "complete",
}

_ESCALATED_OUTPUT = {
    "integration_type_normalized": "AMBIGUOUS",
    "integration_tier": "UNCLASSIFIED_PENDING_REVIEW",
    "data_classification": "REGULATED",
    "eu_personal_data_present": "UNKNOWN",
    "fast_track_eligible": False,
    "fast_track_rationale": "DISALLOWED_AMBIGUOUS_SCOPE",
    "security_followup_required": True,
    "nda_status_from_questionnaire": "EXECUTED",
    "required_security_actions": [
        {
            "action_type": "SECURITY_REVIEW",
            "reason": "Integration scope ambiguous; manual review required.",
            "owner": "IT Security",
        }
    ],
    "policy_citations": [
        {
            "source_id": "ISP-001",
            "version": "4.2",
            "chunk_id": "ISP-001__section_12",
            "section_id": "12",
            "citation_class": "PRIMARY",
        }
    ],
    "status": "escalated",
}

_BLOCKED_OUTPUT = {
    "status": "blocked",
    "errors": ["Bundle violation: prohibited source detected in IT Security bundle."],
}


def _validate_bundle(bundle: ContextBundle) -> None:
    """Validate bundle invariants; raise ValueError if malformed."""
    sf = bundle.structured_fields

    # Verify admissibility
    if bundle.admissibility_status not in ("ADMISSIBLE", "PARTIAL"):
        raise ValueError(
            f"STEP-02 mock agent: bundle admissibility_status is "
            f"{bundle.admissibility_status!r}; expected ADMISSIBLE or PARTIAL."
        )

    # Validate required structured fields (nested under questionnaire key)
    questionnaire: dict[str, Any] = sf.get("questionnaire", {})
    missing = [f for f in _REQUIRED_STRUCTURED_FIELDS if f not in questionnaire]
    if missing:
        raise ValueError(
            f"STEP-02 mock agent: malformed bundle — required structured fields "
            f"missing from questionnaire: {missing!r}. Present: {list(questionnaire.keys())!r}"
        )

    # Validate Slack is not primary evidence
    for chunk in bundle.admitted_evidence:
        if chunk.source_id == "SLK-001" and chunk.is_primary_citable:
            raise ValueError(
                "STEP-02 mock agent: bundle violation — Slack chunk admitted as "
                f"primary evidence: chunk_id={chunk.chunk_id!r}"
            )

    # Validate Thread 4 is not admitted
    for chunk in bundle.admitted_evidence:
        if chunk.source_id == "SLK-001":
            thread_id = str(chunk.extra_metadata.get("thread_id", ""))
            if thread_id in ("T4", "4", "thread_4"):
                raise ValueError(
                    "STEP-02 mock agent: bundle violation — Slack Thread 4 chunk "
                    f"was admitted: chunk_id={chunk.chunk_id!r}"
                )


def run(
    bundle: ContextBundle,
    scenario_name: str,
    signal: str = "complete",
) -> tuple[dict[str, Any], str, EscalationPayload | None]:
    """Execute mock STEP-02 IT Security determination.

    Validates the bundle first (raising ValueError on structural violations),
    then fires the pre-determined signal requested by the scenario.
    """
    _validate_bundle(bundle)

    signal_norm = signal.lower()
    if signal_norm == "escalated":
        escalation = EscalationPayload(
            evidence_condition="Security classification requires review before downstream execution.",
            resolution_owner="IT Security",
        )
        return _ESCALATED_OUTPUT.copy(), "ESCALATED", escalation
    if signal_norm == "blocked":
        return _BLOCKED_OUTPUT.copy(), "BLOCKED", None
    return _COMPLETE_OUTPUT.copy(), "COMPLETE", None
