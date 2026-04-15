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
    report_acceptance,
) -> None:
    output = run_llm_agent(
        agent_name=AGENT,
        bundle=scenario_2_bundles[AGENT],
        pipeline_run_id=scenario_2_bundles["_pipeline_run_id"],
    )
    report_acceptance(
        check_id="A-02",
        agent=AGENT,
        passed=(output.get("dpa_required") is True and output.get("dpa_blocker") is True),
        detail=f"dpa_required={output.get('dpa_required')!r} dpa_blocker={output.get('dpa_blocker')!r}",
    )


def test_a03_nda_not_executed_sets_blocker(
    run_llm_agent,
    scenario_2_bundles: dict[str, Any],
    report_acceptance,
) -> None:
    output = run_llm_agent(
        agent_name=AGENT,
        bundle=scenario_2_bundles[AGENT],
        pipeline_run_id=scenario_2_bundles["_pipeline_run_id"],
    )
    nda_status = output.get("nda_status")
    nda_blocker = output.get("nda_blocker")
    report_acceptance(
        check_id="A-03",
        agent=AGENT,
        passed=(nda_status != "EXECUTED" and nda_blocker is True),
        detail=f"nda_status={nda_status!r} nda_blocker={nda_blocker!r}",
    )


def test_a07_dpa_blocker_forces_escalated_never_complete(
    run_llm_agent,
    scenario_2_bundles: dict[str, Any],
    report_acceptance,
) -> None:
    output = run_llm_agent(
        agent_name=AGENT,
        bundle=scenario_2_bundles[AGENT],
        pipeline_run_id=scenario_2_bundles["_pipeline_run_id"],
    )
    status = output.get("status")
    report_acceptance(
        check_id="A-07",
        agent=AGENT,
        passed=(output.get("dpa_blocker") is True and status == "escalated"),
        detail=f"dpa_blocker={output.get('dpa_blocker')!r} status={status!r}",
    )
