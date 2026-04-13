"""Scenario fixtures for deterministic orchestration demos and tests."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class ScenarioFixture:
    name: str
    description: str
    questionnaire_overrides: dict[str, Any] = field(default_factory=dict)
    indexed_results: dict[tuple[str, tuple[str, ...]], list[dict[str, Any]]] = field(default_factory=dict)
    agent_outputs: dict[str, dict[str, Any]] = field(default_factory=dict)
    expected_overall_status: str = "IN_PROGRESS"
    expected_step_statuses: dict[str, str] = field(default_factory=dict)


def _chunk(
    *,
    source_id: str,
    version: str,
    chunk_id: str,
    section_id: str | None = None,
    row_id: str | None = None,
    thread_id: str | None = None,
    text: str = "",
    citation_class: str = "PRIMARY",
) -> dict[str, Any]:
    return {
        "source_id": source_id,
        "version": version,
        "chunk_id": chunk_id,
        "section_id": section_id,
        "row_id": row_id,
        "thread_id": thread_id,
        "text": text or chunk_id,
        "retrieval_score": 1.0,
        "rerank_score": 1.0,
        "citation_class": citation_class,
    }


def complete_demo_scenario() -> ScenarioFixture:
    indexed_results = {
        ("ISP-001", ("ERP integration tier", "12.2", "integration classification", "tier")): [
            _chunk(source_id="ISP-001", version="4.2", chunk_id="ISP-001__section_12_2_3", section_id="12.2.3", text="Export-only integrations are Tier 3."),
        ],
        ("ISP-001", ("regulated data", "data classification", "third-party access", "12")): [
            _chunk(source_id="ISP-001", version="4.2", chunk_id="ISP-001__section_12", section_id="12", text="Unregulated export-only data may qualify for low-risk treatment."),
        ],
        ("ISP-001", ("fast track", "manual review", "regulated data", "third-party risk")): [
            _chunk(source_id="ISP-001", version="4.2", chunk_id="ISP-001__section_17_3", section_id="17.3", text="Low-risk export-only vendors may be fast-tracked."),
        ],
        ("ISP-001", ("NDA", "12.1.4", "information exchange", "non-disclosure")): [
            _chunk(source_id="ISP-001", version="4.2", chunk_id="ISP-001__section_12_1_4", section_id="12.1.4", text="NDA must be executed before information exchange."),
        ],
        ("DPA-TM-001", ("EU personal data", "GDPR", "Art. 28", "employee data")): [
            _chunk(source_id="DPA-TM-001", version="2.1", chunk_id="DPA-TM-001__row_A-01", row_id="A-01", text="GDPR Art. 28 DPA required when EU personal data is processed."),
        ],
        ("PAM-001", ("vendor class", "deal size", "approval path", "standard", "fast track")): [
            _chunk(source_id="PAM-001", version="3.0", chunk_id="PAM-001__row_A-T1", row_id="A-T1", text="Class A under threshold may use FAST_TRACK."),
        ],
        ("PAM-001", ("fast track", "expedited", "eligible", "low risk")): [
            _chunk(source_id="PAM-001", version="3.0", chunk_id="PAM-001__row_FAST", row_id="FAST-01", text="Fast-track routing row."),
        ],
        ("SLK-001", ("OptiChain", "vendor approval", "procurement", "onboarding")): [],
    }
    agent_outputs = {
        "it_security_agent": {
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
                    "chunk_id": "ISP-001__section_12_2_3",
                    "section_id": "12.2.3",
                    "citation_class": "PRIMARY",
                }
            ],
            "status": "complete",
        },
        "legal_agent": {
            "dpa_required": False,
            "dpa_blocker": False,
            "nda_status": "EXECUTED",
            "nda_blocker": False,
            "trigger_rule_cited": [],
            "policy_citations": [
                {
                    "source_id": "ISP-001",
                    "version": "4.2",
                    "chunk_id": "ISP-001__section_12_1_4",
                    "section_id": "12.1.4",
                    "citation_class": "PRIMARY",
                }
            ],
            "status": "complete",
        },
        "procurement_agent": {
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
        },
        "checklist_assembler": {
            "pipeline_run_id": "SCENARIO_PIPELINE_RUN_ID",
            "vendor_name": "OptiChain, Inc.",
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
            "citations": [
                {
                    "source_name": "ISP-001",
                    "version": "4.2",
                    "section": "12.2.3",
                    "retrieval_timestamp": "",
                    "agent_id": "it_security_agent",
                },
                {
                    "source_name": "PAM-001",
                    "version": "3.0",
                    "section": "A-T1",
                    "retrieval_timestamp": "",
                    "agent_id": "procurement_agent",
                },
            ],
        },
        "checkoff_agent": {
            "guidance_documents": [
                {
                    "stakeholder_role": "Procurement Manager",
                    "domain": "procurement",
                    "instructions": "Pipeline status is COMPLETE. Review procurement approval and complete signoff.",
                    "blockers_owned": [],
                    "required_security_actions": [],
                    "next_steps": ["Review approval requirement for procurement"],
                    "citations": [
                        {
                            "source_name": "PAM-001",
                            "version": "3.0",
                            "section": "A-T1",
                            "retrieval_timestamp": "",
                            "agent_id": "procurement_agent",
                        }
                    ],
                }
            ],
            "status": "complete",
        },
    }
    return ScenarioFixture(
        name="complete_demo",
        description="Happy-path scenario proving full sequential completion through STEP-06.",
        questionnaire_overrides={
            "product_and_integration": {
                "erp_integration": {
                    "erp_type": "EXPORT_ONLY",
                    "integration_description": "Scheduled export-only transfer over SFTP. No service account and no persistent ERP session.",
                }
            },
            "data_handling": {
                "personal_data_in_scope": False,
                "data_categories_in_scope": ["Inventory position exports", "Demand forecast outputs"],
                "data_subjects": {
                    "eu_personal_data_flag": False,
                    "data_subjects_eu": False,
                },
            },
            "legal_and_contractual_status": {
                "existing_nda_status": "EXECUTED",
                "dpa_status": "EXECUTED",
                "dpa_required": False,
            },
        },
        indexed_results=indexed_results,
        agent_outputs=agent_outputs,
        expected_overall_status="COMPLETE",
        expected_step_statuses={
            "STEP-01": "COMPLETE",
            "STEP-02": "COMPLETE",
            "STEP-03": "COMPLETE",
            "STEP-04": "COMPLETE",
            "STEP-05": "COMPLETE",
            "STEP-06": "COMPLETE",
        },
    )


def escalated_security_scenario() -> ScenarioFixture:
    indexed_results = {
        ("ISP-001", ("ERP integration tier", "12.2", "integration classification", "tier")): [
            _chunk(source_id="ISP-001", version="4.2", chunk_id="ISP-001__section_12_2", section_id="12.2", text="Ambiguous ERP patterns require manual review."),
        ],
        ("ISP-001", ("regulated data", "data classification", "third-party access", "12")): [
            _chunk(source_id="ISP-001", version="4.2", chunk_id="ISP-001__section_12", section_id="12", text="Employee-linked data is regulated."),
        ],
        ("ISP-001", ("fast track", "manual review", "regulated data", "third-party risk")): [
            _chunk(source_id="ISP-001", version="4.2", chunk_id="ISP-001__section_17_3", section_id="17.3", text="Ambiguous integrations are not fast-track eligible."),
        ],
        ("ISP-001", ("NDA", "12.1.4", "information exchange", "non-disclosure")): [
            _chunk(source_id="ISP-001", version="4.2", chunk_id="ISP-001__section_12_1_4", section_id="12.1.4", text="NDA must be executed before information exchange."),
        ],
    }
    agent_outputs = {
        "it_security_agent": {
            "integration_type_normalized": "AMBIGUOUS",
            "integration_tier": "UNCLASSIFIED_PENDING_REVIEW",
            "data_classification": "REGULATED",
            "eu_personal_data_present": "YES",
            "fast_track_eligible": False,
            "fast_track_rationale": "DISALLOWED_AMBIGUOUS_SCOPE",
            "security_followup_required": True,
            "nda_status_from_questionnaire": "PENDING",
            "required_security_actions": [
                {
                    "action_type": "SECURITY_REVIEW",
                    "reason": "ERP integration tier remains unclassified.",
                    "owner": "IT Security",
                }
            ],
            "policy_citations": [
                {
                    "source_id": "ISP-001",
                    "version": "4.2",
                    "chunk_id": "ISP-001__section_12_2",
                    "section_id": "12.2",
                    "citation_class": "PRIMARY",
                }
            ],
            "status": "escalated",
        }
    }
    return ScenarioFixture(
        name="escalated_security",
        description="Default questionnaire posture halts progression after STEP-02 escalation.",
        indexed_results=indexed_results,
        agent_outputs=agent_outputs,
        expected_overall_status="ESCALATED",
        expected_step_statuses={
            "STEP-01": "COMPLETE",
            "STEP-02": "ESCALATED",
            "STEP-03": "PENDING",
            "STEP-04": "PENDING",
            "STEP-05": "PENDING",
            "STEP-06": "PENDING",
        },
    )


def get_scenario_fixture(name: str) -> ScenarioFixture:
    fixtures = {
        "complete_demo": complete_demo_scenario(),
        "escalated_security": escalated_security_scenario(),
    }
    try:
        return fixtures[name]
    except KeyError as exc:
        raise KeyError(f"Unsupported scenario fixture: {name}") from exc
