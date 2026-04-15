"""Invariants: ``upstream_escalation_propagates_to_checklist`` and
``upstream_block_propagates_to_checklist``.

STEP-05 is the roll-up step. It does not re-decide anything — a single
upstream escalation or block must bubble up to ``overall_status``.

We test both directions on the scenario-1 bundle (whose upstream domain
outputs are all ``complete``), mutating one upstream status at a time so
each invariant is exercised in isolation.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any

import pytest


pytestmark = [pytest.mark.api, pytest.mark.layer_handoff]


UPSTREAM_AGENTS = ("it_security_agent", "legal_agent", "procurement_agent")


@pytest.mark.scenario1
@pytest.mark.parametrize("upstream", UPSTREAM_AGENTS)
def test_single_upstream_blocked_forces_overall_blocked(
    run_llm_agent,
    scenario_1_bundles: dict[str, Any],
    splice_upstream,
    upstream: str,
) -> None:
    """A ``blocked`` status on any one upstream domain output forces BLOCKED."""
    bundle = splice_upstream(
        scenario_1_bundles["checklist_assembler"],
        path=f"{upstream}.status",
        value="blocked",
    )
    # Provide a plausible error string so the bundle is well-formed.
    bundle = splice_upstream(bundle, path=f"{upstream}.error", value="simulated block")

    output = run_llm_agent(
        agent_name="checklist_assembler",
        bundle=bundle,
        pipeline_run_id=scenario_1_bundles["_pipeline_run_id"],
    )
    assert output.get("overall_status") == "BLOCKED", (
        f"upstream_block_propagates invariant violated for upstream={upstream}; "
        f"output={output!r}"
    )


@pytest.mark.scenario1
@pytest.mark.parametrize("upstream", UPSTREAM_AGENTS)
def test_single_upstream_escalated_forces_overall_escalated(
    run_llm_agent,
    scenario_1_bundles: dict[str, Any],
    splice_upstream,
    upstream: str,
) -> None:
    """An ``escalated`` status on any one upstream domain output must bubble up."""
    bundle = splice_upstream(
        scenario_1_bundles["checklist_assembler"],
        path=f"{upstream}.status",
        value="escalated",
    )
    output = run_llm_agent(
        agent_name="checklist_assembler",
        bundle=bundle,
        pipeline_run_id=scenario_1_bundles["_pipeline_run_id"],
    )
    assert output.get("overall_status") == "ESCALATED", (
        f"upstream_escalation_propagates invariant violated for upstream={upstream}; "
        f"output={output!r}"
    )
