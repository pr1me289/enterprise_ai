"""Runnable first-pass orchestration demo."""

from __future__ import annotations

import json
from pathlib import Path

from orchestration.mocks import ScenarioIndexedBackend, ScenarioLLMAdapter
from orchestration.scenarios import get_scenario_fixture
from orchestration.supervisor import Supervisor


def run_demo_scenario(name: str) -> dict:
    repo_root = Path(__file__).resolve().parents[2]
    scenario = get_scenario_fixture(name)
    supervisor = Supervisor(
        repo_root=repo_root,
        questionnaire_path=repo_root / "mock_documents" / "OptiChain_VSQ_001_v2_1.json",
        questionnaire_overrides=scenario.questionnaire_overrides,
        indexed_backend=ScenarioIndexedBackend(results=scenario.indexed_results) if scenario.indexed_results else None,
        llm_adapter=ScenarioLLMAdapter(outputs=scenario.agent_outputs),
    )
    state = supervisor.run()
    return {
        "scenario": scenario.name,
        "pipeline_run_id": state.pipeline_run_id,
        "overall_status": state.overall_status.value,
        "step_statuses": {step.value: status.value for step, status in state.step_statuses.items()},
        "final_output": state.determinations["step_06_guidance"] or state.determinations["step_05_checklist"],
        "audit_entry_count": len(supervisor.audit_logger.entries),
    }


def run_demo() -> dict:
    return run_demo_scenario("complete_demo")


def run_all_demo_scenarios() -> list[dict]:
    return [
        run_demo_scenario("complete_demo"),
        run_demo_scenario("escalated_security"),
    ]


if __name__ == "__main__":
    print(json.dumps(run_all_demo_scenarios(), indent=2, sort_keys=True))
