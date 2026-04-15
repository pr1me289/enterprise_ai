"""End-to-end real-API pipeline run for Scenario 1.

Drives the Supervisor through all six steps against the actual Anthropic
API using ``AnthropicLLMAdapter`` — this is the Layer-4 test that closes
the loop between the per-agent unit suite, the handoff invariants, and
the deterministic mock-pipeline harness in ``test_harness/``.

The assertions are intentionally narrow (status roll-up only) — per-field
correctness lives in the Layer-1 unit tests. If this test regresses it
means the pipeline scaffolding broke, not that a single agent's prompt
needs re-tuning.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest


pytestmark = [pytest.mark.api, pytest.mark.full_pipeline, pytest.mark.scenario1]


REPO_ROOT = Path(__file__).resolve().parents[2]


def test_scenario_1_full_pipeline_runs_to_completion(anthropic_client, live_monitor) -> None:
    from agents.llm_caller import AnthropicLLMAdapter
    from orchestration.models.enums import StepId
    from orchestration.scenarios import complete_demo_scenario
    from orchestration.supervisor import Supervisor

    fx = complete_demo_scenario()
    questionnaire_path = REPO_ROOT / "mock_documents" / "OptiChain_VSQ_001_v2_1.json"

    adapter = AnthropicLLMAdapter(
        repo_root=REPO_ROOT,
        client=anthropic_client,
    )
    supervisor = Supervisor(
        repo_root=REPO_ROOT,
        questionnaire_path=questionnaire_path,
        chunk_dir=REPO_ROOT / "data" / "processed" / "chunks",
        questionnaire_overrides=fx.questionnaire_overrides,
        llm_adapter=adapter,
    )
    supervisor.run()

    # Stream a PIPELINE_STEP event per step for Layer-4 visibility. The event
    # mirrors the shape emitted by the mock-harness console monitor so the
    # two layers render identically.
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

    # STEP-05 should have run and produced a COMPLETE roll-up.
    step05_bundle = supervisor.last_bundle_by_step.get(StepId.STEP_05)
    assert step05_bundle is not None, "STEP-05 did not execute in full pipeline run"
    step05_output = supervisor.state.determinations.get("step_05_checklist") or {}
    assert step05_output.get("overall_status") == "COMPLETE", (
        f"scenario-1 full pipeline did not complete the roll-up; "
        f"step05_output={step05_output!r}"
    )

    # STEP-06 should also have run.
    step06_output = supervisor.state.determinations.get("step_06_guidance") or {}
    assert step06_output.get("status") == "complete", (
        f"scenario-1 full pipeline did not complete STEP-06; "
        f"step06_output={step06_output!r}"
    )
