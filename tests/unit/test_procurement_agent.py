"""Layer 1 per-agent unit tests for ``procurement_agent`` (STEP-04).

Covered:
  * Scenario 1 happy path — FAST_TRACK approval path.
  * Scenario 2 escalated path — STANDARD path, fast_track_eligible=false.
  * Missing ``legal_output`` upstream → blocked (cannot decide approval path
    without legal).
  * Fast-track passthrough — if the upstream security agent says
    ``fast_track_eligible=False`` the procurement agent must not flip it to
    True. This is the local mirror of the Layer-2 handoff invariant.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any

import pytest

from tests.support.bundle_builder import drop_key, set_value


pytestmark = [pytest.mark.api, pytest.mark.layer_unit]


AGENT = "procurement_agent"


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
def test_missing_legal_output_blocks(
    invoke_raw,
    scenario_1_bundles: dict[str, Any],
) -> None:
    """Procurement cannot decide the approval path without legal's verdict."""
    bundle = drop_key(scenario_1_bundles[AGENT], "legal_output")
    output = invoke_raw(
        agent_name=AGENT,
        bundle=bundle,
        pipeline_run_id=scenario_1_bundles["_pipeline_run_id"],
    )
    assert output.get("status") != "complete", (
        f"procurement agent returned complete without legal_output; output={output!r}"
    )


@pytest.mark.scenario_1
def test_upstream_false_fast_track_is_preserved(
    invoke_raw,
    scenario_1_bundles: dict[str, Any],
) -> None:
    """If IT security says ``fast_track_eligible=false`` procurement must
    respect that determination rather than re-deciding eligibility.
    """
    bundle = deepcopy(scenario_1_bundles[AGENT])
    bundle = set_value(bundle, "it_security_output.fast_track_eligible", False)
    bundle = set_value(
        bundle,
        "it_security_output.fast_track_rationale",
        "DISALLOWED_REGULATED_DATA",
    )
    output = invoke_raw(
        agent_name=AGENT,
        bundle=bundle,
        pipeline_run_id=scenario_1_bundles["_pipeline_run_id"],
    )
    assert output.get("fast_track_eligible") is False, (
        "procurement agent overrode upstream fast_track_eligible=False; "
        f"output={output!r}"
    )
