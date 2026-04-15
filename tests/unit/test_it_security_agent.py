"""Layer 1 per-agent unit tests for ``it_security_agent`` (STEP-02).

Covered:
  * Scenario 1 happy path — UNREGULATED / EXPORT_ONLY / TIER_3 / fast_track.
  * Scenario 2 escalated path — REGULATED / AMBIGUOUS / UNCLASSIFIED_PENDING_REVIEW.
  * Missing ``questionnaire`` upstream → the agent must not invent data and
    should return a non-``complete`` status.
  * Data-classification forcing function — if ``eu_personal_data_flag=true``
    the agent must surface ``REGULATED`` regardless of self-reported value.

Every test is gated on ``@pytest.mark.api`` (real Anthropic call) and tagged
``layer_unit`` so ``pytest -m "layer_unit and api"`` picks them up.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any

import pytest

from tests.support.bundle_builder import drop_key, set_value


pytestmark = [pytest.mark.api, pytest.mark.layer_unit]


AGENT = "it_security_agent"


# ---------------------------------------------------------------------------
# Scenario 1: Clean governed completion
# ---------------------------------------------------------------------------


@pytest.mark.scenario1
def test_scenario_1_happy_path(
    invoke_and_assert,
    scenario_1_bundles: dict[str, Any],
) -> None:
    bundle = scenario_1_bundles[AGENT]
    pipeline_run_id = scenario_1_bundles["_pipeline_run_id"]
    invoke_and_assert(
        scenario="scenario_1",
        agent_name=AGENT,
        bundle=bundle,
        pipeline_run_id=pipeline_run_id,
    )


# ---------------------------------------------------------------------------
# Scenario 2: Escalated / regulated
# ---------------------------------------------------------------------------


@pytest.mark.scenario2
def test_scenario_2_escalated_path(
    invoke_and_assert,
    scenario_2_bundles: dict[str, Any],
) -> None:
    bundle = scenario_2_bundles[AGENT]
    pipeline_run_id = scenario_2_bundles["_pipeline_run_id"]
    invoke_and_assert(
        scenario="scenario_2",
        agent_name=AGENT,
        bundle=bundle,
        pipeline_run_id=pipeline_run_id,
    )


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


@pytest.mark.scenario1
def test_missing_questionnaire_blocks(
    invoke_raw,
    scenario_1_bundles: dict[str, Any],
) -> None:
    """Dropping the entire ``questionnaire`` subtree should not produce a
    ``complete`` status — the agent lacks the signals required to decide.
    """
    bundle = scenario_1_bundles[AGENT]
    mutated = drop_key(bundle, "questionnaire")
    output = invoke_raw(
        agent_name=AGENT,
        bundle=mutated,
        pipeline_run_id=scenario_1_bundles["_pipeline_run_id"],
    )
    assert output.get("status") != "complete", (
        f"agent returned status=complete despite missing questionnaire; output={output!r}"
    )


@pytest.mark.scenario1
def test_eu_personal_data_forces_regulated(
    invoke_raw,
    scenario_1_bundles: dict[str, Any],
) -> None:
    """Flipping ``eu_personal_data_flag`` to True on the S1 bundle must force
    the classification toward REGULATED and preclude a fast-track result.

    This catches drift where the agent over-weights the self-reported
    classification field and ignores the EU-subjects trigger.
    """
    bundle = scenario_1_bundles[AGENT]
    mutated = set_value(bundle, "questionnaire.eu_personal_data_flag", True)
    mutated = set_value(mutated, "questionnaire.data_subjects_eu", True)
    output = invoke_raw(
        agent_name=AGENT,
        bundle=mutated,
        pipeline_run_id=scenario_1_bundles["_pipeline_run_id"],
    )
    # Either REGULATED outright, or the agent should surface EU subjects and
    # refuse fast-track. Both outcomes are acceptable — but UNREGULATED +
    # fast_track is not.
    is_regulated = output.get("data_classification") == "REGULATED"
    eu_present = output.get("eu_personal_data_present") == "YES"
    fast_track = output.get("fast_track_eligible") is True
    assert is_regulated or eu_present, (
        f"agent ignored EU personal data flag; output={output!r}"
    )
    if eu_present or is_regulated:
        assert not fast_track, (
            f"agent fast-tracked a vendor with EU personal data; output={output!r}"
        )
