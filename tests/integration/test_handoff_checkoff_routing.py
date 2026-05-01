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


@pytest.mark.scenario_2
def test_checkoff_runs_on_escalated(
    run_llm_agent,
    scenario_2_bundles: dict[str, Any],
    report_handoff,
) -> None:
    """Scenario-2 STEP-06 bundle carries overall_status=ESCALATED upstream."""
    output = run_llm_agent(
        agent_name="checkoff_agent",
        bundle=scenario_2_bundles["checkoff_agent"],
        pipeline_run_id=scenario_2_bundles["_pipeline_run_id"],
    )
    status = output.get("status")
    report_handoff(
        invariant="checkoff_runs_on_escalated",
        upstream="STEP-05(ESCALATED)",
        downstream="STEP-06",
        passed=(status == "complete"),
        detail=f"status={status!r}",
    )


@pytest.mark.scenario_1
def test_checkoff_blocks_when_checklist_missing(
    run_llm_agent,
    scenario_1_bundles: dict[str, Any],
    report_handoff,
) -> None:
    bundle = drop_key(scenario_1_bundles["checkoff_agent"], "finalized_checklist")
    output = run_llm_agent(
        agent_name="checkoff_agent",
        bundle=bundle,
        pipeline_run_id=scenario_1_bundles["_pipeline_run_id"],
    )
    status = output.get("status")
    report_handoff(
        invariant="checkoff_blocks_when_checklist_missing",
        upstream="STEP-05(absent)",
        downstream="STEP-06",
        passed=(status != "complete"),
        detail=f"status={status!r}",
    )
