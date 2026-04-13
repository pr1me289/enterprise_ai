"""Tests for the runtime data contracts introduced in feature/supervisor-orchestration-v2."""

from __future__ import annotations

import pytest

from orchestration.models.context_bundle import ContextBundle, ExcludedChunk
from orchestration.models.contracts import StepExecutionResult
from orchestration.models.determinations import (
    PolicyCitation,
    Step01IntakeDetermination,
    Step02SecurityDetermination,
    Step03LegalDetermination,
    Step04ProcurementDetermination,
    Step05ChecklistDetermination,
    Step06CheckoffDetermination,
)
from orchestration.models.enums import StepId, StepStatus
from orchestration.models.escalation import EscalationPayload
from orchestration.models.retrieved_chunk import RetrievedChunk


# ---------------------------------------------------------------------------
# EscalationPayload
# ---------------------------------------------------------------------------

class TestEscalationPayload:
    def test_basic_construction(self) -> None:
        ep = EscalationPayload(
            evidence_condition="Something needs review.",
            resolution_owner="IT Security",
        )
        assert ep.evidence_condition == "Something needs review."
        assert ep.resolution_owner == "IT Security"
        assert ep.additional_context == {}

    def test_to_dict_minimal(self) -> None:
        ep = EscalationPayload(
            evidence_condition="Cond",
            resolution_owner="Owner",
        )
        d = ep.to_dict()
        assert d == {"evidence_condition": "Cond", "resolution_owner": "Owner"}

    def test_to_dict_with_additional_context(self) -> None:
        ep = EscalationPayload(
            evidence_condition="Cond",
            resolution_owner="Owner",
            additional_context={"ticket_id": "SEC-123"},
        )
        d = ep.to_dict()
        assert d["ticket_id"] == "SEC-123"
        assert "evidence_condition" in d

    def test_spreading_into_audit_details(self) -> None:
        """Verify that to_dict() can be spread as kwargs into audit details."""
        ep = EscalationPayload(evidence_condition="X", resolution_owner="Y")
        details = {"step_id": "STEP-02", **ep.to_dict()}
        assert details["step_id"] == "STEP-02"
        assert details["evidence_condition"] == "X"
        assert details["resolution_owner"] == "Y"


# ---------------------------------------------------------------------------
# RetrievedChunk
# ---------------------------------------------------------------------------

class TestRetrievedChunk:
    def _make_chunk(self, **overrides) -> RetrievedChunk:
        defaults = dict(
            source_id="ISP-001",
            source_name="IT Security Policy",
            source_type="POLICY_DOCUMENT",
            chunk_id="ISP-001__section_12",
            authority_tier=1,
            retrieval_lane="indexed_hybrid",
            is_primary_citable=True,
            text="ERP integrations are classified by tier.",
            citation_label="ISP-001 §12",
        )
        defaults.update(overrides)
        return RetrievedChunk(**defaults)

    def test_construction(self) -> None:
        chunk = self._make_chunk()
        assert chunk.source_id == "ISP-001"
        assert chunk.authority_tier == 1
        assert chunk.is_primary_citable is True

    def test_to_dict_keys(self) -> None:
        chunk = self._make_chunk()
        d = chunk.to_dict()
        expected_keys = {
            "source_id", "source_name", "source_type", "chunk_id",
            "authority_tier", "retrieval_lane", "is_primary_citable",
            "text", "citation_label",
        }
        assert expected_keys.issubset(d.keys())

    def test_to_dict_extra_metadata_included(self) -> None:
        chunk = self._make_chunk(extra_metadata={"version": "4.2"})
        d = chunk.to_dict()
        assert d["extra_metadata"] == {"version": "4.2"}

    def test_to_dict_no_extra_metadata_omitted(self) -> None:
        chunk = self._make_chunk()
        d = chunk.to_dict()
        assert "extra_metadata" not in d


# ---------------------------------------------------------------------------
# ContextBundle / ExcludedChunk
# ---------------------------------------------------------------------------

