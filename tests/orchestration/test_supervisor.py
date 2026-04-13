from __future__ import annotations

from orchestration.demo import run_demo
from orchestration.models.enums import AuditEventType, RunStatus, StepId, StepStatus
from orchestration.supervisor import Supervisor


def test_supervisor_demo_runs_happy_path(repo_root):
    result = run_demo()

    assert result["overall_status"] == "COMPLETE"
    assert result["step_statuses"]["STEP-06"] == "COMPLETE"
    assert result["final_output"]["status"] == "complete"
    assert result["audit_entry_count"] > 10


def test_supervisor_default_questionnaire_escalates_at_security(mock_documents_dir, repo_root):
    supervisor = Supervisor(
        repo_root=repo_root,
        questionnaire_path=mock_documents_dir / "OptiChain_VSQ_001_v2_1.json",
    )

    state = supervisor.run()

    assert state.overall_status is RunStatus.ESCALATED
    assert state.step_statuses[StepId.STEP_01] is StepStatus.COMPLETE
    assert state.step_statuses[StepId.STEP_02] is StepStatus.ESCALATED
    assert state.step_statuses[StepId.STEP_03] is StepStatus.PENDING
    assert state.determinations["step_02_security_classification"]["status"] == "escalated"
    assert any(entry.event_type is AuditEventType.RETRIEVAL for entry in supervisor.audit_logger.entries)
    assert any(entry.event_type is AuditEventType.ESCALATION for entry in supervisor.audit_logger.entries)
