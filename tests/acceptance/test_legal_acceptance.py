"""Legal (STEP-03) acceptance checks.

From the testing prompt's Layer-3 table:
  * A-02 — DPA required + no executed DPA ⇒ dpa_blocker=true.
  * A-03 — nda_status != EXECUTED          ⇒ nda_blocker=true.
  * A-07 — dpa_blocker=true                ⇒ status=escalated, never complete.
"""

from __future__ import annotations

from typing import Any

import pytest


pytestmark = [pytest.mark.api, pytest.mark.layer_acceptance, pytest.mark.scenario2]


AGENT = "legal_agent"


def test_a02_dpa_required_plus_not_executed_sets_blocker(
    run_llm_agent,
    scenario_2_bundles: dict[str, Any],
) -> None:
    output = run_llm_agent(
        agent_name=AGENT,
        bundle=scenario_2_bundles[AGENT],
        pipeline_run_id=scenario_2_bundles["_pipeline_run_id"],
    )
    assert output.get("dpa_required") is True, (
        f"A-02 precondition not met (dpa_required != True); output={output!r}"
    )
    assert output.get("dpa_blocker") is True, (
        f"A-02 violated: dpa_required=True but dpa_blocker!=True; output={output!r}"
    )


def test_a03_nda_not_executed_sets_blocker(
    run_llm_agent,
    scenario_2_bundles: dict[str, Any],
) -> None:
    output = run_llm_agent(
        agent_name=AGENT,
        bundle=scenario_2_bundles[AGENT],
        pipeline_run_id=scenario_2_bundles["_pipeline_run_id"],
    )
    assert output.get("nda_status") != "EXECUTED", (
        f"A-03 precondition not met (nda_status == EXECUTED); output={output!r}"
    )
    assert output.get("nda_blocker") is True, (
        f"A-03 violated: nda_status!=EXECUTED but nda_blocker!=True; output={output!r}"
    )


def test_a07_dpa_blocker_forces_escalated_never_complete(
    run_llm_agent,
    scenario_2_bundles: dict[str, Any],
) -> None:
    output = run_llm_agent(
        agent_name=AGENT,
        bundle=scenario_2_bundles[AGENT],
        pipeline_run_id=scenario_2_bundles["_pipeline_run_id"],
    )
    assert output.get("dpa_blocker") is True, (
        f"A-07 precondition not met (dpa_blocker != True); output={output!r}"
    )
    status = output.get("status")
    assert status == "escalated", (
        f"A-07 violated: dpa_blocker=True must force status=escalated, "
        f"got status={status!r}; output={output!r}"
    )
    assert status != "complete", (
        f"A-07 violated: dpa_blocker=True must not return status=complete; "
        f"output={output!r}"
    )
