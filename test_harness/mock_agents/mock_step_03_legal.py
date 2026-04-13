"""Mock STEP-03 Legal agent.

Bundle-aware deterministic agent.

Validates:
- upstream security output is present in structured_fields
- questionnaire EU and NDA fields are present
- Slack is not primary evidence

For scenario_1_complete: returns COMPLETE (no DPA required, NDA executed).
For scenario_2_escalated: returns ESCALATED (DPA required but not executed).
"""

from __future__ import annotations

from typing import Any

from orchestration.models.context_bundle import ContextBundle
from orchestration.models.escalation import EscalationPayload

_REQUIRED_STRUCTURED_FIELDS = (
    "eu_personal_data_flag",
    "existing_nda_status",
)

_COMPLETE_OUTPUT = {
    "dpa_required": False,
    "dpa_blocker": False,
    "nda_status": "EXECUTED",
    "nda_blocker": False,
    "trigger_rule_cited": [],
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
    "dpa_required": True,
    "dpa_blocker": True,
    "nda_status": "EXECUTED",
    "nda_blocker": False,
    "trigger_rule_cited": [
        {
            "source_id": "DPA-TM-001",
            "version": "1.3",
            "row_id": "R1",
            "trigger_condition": "EU personal data present and DPA not executed.",
            "citation_class": "PRIMARY",
        }
    ],
    "policy_citations": [
        {
            "source_id": "DPA-TM-001",
            "version": "1.3",
            "chunk_id": "DPA-TM-001__row_R1",
            "section_id": "R1",
            "citation_class": "PRIMARY",
        }
    ],
    "status": "escalated",
}


def _validate_bundle(bundle: ContextBundle) -> None:
    """Validate bundle invariants for STEP-03; raise ValueError if malformed."""
    sf = bundle.structured_fields

    # Upstream security output must be present
    security_output = sf.get("security_output")
    if not security_output:
        raise ValueError(
            "STEP-03 mock agent: malformed bundle — 'security_output' missing "
            f"from structured_fields. Keys: {list(sf.keys())!r}"
        )

    # Questionnaire EU/NDA fields must be present
    questionnaire: dict[str, Any] = sf.get("questionnaire", {})
    missing = [f for f in _REQUIRED_STRUCTURED_FIELDS if f not in questionnaire]
    if missing:
        raise ValueError(
            f"STEP-03 mock agent: malformed bundle — required questionnaire fields "
            f"missing: {missing!r}. Present: {list(questionnaire.keys())!r}"
        )

    # Validate Slack is not primary evidence
    for chunk in bundle.admitted_evidence:
        if chunk.source_id == "SLK-001" and chunk.is_primary_citable:
            raise ValueError(
                "STEP-03 mock agent: bundle violation — Slack admitted as primary "
                f"evidence: chunk_id={chunk.chunk_id!r}"
            )


def run(
    bundle: ContextBundle,
    scenario_name: str,
) -> tuple[dict[str, Any], str, EscalationPayload | None]:
    """Execute mock STEP-03 Legal determination."""
    _validate_bundle(bundle)

    if scenario_name == "scenario_2_escalated":
        escalation = EscalationPayload(
            evidence_condition="EU personal data present and DPA not executed — GDPR Art. 28 blocker.",
            resolution_owner="Legal (General Counsel)",
            additional_context={"dpa_required": True, "dpa_blocker": True},
        )
        return _ESCALATED_OUTPUT.copy(), "ESCALATED", escalation

    return _COMPLETE_OUTPUT.copy(), "COMPLETE", None
