"""IT Security (STEP-02) acceptance checks.

From the testing prompt's Layer-3 table:
  * A-03           — REGULATED data forbids fast-track.
  * A-03 variant   — AMBIGUOUS ERP type forbids fast-track.
  * A-04 (shared)  — no PRIMARY citation from a Tier-3 source.
"""

from __future__ import annotations

from typing import Any

import pytest

from tests.support.bundle_builder import set_value


pytestmark = [pytest.mark.api, pytest.mark.layer_acceptance]


AGENT = "it_security_agent"


@pytest.mark.scenario2
def test_a03_regulated_data_forbids_fast_track(
    run_llm_agent,
    scenario_2_bundles: dict[str, Any],
) -> None:
    """A-03: REGULATED data classification must pin fast_track_eligible=False."""
    output = run_llm_agent(
        agent_name=AGENT,
        bundle=scenario_2_bundles[AGENT],
        pipeline_run_id=scenario_2_bundles["_pipeline_run_id"],
    )
    assert output.get("data_classification") == "REGULATED", (
        f"scenario-2 bundle did not classify REGULATED; output={output!r}"
    )
    assert output.get("fast_track_eligible") is False, (
        f"A-03 violated: REGULATED data was fast-tracked; output={output!r}"
    )


@pytest.mark.scenario1
def test_a03_variant_ambiguous_erp_forbids_fast_track(
    run_llm_agent,
    scenario_1_bundles: dict[str, Any],
) -> None:
    """A-03 variant: AMBIGUOUS integration type also blocks fast-track."""
    bundle = set_value(
        scenario_1_bundles[AGENT],
        "questionnaire.integration_details.erp_type",
        "AMBIGUOUS",
    )
    # Also overwrite the supervisor-captured integration_description so the
    # agent has a reason to classify AMBIGUOUS rather than EXPORT_ONLY.
    bundle = set_value(
        bundle,
        "questionnaire.integration_details.integration_description",
        "Vendor may deploy an extraction agent with service-account credentials "
        "to pull ERP data on a recurring schedule.",
    )
    output = run_llm_agent(
        agent_name=AGENT,
        bundle=bundle,
        pipeline_run_id=scenario_1_bundles["_pipeline_run_id"],
    )
    assert output.get("fast_track_eligible") is False, (
        f"A-03 variant violated: AMBIGUOUS ERP type was fast-tracked; output={output!r}"
    )


@pytest.mark.scenario1
def test_a04_no_primary_tier3_citation_scenario_1(
    run_llm_agent,
    scenario_1_bundles: dict[str, Any],
    assert_no_primary_tier3_citation,
) -> None:
    output = run_llm_agent(
        agent_name=AGENT,
        bundle=scenario_1_bundles[AGENT],
        pipeline_run_id=scenario_1_bundles["_pipeline_run_id"],
    )
    assert_no_primary_tier3_citation(output)


@pytest.mark.scenario2
def test_a04_no_primary_tier3_citation_scenario_2(
    run_llm_agent,
    scenario_2_bundles: dict[str, Any],
    assert_no_primary_tier3_citation,
) -> None:
    output = run_llm_agent(
        agent_name=AGENT,
        bundle=scenario_2_bundles[AGENT],
        pipeline_run_id=scenario_2_bundles["_pipeline_run_id"],
    )
    assert_no_primary_tier3_citation(output)