class TestContextBundle:
    def _make_chunk(self) -> RetrievedChunk:
        return RetrievedChunk(
            source_id="ISP-001",
            source_name="IT Security Policy",
            source_type="POLICY_DOCUMENT",
            chunk_id="ISP-001__section_12",
            authority_tier=1,
            retrieval_lane="indexed_hybrid",
            is_primary_citable=True,
            text="Policy text.",
            citation_label="ISP-001 §12",
        )

    def test_empty_bundle(self) -> None:
        bundle = ContextBundle(step_id=StepId.STEP_02)
        assert bundle.admitted_evidence == []
        assert bundle.excluded_evidence == []
        assert bundle.admissibility_status == "PENDING"

    def test_to_dict_step_id_serialised(self) -> None:
        bundle = ContextBundle(step_id=StepId.STEP_03, admissibility_status="ADMISSIBLE")
        d = bundle.to_dict()
        assert d["step_id"] == "STEP-03"
        assert d["admissibility_status"] == "ADMISSIBLE"

    def test_excluded_chunk_round_trip(self) -> None:
        chunk = self._make_chunk()
        excluded = ExcludedChunk(chunk=chunk, exclusion_reason="prohibited_source")
        d = excluded.to_dict()
        assert d["exclusion_reason"] == "prohibited_source"
        assert d["chunk"]["chunk_id"] == "ISP-001__section_12"

    def test_bundle_with_admitted_and_excluded(self) -> None:
        chunk = self._make_chunk()
        excluded = ExcludedChunk(chunk=chunk, exclusion_reason="missing_fields")
        bundle = ContextBundle(
            step_id=StepId.STEP_02,
            admitted_evidence=[chunk],
            excluded_evidence=[excluded],
            structured_fields={"data_classification": "UNREGULATED"},
            admissibility_status="PARTIAL",
        )
        d = bundle.to_dict()
        assert len(d["admitted_evidence"]) == 1
        assert len(d["excluded_evidence"]) == 1
        assert d["structured_fields"]["data_classification"] == "UNREGULATED"


# ---------------------------------------------------------------------------
# Determination dataclasses
# ---------------------------------------------------------------------------

class TestPolicyCitation:
    def test_minimal(self) -> None:
        cite = PolicyCitation(
            source_id="ISP-001",
            version="4.2",
            chunk_id="ISP-001__section_12",
            citation_class="PRIMARY",
        )
        d = cite.to_dict()
        assert d["source_id"] == "ISP-001"
        assert "section_id" not in d
        assert "row_id" not in d

    def test_with_optional_fields(self) -> None:
        cite = PolicyCitation(
            source_id="ISP-001",
            version="4.2",
            chunk_id="ISP-001__section_12",
            citation_class="PRIMARY",
            section_id="12",
        )
        d = cite.to_dict()
        assert d["section_id"] == "12"


class TestStep02SecurityDetermination:
    def _make(self) -> Step02SecurityDetermination:
        return Step02SecurityDetermination(
            integration_type_normalized="EXPORT_ONLY",
            integration_tier="TIER_3",
            data_classification="UNREGULATED",
            eu_personal_data_present="NO",
            fast_track_eligible=True,
            fast_track_rationale="ELIGIBLE_LOW_RISK",
            security_followup_required=False,
            nda_status_from_questionnaire="EXECUTED",
            required_security_actions=[],
            policy_citations=[],
            status="complete",
        )

    def test_to_dict_has_required_fields(self) -> None:
        from orchestration.validation.output_validator import REQUIRED_OUTPUT_FIELDS
        det = self._make()
        d = det.to_dict()
        for field in REQUIRED_OUTPUT_FIELDS["STEP-02"]:
            assert field in d, f"Missing field: {field}"


class TestStep03LegalDetermination:
    def _make(self) -> Step03LegalDetermination:
        return Step03LegalDetermination(
            dpa_required=False,
            dpa_blocker=False,
            nda_status="EXECUTED",
            nda_blocker=False,
            trigger_rule_cited=[],
            policy_citations=[],
            status="complete",
        )

    def test_to_dict_has_required_fields(self) -> None:
        from orchestration.validation.output_validator import REQUIRED_OUTPUT_FIELDS
        det = self._make()
        d = det.to_dict()
        for field in REQUIRED_OUTPUT_FIELDS["STEP-03"]:
            assert field in d, f"Missing field: {field}"


