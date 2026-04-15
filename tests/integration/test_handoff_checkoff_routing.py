"""Invariants: ``checkoff_runs_on_escalated`` and ``checkoff_blocks_when_checklist_missing``.

STEP-06 produces guidance documents that route the vendor's case to
stakeholders. Its behavior depends on the shape of the incoming bundle:

* When STEP-05.overall_status == ESCALATED, STEP-06 must still run to
  completion — the escalation is routed, not halted.
* When the STEP-05 roll-up is absent entirely, STEP-06 cannot route and
  must return a non-complete status.
"""

from __future__ import annotations

from typing import Any

import pytest

from tests.support.bundle_builder import drop_key


pytestmark = [pytest.mark.api, pytest.mark.layer_handoff]


@pytest.mark.scenario2
def test_checkoff_runs_on_escalated(
    run_llm_agent,
    scenario_2_bundles: dict[str, Any],
) -> None:
    """Scenario-2 STEP-06 bundle carries overall_status=ESCALATED upstream."""
    output = run_llm_agent(
        agent_name="checkoff_agent",
        bundle=scenario_2_bundles["checkoff_agent"],
        pipeline_run_id=scenario_2_bundles["_pipeline_run_id"],
    )
    assert output.get("status") == "complete", (
        "checkoff_runs_on_escalated invariant violated; "
        f"output={output!r}"
    )


@pytest.mark.scenario1
def test_checkoff_blocks_when_checklist_missing(
    run_llm_agent,
    scenario_1_bundles: dict[str, Any],
) -> None:
    bundle = drop_key(scenario_1_bundles["checkoff_agent"], "finalized_checklist")
    output = run_llm_agent(
        agent_name="checkoff_agent",
        bundle=bundle,
        pipeline_run_id=scenario_1_bundles["_pipeline_run_id"],
    )
    assert output.get("status") != "complete", (
        "checkoff_blocks_when_checklist_missing invariant violated; "
        f"output={output!r}"
    )
