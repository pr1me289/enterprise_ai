"""Mock STEP-04 Procurement agent.

Bundle-aware deterministic agent.

Validates:
- upstream security and legal outputs are present
- questionnaire vendor fields are present
- Slack chunks are not primary evidence
"""

from __future__ import annotations

from typing import Any

from orchestration.models.context_bundle import ContextBundle
from orchestration.models.escalation import EscalationPayload

_COMPLETE_OUTPUT = {
    "approval_path": "FAST_TRACK",
    "fast_track_eligible": True,
    "required_approvals": [
        {
            "approver": "Procurement Manager",
            "domain": "procurement",
            "status": "PENDING",
            "blocker": False,
            "estimated_completion": "2 business days",
        }
    ],
    "estimated_timeline": "2 business days",
    "policy_citations": [
        {
            "source_id": "PAM-001",
            "version": "3.0",
            "chunk_id": "PAM-001__row_A-T1",
            "row_id": "A-T1",
            "approval_path_condition": "Class A / 210000",
            "citation_class": "PRIMARY",
        }
    ],
    "status": "complete",
}


def _validate_bundle(bundle: ContextBundle) -> None:
    sf = bundle.structured_fields

    it_security = sf.get("it_security_output")
    if not it_security:
        raise ValueError(
            "STEP-04 mock agent: malformed bundle — 'it_security_output' missing. "
            f"Keys: {list(sf.keys())!r}"
        )

    legal_output = sf.get("legal_output")
    if not legal_output:
        raise ValueError(
            "STEP-04 mock agent: malformed bundle — 'legal_output' missing. "
            f"Keys: {list(sf.keys())!r}"
        )

    # Validate Slack is not primary evidence
    for chunk in bundle.admitted_evidence:
        if chunk.source_id == "SLK-001" and chunk.is_primary_citable:
            raise ValueError(
                "STEP-04 mock agent: bundle violation — Slack admitted as primary "
                f"evidence: chunk_id={chunk.chunk_id!r}"
            )


_ESCALATED_OUTPUT = {
    "approval_path": "STANDARD",
    "fast_track_eligible": False,
    "required_approvals": [],
    "estimated_timeline": "",
    "policy_citations": [],
    "status": "escalated",
}

_BLOCKED_OUTPUT = {
    "status": "blocked",
    "errors": ["Bundle violation: prohibited source detected in Procurement bundle."],
}


def run(
    bundle: ContextBundle,
    scenario_name: str,
    signal: str = "complete",
) -> tuple[dict[str, Any], str, EscalationPayload | None]:
    """Execute mock STEP-04 Procurement routing determination.

    Validates the bundle first (raising ValueError on structural violations),
    then fires the pre-determined signal requested by the scenario.
    """
    _validate_bundle(bundle)

    signal_norm = signal.lower()
    if signal_norm == "escalated":
        escalation = EscalationPayload(
            evidence_condition="No matching approval-matrix row for the vendor profile.",
            resolution_owner="Procurement",
        )
        return _ESCALATED_OUTPUT.copy(), "ESCALATED", escalation
    if signal_norm == "blocked":
        return _BLOCKED_OUTPUT.copy(), "BLOCKED", None
    return _COMPLETE_OUTPUT.copy(), "COMPLETE", None
