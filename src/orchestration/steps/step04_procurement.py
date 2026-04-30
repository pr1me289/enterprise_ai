"""STEP-04 Procurement step."""

from __future__ import annotations

import re
from typing import Any

from orchestration.models.contracts import GateDecision, RetrievalRequest, StepExecutionResult
from orchestration.models.enums import RetrievalLane, StepId, StepStatus
from orchestration.models.escalation import EscalationPayload
from orchestration.pipeline_state import PipelineState
from orchestration.steps.base import BaseStepHandler


_VENDOR_CLASS_LETTER_RE = re.compile(r"\bClass\s+([A-Z])\b", re.IGNORECASE)
_TIER_RE = re.compile(r"\bT(?:IER[_\s-]?)?(\d+)\b", re.IGNORECASE)
_ROW_ID_RE = re.compile(r"^([A-Z])-T(\d+)$", re.IGNORECASE)


def _extract_class_letter(value: Any) -> str | None:
    """Pull the single-letter vendor class out of free-form questionnaire text.

    Examples:
        "Class A — Enterprise Platform" → "A"
        "Class D — Technology Professional Services" → "D"
        "A" → "A"
        None → None
    """
    if not isinstance(value, str):
        return None
    if len(value) == 1 and value.isalpha():
        return value.upper()
    m = _VENDOR_CLASS_LETTER_RE.search(value)
    return m.group(1).upper() if m else None


def _extract_tier_number(value: Any) -> str | None:
    """Pull the tier number suffix out of an IT Security tier string.

    Examples:
        "TIER_1" → "1"
        "T2" → "2"
        "Tier 3" → "3"
        None → None
    """
    if not isinstance(value, str):
        return None
    m = _TIER_RE.search(value)
    return m.group(1) if m else None


def _row_primary_keys(row: Any) -> tuple[str, str] | None:
    """Extract (class_letter, tier_number) primary keys from a PAM-001 row chunk.

    Prefers the structured ``row_id`` field (e.g., "A-T1") and falls back to
    parsing the chunk text. Returns ``None`` when neither source yields both
    keys — such rows can't participate in primary-key matching.
    """
    if not isinstance(row, dict):
        return None
    row_id = row.get("row_id")
    if isinstance(row_id, str):
        m = _ROW_ID_RE.match(row_id.strip())
        if m:
            return m.group(1).upper(), m.group(2)
    text = row.get("text") if isinstance(row.get("text"), str) else ""
    cls = _extract_class_letter(text)
    tier = _extract_tier_number(text)
    if cls and tier:
        return cls, tier
    return None


def _count_primary_key_matches(
    matrix_rows: list[Any],
    vendor_class: Any,
    integration_tier: Any,
) -> int:
    """Count retrieved PAM-001 rows whose (Class, Tier) match the vendor profile.

    A row counts as a match only when **both** primary keys agree exactly with
    the vendor's class letter and integration tier number, per Procurement
    Agent Spec §8.3 strict-primary-key matching.
    """
    target_class = _extract_class_letter(vendor_class)
    target_tier = _extract_tier_number(integration_tier)
    if target_class is None or target_tier is None:
        return 0
    matches = 0
    for row in matrix_rows or ():
        keys = _row_primary_keys(row)
        if keys == (target_class, target_tier):
            matches += 1
    return matches