class TestStep04ProcurementDetermination:
    def _make(self) -> Step04ProcurementDetermination:
        return Step04ProcurementDetermination(
            fast_track_eligible=True,
            required_approvals=[],
            estimated_timeline="2 business days",
            policy_citations=[],
            status="complete",
            approval_path="FAST_TRACK",
        )

    def test_to_dict_has_required_fields(self) -> None:
        from orchestration.validation.output_validator import REQUIRED_OUTPUT_FIELDS
        det = self._make()
        d = det.to_dict()
        for field in REQUIRED_OUTPUT_FIELDS["STEP-04"]:
            assert field in d, f"Missing field: {field}"


class TestStep05ChecklistDetermination:
    def _make(self) -> Step05ChecklistDetermination:
        return Step05ChecklistDetermination(
            pipeline_run_id="run-001",
            vendor_name="OptiChain, Inc.",
            overall_status="COMPLETE",
        )

    def test_to_dict_has_required_fields(self) -> None:
        from orchestration.validation.output_validator import REQUIRED_OUTPUT_FIELDS
        det = self._make()
        d = det.to_dict()
        for field in REQUIRED_OUTPUT_FIELDS["STEP-05"]:
            assert field in d, f"Missing field: {field}"


class TestStep06CheckoffDetermination:
    def test_to_dict_has_required_fields(self) -> None:
        from orchestration.validation.output_validator import REQUIRED_OUTPUT_FIELDS
        det = Step06CheckoffDetermination(status="complete")
        d = det.to_dict()
        for field in REQUIRED_OUTPUT_FIELDS["STEP-06"]:
            assert field in d, f"Missing field: {field}"


# ---------------------------------------------------------------------------
# StepExecutionResult.escalation_payload type contract
# ---------------------------------------------------------------------------

class TestStepExecutionResultEscalationPayload:
    def test_accepts_escalation_payload_object(self) -> None:
        ep = EscalationPayload(
            evidence_condition="Manual review required.",
            resolution_owner="IT Security",
        )
        result = StepExecutionResult(
            step_id=StepId.STEP_02,
            step_status=StepStatus.ESCALATED,
            escalation_payload=ep,
        )
        assert result.escalation_payload is ep
        assert result.escalation_payload.resolution_owner == "IT Security"

    def test_accepts_none(self) -> None:
        result = StepExecutionResult(
            step_id=StepId.STEP_02,
            step_status=StepStatus.COMPLETE,
            escalation_payload=None,
        )
        assert result.escalation_payload is None

    def test_to_dict_round_trip_via_audit(self) -> None:
        ep = EscalationPayload(
            evidence_condition="Classification ambiguous.",
            resolution_owner="Legal",
            additional_context={"priority": "HIGH"},
        )
        result = StepExecutionResult(
            step_id=StepId.STEP_03,
            step_status=StepStatus.ESCALATED,
            escalation_payload=ep,
        )
        # Simulate what audit_logger.log_escalation does
        details = {"step_id": result.step_id.value, **result.escalation_payload.to_dict()}
        assert details["step_id"] == "STEP-03"
        assert details["evidence_condition"] == "Classification ambiguous."
        assert details["resolution_owner"] == "Legal"
        assert details["priority"] == "HIGH"


# ---------------------------------------------------------------------------
# AuditLogger.log_escalation integration
# ---------------------------------------------------------------------------

class TestAuditLoggerLogEscalation:
    def test_log_escalation_accepts_payload_object(self) -> None:
        from orchestration.audit.audit_logger import AuditLogger

        logger = AuditLogger(pipeline_run_id="test-run-001")
        ep = EscalationPayload(
            evidence_condition="Security review required.",
            resolution_owner="IT Security",
        )
        entry = logger.log_escalation(
            agent_id="it_security_agent",
            step_id="STEP-02",
            payload=ep,
        )
        assert entry.details["step_id"] == "STEP-02"
        assert entry.details["evidence_condition"] == "Security review required."
        assert entry.details["resolution_owner"] == "IT Security"

    def test_log_escalation_with_additional_context(self) -> None:
        from orchestration.audit.audit_logger import AuditLogger

        logger = AuditLogger(pipeline_run_id="test-run-002")
        ep = EscalationPayload(
            evidence_condition="DPA blocker.",
            resolution_owner="Legal (General Counsel)",
            additional_context={"dpa_blocker": True},
        )
        entry = logger.log_escalation(
            agent_id="legal_agent",
            step_id="STEP-03",
            payload=ep,
        )
        assert entry.details["dpa_blocker"] is True
