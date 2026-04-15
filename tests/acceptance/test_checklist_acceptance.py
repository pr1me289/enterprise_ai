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
) -> None:
    bundle = set_value(scenario_1_bundles[AGENT], f"{upstream}.status", "escalated")
    output = run_llm_agent(
        agent_name=AGENT,
        bundle=bundle,
        pipeline_run_id=scenario_1_bundles["_pipeline_run_id"],
    )
    overall = output.get("overall_status")
    assert overall == "ESCALATED", (
        f"A-01 violated for upstream={upstream}: overall_status={overall!r} "
        f"(expected ESCALATED); output={output!r}"
    )
    assert overall != "COMPLETE", (
        f"A-01 violated for upstream={upstream}: overall_status returned COMPLETE; "
        f"output={output!r}"
    )


@pytest.mark.parametrize("upstream", UPSTREAM_AGENTS)
def test_a05_missing_domain_output_forces_blocked(
    run_llm_agent,
    scenario_1_bundles: dict[str, Any],
    upstream: str,
) -> None:
    bundle = drop_key(scenario_1_bundles[AGENT], upstream)
    output = run_llm_agent(
        agent_name=AGENT,
        bundle=bundle,
        pipeline_run_id=scenario_1_bundles["_pipeline_run_id"],
    )
    assert output.get("overall_status") == "BLOCKED", (
        f"A-05 violated for missing upstream={upstream}; output={output!r}"
    )
