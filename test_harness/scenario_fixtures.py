"""Scenario fixture definitions for the deterministic orchestration test harness.

Each fixture declares:
- scenario name and expected terminal outcome
- expected step-by-step statuses
- expected bundle invariants (required sources, forbidden sources, structured fields)
- pre-determined signals each mock agent emits for the scenario
- expected retrieval-lane mapping and steps that must not retrieve at all
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class BundleInvariant:
    """Invariants that must hold for a step's context bundle."""

    step_id: str
    required_source_ids: tuple[str, ...] = field(default_factory=tuple)
    required_structured_fields: tuple[str, ...] = field(default_factory=tuple)
    forbidden_source_ids: tuple[str, ...] = field(default_factory=tuple)
    slack_must_not_be_primary: bool = True
    thread4_must_be_excluded: bool = False


@dataclass(frozen=True, slots=True)
class HarnessFixture:
    """Full scenario fixture for the test harness."""

    scenario_name: str
    description: str
    questionnaire_path_key: str  # "scenario_1" or "scenario_2" or "none"
    questionnaire_overrides: dict[str, Any]
    expected_terminal_status: str
    expected_terminal_step: str
    expected_step_statuses: dict[str, str]
    bundle_invariants: tuple[BundleInvariant, ...]
    escalation_at_step: str | None = None
    block_at_step: str | None = None
    # Pre-determined signals the mock agents fire for this scenario.  Keys are
    # LLMAgentRunner agent names ("it_security_agent", "legal_agent",
    # "procurement_agent", "checklist_assembler", "checkoff_agent").  Values
    # are "complete" | "escalated" | "blocked".  Missing keys default to
    # "complete" at dispatch time.
    agent_signals: dict[str, str] = field(default_factory=dict)
    # Steps that must emit zero retrieval audit entries.  Per the context
    # contract, STEP-05 (Checklist Assembler) and STEP-06 (Checkoff) are
    # downstream-only consumers — they read assembled outputs and runtime
    # state via pipeline state reads, but may not issue raw retrieval
    # requests against the indexed or direct stores.  The harness asserts
    # this by inspecting audit-log event_type=RETRIEVAL entries for these
    # steps.
    forbidden_retrieval_steps: tuple[str, ...] = field(default_factory=tuple)


# ---------------------------------------------------------------------------
# Standard invariants reused across scenarios
# ---------------------------------------------------------------------------

_STEP_01_INVARIANT = BundleInvariant(
    step_id="STEP-01",
    required_source_ids=(),  # STEP-01 uses only direct retrieval; no ContextBundle produced
    required_structured_fields=(),
    forbidden_source_ids=(),
)

_STEP_02_INVARIANT = BundleInvariant(
    step_id="STEP-02",
    required_source_ids=("VQ-OC-001", "ISP-001"),
    required_structured_fields=("questionnaire", "policy_chunks"),
    forbidden_source_ids=("DPA-TM-001", "PAM-001", "SLK-001"),
    slack_must_not_be_primary=True,
    thread4_must_be_excluded=True,
)

_STEP_03_INVARIANT = BundleInvariant(
    step_id="STEP-03",
    required_source_ids=("VQ-OC-001", "DPA-TM-001", "ISP-001"),
    required_structured_fields=(
        "security_output",
        "questionnaire",
        "dpa_trigger_rows",
        "nda_clause_chunks",
    ),
    forbidden_source_ids=("PAM-001", "SLK-001"),
    slack_must_not_be_primary=True,
)

_STEP_04_INVARIANT = BundleInvariant(
    step_id="STEP-04",
    required_source_ids=("VQ-OC-001", "PAM-001"),
    required_structured_fields=(
        "it_security_output",
        "legal_output",
        "questionnaire",
        "approval_path_matrix_rows",
    ),
    forbidden_source_ids=("DPA-TM-001",),
    slack_must_not_be_primary=True,
)

# STEP-05 Assembler: per the context contract, sees no raw evidence at all.
_STEP_05_INVARIANT = BundleInvariant(
    step_id="STEP-05",
    required_source_ids=(),
    required_structured_fields=(
        "it_security_agent",
        "legal_agent",
        "procurement_agent",
        "pipeline_run_id",
    ),
    forbidden_source_ids=("ISP-001", "DPA-TM-001", "PAM-001", "SLK-001"),
)

_STEP_06_INVARIANT = BundleInvariant(
    step_id="STEP-06",
    required_source_ids=(),
    required_structured_fields=(
        "finalized_checklist",
        "stakeholder_map",
    ),
    forbidden_source_ids=("ISP-001", "DPA-TM-001", "PAM-001", "SLK-001"),
)


# ---------------------------------------------------------------------------
# Scenario 1: Happy-path complete — every mock agent returns COMPLETE
# ---------------------------------------------------------------------------

