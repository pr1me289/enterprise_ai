"""Checklist Assembler (STEP-05) acceptance checks.

From the testing prompt's Layer-3 table:
  * A-01 — one upstream step escalated ⇒ overall_status=ESCALATED, never COMPLETE.
  * A-05 — one upstream domain output missing ⇒ overall_status=BLOCKED.
"""

from __future__ import annotations

from typing import Any

import pytest

from tests.support.bundle_builder import drop_key, set_value


pytestmark = [pytest.mark.api, pytest.mark.layer_acceptance, pytest.mark.scenario1]


AGENT = "checklist_assembler"

UPSTREAM_AGENTS = ("it_security_agent", "legal_agent", "procurement_agent")


@pytest.mark.parametrize("upstream", UPSTREAM_AGENTS)
def test_a01_single_escalation_forces_escalated(
    run_llm_agent,
    scenario_1_bundles: dict[str, Any],
    upstream: str,
    report_acceptance,
) -> None:
    bundle = set_value(scenario_1_bundles[AGENT], f"{upstream}.status", "escalated")
    output = run_llm_agent(
        agent_name=AGENT,
        bundle=bundle,
        pipeline_run_id=scenario_1_bundles["_pipeline_run_id"],
    )
    overall = output.get("overall_status")
    report_acceptance(
        check_id="A-01",
        agent=AGENT,
        passed=(overall == "ESCALATED" and overall != "COMPLETE"),
        detail=f"upstream={upstream} overall_status={overall!r}",
    )


@pytest.mark.parametrize("upstream", UPSTREAM_AGENTS)
def test_a05_missing_domain_output_forces_blocked(
    run_llm_agent,
    scenario_1_bundles: dict[str, Any],
    upstream: str,
    report_acceptance,
) -> None:
    bundle = drop_key(scenario_1_bundles[AGENT], upstream)
    output = run_llm_agent(
        agent_name=AGENT,
        bundle=bundle,
        pipeline_run_id=scenario_1_bundles["_pipeline_run_id"],
    )
    overall = output.get("overall_status")
    report_acceptance(
        check_id="A-05",
        agent=AGENT,
        passed=(overall == "BLOCKED"),
        detail=f"missing_upstream={upstream} overall_status={overall!r}",
    )
