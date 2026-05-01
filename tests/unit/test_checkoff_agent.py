"""Layer 1 per-agent unit tests for ``checkoff_agent`` (STEP-06).

STEP-06 produces the final stakeholder-facing guidance document set. It runs
only when the checklist's ``overall_status`` is COMPLETE *or* ESCALATED — a
BLOCKED checklist halts the pipeline one step earlier.

Covered:
  * Scenario 1 — clean completion, status=complete.
  * Scenario 2 — escalated path still produces status=complete (the routing
    is to stakeholders, not a re-decision), and the guidance-document list
    must cover all five required roles.
  * Missing ``finalized_checklist`` → blocked (cannot route without a roll-up).
"""

from __future__ import annotations

from typing import Any

import pytest

from tests.support.bundle_builder import drop_key


pytestmark = [pytest.mark.api, pytest.mark.layer_unit]


AGENT = "checkoff_agent"


# ---------------------------------------------------------------------------
# Scenarios
# ---------------------------------------------------------------------------


@pytest.mark.scenario_1
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


@pytest.mark.scenario_2
def test_scenario_2_escalated_path_routes_to_stakeholders(
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


@pytest.mark.scenario_1
def test_missing_finalized_checklist_blocks(
    invoke_raw,
    scenario_1_bundles: dict[str, Any],
) -> None:
    """Without STEP-05's finalized_checklist there is nothing to route."""
    bundle = drop_key(scenario_1_bundles[AGENT], "finalized_checklist")
    output = invoke_raw(
        agent_name=AGENT,
        bundle=bundle,
        pipeline_run_id=scenario_1_bundles["_pipeline_run_id"],
    )
    assert output.get("status") != "complete", (
        "checkoff agent returned complete despite missing finalized_checklist; "
        f"output={output!r}"
    )
