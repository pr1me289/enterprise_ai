"""Step determination dataclasses representing validated agent outputs per step."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class PolicyCitation:
    """A single policy citation produced by an agent."""

    source_id: str
    version: str
    chunk_id: str
    citation_class: str
    section_id: str | None = None
    row_id: str | None = None
    thread_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "source_id": self.source_id,
            "version": self.version,
            "chunk_id": self.chunk_id,
            "citation_class": self.citation_class,
        }
        if self.section_id is not None:
            result["section_id"] = self.section_id
        if self.row_id is not None:
            result["row_id"] = self.row_id
        if self.thread_id is not None:
            result["thread_id"] = self.thread_id
        return result


@dataclass(slots=True)
class Step01IntakeDetermination:
    """STEP-01 intake / vendor questionnaire validation outcome."""

    questionnaire_valid: bool
    vendor_name: str
    status: str
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "questionnaire_valid": self.questionnaire_valid,
            "vendor_name": self.vendor_name,
            "status": self.status,
            "notes": self.notes,
        }


@dataclass(slots=True)
class Step02SecurityDetermination:
    """STEP-02 IT Security classification determination.

    Field names derived from ``REQUIRED_OUTPUT_FIELDS["STEP-02"]`` and the
    ``it_security_agent`` output shapes in ``scenarios.py``.
    """

    integration_type_normalized: str
    integration_tier: str
    data_classification: str
    eu_personal_data_present: str
    fast_track_eligible: bool
    fast_track_rationale: str
    security_followup_required: bool
    nda_status_from_questionnaire: str
    required_security_actions: list[dict[str, Any]]
    policy_citations: list[dict[str, Any]]
    status: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "integration_type_normalized": self.integration_type_normalized,
            "integration_tier": self.integration_tier,
            "data_classification": self.data_classification,
            "eu_personal_data_present": self.eu_personal_data_present,
            "fast_track_eligible": self.fast_track_eligible,
            "fast_track_rationale": self.fast_track_rationale,
            "security_followup_required": self.security_followup_required,
            "nda_status_from_questionnaire": self.nda_status_from_questionnaire,
            "required_security_actions": self.required_security_actions,
            "policy_citations": self.policy_citations,
            "status": self.status,
        }


@dataclass(slots=True)
class Step03LegalDetermination:
    """STEP-03 Legal review determination.

    Field names derived from ``REQUIRED_OUTPUT_FIELDS["STEP-03"]`` and the
    ``legal_agent`` output shapes in ``scenarios.py``.
    """

    dpa_required: bool
    dpa_blocker: bool
    nda_status: str
    nda_blocker: bool
    trigger_rule_cited: list[Any]
    policy_citations: list[dict[str, Any]]
    status: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "dpa_required": self.dpa_required,
            "dpa_blocker": self.dpa_blocker,
            "nda_status": self.nda_status,
            "nda_blocker": self.nda_blocker,
            "trigger_rule_cited": self.trigger_rule_cited,
            "policy_citations": self.policy_citations,
            "status": self.status,
        }


@dataclass(slots=True)
class Step04ProcurementDetermination:
    """STEP-04 Procurement routing determination.

    Field names derived from ``REQUIRED_OUTPUT_FIELDS["STEP-04"]`` and the
    ``procurement_agent`` output shapes in ``scenarios.py``.
    """

    fast_track_eligible: bool
    required_approvals: list[dict[str, Any]]
    estimated_timeline: str
    policy_citations: list[dict[str, Any]]
    status: str
    approval_path: str | None = None

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "fast_track_eligible": self.fast_track_eligible,
            "required_approvals": self.required_approvals,
            "estimated_timeline": self.estimated_timeline,
            "policy_citations": self.policy_citations,
            "status": self.status,
        }
        if self.approval_path is not None:
            result["approval_path"] = self.approval_path
        return result


@dataclass(slots=True)
class Step05ChecklistDetermination:
    """STEP-05 Checklist assembly determination.

    Field names derived from ``REQUIRED_OUTPUT_FIELDS["STEP-05"]`` and the
    ``checklist_assembler`` output shapes in ``scenarios.py``.
    """

    pipeline_run_id: str
    vendor_name: str
    overall_status: str
    data_classification: str | None = None
    dpa_required: bool | None = None
    fast_track_eligible: bool | None = None
    required_security_actions: list[Any] = field(default_factory=list)
    approval_path: str | None = None
    required_approvals: list[dict[str, Any]] = field(default_factory=list)
    blockers: list[Any] = field(default_factory=list)
    citations: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "pipeline_run_id": self.pipeline_run_id,
            "vendor_name": self.vendor_name,
            "overall_status": self.overall_status,
            "data_classification": self.data_classification,
            "dpa_required": self.dpa_required,
            "fast_track_eligible": self.fast_track_eligible,
            "required_security_actions": self.required_security_actions,
            "approval_path": self.approval_path,
            "required_approvals": self.required_approvals,
            "blockers": self.blockers,
            "citations": self.citations,
        }


@dataclass(slots=True)
class Step06CheckoffDetermination:
    """STEP-06 Stakeholder check-off determination.

    Field names derived from ``REQUIRED_OUTPUT_FIELDS["STEP-06"]`` and the
    ``checkoff_agent`` output shapes in ``scenarios.py``.
    """

    status: str
    guidance_documents: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "guidance_documents": self.guidance_documents,
        }
