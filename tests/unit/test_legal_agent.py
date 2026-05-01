"""Layer 1 per-agent unit tests for ``legal_agent`` (STEP-03).

Covered:
  * Scenario 1 happy path — no DPA required, NDA executed.
  * Scenario 2 escalated path — DPA required + NDA pending blocker, with
    trigger rows A-01 / E-01 cited.
  * Missing ``security_output`` upstream → agent must not mint ``complete``.
  * DPA trigger injection — when DPA trigger rows are supplied on top of an
    S1 baseline, the agent must flip ``dpa_required`` to True.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any

import pytest

from tests.support.bundle_builder import drop_key, set_value


pytestmark = [pytest.mark.api, pytest.mark.layer_unit]


AGENT = "legal_agent"


# ---------------------------------------------------------------------------
# Scenarios
# ---------------------------------------------------------------------------


@pytest.mark.scenario_1
def test_scenario_1_happy_path(
    invoke_and_assert,
    scenario_1_bundles: dict[str, Any],
) -> None:
    bundle = scenario_1_bundles[AGENT]
    invoke_and_assert(
        scenario="scenario_1",
        agent_name=AGENT,
        bundle=bundle,
        pipeline_run_id=scenario_1_bundles["_pipeline_run_id"],
    )


@pytest.mark.scenario_2
def test_scenario_2_escalated_path(
    invoke_and_assert,
    scenario_2_bundles: dict[str, Any],
) -> None:
    bundle = scenario_2_bundles[AGENT]
    invoke_and_assert(
        scenario="scenario_2",
        agent_name=AGENT,
        bundle=bundle,
        pipeline_run_id=scenario_2_bundles["_pipeline_run_id"],
    )


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


@pytest.mark.scenario_1
def test_missing_security_output_blocks(
    invoke_raw,
    scenario_1_bundles: dict[str, Any],
) -> None:
    """STEP-03 must not run to completion without STEP-02's output."""
    bundle = drop_key(scenario_1_bundles[AGENT], "security_output")
    output = invoke_raw(
        agent_name=AGENT,
        bundle=bundle,
        pipeline_run_id=scenario_1_bundles["_pipeline_run_id"],
    )
    assert output.get("status") != "complete", (
        f"legal agent returned complete without security_output; output={output!r}"
    )


@pytest.mark.scenario_1
def test_dpa_trigger_flips_dpa_required(
    invoke_raw,
    scenario_1_bundles: dict[str, Any],
) -> None:
    """If the retrieval router injects a DPA trigger row into the bundle the
    agent must acknowledge the DPA requirement — even on an otherwise
    unregulated S1 flow — by setting ``dpa_required=true``.
    """
    bundle = deepcopy(scenario_1_bundles[AGENT])
    bundle = set_value(
        bundle,
        "dpa_trigger_rows",
        [
            {
                "row_id": "A-01",
                "matrix_id": "DPA-TM-001",
                "version": "1.3",
                "trigger_text": "EU personal data processed by vendor.",
            }
        ],
    )
    # Also nudge the upstream evidence so the agent cannot explain the trigger
    # away by appealing to the security_output.
    bundle = set_value(bundle, "questionnaire.eu_personal_data_flag", True)
    bundle = set_value(bundle, "questionnaire.data_subjects_eu", True)
    output = invoke_raw(
        agent_name=AGENT,
        bundle=bundle,
        pipeline_run_id=scenario_1_bundles["_pipeline_run_id"],
    )
    assert output.get("dpa_required") is True, (
        f"legal agent ignored DPA trigger row A-01; output={output!r}"
    )