SCENARIO_1_COMPLETE = HarnessFixture(
    scenario_name="scenario_1_complete",
    description="Happy-path: all agents emit COMPLETE; pipeline terminates COMPLETE at STEP-06.",
    questionnaire_path_key="scenario_1",
    questionnaire_overrides={
        "product_and_integration": {
            "erp_integration": {
                "erp_type": "EXPORT_ONLY",
                "integration_description": "Scheduled export-only transfer over SFTP. No service account.",
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
    expected_terminal_status="COMPLETE",
    expected_terminal_step="STEP-06",
    expected_step_statuses={
        "STEP-01": "COMPLETE",
        "STEP-02": "COMPLETE",
        "STEP-03": "COMPLETE",
        "STEP-04": "COMPLETE",
        "STEP-05": "COMPLETE",
        "STEP-06": "COMPLETE",
    },
    bundle_invariants=(
        _STEP_01_INVARIANT,
        _STEP_02_INVARIANT,
        _STEP_03_INVARIANT,
        _STEP_04_INVARIANT,
        _STEP_05_INVARIANT,
        _STEP_06_INVARIANT,
    ),
    agent_signals={
        "it_security_agent": "complete",
        "legal_agent": "complete",
        "procurement_agent": "complete",
        "checklist_assembler": "complete",
        "checkoff_agent": "complete",
    },
    forbidden_retrieval_steps=("STEP-05", "STEP-06"),
)


# ---------------------------------------------------------------------------
# Scenario 2: ESCALATED at STEP-03 (Legal)
# ---------------------------------------------------------------------------

SCENARIO_2_ESCALATED = HarnessFixture(
    scenario_name="scenario_2_escalated",
    description="Legal agent fires ESCALATED at STEP-03; pipeline halts there.",
    questionnaire_path_key="scenario_2",
    questionnaire_overrides={
        "product_and_integration": {
            "erp_integration": {
                "erp_type": "EXPORT_ONLY",
                "integration_description": "Scheduled export-only transfer over SFTP.",
            }
        },
        "data_handling": {
            "personal_data_in_scope": True,
            "data_categories_in_scope": ["Employee payroll data", "HR records"],
            "data_subjects": {
                "eu_personal_data_flag": True,
                "data_subjects_eu": True,
            },
        },
        "legal_and_contractual_status": {
            "existing_nda_status": "EXECUTED",
            "dpa_status": "NOT_STARTED",
            "dpa_required": True,
        },
    },
    expected_terminal_status="ESCALATED",
    expected_terminal_step="STEP-03",
    expected_step_statuses={
        "STEP-01": "COMPLETE",
        "STEP-02": "COMPLETE",
        "STEP-03": "ESCALATED",
        "STEP-04": "PENDING",
        "STEP-05": "PENDING",
        "STEP-06": "PENDING",
    },
    bundle_invariants=(
        _STEP_01_INVARIANT,
        _STEP_02_INVARIANT,
        _STEP_03_INVARIANT,
    ),
    agent_signals={
        "it_security_agent": "complete",
        "legal_agent": "escalated",
    },
    escalation_at_step="STEP-03",
    forbidden_retrieval_steps=(),
)


# ---------------------------------------------------------------------------
# Scenario: BLOCKED at STEP-01 (missing questionnaire — gate rejection)
# ---------------------------------------------------------------------------

SCENARIO_BLOCKED_MISSING_QUESTIONNAIRE = HarnessFixture(
    scenario_name="scenario_blocked_missing_questionnaire",
    description="Questionnaire missing; STEP-01 handler emits BLOCKED; no downstream steps execute.",
    questionnaire_path_key="none",
    questionnaire_overrides={},
    expected_terminal_status="BLOCKED",
    expected_terminal_step="STEP-01",
    expected_step_statuses={
        "STEP-01": "BLOCKED",
        "STEP-02": "PENDING",
        "STEP-03": "PENDING",
        "STEP-04": "PENDING",
        "STEP-05": "PENDING",
        "STEP-06": "PENDING",
    },
    bundle_invariants=(
        BundleInvariant(
            step_id="STEP-01",
            required_source_ids=(),
            required_structured_fields=(),
        ),
    ),
    block_at_step="STEP-01",
)


# ---------------------------------------------------------------------------
# Scenario: ESCALATED at STEP-02 (IT Security classification ambiguous)
# ---------------------------------------------------------------------------

SCENARIO_STEP02_ESCALATED = HarnessFixture(
    scenario_name="scenario_step02_escalated",
    description="IT Security agent fires ESCALATED at STEP-02; pipeline halts there.",
    questionnaire_path_key="scenario_1",  # reuse a valid questionnaire
    questionnaire_overrides={
        "product_and_integration": {
            "erp_integration": {
                "erp_type": "EXPORT_ONLY",
                "integration_description": "Scheduled export-only transfer over SFTP. No service account.",
            }
        },
        "data_handling": {
            "personal_data_in_scope": False,
            "data_categories_in_scope": [],
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
    expected_terminal_status="ESCALATED",
    expected_terminal_step="STEP-02",
    expected_step_statuses={
        "STEP-01": "COMPLETE",
        "STEP-02": "ESCALATED",
        "STEP-03": "PENDING",
        "STEP-04": "PENDING",
        "STEP-05": "PENDING",
        "STEP-06": "PENDING",
    },
    bundle_invariants=(
        _STEP_01_INVARIANT,
        _STEP_02_INVARIANT,
    ),
    agent_signals={
        "it_security_agent": "escalated",
    },
    escalation_at_step="STEP-02",
)


# ---------------------------------------------------------------------------
# Scenario: ESCALATED at STEP-04 (Procurement no matching matrix row)
# ---------------------------------------------------------------------------

SCENARIO_STEP04_ESCALATED = HarnessFixture(
    scenario_name="scenario_step04_escalated",
    description="Procurement agent fires ESCALATED at STEP-04; pipeline halts there.",
    questionnaire_path_key="scenario_1",
    questionnaire_overrides={
        "product_and_integration": {
            "erp_integration": {
                "erp_type": "EXPORT_ONLY",
                "integration_description": "Scheduled export-only transfer over SFTP.",
            }
        },
        "data_handling": {
            "personal_data_in_scope": False,
            "data_categories_in_scope": [],
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
    expected_terminal_status="ESCALATED",
    expected_terminal_step="STEP-04",
    expected_step_statuses={
        "STEP-01": "COMPLETE",
        "STEP-02": "COMPLETE",
        "STEP-03": "COMPLETE",
        "STEP-04": "ESCALATED",
        "STEP-05": "PENDING",
        "STEP-06": "PENDING",
    },
    bundle_invariants=(
        _STEP_01_INVARIANT,
        _STEP_02_INVARIANT,
        _STEP_03_INVARIANT,
        _STEP_04_INVARIANT,
    ),
    agent_signals={
        "it_security_agent": "complete",
        "legal_agent": "complete",
        "procurement_agent": "escalated",
    },
    escalation_at_step="STEP-04",
)


# ---------------------------------------------------------------------------
# Scenario: BLOCKED at STEP-03 (Legal signal-injected block)
# ---------------------------------------------------------------------------

SCENARIO_STEP03_BLOCKED = HarnessFixture(
    scenario_name="scenario_step03_blocked",
    description="Legal agent fires BLOCKED at STEP-03; pipeline halts there.",
    questionnaire_path_key="scenario_1",
    questionnaire_overrides={
        "product_and_integration": {
            "erp_integration": {
                "erp_type": "EXPORT_ONLY",
                "integration_description": "Scheduled export-only transfer over SFTP.",
            }
        },
        "data_handling": {
            "personal_data_in_scope": False,
            "data_categories_in_scope": [],
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
    expected_terminal_status="BLOCKED",
    expected_terminal_step="STEP-03",
    expected_step_statuses={
        "STEP-01": "COMPLETE",
        "STEP-02": "COMPLETE",
        "STEP-03": "BLOCKED",
        "STEP-04": "PENDING",
        "STEP-05": "PENDING",
        "STEP-06": "PENDING",
    },
    bundle_invariants=(
        _STEP_01_INVARIANT,
        _STEP_02_INVARIANT,
        _STEP_03_INVARIANT,
    ),
    agent_signals={
        "it_security_agent": "complete",
        "legal_agent": "blocked",
    },
    block_at_step="STEP-03",
)


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

FIXTURES: dict[str, HarnessFixture] = {
    SCENARIO_1_COMPLETE.scenario_name: SCENARIO_1_COMPLETE,
    SCENARIO_2_ESCALATED.scenario_name: SCENARIO_2_ESCALATED,
    SCENARIO_BLOCKED_MISSING_QUESTIONNAIRE.scenario_name: SCENARIO_BLOCKED_MISSING_QUESTIONNAIRE,
    SCENARIO_STEP02_ESCALATED.scenario_name: SCENARIO_STEP02_ESCALATED,
    SCENARIO_STEP04_ESCALATED.scenario_name: SCENARIO_STEP04_ESCALATED,
    SCENARIO_STEP03_BLOCKED.scenario_name: SCENARIO_STEP03_BLOCKED,
}


def get_fixture(scenario_name: str) -> HarnessFixture:
    try:
        return FIXTURES[scenario_name]
    except KeyError as exc:
        raise KeyError(f"Unknown scenario fixture: {scenario_name!r}. Available: {list(FIXTURES)}") from exc
