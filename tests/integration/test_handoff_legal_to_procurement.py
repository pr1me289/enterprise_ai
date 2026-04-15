"""Invariant: ``legal_escalation_forces_procurement_escalation``.

If STEP-03.status == "escalated" then STEP-04.status must also be
"escalated". Procurement cannot stamp the approval path as complete when
Legal has outstanding DPA/NDA blockers.

Verified by running STEP-03 on the scenario-2 bundle (which synthesizes
escalated DPA/NDA conditions), splicing its real output into STEP-04, and
asserting the downstream escalation.
"""

from __future__ import annotations

from typing import Any

import pytest


pytestmark = [pytest.mark.api, pytest.mark.layer_handoff, pytest.mark.scenario2]


def test_legal_escalation_forces_procurement_escalation(
    run_llm_agent,
    scenario_2_bundles: dict[str, Any],
    splice_upstream,
) -> None:
    pipeline_run_id = scenario_2_bundles["_pipeline_run_id"]

    step03_output = run_llm_agent(
        agent_name="legal_agent",
        bundle=scenario_2_bundles["legal_agent"],
        pipeline_run_id=pipeline_run_id,
    )
    assert step03_output.get("status") == "escalated", (
        f"scenario-2 STEP-03 expected status=escalated, got {step03_output!r}"
    )

    step04_bundle = splice_upstream(
        scenario_2_bundles["procurement_agent"],
        path="legal_output",
        value=step03_output,
    )
    step04_output = run_llm_agent(
        agent_name="procurement_agent",
        bundle=step04_bundle,
        pipeline_run_id=pipeline_run_id,
    )

    assert step04_output.get("status") == "escalated", (
        "legal_escalation_forces_procurement_escalation invariant violated; "
        f"step03_status=escalated step04_status={step04_output.get('status')!r} "
        f"full_step04={step04_output!r}"
    )
