"""Step handler audit tests.

Covers per-handler requirements from orchestration_layer_build_prompt.md,
context_contract.md, and design_doc.md:

- Each handler's happy path (COMPLETE output)
- Each handler's escalation path (ESCALATED with EscalationPayload)
- Each handler's gate check (BLOCKED when prerequisites not met)
- Step 05 compiles all prior determinations
- Step 06 does not alter the checklist result
- Step 01 output uses Step01IntakeDetermination typed model fields
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from orchestration.mocks import ScenarioIndexedBackend, ScenarioLLMAdapter
from orchestration.models.determinations import Step01IntakeDetermination
from orchestration.models.enums import StepId, StepStatus
from orchestration.scenarios import complete_demo_scenario, escalated_security_scenario
from orchestration.supervisor import Supervisor


REPO_ROOT = Path(__file__).resolve().parents[2]
QUESTIONNAIRE_PATH = REPO_ROOT / "mock_documents" / "OptiChain_VSQ_001_v2_1.json"


def _make_supervisor(
    *,
    questionnaire_overrides: dict[str, Any] | None = None,
    indexed_results: dict | None = None,
    agent_outputs: dict[str, dict[str, Any]] | None = None,
) -> Supervisor:
    return Supervisor(
        repo_root=REPO_ROOT,
        questionnaire_path=QUESTIONNAIRE_PATH,
        questionnaire_overrides=questionnaire_overrides,
        indexed_backend=ScenarioIndexedBackend(results=indexed_results or {}),
        llm_adapter=ScenarioLLMAdapter(outputs=agent_outputs or {}),
    )


# ---------------------------------------------------------------------------
# Step 01 — Intake
# ---------------------------------------------------------------------------


class TestStep01Intake:
    def test_happy_path_complete(self, mock_documents_dir: Path, repo_root: Path) -> None:
        """Step 01 emits COMPLETE when questionnaire exists and is complete."""
        scenario = complete_demo_scenario()
        supervisor = Supervisor(
            repo_root=repo_root,
            questionnaire_path=mock_documents_dir / "OptiChain_VSQ_001_v2_1.json",
            questionnaire_overrides=scenario.questionnaire_overrides,
            indexed_backend=ScenarioIndexedBackend(results=scenario.indexed_results),
            llm_adapter=ScenarioLLMAdapter(outputs=scenario.agent_outputs),
        )
        state = supervisor.run()

        assert state.step_statuses[StepId.STEP_01] is StepStatus.COMPLETE
        intake_output = state.determinations["step_01_intake"]
        assert intake_output is not None
        # Must use typed Step01IntakeDetermination fields
        assert "questionnaire_valid" in intake_output
        assert "vendor_name" in intake_output
        assert "status" in intake_output
        assert "notes" in intake_output
        assert intake_output["questionnaire_valid"] is True
        assert intake_output["status"] == StepStatus.COMPLETE.value

    def test_step01_output_keys_match_typed_determination(
        self, mock_documents_dir: Path, repo_root: Path
    ) -> None:
        """Output dict keys must match Step01IntakeDetermination.to_dict() keys."""
        scenario = complete_demo_scenario()
        supervisor = Supervisor(
            repo_root=repo_root,
            questionnaire_path=mock_documents_dir / "OptiChain_VSQ_001_v2_1.json",
            questionnaire_overrides=scenario.questionnaire_overrides,
            indexed_backend=ScenarioIndexedBackend(results=scenario.indexed_results),
            llm_adapter=ScenarioLLMAdapter(outputs=scenario.agent_outputs),
        )
        supervisor.run()
        output = supervisor.state.determinations["step_01_intake"]
        assert output is not None
        expected_keys = set(Step01IntakeDetermination(
            questionnaire_valid=True, vendor_name="x", status="COMPLETE", notes=[]
        ).to_dict().keys())
        assert set(output.keys()) == expected_keys

    def test_gate_always_open(self, mock_documents_dir: Path, repo_root: Path) -> None:
        """Step 01 gate is always open (no prerequisites)."""
        scenario = complete_demo_scenario()
        supervisor = Supervisor(
            repo_root=repo_root,
            questionnaire_path=mock_documents_dir / "OptiChain_VSQ_001_v2_1.json",
            questionnaire_overrides=scenario.questionnaire_overrides,
            indexed_backend=ScenarioIndexedBackend(results=scenario.indexed_results),
            llm_adapter=ScenarioLLMAdapter(outputs=scenario.agent_outputs),
        )
        gate = supervisor.handlers[StepId.STEP_01].check_gate(supervisor.state)
        assert gate.allowed is True

    def test_vendor_name_propagated_to_pipeline_state(
        self, mock_documents_dir: Path, repo_root: Path
    ) -> None:
        """vendor_name from questionnaire is stored on PipelineState after Step 01."""
        scenario = complete_demo_scenario()
        supervisor = Supervisor(
            repo_root=repo_root,
            questionnaire_path=mock_documents_dir / "OptiChain_VSQ_001_v2_1.json",
            questionnaire_overrides=scenario.questionnaire_overrides,
            indexed_backend=ScenarioIndexedBackend(results=scenario.indexed_results),
            llm_adapter=ScenarioLLMAdapter(outputs=scenario.agent_outputs),
        )
        supervisor.run()
        assert supervisor.state.vendor_name is not None
        assert len(supervisor.state.vendor_name) > 0

    def test_blocked_when_questionnaire_missing_required_fields(
        self, mock_documents_dir: Path, repo_root: Path
    ) -> None:
        """Step 01 emits BLOCKED when required completeness fields are absent.

        Setting top-level questionnaire sections to non-dict values (strings)
        makes all nested field paths unresolvable, triggering missing_fields.
        """
        overrides = {
            # Replace dict sections with scalars so nested paths cannot be resolved
            "product_and_integration": "REMOVED",
            "data_handling": "REMOVED",
            "legal_and_contractual_status": "REMOVED",
            "contract_details": "REMOVED",
        }
        scenario = complete_demo_scenario()
        supervisor = Supervisor(
            repo_root=repo_root,
            questionnaire_path=mock_documents_dir / "OptiChain_VSQ_001_v2_1.json",
            questionnaire_overrides=overrides,
            indexed_backend=ScenarioIndexedBackend(results=scenario.indexed_results),
            llm_adapter=ScenarioLLMAdapter(outputs=scenario.agent_outputs),
        )
        supervisor.run()
        # Step 01 should be BLOCKED; subsequent steps should not advance past it
        assert supervisor.state.step_statuses[StepId.STEP_01] is StepStatus.BLOCKED
        intake_output = supervisor.state.determinations["step_01_intake"]
        assert intake_output is not None
        assert intake_output["questionnaire_valid"] is False
        assert intake_output["status"] == StepStatus.BLOCKED.value
        assert len(intake_output["notes"]) > 0


# ---------------------------------------------------------------------------
# Step 02 — Security
# ---------------------------------------------------------------------------


class TestStep02Security:
    def test_happy_path_complete(self, mock_documents_dir: Path, repo_root: Path) -> None:
        """Step 02 emits COMPLETE for a low-risk export-only scenario."""
        scenario = complete_demo_scenario()
        supervisor = Supervisor(
            repo_root=repo_root,
            questionnaire_path=mock_documents_dir / "OptiChain_VSQ_001_v2_1.json",
            questionnaire_overrides=scenario.questionnaire_overrides,
            indexed_backend=ScenarioIndexedBackend(results=scenario.indexed_results),
            llm_adapter=ScenarioLLMAdapter(outputs=scenario.agent_outputs),
        )
        supervisor.run()

        assert supervisor.state.step_statuses[StepId.STEP_02] is StepStatus.COMPLETE
        output = supervisor.state.determinations["step_02_security_classification"]
        assert output is not None
        assert output["status"] == "complete"
        assert output["fast_track_eligible"] is True
        assert output["data_classification"] == "UNREGULATED"
        assert output["integration_tier"] == "TIER_3"

    def test_escalation_path_ambiguous_integration(
        self, mock_documents_dir: Path, repo_root: Path
    ) -> None:
        """Step 02 emits ESCALATED for ambiguous ERP integration with regulated data."""
        scenario = escalated_security_scenario()
        supervisor = Supervisor(
            repo_root=repo_root,
            questionnaire_path=mock_documents_dir / "OptiChain_VSQ_001_v2_1.json",
            questionnaire_overrides=scenario.questionnaire_overrides,
            indexed_backend=ScenarioIndexedBackend(results=scenario.indexed_results),
            llm_adapter=ScenarioLLMAdapter(outputs=scenario.agent_outputs),
        )
        supervisor.run()

        assert supervisor.state.step_statuses[StepId.STEP_02] is StepStatus.ESCALATED
        output = supervisor.state.determinations["step_02_security_classification"]
        assert output["status"] == "escalated"
        assert output["fast_track_eligible"] is False

    def test_escalation_payload_present_on_escalation(
        self, mock_documents_dir: Path, repo_root: Path
    ) -> None:
        """An EscalationPayload must be created and stored when Step 02 escalates."""
        scenario = escalated_security_scenario()
        supervisor = Supervisor(
            repo_root=repo_root,
            questionnaire_path=mock_documents_dir / "OptiChain_VSQ_001_v2_1.json",
            questionnaire_overrides=scenario.questionnaire_overrides,
            indexed_backend=ScenarioIndexedBackend(results=scenario.indexed_results),
            llm_adapter=ScenarioLLMAdapter(outputs=scenario.agent_outputs),
        )
        supervisor.run()

        assert len(supervisor.state.escalations) >= 1
        # Escalations are stored as serialized audit log entries.
        # The payload fields are nested under "details".
        escalation_entry = supervisor.state.escalations[0]
        details = escalation_entry.get("details", escalation_entry)
        assert "evidence_condition" in details
        assert "resolution_owner" in details
        assert details["resolution_owner"] == "IT Security"

    def test_gate_blocked_when_step01_not_complete(
        self, mock_documents_dir: Path, repo_root: Path
    ) -> None:
        """Step 02 gate is blocked when Step 01 is not COMPLETE."""
        scenario = complete_demo_scenario()
        supervisor = Supervisor(
            repo_root=repo_root,
            questionnaire_path=mock_documents_dir / "OptiChain_VSQ_001_v2_1.json",
            questionnaire_overrides=scenario.questionnaire_overrides,
            indexed_backend=ScenarioIndexedBackend(results=scenario.indexed_results),
            llm_adapter=ScenarioLLMAdapter(outputs=scenario.agent_outputs),
        )
        # Leave STEP-01 in PENDING state (do not run it)
        gate = supervisor.handlers[StepId.STEP_02].check_gate(supervisor.state)
        assert gate.allowed is False
        assert gate.reason is not None
        assert "STEP-01" in gate.reason

    def test_output_has_required_fields(self, mock_documents_dir: Path, repo_root: Path) -> None:
        """Step 02 output must contain all REQUIRED_OUTPUT_FIELDS for STEP-02."""
        from orchestration.validation.output_validator import REQUIRED_OUTPUT_FIELDS

        scenario = complete_demo_scenario()
        supervisor = Supervisor(
            repo_root=repo_root,
            questionnaire_path=mock_documents_dir / "OptiChain_VSQ_001_v2_1.json",
            questionnaire_overrides=scenario.questionnaire_overrides,
            indexed_backend=ScenarioIndexedBackend(results=scenario.indexed_results),
            llm_adapter=ScenarioLLMAdapter(outputs=scenario.agent_outputs),
        )
        supervisor.run()

        output = supervisor.state.determinations["step_02_security_classification"]
        assert output is not None
        for field in REQUIRED_OUTPUT_FIELDS["STEP-02"]:
            assert field in output, f"Missing required field: {field}"

    def test_fast_track_eligible_only_when_unregulated_export_only(
        self, mock_documents_dir: Path, repo_root: Path
    ) -> None:
        """fast_track_eligible must be False when data is regulated or integration is ambiguous."""
        scenario = escalated_security_scenario()
        supervisor = Supervisor(
            repo_root=repo_root,
            questionnaire_path=mock_documents_dir / "OptiChain_VSQ_001_v2_1.json",
            questionnaire_overrides=scenario.questionnaire_overrides,
            indexed_backend=ScenarioIndexedBackend(results=scenario.indexed_results),
            llm_adapter=ScenarioLLMAdapter(outputs=scenario.agent_outputs),
        )
        supervisor.run()

        output = supervisor.state.determinations["step_02_security_classification"]
        assert output["fast_track_eligible"] is False
        assert output["data_classification"] == "REGULATED"


# ---------------------------------------------------------------------------
# Step 03 — Legal
# ---------------------------------------------------------------------------


class TestStep03Legal:
    def test_happy_path_complete(self, mock_documents_dir: Path, repo_root: Path) -> None:
        """Step 03 emits COMPLETE when NDA is executed and DPA is not required."""
        scenario = complete_demo_scenario()
        supervisor = Supervisor(
            repo_root=repo_root,
            questionnaire_path=mock_documents_dir / "OptiChain_VSQ_001_v2_1.json",
            questionnaire_overrides=scenario.questionnaire_overrides,
            indexed_backend=ScenarioIndexedBackend(results=scenario.indexed_results),
            llm_adapter=ScenarioLLMAdapter(outputs=scenario.agent_outputs),
        )
        supervisor.run()

        assert supervisor.state.step_statuses[StepId.STEP_03] is StepStatus.COMPLETE
        output = supervisor.state.determinations["step_03_legal"]
        assert output is not None
        assert output["status"] == "complete"
        assert output["dpa_required"] is False
        assert output["dpa_blocker"] is False
        assert output["nda_blocker"] is False
        assert output["nda_status"] == "EXECUTED"

    def test_gate_blocked_when_step02_not_complete(
        self, mock_documents_dir: Path, repo_root: Path
    ) -> None:
        """Step 03 gate is blocked when Step 02 is not COMPLETE."""
        scenario = complete_demo_scenario()
        supervisor = Supervisor(
            repo_root=repo_root,
            questionnaire_path=mock_documents_dir / "OptiChain_VSQ_001_v2_1.json",
            questionnaire_overrides=scenario.questionnaire_overrides,
            indexed_backend=ScenarioIndexedBackend(results=scenario.indexed_results),
            llm_adapter=ScenarioLLMAdapter(outputs=scenario.agent_outputs),
        )
        # With STEP-02 in PENDING state, gate must deny
        gate = supervisor.handlers[StepId.STEP_03].check_gate(supervisor.state)
        assert gate.allowed is False
        assert "STEP-02" in (gate.reason or "")

    def test_step03_skipped_when_step02_escalates(
        self, mock_documents_dir: Path, repo_root: Path
    ) -> None:
        """Step 03 is not executed when Step 02 escalates (pipeline halts at STEP-02)."""
        scenario = escalated_security_scenario()
        supervisor = Supervisor(
            repo_root=repo_root,
            questionnaire_path=mock_documents_dir / "OptiChain_VSQ_001_v2_1.json",
            questionnaire_overrides=scenario.questionnaire_overrides,
            indexed_backend=ScenarioIndexedBackend(results=scenario.indexed_results),
            llm_adapter=ScenarioLLMAdapter(outputs=scenario.agent_outputs),
        )
        supervisor.run()

        # Step 03 should remain PENDING — not run after STEP-02 ESCALATED
        assert supervisor.state.step_statuses[StepId.STEP_03] is StepStatus.PENDING
        assert supervisor.state.determinations["step_03_legal"] is None

    def test_output_has_required_fields(self, mock_documents_dir: Path, repo_root: Path) -> None:
        """Step 03 output must contain all REQUIRED_OUTPUT_FIELDS for STEP-03."""
        from orchestration.validation.output_validator import REQUIRED_OUTPUT_FIELDS

        scenario = complete_demo_scenario()
        supervisor = Supervisor(
            repo_root=repo_root,
            questionnaire_path=mock_documents_dir / "OptiChain_VSQ_001_v2_1.json",
            questionnaire_overrides=scenario.questionnaire_overrides,
            indexed_backend=ScenarioIndexedBackend(results=scenario.indexed_results),
            llm_adapter=ScenarioLLMAdapter(outputs=scenario.agent_outputs),
        )
        supervisor.run()

        output = supervisor.state.determinations["step_03_legal"]
        assert output is not None
        for field in REQUIRED_OUTPUT_FIELDS["STEP-03"]:
            assert field in output, f"Missing required field: {field}"

    def test_dpa_trigger_applicability_inspected(
        self, mock_documents_dir: Path, repo_root: Path
    ) -> None:
        """Step 03 must inspect DPA trigger applicability and expose dpa_required."""
        scenario = complete_demo_scenario()
        supervisor = Supervisor(
            repo_root=repo_root,
            questionnaire_path=mock_documents_dir / "OptiChain_VSQ_001_v2_1.json",
            questionnaire_overrides=scenario.questionnaire_overrides,
            indexed_backend=ScenarioIndexedBackend(results=scenario.indexed_results),
            llm_adapter=ScenarioLLMAdapter(outputs=scenario.agent_outputs),
        )
        supervisor.run()

        output = supervisor.state.determinations["step_03_legal"]
        assert "dpa_required" in output
        assert "dpa_blocker" in output
        assert "trigger_rule_cited" in output

    def test_nda_status_inspected(self, mock_documents_dir: Path, repo_root: Path) -> None:
        """Step 03 must inspect NDA status and expose nda_status and nda_blocker."""
        scenario = complete_demo_scenario()
        supervisor = Supervisor(
            repo_root=repo_root,
            questionnaire_path=mock_documents_dir / "OptiChain_VSQ_001_v2_1.json",
            questionnaire_overrides=scenario.questionnaire_overrides,
            indexed_backend=ScenarioIndexedBackend(results=scenario.indexed_results),
            llm_adapter=ScenarioLLMAdapter(outputs=scenario.agent_outputs),
        )
        supervisor.run()

        output = supervisor.state.determinations["step_03_legal"]
        assert "nda_status" in output
        assert "nda_blocker" in output


# ---------------------------------------------------------------------------
# Step 04 — Procurement
# ---------------------------------------------------------------------------


class TestStep04Procurement:
    def test_happy_path_complete_fast_track(
        self, mock_documents_dir: Path, repo_root: Path
    ) -> None:
        """Step 04 emits COMPLETE with FAST_TRACK path for low-risk scenario."""
        scenario = complete_demo_scenario()
        supervisor = Supervisor(
            repo_root=repo_root,
            questionnaire_path=mock_documents_dir / "OptiChain_VSQ_001_v2_1.json",
            questionnaire_overrides=scenario.questionnaire_overrides,
            indexed_backend=ScenarioIndexedBackend(results=scenario.indexed_results),
            llm_adapter=ScenarioLLMAdapter(outputs=scenario.agent_outputs),
        )
        supervisor.run()

        assert supervisor.state.step_statuses[StepId.STEP_04] is StepStatus.COMPLETE
        output = supervisor.state.determinations["step_04_procurement"]
        assert output is not None
        assert output["status"] == "complete"
        assert output["fast_track_eligible"] is True
        assert output["approval_path"] == "FAST_TRACK"
        assert len(output["required_approvals"]) > 0

    def test_gate_blocked_when_step03_not_terminal(
        self, mock_documents_dir: Path, repo_root: Path
    ) -> None:
        """Step 04 gate is blocked when Step 03 has not reached a terminal state."""
        scenario = complete_demo_scenario()
        supervisor = Supervisor(
            repo_root=repo_root,
            questionnaire_path=mock_documents_dir / "OptiChain_VSQ_001_v2_1.json",
            questionnaire_overrides=scenario.questionnaire_overrides,
            indexed_backend=ScenarioIndexedBackend(results=scenario.indexed_results),
            llm_adapter=ScenarioLLMAdapter(outputs=scenario.agent_outputs),
        )
        # STEP-03 is PENDING; gate must deny
        gate = supervisor.handlers[StepId.STEP_04].check_gate(supervisor.state)
        assert gate.allowed is False

    def test_gate_blocked_when_step03_determination_missing(
        self, mock_documents_dir: Path, repo_root: Path
    ) -> None:
        """Step 04 gate is blocked when Step 03 determination is absent from pipeline state."""
        scenario = complete_demo_scenario()
        supervisor = Supervisor(
            repo_root=repo_root,
            questionnaire_path=mock_documents_dir / "OptiChain_VSQ_001_v2_1.json",
            questionnaire_overrides=scenario.questionnaire_overrides,
            indexed_backend=ScenarioIndexedBackend(results=scenario.indexed_results),
            llm_adapter=ScenarioLLMAdapter(outputs=scenario.agent_outputs),
        )
        # Simulate Step 03 terminal but no determination stored
        supervisor.state.step_statuses[StepId.STEP_03] = StepStatus.COMPLETE
        supervisor.state.determinations["step_03_legal"] = None
        gate = supervisor.handlers[StepId.STEP_04].check_gate(supervisor.state)
        assert gate.allowed is False

    def test_gate_allowed_when_step03_escalated_with_determination(
        self, mock_documents_dir: Path, repo_root: Path
    ) -> None:
        """Step 04 gate allows execution when Step 03 is ESCALATED but determination is present.

        This reflects the context contract: Step 04 can proceed even if Step 03 escalated,
        provided the determination is present in pipeline state.
        """
        scenario = complete_demo_scenario()
        supervisor = Supervisor(
            repo_root=repo_root,
            questionnaire_path=mock_documents_dir / "OptiChain_VSQ_001_v2_1.json",
            questionnaire_overrides=scenario.questionnaire_overrides,
            indexed_backend=ScenarioIndexedBackend(results=scenario.indexed_results),
            llm_adapter=ScenarioLLMAdapter(outputs=scenario.agent_outputs),
        )
        supervisor.state.step_statuses[StepId.STEP_03] = StepStatus.ESCALATED
        supervisor.state.determinations["step_03_legal"] = {
            "dpa_required": True,
            "dpa_blocker": True,
            "nda_status": "PENDING",
            "nda_blocker": True,
            "trigger_rule_cited": [],
            "policy_citations": [],
            "status": "escalated",
        }
        gate = supervisor.handlers[StepId.STEP_04].check_gate(supervisor.state)
        assert gate.allowed is True

    def test_output_has_required_fields(self, mock_documents_dir: Path, repo_root: Path) -> None:
        """Step 04 output must contain all REQUIRED_OUTPUT_FIELDS for STEP-04."""
        from orchestration.validation.output_validator import REQUIRED_OUTPUT_FIELDS

        scenario = complete_demo_scenario()
        supervisor = Supervisor(
            repo_root=repo_root,
            questionnaire_path=mock_documents_dir / "OptiChain_VSQ_001_v2_1.json",
            questionnaire_overrides=scenario.questionnaire_overrides,
            indexed_backend=ScenarioIndexedBackend(results=scenario.indexed_results),
            llm_adapter=ScenarioLLMAdapter(outputs=scenario.agent_outputs),
        )
        supervisor.run()

        output = supervisor.state.determinations["step_04_procurement"]
        assert output is not None
        for field in REQUIRED_OUTPUT_FIELDS["STEP-04"]:
            assert field in output, f"Missing required field: {field}"

    def test_upstream_security_and_legal_outputs_incorporated(
        self, mock_documents_dir: Path, repo_root: Path
    ) -> None:
        """Step 04 incorporates upstream Step 02 and Step 03 outputs for routing decisions."""
        scenario = complete_demo_scenario()
        supervisor = Supervisor(
            repo_root=repo_root,
            questionnaire_path=mock_documents_dir / "OptiChain_VSQ_001_v2_1.json",
            questionnaire_overrides=scenario.questionnaire_overrides,
            indexed_backend=ScenarioIndexedBackend(results=scenario.indexed_results),
            llm_adapter=ScenarioLLMAdapter(outputs=scenario.agent_outputs),
        )
        supervisor.run()

        # Approval path must reflect the upstream fast_track_eligible determination
        s02 = supervisor.state.determinations["step_02_security_classification"]
        s04 = supervisor.state.determinations["step_04_procurement"]
        assert s04["fast_track_eligible"] == s02["fast_track_eligible"]


# ---------------------------------------------------------------------------
# Step 05 — Checklist
# ---------------------------------------------------------------------------


class TestStep05Checklist:
    def test_happy_path_complete(self, mock_documents_dir: Path, repo_root: Path) -> None:
        """Step 05 emits COMPLETE and assembles the final approval checklist."""
        scenario = complete_demo_scenario()
        supervisor = Supervisor(
            repo_root=repo_root,
            questionnaire_path=mock_documents_dir / "OptiChain_VSQ_001_v2_1.json",
            questionnaire_overrides=scenario.questionnaire_overrides,
            indexed_backend=ScenarioIndexedBackend(results=scenario.indexed_results),
            llm_adapter=ScenarioLLMAdapter(outputs=scenario.agent_outputs),
        )
        supervisor.run()

        assert supervisor.state.step_statuses[StepId.STEP_05] is StepStatus.COMPLETE
        output = supervisor.state.determinations["step_05_checklist"]
        assert output is not None
        assert output["overall_status"] == "COMPLETE"

    def test_compiles_all_prior_determinations(
        self, mock_documents_dir: Path, repo_root: Path
    ) -> None:
        """Step 05 checklist output must reflect data from Steps 02, 03, and 04."""
        scenario = complete_demo_scenario()
        supervisor = Supervisor(
            repo_root=repo_root,
            questionnaire_path=mock_documents_dir / "OptiChain_VSQ_001_v2_1.json",
            questionnaire_overrides=scenario.questionnaire_overrides,
            indexed_backend=ScenarioIndexedBackend(results=scenario.indexed_results),
            llm_adapter=ScenarioLLMAdapter(outputs=scenario.agent_outputs),
        )
        supervisor.run()

        s02 = supervisor.state.determinations["step_02_security_classification"]
        s03 = supervisor.state.determinations["step_03_legal"]
        s04 = supervisor.state.determinations["step_04_procurement"]
        s05 = supervisor.state.determinations["step_05_checklist"]

        assert s05 is not None
        # data_classification from Step 02
        assert s05["data_classification"] == s02["data_classification"]
        # dpa_required from Step 03
        assert s05["dpa_required"] == s03["dpa_required"]
        # fast_track_eligible from Step 02
        assert s05["fast_track_eligible"] == s02["fast_track_eligible"]
        # approval_path from Step 04
        assert s05["approval_path"] == s04["approval_path"]
        # required_approvals from Step 04
        assert s05["required_approvals"] == s04["required_approvals"]

    def test_gate_blocked_when_prerequisite_steps_not_terminal(
        self, mock_documents_dir: Path, repo_root: Path
    ) -> None:
        """Step 05 gate is blocked when any of Steps 01-04 are not in a terminal state."""
        scenario = complete_demo_scenario()
        supervisor = Supervisor(
            repo_root=repo_root,
            questionnaire_path=mock_documents_dir / "OptiChain_VSQ_001_v2_1.json",
            questionnaire_overrides=scenario.questionnaire_overrides,
            indexed_backend=ScenarioIndexedBackend(results=scenario.indexed_results),
            llm_adapter=ScenarioLLMAdapter(outputs=scenario.agent_outputs),
        )
        # Leave all steps as PENDING
        gate = supervisor.handlers[StepId.STEP_05].check_gate(supervisor.state)
        assert gate.allowed is False

    def test_gate_allowed_when_all_prior_steps_terminal(
        self, mock_documents_dir: Path, repo_root: Path
    ) -> None:
        """Step 05 gate opens when all Steps 01-04 are terminal AND determinations are present."""
        scenario = complete_demo_scenario()
        supervisor = Supervisor(
            repo_root=repo_root,
            questionnaire_path=mock_documents_dir / "OptiChain_VSQ_001_v2_1.json",
            questionnaire_overrides=scenario.questionnaire_overrides,
            indexed_backend=ScenarioIndexedBackend(results=scenario.indexed_results),
            llm_adapter=ScenarioLLMAdapter(outputs=scenario.agent_outputs),
        )
        for step in (StepId.STEP_01, StepId.STEP_02, StepId.STEP_03, StepId.STEP_04):
            supervisor.state.step_statuses[step] = StepStatus.COMPLETE
        # Gate additionally requires upstream determinations to be populated.
        supervisor.state.determinations["step_02_security_classification"] = {"status": "complete"}
        supervisor.state.determinations["step_03_legal"] = {"status": "complete"}
        supervisor.state.determinations["step_04_procurement"] = {"status": "complete"}
        gate = supervisor.handlers[StepId.STEP_05].check_gate(supervisor.state)
        assert gate.allowed is True

    def test_output_has_required_fields(self, mock_documents_dir: Path, repo_root: Path) -> None:
        """Step 05 output must contain all REQUIRED_OUTPUT_FIELDS for STEP-05."""
        from orchestration.validation.output_validator import REQUIRED_OUTPUT_FIELDS

        scenario = complete_demo_scenario()
        supervisor = Supervisor(
            repo_root=repo_root,
            questionnaire_path=mock_documents_dir / "OptiChain_VSQ_001_v2_1.json",
            questionnaire_overrides=scenario.questionnaire_overrides,
            indexed_backend=ScenarioIndexedBackend(results=scenario.indexed_results),
            llm_adapter=ScenarioLLMAdapter(outputs=scenario.agent_outputs),
        )
        supervisor.run()

        output = supervisor.state.determinations["step_05_checklist"]
        assert output is not None
        for field in REQUIRED_OUTPUT_FIELDS["STEP-05"]:
            assert field in output, f"Missing required field: {field}"

    def test_blockers_list_empty_on_clean_path(
        self, mock_documents_dir: Path, repo_root: Path
    ) -> None:
        """Step 05 blockers list must be empty on the clean fast-track path."""
        scenario = complete_demo_scenario()
        supervisor = Supervisor(
            repo_root=repo_root,
            questionnaire_path=mock_documents_dir / "OptiChain_VSQ_001_v2_1.json",
            questionnaire_overrides=scenario.questionnaire_overrides,
            indexed_backend=ScenarioIndexedBackend(results=scenario.indexed_results),
            llm_adapter=ScenarioLLMAdapter(outputs=scenario.agent_outputs),
        )
        supervisor.run()

        output = supervisor.state.determinations["step_05_checklist"]
        assert output["blockers"] == []

    def test_citations_aggregated_from_upstream_agents(
        self, mock_documents_dir: Path, repo_root: Path
    ) -> None:
        """Step 05 citations must aggregate policy citations from upstream agents."""
        scenario = complete_demo_scenario()
        supervisor = Supervisor(
            repo_root=repo_root,
            questionnaire_path=mock_documents_dir / "OptiChain_VSQ_001_v2_1.json",
            questionnaire_overrides=scenario.questionnaire_overrides,
            indexed_backend=ScenarioIndexedBackend(results=scenario.indexed_results),
            llm_adapter=ScenarioLLMAdapter(outputs=scenario.agent_outputs),
        )
        supervisor.run()

        output = supervisor.state.determinations["step_05_checklist"]
        assert isinstance(output["citations"], list)
        assert len(output["citations"]) > 0


# ---------------------------------------------------------------------------
# Step 06 — Checkoff
# ---------------------------------------------------------------------------


class TestStep06Checkoff:
    def test_happy_path_complete(self, mock_documents_dir: Path, repo_root: Path) -> None:
        """Step 06 emits COMPLETE and generates stakeholder guidance."""
        scenario = complete_demo_scenario()
        supervisor = Supervisor(
            repo_root=repo_root,
            questionnaire_path=mock_documents_dir / "OptiChain_VSQ_001_v2_1.json",
            questionnaire_overrides=scenario.questionnaire_overrides,
            indexed_backend=ScenarioIndexedBackend(results=scenario.indexed_results),
            llm_adapter=ScenarioLLMAdapter(outputs=scenario.agent_outputs),
        )
        supervisor.run()

        assert supervisor.state.step_statuses[StepId.STEP_06] is StepStatus.COMPLETE
        output = supervisor.state.determinations["step_06_guidance"]
        assert output is not None
        assert output["status"] == "complete"
        assert "guidance_documents" in output
        assert len(output["guidance_documents"]) > 0

    def test_does_not_alter_checklist_result(
        self, mock_documents_dir: Path, repo_root: Path
    ) -> None:
        """Step 06 output must not change the overall_status of the Step 05 checklist."""
        scenario = complete_demo_scenario()
        supervisor = Supervisor(
            repo_root=repo_root,
            questionnaire_path=mock_documents_dir / "OptiChain_VSQ_001_v2_1.json",
            questionnaire_overrides=scenario.questionnaire_overrides,
            indexed_backend=ScenarioIndexedBackend(results=scenario.indexed_results),
            llm_adapter=ScenarioLLMAdapter(outputs=scenario.agent_outputs),
        )
        supervisor.run()

        s05_output = supervisor.state.determinations["step_05_checklist"]
        s06_output = supervisor.state.determinations["step_06_guidance"]

        assert s05_output is not None
        assert s06_output is not None

        # Step 06 output must NOT contain overall_status (which would replicate/alter the checklist)
        assert "overall_status" not in s06_output
        # Step 05 checklist is unchanged
        assert s05_output["overall_status"] == "COMPLETE"

    def test_guidance_documents_reference_step05_checklist_data(
        self, mock_documents_dir: Path, repo_root: Path
    ) -> None:
        """Guidance documents must use finalized checklist data (not independently derived)."""
        scenario = complete_demo_scenario()
        supervisor = Supervisor(
            repo_root=repo_root,
            questionnaire_path=mock_documents_dir / "OptiChain_VSQ_001_v2_1.json",
            questionnaire_overrides=scenario.questionnaire_overrides,
            indexed_backend=ScenarioIndexedBackend(results=scenario.indexed_results),
            llm_adapter=ScenarioLLMAdapter(outputs=scenario.agent_outputs),
        )
        supervisor.run()

        s05 = supervisor.state.determinations["step_05_checklist"]
        s06 = supervisor.state.determinations["step_06_guidance"]
        docs = s06["guidance_documents"]

        # Each guidance document must reference a stakeholder role from required_approvals
        approver_roles = {a["approver"] for a in s05["required_approvals"]}
        doc_roles = {doc["stakeholder_role"] for doc in docs}
        assert len(doc_roles & approver_roles) > 0, (
            "At least one guidance document must address an approver from the checklist"
        )

    def test_gate_blocked_when_step05_not_complete(
        self, mock_documents_dir: Path, repo_root: Path
    ) -> None:
        """Step 06 gate is blocked when Step 05 is not COMPLETE."""
        scenario = complete_demo_scenario()
        supervisor = Supervisor(
            repo_root=repo_root,
            questionnaire_path=mock_documents_dir / "OptiChain_VSQ_001_v2_1.json",
            questionnaire_overrides=scenario.questionnaire_overrides,
            indexed_backend=ScenarioIndexedBackend(results=scenario.indexed_results),
            llm_adapter=ScenarioLLMAdapter(outputs=scenario.agent_outputs),
        )
        # STEP-05 not yet run
        gate = supervisor.handlers[StepId.STEP_06].check_gate(supervisor.state)
        assert gate.allowed is False
        assert "STEP-05" in (gate.reason or "")

    def test_output_has_required_fields(self, mock_documents_dir: Path, repo_root: Path) -> None:
        """Step 06 output must contain all REQUIRED_OUTPUT_FIELDS for STEP-06."""
        from orchestration.validation.output_validator import REQUIRED_OUTPUT_FIELDS

        scenario = complete_demo_scenario()
        supervisor = Supervisor(
            repo_root=repo_root,
            questionnaire_path=mock_documents_dir / "OptiChain_VSQ_001_v2_1.json",
            questionnaire_overrides=scenario.questionnaire_overrides,
            indexed_backend=ScenarioIndexedBackend(results=scenario.indexed_results),
            llm_adapter=ScenarioLLMAdapter(outputs=scenario.agent_outputs),
        )
        supervisor.run()

        output = supervisor.state.determinations["step_06_guidance"]
        assert output is not None
        for field in REQUIRED_OUTPUT_FIELDS["STEP-06"]:
            assert field in output, f"Missing required field: {field}"


# ---------------------------------------------------------------------------
# Cross-cutting: full pipeline scenario assertions
# ---------------------------------------------------------------------------


class TestFullPipelineScenarios:
    def test_scenario1_all_steps_complete(self, mock_documents_dir: Path, repo_root: Path) -> None:
        """Scenario 1: all six steps complete cleanly on the fast-track path."""
        scenario = complete_demo_scenario()
        supervisor = Supervisor(
            repo_root=repo_root,
            questionnaire_path=mock_documents_dir / "OptiChain_VSQ_001_v2_1.json",
            questionnaire_overrides=scenario.questionnaire_overrides,
            indexed_backend=ScenarioIndexedBackend(results=scenario.indexed_results),
            llm_adapter=ScenarioLLMAdapter(outputs=scenario.agent_outputs),
        )
        state = supervisor.run()

        assert state.overall_status.value == scenario.expected_overall_status
        for step_id_str, expected_status in scenario.expected_step_statuses.items():
            step_id = StepId(step_id_str)
            assert state.step_statuses[step_id].value == expected_status, (
                f"{step_id_str}: expected {expected_status}, got {state.step_statuses[step_id].value}"
            )

    def test_scenario2_halts_at_step02_escalation(
        self, mock_documents_dir: Path, repo_root: Path
    ) -> None:
        """Scenario 2: pipeline halts at Step 02 ESCALATED; Steps 03-06 remain PENDING."""
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
        for step_id_str, expected_status in scenario.expected_step_statuses.items():
            step_id = StepId(step_id_str)
            assert state.step_statuses[step_id].value == expected_status, (
                f"{step_id_str}: expected {expected_status}, got {state.step_statuses[step_id].value}"
            )

    def test_scenario2_step06_not_reached(
        self, mock_documents_dir: Path, repo_root: Path
    ) -> None:
        """Scenario 2: Step 06 must never execute when pipeline halts at Step 02."""
        scenario = escalated_security_scenario()
        supervisor = Supervisor(
            repo_root=repo_root,
            questionnaire_path=mock_documents_dir / "OptiChain_VSQ_001_v2_1.json",
            questionnaire_overrides=scenario.questionnaire_overrides,
            indexed_backend=ScenarioIndexedBackend(results=scenario.indexed_results),
            llm_adapter=ScenarioLLMAdapter(outputs=scenario.agent_outputs),
        )
        supervisor.run()

        assert supervisor.state.step_statuses[StepId.STEP_06] is StepStatus.PENDING
        assert supervisor.state.determinations["step_06_guidance"] is None

    def test_all_steps_produce_determinations_on_complete_path(
        self, mock_documents_dir: Path, repo_root: Path
    ) -> None:
        """On the complete path, all six determination slots must be populated."""
        scenario = complete_demo_scenario()
        supervisor = Supervisor(
            repo_root=repo_root,
            questionnaire_path=mock_documents_dir / "OptiChain_VSQ_001_v2_1.json",
            questionnaire_overrides=scenario.questionnaire_overrides,
            indexed_backend=ScenarioIndexedBackend(results=scenario.indexed_results),
            llm_adapter=ScenarioLLMAdapter(outputs=scenario.agent_outputs),
        )
        supervisor.run()

        for key in (
            "step_01_intake",
            "step_02_security_classification",
            "step_03_legal",
            "step_04_procurement",
            "step_05_checklist",
            "step_06_guidance",
        ):
            assert supervisor.state.determinations[key] is not None, (
                f"Determination slot '{key}' must be populated after full run"
            )
