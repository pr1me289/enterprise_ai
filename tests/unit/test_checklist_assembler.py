"""Layer 1 per-agent unit tests for ``checklist_assembler`` (STEP-05).

STEP-05 is the roll-up step. It does not re-decide anything; it aggregates
the three domain outputs into a single ``overall_status`` + blocker list.

Covered:
  * Scenario 1 — all upstream complete → ``overall_status=COMPLETE``, blockers=[].
  * Scenario 2 — escalations present → ``overall_status=ESCALATED`` with
    blockers naming the DPA and NDA issues.
  * Any upstream ``blocked`` → ``overall_status=BLOCKED``.
  * Escalation propagation — a single upstream ``escalated`` must bubble up
    into the checklist even when the other two are complete.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any

import pytest

from tests.support.bundle_builder import set_value


pytestmark = [pytest.mark.api, pytest.mark.layer_unit]


AGENT = "checklist_assembler"


# ---------------------------------------------------------------------------
# Scenarios
# ---------------------------------------------------------------------------


@pytest.mark.scenario1
def test_scenario_1_happy_path(
    invoke_and_assert,
    scenario_1_bundles: dict[str, Any],
) -> None:
    bundle = scenario_1_bundles[AGENT]
    invoke_and_assert(
        scenario="scenario_1",
        agent_name=AGENT,
        bundle=bundle,
        pipeline_run_id=scenario_1_bundles["_pipeline_run_id"],
    )


@pytest.mark.scenario2
def test_scenario_2_escalated_path(
    invoke_and_assert,
    scenario_2_bundles: dict[str, Any],
) -> None:
    bundle = scenario_2_bundles[AGENT]
    invoke_and_assert(
        scenario="scenario_2",
        agent_name=AGENT,
        bundle=bundle,
        pipeline_run_id=scenario_2_bundles["_pipeline_run_id"],
    )


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


@pytest.mark.scenario1
def test_upstream_blocked_propagates(
    invoke_raw,
    scenario_1_bundles: dict[str, Any],
) -> None:
    """Any single upstream ``blocked`` status must force overall BLOCKED."""
    bundle = deepcopy(scenario_1_bundles[AGENT])
    bundle = set_value(bundle, "legal_agent.status", "blocked")
    bundle = set_value(bundle, "legal_agent.error", "missing evidence in bundle")
    output = invoke_raw(
        agent_name=AGENT,
        bundle=bundle,
        pipeline_run_id=scenario_1_bundles["_pipeline_run_id"],
    )
    assert output.get("overall_status") == "BLOCKED", (
        f"checklist did not propagate blocked status; output={output!r}"
    )


@pytest.mark.scenario1
def test_single_escalation_propagates(
    invoke_raw,
    scenario_1_bundles: dict[str, Any],
) -> None:
    """A single upstream ``escalated`` status must bubble up even when the
    other two upstream statuses are complete.
    """
    bundle = deepcopy(scenario_1_bundles[AGENT])
    bundle = set_value(bundle, "it_security_agent.status", "escalated")
    bundle = set_value(bundle, "it_security_agent.security_followup_required", True)
    output = invoke_raw(
        agent_name=AGENT,
        bundle=bundle,
        pipeline_run_id=scenario_1_bundles["_pipeline_run_id"],
    )
    assert output.get("overall_status") == "ESCALATED", (
        "checklist did not propagate single-agent escalated status; "
        f"output={output!r}"
    )
