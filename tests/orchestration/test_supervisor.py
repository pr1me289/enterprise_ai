from __future__ import annotations

from orchestration.demo import run_all_demo_scenarios, run_demo_scenario
from orchestration.mocks import ScenarioIndexedBackend, ScenarioLLMAdapter
from orchestration.models.enums import AuditEventType
from orchestration.scenarios import complete_demo_scenario, escalated_security_scenario
from orchestration.supervisor import Supervisor


def test_supervisor_demo_runs_happy_path():
    scenario = complete_demo_scenario()
    result = run_demo_scenario(scenario.name)

    assert result["overall_status"] == scenario.expected_overall_status
    assert result["step_statuses"] == scenario.expected_step_statuses
    assert result["final_output"]["status"] == "complete"
    assert result["audit_entry_count"] > 10


def test_supervisor_default_questionnaire_escalates_at_security(mock_documents_dir, repo_root):
    scenario = escalated_security_scenario()
    supervisor = Supervisor(
        repo_root=repo_root,
        questionnaire_path=mock_documents_dir / "OptiChain_VSQ_001_v2_1.json",
        questionnaire_overrides=scenario.questionnaire_overrides,
        indexed_backend=ScenarioIndexedBackend(results=scenario.indexed_results),
        llm_adapter=ScenarioLLMAdapter(outputs=scenario.agent_outputs),
    )

    state = supervisor.run()

    assert state.overall_status.value == scenario.expected_overall_status
    assert {k.value: v.value for k, v in state.step_statuses.items()} == scenario.expected_step_statuses
    assert state.determinations["step_02_security_classification"]["status"] == "escalated"
    assert any(entry.event_type is AuditEventType.RETRIEVAL for entry in supervisor.audit_logger.entries)
    assert any(entry.event_type is AuditEventType.ESCALATION for entry in supervisor.audit_logger.entries)
    assert any(
        entry.event_type is AuditEventType.RUN_EVENT
        and entry.details["message"] == "Pipeline halted in escalated state"
        for entry in supervisor.audit_logger.entries
    )


def test_two_demo_scenarios_run_correctly():
    results = run_all_demo_scenarios()

    assert [item["scenario"] for item in results] == ["complete_demo", "escalated_security"]
    assert results[0]["overall_status"] == "COMPLETE"
    assert results[1]["overall_status"] == "ESCALATED"
