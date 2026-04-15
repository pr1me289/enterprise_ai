"""Procurement (STEP-04) acceptance checks.

From the testing prompt's Layer-3 table:
  * A-02 — Scenario 1 paired run: STEP-04.fast_track_eligible exactly equals
           STEP-02.fast_track_eligible. This is the *paired* form of the
           handoff invariant; the unit-level form lives in
           tests/integration/test_handoff_fast_track.py.
  * A-04 — No PRIMARY citation with a Tier-3 source_id.
"""

from __future__ import annotations

from typing import Any

import pytest


pytestmark = [pytest.mark.api, pytest.mark.layer_acceptance]


AGENT = "procurement_agent"


@pytest.mark.scenario1
def test_a02_fast_track_passthrough_scenario_1(
    run_llm_agent,
    scenario_1_bundles: dict[str, Any],
    report_acceptance,
) -> None:
    """Paired-run equality: STEP-04.fast_track_eligible == STEP-02.fast_track_eligible."""
    pipeline_run_id = scenario_1_bundles["_pipeline_run_id"]

    step02 = run_llm_agent(
        agent_name="it_security_agent",
        bundle=scenario_1_bundles["it_security_agent"],
        pipeline_run_id=pipeline_run_id,
    )
    step04 = run_llm_agent(
        agent_name=AGENT,
        bundle=scenario_1_bundles[AGENT],
        pipeline_run_id=pipeline_run_id,
    )
    report_acceptance(
        check_id="A-02",
        agent=AGENT,
        passed=(step02.get("fast_track_eligible") == step04.get("fast_track_eligible")),
        detail=f"step02={step02.get('fast_track_eligible')!r} step04={step04.get('fast_track_eligible')!r}",
    )


@pytest.mark.scenario1
def test_a04_no_primary_tier3_citation_scenario_1(
    run_llm_agent,
    scenario_1_bundles: dict[str, Any],
    assert_no_primary_tier3_citation,
    report_acceptance,
) -> None:
    output = run_llm_agent(
        agent_name=AGENT,
        bundle=scenario_1_bundles[AGENT],
        pipeline_run_id=scenario_1_bundles["_pipeline_run_id"],
    )
    try:
        assert_no_primary_tier3_citation(output)
        report_acceptance(check_id="A-04", agent=AGENT, passed=True, detail="scenario_1")
    except AssertionError as exc:
        report_acceptance(check_id="A-04", agent=AGENT, passed=False, detail=f"scenario_1: {exc}")
        raise


@pytest.mark.scenario2
def test_a04_no_primary_tier3_citation_scenario_2(
    run_llm_agent,
    scenario_2_bundles: dict[str, Any],
    assert_no_primary_tier3_citation,
    report_acceptance,
) -> None:
    output = run_llm_agent(
        agent_name=AGENT,
        bundle=scenario_2_bundles[AGENT],
        pipeline_run_id=scenario_2_bundles["_pipeline_run_id"],
    )
    try:
        assert_no_primary_tier3_citation(output)
        report_acceptance(check_id="A-04", agent=AGENT, passed=True, detail="scenario_2")
    except AssertionError as exc:
        report_acceptance(check_id="A-04", agent=AGENT, passed=False, detail=f"scenario_2: {exc}")
        raise