class Step04ProcurementHandler(BaseStepHandler):
    def check_gate(self, state: PipelineState) -> GateDecision:
        step03_status = state.step_statuses[StepId.STEP_03]
        if step03_status not in {StepStatus.COMPLETE, StepStatus.ESCALATED}:
            return GateDecision(allowed=False, reason="STEP-03 must be terminal", resolution_owner="Legal")
        if not state.determinations["step_03_legal"]:
            return GateDecision(allowed=False, reason="STEP-03 output missing", resolution_owner="Legal")
        return GateDecision(allowed=True)

    def execute(self, state: PipelineState) -> StepExecutionResult:
        retrievals = {
            "it_security_output": self.router.route(
                RetrievalRequest(
                    request_id="R04-SQ-01",
                    lane=RetrievalLane.RUNTIME_READ,
                    source_id="STEP-02",
                    access_role=self.definition.access_role,
                    output_name="it_security_output",
                    runtime_target="determination:step_02_security_classification",
                    field_map={
                        "data_classification": ("data_classification",),
                        "fast_track_eligible": ("fast_track_eligible",),
                        "integration_tier": ("integration_tier",),
                        "security_followup_required": ("security_followup_required",),
                        "policy_citations": ("policy_citations",),
                        "status": ("status",),
                    },
                ),
                state=state,
            ),
            "legal_output": self.router.route(
                RetrievalRequest(
                    request_id="R04-SQ-02",
                    lane=RetrievalLane.RUNTIME_READ,
                    source_id="STEP-03",
                    access_role=self.definition.access_role,
                    output_name="legal_output",
                    runtime_target="determination:step_03_legal",
                    field_map={
                        "dpa_required": ("dpa_required",),
                        "dpa_blocker": ("dpa_blocker",),
                        "nda_status": ("nda_status",),
                        "nda_blocker": ("nda_blocker",),
                        "trigger_rule_cited": ("trigger_rule_cited",),
                        "policy_citations": ("policy_citations",),
                        "status": ("status",),
                    },
                ),
                state=state,
            ),
            "vendor_relationship": self.router.route(
                RetrievalRequest(
                    request_id="R04-SQ-03",
                    lane=RetrievalLane.DIRECT_STRUCTURED,
                    source_id="VQ-OC-001",
                    access_role=self.definition.access_role,
                    output_name="vendor_relationship",
                    field_map={
                        "vendor_class": ("contract_details.vendor_class_assigned",),
                        "deal_size": ("contract_details.annual_contract_value_usd",),
                        "existing_nda_status": ("legal_and_contractual_status.existing_nda_status",),
                        "existing_msa": ("legal_and_contractual_status.existing_msa",),
                    },
                ),
                state=state,
            ),
            "approval_matrix_rows": self.router.route(
                RetrievalRequest(
                    request_id="R04-SQ-04",
                    lane=RetrievalLane.INDEXED_HYBRID,
                    source_id="PAM-001",
                    access_role=self.definition.access_role,
                    output_name="approval_matrix_rows",
                    search_terms=("approval", "authority", "vendor class", "integration tier"),
                ),
                state=state,
            ),
            "fast_track_rows": self.router.route(
                RetrievalRequest(
                    request_id="R04-SQ-05",
                    lane=RetrievalLane.INDEXED_HYBRID,
                    source_id="PAM-001",
                    access_role=self.definition.access_role,
                    output_name="fast_track_rows",
                    search_terms=("fast track", "routing", "eligible", "unregulated"),
                ),
                state=state,
            ),
            "slack_procurement": self.router.route(
                RetrievalRequest(
                    request_id="R04-SQ-07",
                    lane=RetrievalLane.INDEXED_HYBRID,
                    source_id="SLK-001",
                    access_role=self.definition.access_role,
                    output_name="slack_procurement",
                    search_terms=("OptiChain", "vendor approval", "procurement", "onboarding"),
                ),
                state=state,
            ),
        }

        present_fields = {
            *retrievals["it_security_output"].payload.keys(),
            *retrievals["legal_output"].payload.keys(),
            *retrievals["vendor_relationship"].payload.keys(),
        }
        missing_fields = [
            *retrievals["it_security_output"].missing_fields,
            *retrievals["legal_output"].missing_fields,
            *retrievals["vendor_relationship"].missing_fields,
        ]
        validation = self.bundle_validator.validate(
            step_id=self.step_id.value,
            source_ids=["STEP-02", "STEP-03", "VQ-OC-001", "PAM-001", "SLK-001"],
            present_fields=present_fields,
            missing_fields=missing_fields,
        )
        # Augment bundle_meta with PAM-001 retrieval-vs-match counts so the
        # Procurement Agent has unambiguous evidence to distinguish "PAM-001
        # entirely missing" (BLOCKED, MISSING_PAM_001) from "PAM-001 rows
        # retrieved but none match the vendor profile" (ESCALATED). Per
        # Procurement Agent Spec §9.1.1, primary_key_match_count == 0 with
        # approval_path_matrix_rows_count > 0 is the load-bearing signal that
        # the case is ESCALATED, not BLOCKED.
        matrix_rows = retrievals["approval_matrix_rows"].payload or []
        vendor_relationship = retrievals["vendor_relationship"].payload or {}
        it_security_output = retrievals["it_security_output"].payload or {}
        primary_key_match_count = _count_primary_key_matches(
            matrix_rows,
            vendor_class=vendor_relationship.get("vendor_class"),
            integration_tier=it_security_output.get("integration_tier"),
        )
        bundle = self.bundle_assembler.assemble_step04(
            retrievals,
            {
                "admissible": validation.admissible,
                "missing_fields": validation.missing_fields,
                "prohibited_sources": validation.prohibited_sources,
                "approval_path_matrix_rows_count": len(matrix_rows),
                "primary_key_match_count": primary_key_match_count,
            },
        )
        output = self.agent_runner.run(
            agent_name=self.definition.assigned_agent,
            bundle=bundle,
            step_metadata={"step_id": self.step_id.value},
        )
        validated = self.output_validator.validate(step_id=self.step_id.value, output=output)
        if not validated.valid:
            return StepExecutionResult(
                step_id=self.step_id,
                step_status=StepStatus.BLOCKED,
                output={"status": "blocked", "errors": validated.errors},
                bundle=bundle,
                retrieval_results=retrievals,
                halt_reason="Invalid STEP-04 output",
            )
        escalation_payload = None
        if output["status"] == "escalated":
            escalation_payload = EscalationPayload(
                evidence_condition="Procurement routing inherited an unresolved constraint or lacked a matrix match.",
                resolution_owner="Procurement Director",
            )
        return StepExecutionResult(
            step_id=self.step_id,
            step_status=self._step_status_from_agent_status(output["status"]),
            output=output,
            bundle=bundle,
            retrieval_results=retrievals,
            agent_status=output["status"],
            escalation_payload=escalation_payload,
        )
