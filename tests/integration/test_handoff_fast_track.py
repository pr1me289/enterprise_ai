"""Invariant: ``fast_track_passthrough``.

STEP-04.fast_track_eligible must equal STEP-02.fast_track_eligible. The
procurement agent must not re-decide eligibility on its own; it must carry
forward the upstream determination from IT Security.

We verify this by:
  1. Running STEP-02 for real on the scenario-1 bundle.
  2. Splicing STEP-02's output into the STEP-04 bundle as
     ``it_security_output``.
  3. Running STEP-04 for real.
  4. Asserting both agents agree on the boolean.
"""

from __future__ import annotations

from typing import Any

import pytest


pytestmark = [pytest.mark.api, pytest.mark.layer_handoff, pytest.mark.scenario1]


def test_fast_track_passthrough_scenario_1(
    run_llm_agent,
    scenario_1_bundles: dict[str, Any],
    splice_upstream,
    report_handoff,
) -> None:
    pipeline_run_id = scenario_1_bundles["_pipeline_run_id"]

    # Run STEP-02 for real.
    step02_output = run_llm_agent(
        agent_name="it_security_agent",
        bundle=scenario_1_bundles["it_security_agent"],
        pipeline_run_id=pipeline_run_id,
    )
    upstream_flag = step02_output.get("fast_track_eligible")
    assert upstream_flag is True, (
        f"scenario-1 STEP-02 expected fast_track_eligible=True, got {step02_output!r}"
    )

    # Splice STEP-02's output into the STEP-04 bundle and run STEP-04.
    step04_bundle = splice_upstream(
        scenario_1_bundles["procurement_agent"],
        path="it_security_output",
        value=step02_output,
    )
    step04_output = run_llm_agent(
        agent_name="procurement_agent",
        bundle=step04_bundle,
        pipeline_run_id=pipeline_run_id,
    )

    downstream_flag = step04_output.get("fast_track_eligible")
    report_handoff(
        invariant="fast_track_passthrough",
        upstream="STEP-02",
        downstream="STEP-04",
        passed=(downstream_flag == upstream_flag),
        detail=f"step02={upstream_flag!r} step04={downstream_flag!r}",
    )
