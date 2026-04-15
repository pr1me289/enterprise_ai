"""Ground-truth expected outputs per scenario, encoded from the testing prompt.

Each expectation is declared as an ``ExpectationSet`` mapping agent name to a
list of ``FieldExpectation``. The assertion helpers in
``tests.support.field_reporter`` consume these declaratively and emit a
per-field pass/fail report.

Kept deliberately narrow: only enum, boolean, and structural presence/emptiness
checks — never free-text content (per prompt §"Assertion rules" and the
"Do not assert on free-text fields" rule).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

# ---------------------------------------------------------------------------
# Field-expectation primitives
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class FieldExpectation:
    """One assertion on one field of an agent output.

    Exactly one of the following is set:
      * ``equals`` — value must compare equal
      * ``one_of`` — value must be in the set
      * ``non_empty`` — value must be a non-empty list/str/dict
      * ``empty`` — value must be an empty list ([])
      * ``predicate`` — value satisfies a custom callable returning bool
    """

    path: str  # dotted path into the output dict (e.g., "status" or "blockers.0.blocker_type")
    description: str
    equals: Any = None
    one_of: tuple[Any, ...] | None = None
    non_empty: bool = False
    empty: bool = False
    predicate: Callable[[Any], bool] | None = None
    # When True and the field is absent from the output, treat as PASS (the
    # agent is allowed to omit this field). Used for spec-declared fields that
    # the output_validator does not require.
    optional: bool = False


@dataclass(frozen=True)
class ExpectationSet:
    """Grouped expectations for a given (scenario, agent) pair."""

    scenario: str
    agent: str
    step: str
    expectations: tuple[FieldExpectation, ...]
    notes: str = ""


# ---------------------------------------------------------------------------
# Predicate helpers
# ---------------------------------------------------------------------------


def _contains_any_substring(target_subs: tuple[str, ...]) -> Callable[[Any], bool]:
    """Return a predicate: value (iterable or string) contains any substring."""
    def check(value: Any) -> bool:
        if value is None:
            return False
        haystack_items: list[str] = []
        if isinstance(value, str):
            haystack_items.append(value)
        elif isinstance(value, (list, tuple)):
            for entry in value:
                if isinstance(entry, str):
                    haystack_items.append(entry)
                elif isinstance(entry, dict):
                    haystack_items.extend(str(v) for v in entry.values() if isinstance(v, str))
        elif isinstance(value, dict):
            haystack_items.extend(str(v) for v in value.values() if isinstance(v, str))
        return any(sub in hay for hay in haystack_items for sub in target_subs)
    return check


def _roles_present(required_roles: tuple[str, ...]) -> Callable[[Any], bool]:
    """Return a predicate: every required role label appears in a guidance-document list.

    Accepts both explicit ``role`` / ``role_label`` keys on each entry. Matching
    is substring-based to tolerate prefix/suffix variation (e.g., "CISO" vs.
    "CISO (K. Whitfield)").
    """
    def check(value: Any) -> bool:
        if not isinstance(value, list) or not value:
            return False
        entry_labels: list[str] = []
        for entry in value:
            if isinstance(entry, dict):
                for key in ("role", "role_label", "role_id", "stakeholder_role", "approver_role"):
                    label = entry.get(key)
                    if isinstance(label, str):
                        entry_labels.append(label)
        missing = [r for r in required_roles if not any(r.lower() in lab.lower() for lab in entry_labels)]
        return not missing
    return check


# ---------------------------------------------------------------------------
# Scenario 1 — Clean Governed Completion
# ---------------------------------------------------------------------------


SCENARIO_1_EXPECTATIONS: dict[str, ExpectationSet] = {
    "it_security_agent": ExpectationSet(
        scenario="scenario_1",
        agent="it_security_agent",
        step="STEP-02",
        expectations=(
            FieldExpectation("data_classification", "UNREGULATED", equals="UNREGULATED"),
            FieldExpectation("integration_type_normalized", "EXPORT_ONLY", equals="EXPORT_ONLY"),
            FieldExpectation("integration_tier", "TIER_3", equals="TIER_3"),
            FieldExpectation("eu_personal_data_present", "NO", equals="NO"),
            FieldExpectation("fast_track_eligible", "true", equals=True),
            FieldExpectation("fast_track_rationale", "ELIGIBLE_LOW_RISK", equals="ELIGIBLE_LOW_RISK"),
            FieldExpectation("security_followup_required", "false", equals=False),
            FieldExpectation("required_security_actions", "[]", empty=True),
            FieldExpectation("nda_status_from_questionnaire", "EXECUTED", equals="EXECUTED"),
            FieldExpectation("status", "complete", equals="complete"),
            FieldExpectation("policy_citations", "non-empty", non_empty=True),
        ),
    ),
    "legal_agent": ExpectationSet(
        scenario="scenario_1",
        agent="legal_agent",
        step="STEP-03",
        expectations=(
            FieldExpectation("dpa_required", "false", equals=False),
            FieldExpectation("dpa_blocker", "false", equals=False),
            FieldExpectation("nda_status", "EXECUTED", equals="EXECUTED"),
            FieldExpectation("nda_blocker", "false", equals=False),
            FieldExpectation("trigger_rule_cited", "[]", empty=True),
            FieldExpectation("status", "complete", equals="complete"),
            FieldExpectation("policy_citations", "non-empty", non_empty=True),
        ),
    ),
    "procurement_agent": ExpectationSet(
        scenario="scenario_1",
        agent="procurement_agent",
        step="STEP-04",
        expectations=(
            FieldExpectation("approval_path", "FAST_TRACK", equals="FAST_TRACK"),
            FieldExpectation("fast_track_eligible", "true", equals=True),
            FieldExpectation("status", "complete", equals="complete"),
            FieldExpectation("policy_citations", "non-empty", non_empty=True),
        ),
    ),
    "checklist_assembler": ExpectationSet(
        scenario="scenario_1",
        agent="checklist_assembler",
        step="STEP-05",
        expectations=(
            FieldExpectation("overall_status", "COMPLETE", equals="COMPLETE"),
            FieldExpectation("blockers", "[]", empty=True),
            FieldExpectation("fast_track_eligible", "true", equals=True, optional=True),
            FieldExpectation("approval_path", "FAST_TRACK", equals="FAST_TRACK", optional=True),
        ),
    ),
    "checkoff_agent": ExpectationSet(
        scenario="scenario_1",
        agent="checkoff_agent",
        step="STEP-06",
        expectations=(
            FieldExpectation("status", "complete", equals="complete"),
        ),
    ),
}


# ---------------------------------------------------------------------------
# Scenario 2 — Escalated Path (Regulated Vendor)
# ---------------------------------------------------------------------------


_SCENARIO_2_TRIGGER_PREDICATE = _contains_any_substring(("A-01", "E-01"))
_SCENARIO_2_BLOCKERS_PREDICATE = _contains_any_substring(("DPA", "NDA", "dpa", "nda"))
_SCENARIO_2_REQUIRED_ROLES = ("CISO", "General Counsel", "CPO", "VP Operations", "SVP Operations")


SCENARIO_2_EXPECTATIONS: dict[str, ExpectationSet] = {
    "it_security_agent": ExpectationSet(
        scenario="scenario_2",
        agent="it_security_agent",
        step="STEP-02",
        expectations=(
            FieldExpectation("data_classification", "REGULATED", equals="REGULATED"),
            FieldExpectation("integration_type_normalized", "AMBIGUOUS", equals="AMBIGUOUS"),
            FieldExpectation(
                "integration_tier",
                "UNCLASSIFIED_PENDING_REVIEW",
                equals="UNCLASSIFIED_PENDING_REVIEW",
            ),
            FieldExpectation("eu_personal_data_present", "YES", equals="YES"),
            FieldExpectation("fast_track_eligible", "false", equals=False),
            FieldExpectation(
                "fast_track_rationale",
                "DISALLOWED_AMBIGUOUS_SCOPE or DISALLOWED_REGULATED_DATA",
                one_of=("DISALLOWED_AMBIGUOUS_SCOPE", "DISALLOWED_REGULATED_DATA"),
            ),
            FieldExpectation("security_followup_required", "true", equals=True),
            FieldExpectation("required_security_actions", "non-empty", non_empty=True),
            FieldExpectation("nda_status_from_questionnaire", "PENDING", equals="PENDING"),
            FieldExpectation("status", "escalated", equals="escalated"),
            FieldExpectation("policy_citations", "non-empty", non_empty=True),
        ),
    ),
    "legal_agent": ExpectationSet(
        scenario="scenario_2",
        agent="legal_agent",
        step="STEP-03",
        expectations=(
            FieldExpectation("dpa_required", "true", equals=True),
            FieldExpectation("dpa_blocker", "true", equals=True),
            FieldExpectation("nda_status", "PENDING", equals="PENDING"),
            FieldExpectation("nda_blocker", "true", equals=True),
            FieldExpectation(
                "trigger_rule_cited",
                "includes A-01 or E-01",
                predicate=_SCENARIO_2_TRIGGER_PREDICATE,
            ),
            FieldExpectation("status", "escalated", equals="escalated"),
            FieldExpectation("policy_citations", "non-empty", non_empty=True),
        ),
    ),
    "procurement_agent": ExpectationSet(
        scenario="scenario_2",
        agent="procurement_agent",
        step="STEP-04",
        expectations=(
            FieldExpectation("approval_path", "STANDARD", equals="STANDARD", optional=True),
            FieldExpectation("fast_track_eligible", "false", equals=False),
            FieldExpectation("status", "escalated", equals="escalated"),
            FieldExpectation("policy_citations", "non-empty", non_empty=True),
        ),
    ),
    "checklist_assembler": ExpectationSet(
        scenario="scenario_2",
        agent="checklist_assembler",
        step="STEP-05",
        expectations=(
            FieldExpectation("overall_status", "ESCALATED", equals="ESCALATED"),
            FieldExpectation(
                "blockers",
                "non-empty; mentions DPA and NDA",
                predicate=_SCENARIO_2_BLOCKERS_PREDICATE,
            ),
            FieldExpectation("fast_track_eligible", "false", equals=False, optional=True),
        ),
    ),
    "checkoff_agent": ExpectationSet(
        scenario="scenario_2",
        agent="checkoff_agent",
        step="STEP-06",
        expectations=(
            FieldExpectation("status", "complete", equals="complete"),
            FieldExpectation(
                "guidance_documents",
                "one entry per required role",
                predicate=_roles_present(_SCENARIO_2_REQUIRED_ROLES),
            ),
        ),
    ),
}


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------


EXPECTATIONS_BY_SCENARIO: dict[str, dict[str, ExpectationSet]] = {
    "scenario_1": SCENARIO_1_EXPECTATIONS,
    "scenario_2": SCENARIO_2_EXPECTATIONS,
}


@dataclass(frozen=True)
class CrossStepInvariant:
    """An invariant that holds across more than one agent output in a paired run."""

    name: str
    description: str


# Handoff invariants — evaluated by tests/integration suite
HANDOFF_INVARIANTS: tuple[CrossStepInvariant, ...] = (
    CrossStepInvariant(
        name="fast_track_passthrough",
        description="STEP-04.fast_track_eligible exactly equals STEP-02.fast_track_eligible",
    ),
    CrossStepInvariant(
        name="legal_escalation_forces_procurement_escalation",
        description="If STEP-03.status == escalated then STEP-04.status == escalated",
    ),
    CrossStepInvariant(
        name="upstream_escalation_propagates_to_checklist",
        description="If any of STEP-02/03/04 status == escalated then STEP-05.overall_status == ESCALATED",
    ),
    CrossStepInvariant(
        name="upstream_block_propagates_to_checklist",
        description="If any of STEP-02/03/04 status == blocked then STEP-05.overall_status == BLOCKED",
    ),
    CrossStepInvariant(
        name="checkoff_runs_on_escalated",
        description="STEP-06.status == complete when STEP-05.overall_status == ESCALATED",
    ),
    CrossStepInvariant(
        name="checkoff_blocks_when_checklist_missing",
        description="STEP-06.status == blocked when STEP-05 output absent from bundle",
    ),
)
