"""Load the realistic context bundle for a single (agent, scenario) pair.

The bundles live under ``tests/fixtures/bundles/`` and were generated to
match each agent's input contract (Design Doc §3, per-agent budget rules,
agent_bundle_integrity_checklist). Each fixture is the exact shape the
orchestration layer would hand the agent at runtime — no pipeline state
or supervisor involvement is needed to replay one agent in isolation.

This loader is read-only. It validates the fixture declares the same
``agent`` and ``scenario`` that the caller requested and returns the
inner ``bundle`` payload plus the ``pipeline_run_id``.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

VALID_AGENTS: tuple[str, ...] = (
    "it_security_agent",
    "legal_agent",
    "procurement_agent",
    "checklist_assembler",
    "checkoff_agent",
)

VALID_SCENARIOS: tuple[str, ...] = ("scenario_1", "scenario_2", "scenario_3", "scenario_4", "scenario_5", "scenario_6", "scenario_7", "scenario_8", "scenario_9", "scenario_10", "scenario_11", "scenario_12", "scenario_13", "scenario_14", "scenario_15")

# Per-agent scenario availability. scenario_3 and scenario_4 are
# Legal-Agent-only fixtures:
#   * scenario_3 — dpa_required=true AND dpa_blocker=false (executed DPA on
#     file). Stresses the required-vs-blocker distinction.
#   * scenario_4 — no upstream STEP-02 output in the bundle. Pure gate-
#     condition test: agent must emit status=blocked per Legal_Agent_Spec
#     §8.5 and §12 instead of inferring a determination from the missing
#     input.
#   * scenario_11 — Checklist-Assembler-only fixture. Cross-agent escalation
#     cascade: STEP-02 complete, STEP-03 escalated (dpa_blocker=true, all
#     determination fields resolved), STEP-04 escalated (workflow propagation
#     of upstream DPA gap, approval_path populated). Stresses §8.1 status
#     precedence and §6.2 multi-source blocker assembly per
#     SPEC-AGENT-CLA-001 v0.3.
#   * scenario_12 — Checklist-Assembler-only fixture. Clean COMPLETE happy
#     path: all three upstream agents complete, no blocker flags, no
#     escalations. The reference baseline against which scenario_11's
#     escalated path is compared. Catches over-conservative escalation
#     and phantom blocker fabrication on the happy path.
#   * scenario_13 — Procurement-Agent-only fixture. Clean upstream pass →
#     COMPLETE happy path: STEP-02 complete (EXPORT_ONLY/TIER_3/UNREGULATED,
#     fast_track_eligible=true), STEP-03 complete (dpa_required=false, no
#     blockers), questionnaire matches Q-01-FASTTRACK on both primary keys
#     (vendor_class=TIER_2, integration_tier=TIER_3). Counterpart to
#     scenario_8 — same agent, opposite upstream state. Catches spurious
#     escalation, fast_track_eligible re-derivation, and phantom blocker
#     fabrication on the procurement happy path.
#   * scenario_14 — IT-Security-Agent-only fixture. Policy-over-questionnaire
#     conflict → REGULATED + COMPLETE. Adversarial questionnaire self-reports
#     data_classification_self_reported="NON_REGULATED" with regulated_data_types=[],
#     BUT integration_details.erp_type="DIRECT_API" → TIER_1 → REGULATED per
#     ISP-001 §12.2 + §4. The agent must derive REGULATED from policy and
#     emit a firm COMPLETE (not escalated) with fast_track_rationale=
#     "DISALLOWED_REGULATED_DATA" and security_followup_required=true. Tests
#     ORCH-PLAN-001 STEP-02 classification rules 2, 3, 5 and CC-001 §4
#     authority hierarchy. Catches deferring to vendor self-report on
#     classification, split verdict (correct classification, wrong tier),
#     over-escalation, wrong rationale enum, normalizing nda_status at
#     STEP-02, elevating VQ-OC-001 citations to PRIMARY, empty
#     required_security_actions on followup-required.
#   * scenario_15 — IT-Security-Agent-only fixture. Governing-source
#     retrieval failure → ESCALATED. Honest questionnaire (DIRECT_API / SAP,
#     self-report=LIMITED_OPERATIONAL_DATA, eu_personal_data_flag=YES). ISP-001
#     §12.2 and §4 retrieve cleanly; §12.3 is deliberately ABSENT from the
#     scenario-scoped index so R02-SQ-06 returns EMPTY_RESULT_SET. The agent
#     must escalate (classification rule 6: governing source unavailable →
#     fast_track_eligible=false with fast_track_rationale="DISALLOWED_AMBIGUOUS_SCOPE")
#     while still emitting firm determinations (TIER_1, REGULATED, DIRECT_API,
#     eu_personal_data_present=YES) supported by the chunks that did retrieve.
#     Tests ORCH-PLAN-001 R02-SQ-06 retrieval-failure discipline and CC-001
#     §13.1 escalation payload rules. Catches silent substitution of missing
#     evidence for negative evidence, blanket escalation nulling firm
#     determinations, wrong rationale enum (DISALLOWED_REGULATED_DATA misused
#     when evidence-insufficiency is the actual driver), §12.3 citation
#     hallucination, missing governing-source gap in required_security_actions.
# Other agents have no scenario_3/scenario_4/scenario_11/scenario_12/scenario_13/scenario_14/scenario_15
# bundles — callers requesting one will hit BundleError via fixture_path()
# when the file does not exist.
SCENARIOS_BY_AGENT: dict[str, tuple[str, ...]] = {
    "it_security_agent": ("scenario_1", "scenario_2", "scenario_14", "scenario_15"),
    "legal_agent": ("scenario_1", "scenario_2", "scenario_3", "scenario_4", "scenario_5", "scenario_6"),
    "procurement_agent": ("scenario_1", "scenario_2", "scenario_7", "scenario_8", "scenario_9", "scenario_10", "scenario_13"),
    "checklist_assembler": ("scenario_1", "scenario_2", "scenario_11", "scenario_12"),
    "checkoff_agent": ("scenario_1", "scenario_2"),
}

AGENT_TO_STEP: dict[str, str] = {
    "it_security_agent": "step_02",
    "legal_agent": "step_03",
    "procurement_agent": "step_04",
    "checklist_assembler": "step_05",
    "checkoff_agent": "step_06",
}


class BundleError(Exception):
    """Raised when a bundle fixture is missing, malformed, or mismatched."""


def fixture_path(agent_name: str, scenario: str, *, repo_root: Path) -> Path:
    """Return the expected bundle fixture path for an (agent, scenario)."""
    if agent_name not in VALID_AGENTS:
        raise BundleError(f"unknown agent: {agent_name!r} — expected one of {VALID_AGENTS}")
    if scenario not in VALID_SCENARIOS:
        raise BundleError(f"unknown scenario: {scenario!r} — expected one of {VALID_SCENARIOS}")
    step = AGENT_TO_STEP[agent_name]
    return repo_root / "tests" / "fixtures" / "bundles" / f"{step}_{scenario}.json"


def load_bundle(
    agent_name: str,
    scenario: str,
    *,
    repo_root: Path,
) -> tuple[dict[str, Any], str, Path]:
    """Load ``(bundle_payload, pipeline_run_id, fixture_path)`` for an agent run.

    Validates the fixture's self-declared ``agent`` and ``scenario``
    match the caller's request so we catch accidental mismatches
    between directory name and fixture contents.
    """
    path = fixture_path(agent_name, scenario, repo_root=repo_root)
    if not path.exists():
        raise BundleError(f"fixture not found: {path}")

    try:
        with path.open("r", encoding="utf-8") as handle:
            fixture = json.load(handle)
    except json.JSONDecodeError as exc:
        raise BundleError(f"fixture is not valid JSON: {path} — {exc}") from exc

    declared_agent = fixture.get("agent")
    if declared_agent != agent_name:
        raise BundleError(
            f"fixture {path} declares agent={declared_agent!r} but caller requested {agent_name!r}"
        )

    declared_scenario = fixture.get("scenario")
    if declared_scenario != scenario:
        raise BundleError(
            f"fixture {path} declares scenario={declared_scenario!r} but caller requested {scenario!r}"
        )

    bundle = fixture.get("bundle")
    if not isinstance(bundle, dict):
        raise BundleError(f"fixture {path} has no 'bundle' dict (got {type(bundle).__name__})")

    pipeline_run_id = fixture.get("pipeline_run_id") or ""
    if not isinstance(pipeline_run_id, str):
        raise BundleError(f"fixture {path} has non-string pipeline_run_id: {type(pipeline_run_id).__name__}")

    return bundle, pipeline_run_id, path
