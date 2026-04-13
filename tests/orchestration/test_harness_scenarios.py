"""Pytest tests exercising the deterministic orchestration test harness.

These tests instantiate harness components directly (not subprocess) and
assert against the returned state/fixtures.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from orchestration.config.step_definitions import STEP_ORDER
from orchestration.models.enums import RunStatus, StepId, StepStatus
from test_harness.run_test_scenario import run_scenario
from test_harness.scenario_fixtures import (
    SCENARIO_1_COMPLETE,
    SCENARIO_2_ESCALATED,
    SCENARIO_BLOCKED_MISSING_QUESTIONNAIRE,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _run(scenario_name: str, tmp_path: Path) -> tuple[bool, object, list]:
    return run_scenario(scenario_name, artifacts_root=tmp_path)


# ---------------------------------------------------------------------------
# Scenario 1 — Complete
# ---------------------------------------------------------------------------

def test_scenario_1_complete_runs_to_complete(tmp_path):
    passed, state, _ = _run("scenario_1_complete", tmp_path)
    assert state.overall_status == RunStatus.COMPLETE
    assert passed, "Scenario 1 assertions failed"


def test_scenario_1_no_downstream_steps_after_complete(tmp_path):
    _, state, _ = _run("scenario_1_complete", tmp_path)
    # All steps should be COMPLETE — none PENDING after a full run
    for step_id in STEP_ORDER:
        assert state.step_statuses[step_id] == StepStatus.COMPLETE, (
            f"{step_id.value} is {state.step_statuses[step_id].value}, expected COMPLETE"
        )


def test_scenario_1_slack_thread4_excluded(tmp_path):
    """No Slack Thread 4 chunk should appear in admitted evidence bundles."""
    _, state, bundle_trace = _run("scenario_1_complete", tmp_path)
    for trace in bundle_trace:
        for chunk in trace.get("admitted_chunks", []):
            thread_id = chunk.get("extra_metadata", {}).get("thread_id", "")
            assert thread_id not in ("T4", "4", "thread_4"), (
                f"Thread 4 chunk admitted in {trace['step_id']}: {chunk['chunk_id']!r}"
            )


def test_scenario_1_slack_never_primary_evidence(tmp_path):
    """Slack (SLK-001) chunks must never be primary-citable."""
    _, state, bundle_trace = _run("scenario_1_complete", tmp_path)
    for trace in bundle_trace:
        for chunk in trace.get("admitted_chunks", []):
            if chunk["source_id"] == "SLK-001":
                assert not chunk.get("is_primary_citable"), (
                    f"SLK-001 chunk admitted as primary in {trace['step_id']}: "
                    f"{chunk['chunk_id']!r}"
                )


def test_scenario_1_bundle_trace_written(tmp_path):
    """bundle_trace.json must be written with at least one step entry."""
    import json

    _run("scenario_1_complete", tmp_path)
    # Find the written bundle_trace.json
    traces = list(tmp_path.glob("**/bundle_trace.json"))
    assert traces, "bundle_trace.json was not written"
    data = json.loads(traces[0].read_text())
    assert isinstance(data, list), "bundle_trace.json should contain a list"
    assert len(data) >= 6, f"Expected at least 6 step traces, got {len(data)}"


# ---------------------------------------------------------------------------
# Scenario 2 — Escalated
# ---------------------------------------------------------------------------

def test_scenario_2_escalated_halts_at_step_03(tmp_path):
    passed, state, _ = _run("scenario_2_escalated", tmp_path)
    assert state.overall_status == RunStatus.ESCALATED
    assert state.step_statuses[StepId.STEP_03] == StepStatus.ESCALATED
    assert passed, "Scenario 2 assertions failed"


def test_scenario_2_no_steps_after_escalation(tmp_path):
    _, state, _ = _run("scenario_2_escalated", tmp_path)
    # STEP-04 through STEP-06 must remain PENDING
    for step_id in (StepId.STEP_04, StepId.STEP_05, StepId.STEP_06):
        assert state.step_statuses[step_id] == StepStatus.PENDING, (
            f"{step_id.value} should be PENDING after escalation at STEP-03, "
            f"got {state.step_statuses[step_id].value}"
        )


# ---------------------------------------------------------------------------
# Scenario Blocked — Missing Questionnaire
# ---------------------------------------------------------------------------

def test_scenario_blocked_missing_questionnaire_halts_at_step_01(tmp_path):
    passed, state, _ = _run("scenario_blocked_missing_questionnaire", tmp_path)
    assert state.overall_status == RunStatus.BLOCKED
    assert state.step_statuses[StepId.STEP_01] == StepStatus.BLOCKED
    assert passed, "Blocked scenario assertions failed"


# ---------------------------------------------------------------------------
# Cross-scenario: all scenarios produce audit entries
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("scenario_name", [
    "scenario_1_complete",
    "scenario_2_escalated",
    "scenario_blocked_missing_questionnaire",
])
def test_all_scenarios_produce_audit_entries(scenario_name, tmp_path):
    """Each scenario run must emit at least one audit entry."""
    _, state, _ = _run(scenario_name, tmp_path)
    assert len(state.audit_refs) > 0, (
        f"No audit entries for scenario {scenario_name!r}"
    )
