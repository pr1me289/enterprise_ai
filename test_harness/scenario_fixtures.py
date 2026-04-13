"""Scenario fixture definitions for the deterministic orchestration test harness.

Each fixture declares:
- scenario name and expected terminal outcome
- expected step-by-step statuses
- expected bundle invariants (required sources, expected exclusions)
- final assertion parameters
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


# ---------------------------------------------------------------------------
# Scenario 1: Happy-path complete
# ---------------------------------------------------------------------------

SCENARIO_1_COMPLETE = HarnessFixture(
    scenario_name="scenario_1_complete",
    description="Happy-path: all steps complete, fast-track eligible, COMPLETE terminal state.",
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
        BundleInvariant(
            step_id="STEP-01",
            required_source_ids=("VQ-OC-001",),
            required_structured_fields=("vendor_name",),
        ),
        BundleInvariant(
            step_id="STEP-02",
            required_source_ids=("VQ-OC-001", "ISP-001"),
            required_structured_fields=(
                "integration_details.erp_type",
                "eu_personal_data_flag",
                "existing_nda_status",
            ),
            slack_must_not_be_primary=True,
            thread4_must_be_excluded=True,
        ),
        BundleInvariant(
            step_id="STEP-03",
            required_source_ids=("VQ-OC-001",),
            required_structured_fields=(
                "eu_personal_data_flag",
                "existing_nda_status",
            ),
            slack_must_not_be_primary=True,
        ),
        BundleInvariant(
            step_id="STEP-04",
            required_source_ids=("VQ-OC-001",),
            required_structured_fields=(),
            slack_must_not_be_primary=True,
        ),
        BundleInvariant(
            step_id="STEP-05",
            required_source_ids=(),
            required_structured_fields=(),
        ),
        BundleInvariant(
            step_id="STEP-06",
            required_source_ids=(),
            required_structured_fields=(),
        ),
    ),
)


# ---------------------------------------------------------------------------
# Scenario 2: Escalated at STEP-03 (legal)
# ---------------------------------------------------------------------------

SCENARIO_2_ESCALATED = HarnessFixture(
    scenario_name="scenario_2_escalated",
    description="Escalation scenario: STEP-01 and STEP-02 complete; STEP-03 escalates due to DPA requirement.",
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
        BundleInvariant(
            step_id="STEP-01",
            required_source_ids=("VQ-OC-001",),
            required_structured_fields=("vendor_name",),
        ),
        BundleInvariant(
            step_id="STEP-02",
            required_source_ids=("VQ-OC-001", "ISP-001"),
            slack_must_not_be_primary=True,
            thread4_must_be_excluded=True,
        ),
        BundleInvariant(
            step_id="STEP-03",
            required_source_ids=("VQ-OC-001",),
            required_structured_fields=("eu_personal_data_flag",),
            slack_must_not_be_primary=True,
        ),
    ),
    escalation_at_step="STEP-03",
)


# ---------------------------------------------------------------------------
# Scenario Blocked: Missing questionnaire (STEP-01 gate)
# ---------------------------------------------------------------------------

SCENARIO_BLOCKED_MISSING_QUESTIONNAIRE = HarnessFixture(
    scenario_name="scenario_blocked_missing_questionnaire",
    description="Blocked scenario: questionnaire missing; STEP-01 emits BLOCKED; no downstream steps execute.",
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
# Registry
# ---------------------------------------------------------------------------

FIXTURES: dict[str, HarnessFixture] = {
    SCENARIO_1_COMPLETE.scenario_name: SCENARIO_1_COMPLETE,
    SCENARIO_2_ESCALATED.scenario_name: SCENARIO_2_ESCALATED,
    SCENARIO_BLOCKED_MISSING_QUESTIONNAIRE.scenario_name: SCENARIO_BLOCKED_MISSING_QUESTIONNAIRE,
}


def get_fixture(scenario_name: str) -> HarnessFixture:
    try:
        return FIXTURES[scenario_name]
    except KeyError as exc:
        raise KeyError(f"Unknown scenario fixture: {scenario_name!r}. Available: {list(FIXTURES)}") from exc
