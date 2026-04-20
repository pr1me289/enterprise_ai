"""End-to-end real-API pipeline runs.

Parameterised across scenarios. Each case drives the Supervisor through
all six steps against the actual Anthropic API using
``AnthropicLLMAdapter`` — the Layer-4 closure between the per-agent unit
suite, the handoff invariants, and the deterministic mock-pipeline
harness in ``test_harness/``.

Per-step outputs are recorded via ``tests/support/pipeline_recorder.py``
and evaluated via ``tests/support/pipeline_evaluator.py`` so we inherit
the per-agent contract checks. Scenario-level assertions verify the
orchestration-layer outcome: STEP-05 COMPLETE for the happy path;
ESCALATED halt with no downstream execution for scenario_2.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest


pytestmark = [pytest.mark.api, pytest.mark.full_pipeline]


REPO_ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class ScenarioCase:
    name: str
    overrides_factory: str  # callable name on the scenarios/bundle_builder module
    overrides_source: str   # 'scenarios' or 'bundle_builder'
    expected_overall_status: str
    expected_terminal_statuses: dict[str, str]
    marker: str


_SCENARIO_CASES: tuple[ScenarioCase, ...] = (
    ScenarioCase(
        name="scenario_1",
        overrides_factory="complete_demo_scenario",
        overrides_source="scenarios",
        expected_overall_status="COMPLETE",
        expected_terminal_statuses={
            "STEP-01": "COMPLETE",
            "STEP-02": "COMPLETE",
            "STEP-03": "COMPLETE",
            "STEP-04": "COMPLETE",
            "STEP-05": "COMPLETE",
            "STEP-06": "COMPLETE",
        },
        marker="scenario1",
    ),
    ScenarioCase(
        name="scenario_2",
        overrides_factory="scenario_2_questionnaire_overrides",
        overrides_source="bundle_builder",
        expected_overall_status="ESCALATED",
        # The orchestration contract — whichever upstream step escalates,
        # every downstream step must remain PENDING. We don't pin the
        # exact halt step because scenario_2 can legitimately escalate at
        # STEP-02 (ambiguous tier) or STEP-03 (DPA blocker) depending on
        # how the live IT Security agent resolves the ambiguity. The
        # supervisor's obligation is the same either way: halt + return
        # ESCALATED to I/O.
        expected_terminal_statuses={},  # enforced per-case below
        marker="scenario2",
    ),
)


def _load_overrides(case: ScenarioCase) -> dict[str, Any]:
    if case.overrides_source == "scenarios":
        from orchestration.scenarios import complete_demo_scenario  # type: ignore

        return complete_demo_scenario().questionnaire_overrides
    if case.overrides_source == "bundle_builder":
        from tests.support.bundle_builder import scenario_2_questionnaire_overrides

        return scenario_2_questionnaire_overrides()
    raise RuntimeError(f"unknown overrides_source: {case.overrides_source}")


@pytest.mark.parametrize(
    "case",
    [
        pytest.param(c, marks=getattr(pytest.mark, c.marker), id=c.name)
        for c in _SCENARIO_CASES
    ],
)
def test_pipeline_end_to_end(case: ScenarioCase, anthropic_client, live_monitor) -> None:
    from agents.llm_caller import AnthropicLLMAdapter
    from orchestration.models.enums import StepId, StepStatus
    from orchestration.supervisor import Supervisor

    from tests.support.pipeline_evaluator import (
        evaluate_pipeline_run,
        format_failures,
        verdicts_from_reports,
    )
    from tests.support.pipeline_recorder import (
        next_pipeline_run_number,
        record_pipeline_run,
    )
    from tests.support.pipeline_results_writer import append_results_block

    questionnaire_path = REPO_ROOT / "mock_documents" / "OptiChain_VSQ_001_v2_1.json"
    overrides = _load_overrides(case)

    # Chunks are organised per-scenario on disk (data/processed/scenario_1,
    # data/processed/scenario_2, ...). The Supervisor's default chunk_dir
    # fallback (data/processed/chunks) does not exist, so point it at the
    # scenario-specific directory here.
    chunk_dir = REPO_ROOT / "data" / "processed" / case.name / "chunks"
    assert chunk_dir.is_dir(), (
        f"chunk directory not found for {case.name}: {chunk_dir}. "
        f"Verify data/processed/{case.name}/chunks/ exists."
    )

    adapter = AnthropicLLMAdapter(
        repo_root=REPO_ROOT,
        client=anthropic_client,
    )
    supervisor = Supervisor(
        repo_root=REPO_ROOT,
        questionnaire_path=questionnaire_path,
        chunk_dir=chunk_dir,
        questionnaire_overrides=overrides,
        llm_adapter=adapter,
    )
    supervisor.run()

    # Emit PIPELINE_STEP events for every step so the live monitor matches
    # the shape produced by the mock-harness console monitor.
    step_keys = (
        (StepId.STEP_01, "step_01_intake"),
        (StepId.STEP_02, "step_02_security_classification"),
        (StepId.STEP_03, "step_03_legal"),
        (StepId.STEP_04, "step_04_procurement"),
        (StepId.STEP_05, "step_05_checklist"),
        (StepId.STEP_06, "step_06_guidance"),
    )
    for step_id, key in step_keys:
        ran = supervisor.last_bundle_by_step.get(step_id) is not None
        output = supervisor.state.determinations.get(key) or {}
        status = (
            output.get("overall_status")
            or output.get("status")
            or ("RAN" if ran else "SKIPPED")
        )
        live_monitor.pipeline_step(
            step_id=step_id.value,
            event="step",
            determination=key,
            ran=ran,
            status=status,
        )

    # --- Per-step evaluator assertions (lifted from per_agent_test_env) ---
    reports = evaluate_pipeline_run(scenario=case.name, supervisor=supervisor)
    verdicts = verdicts_from_reports(reports)
    record_dir = REPO_ROOT / "tests" / "recorded_responses" / "full_pipeline"
    pipeline_run_number = next_pipeline_run_number(record_dir)
    record_paths = record_pipeline_run(
        scenario=case.name,
        supervisor=supervisor,
        record_dir=record_dir,
        verdicts=verdicts,
        pipeline_run_number=pipeline_run_number,
    )
    append_results_block(
        results_path=REPO_ROOT / "results" / "full_pipeline_test_results.md",
        pipeline_run_number=pipeline_run_number,
        scenario=case.name,
        supervisor=supervisor,
        reports=reports,
        record_paths=record_paths,
        repo_root=REPO_ROOT,
    )
    per_step_failures = format_failures(reports)
    assert not per_step_failures, (
        f"per-step evaluator failures for {case.name}:\n{per_step_failures}"
    )

    # --- Orchestration-layer assertions ---
    actual_overall = supervisor.state.overall_status.value
    assert actual_overall == case.expected_overall_status, (
        f"{case.name}: overall_status={actual_overall!r} "
        f"!= expected {case.expected_overall_status!r}"
    )

    if case.name == "scenario_1":
        # Every step must be COMPLETE, and STEP-05/06 must produce their
        # expected terminal shape.
        for step_str, expected in case.expected_terminal_statuses.items():
            actual = supervisor.state.step_statuses[StepId(step_str)].value
            assert actual == expected, (
                f"{case.name}: {step_str} status={actual!r} != expected {expected!r}"
            )
        step05_output = supervisor.state.determinations.get("step_05_checklist") or {}
        assert step05_output.get("overall_status") == "COMPLETE", (
            f"{case.name} did not complete the STEP-05 roll-up; "
            f"step05_output={step05_output!r}"
        )
        step06_output = supervisor.state.determinations.get("step_06_guidance") or {}
        assert step06_output.get("status") == "complete", (
            f"{case.name} did not complete STEP-06; "
            f"step06_output={step06_output!r}"
        )
    elif case.name == "scenario_2":
        # Orchestration contract: once a step escalates, every downstream
        # step remains PENDING (supervisor halts), and overall_status
        # propagates ESCALATED back to I/O.
        step_ids = [StepId.STEP_01, StepId.STEP_02, StepId.STEP_03,
                    StepId.STEP_04, StepId.STEP_05, StepId.STEP_06]
        escalated_idx = None
        for i, sid in enumerate(step_ids):
            if supervisor.state.step_statuses[sid] == StepStatus.ESCALATED:
                escalated_idx = i
                break
        assert escalated_idx is not None, (
            f"{case.name}: no step transitioned to ESCALATED — "
            f"statuses={ {s.value: supervisor.state.step_statuses[s].value for s in step_ids} }"
        )
        for sid in step_ids[escalated_idx + 1:]:
            s = supervisor.state.step_statuses[sid]
            assert s == StepStatus.PENDING, (
                f"{case.name}: downstream step {sid.value} "
                f"has status={s.value!r} — expected PENDING after halt at "
                f"{step_ids[escalated_idx].value}"
            )
