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

VALID_SCENARIOS: tuple[str, ...] = ("scenario_1", "scenario_2", "scenario_3", "scenario_4", "scenario_5", "scenario_6")

# Per-agent scenario availability. scenario_3 and scenario_4 are
# Legal-Agent-only fixtures:
#   * scenario_3 — dpa_required=true AND dpa_blocker=false (executed DPA on
#     file). Stresses the required-vs-blocker distinction.
#   * scenario_4 — no upstream STEP-02 output in the bundle. Pure gate-
#     condition test: agent must emit status=blocked per Legal_Agent_Spec
#     §8.5 and §12 instead of inferring a determination from the missing
#     input.
# Other agents have no scenario_3/scenario_4 bundles — callers requesting
# one will hit BundleError via fixture_path() when the file does not exist.
SCENARIOS_BY_AGENT: dict[str, tuple[str, ...]] = {
    "it_security_agent": ("scenario_1", "scenario_2"),
    "legal_agent": ("scenario_1", "scenario_2", "scenario_3", "scenario_4", "scenario_5", "scenario_6"),
    "procurement_agent": ("scenario_1", "scenario_2"),
    "checklist_assembler": ("scenario_1", "scenario_2"),
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
