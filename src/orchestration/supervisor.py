"""Static Supervisor orchestration loop."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from orchestration.agents.llm_agent_runner import LLMAgentRunner, MockLLMAdapter
from orchestration.audit.audit_logger import AuditLogger
from orchestration.config.source_manifest import DEFAULT_STAKEHOLDER_MAP, build_source_manifest
from orchestration.config.step_definitions import STEP_DEFINITIONS
from orchestration.models.contracts import StepExecutionResult
from orchestration.models.enums import RunStatus, StepId, StepStatus
from orchestration.pipeline_state import PipelineState
from orchestration.retrieval.bundle_assembler import BundleAssembler
from orchestration.retrieval.direct_structured import DirectStructuredAccessor
from orchestration.retrieval.hybrid_indexed import MockHybridIndexedBackend
from orchestration.retrieval.router import RetrievalRouter
from orchestration.retrieval.runtime_reads import RuntimeReadAccessor
from orchestration.state_machine import StateMachine
from orchestration.steps.step01_intake import Step01IntakeHandler
from orchestration.steps.step02_security import Step02SecurityHandler
from orchestration.steps.step03_legal import Step03LegalHandler
from orchestration.steps.step04_procurement import Step04ProcurementHandler
from orchestration.steps.step05_checklist import Step05ChecklistHandler
from orchestration.steps.step06_checkoff import Step06CheckoffHandler
from orchestration.validation.bundle_validator import BundleValidator
from orchestration.validation.output_validator import OutputValidator


class Supervisor:
    """Deterministic sequential Supervisor."""

    def __init__(
        self,
        *,
        repo_root: str | Path,
        questionnaire_path: str | Path,
        chunk_dir: str | Path | None = None,
        questionnaire_overrides: dict[str, Any] | None = None,
        llm_adapter: MockLLMAdapter | None = None,
        pipeline_config: dict[str, Any] | None = None,
        indexed_backend: Any | None = None,
    ) -> None:
        self.repo_root = Path(repo_root)
        self.manifest = build_source_manifest()
        self.state = PipelineState.initialize(self.manifest.manifest_version)
        self.audit_logger = AuditLogger(self.state.pipeline_run_id)
        self.direct_accessor = DirectStructuredAccessor(questionnaire_path, overrides=questionnaire_overrides)
        self.indexed_backend = indexed_backend or MockHybridIndexedBackend(
            chunk_dir=chunk_dir or (self.repo_root / "data" / "processed" / "chunks")
        )
        self.runtime_accessor = RuntimeReadAccessor(pipeline_config=pipeline_config or DEFAULT_STAKEHOLDER_MAP)
        self.router = RetrievalRouter(
            direct_accessor=self.direct_accessor,
            indexed_backend=self.indexed_backend,
            runtime_accessor=self.runtime_accessor,
            audit_logger=self.audit_logger,
        )
        self.bundle_assembler = BundleAssembler()
        self.bundle_validator = BundleValidator()
        self.output_validator = OutputValidator()
        self.agent_runner = LLMAgentRunner(
            repo_root=self.repo_root,
            adapter=llm_adapter or MockLLMAdapter(),
        )
        self.handlers = {
            StepId.STEP_01: Step01IntakeHandler(
                definition=STEP_DEFINITIONS[StepId.STEP_01],
                router=self.router,
                bundle_assembler=self.bundle_assembler,
                bundle_validator=self.bundle_validator,
                output_validator=self.output_validator,
                agent_runner=None,
                audit_logger=self.audit_logger,
            ),
            StepId.STEP_02: Step02SecurityHandler(
                definition=STEP_DEFINITIONS[StepId.STEP_02],
                router=self.router,
                bundle_assembler=self.bundle_assembler,
                bundle_validator=self.bundle_validator,
                output_validator=self.output_validator,
                agent_runner=self.agent_runner,
                audit_logger=self.audit_logger,
            ),
            StepId.STEP_03: Step03LegalHandler(
                definition=STEP_DEFINITIONS[StepId.STEP_03],
                router=self.router,
                bundle_assembler=self.bundle_assembler,
                bundle_validator=self.bundle_validator,
                output_validator=self.output_validator,
                agent_runner=self.agent_runner,
                audit_logger=self.audit_logger,
            ),
            StepId.STEP_04: Step04ProcurementHandler(
                definition=STEP_DEFINITIONS[StepId.STEP_04],
                router=self.router,
                bundle_assembler=self.bundle_assembler,
                bundle_validator=self.bundle_validator,
                output_validator=self.output_validator,
                agent_runner=self.agent_runner,
                audit_logger=self.audit_logger,
            ),
            StepId.STEP_05: Step05ChecklistHandler(
                definition=STEP_DEFINITIONS[StepId.STEP_05],
                router=self.router,
                bundle_assembler=self.bundle_assembler,
                bundle_validator=self.bundle_validator,
                output_validator=self.output_validator,
                agent_runner=self.agent_runner,
                audit_logger=self.audit_logger,
            ),
            StepId.STEP_06: Step06CheckoffHandler(
                definition=STEP_DEFINITIONS[StepId.STEP_06],
                router=self.router,
                bundle_assembler=self.bundle_assembler,
                bundle_validator=self.bundle_validator,
                output_validator=self.output_validator,
                agent_runner=self.agent_runner,
                audit_logger=self.audit_logger,
            ),
        }
        self.audit_logger.log_run_event(
            message="Pipeline initialized",
            details={"manifest_version": self.manifest.manifest_version},
        )

    def run(self) -> PipelineState:
        while self.execute_next_step():
            continue
        self._finalize_run()
        return self.state

    def execute_next_step(self) -> bool:
        if not self.state.next_step_queue:
            return False
        step_id = self.state.dequeue()
        if step_id is None:
            return False
        self._run_step(step_id)
        return self.state.overall_status is not RunStatus.BLOCKED and bool(self.state.next_step_queue)

    def _run_step(self, step_id: StepId) -> None:
        handler = self.handlers[step_id]
        gate = handler.check_gate(self.state)
        current_status = self.state.step_statuses[step_id]
        if not gate.allowed:
            self.audit_logger.log_status_change(
                agent_id="supervisor",
                step_id=step_id.value,
                from_status=current_status.value,
                to_status=StepStatus.BLOCKED.value,
                reason=gate.reason,
            )
            self.state.complete_step(step_id, StepStatus.BLOCKED)
            self.state.overall_status = StateMachine.derive_overall_status(self.state)
            return

        self.state.set_current_step(step_id)
        self.audit_logger.log_status_change(
            agent_id="supervisor",
            step_id=step_id.value,
            from_status=current_status.value,
            to_status=StepStatus.IN_PROGRESS.value,
        )
        self.state.step_statuses[step_id] = StepStatus.IN_PROGRESS
        result = handler.execute(self.state)
        self._apply_result(result)

    def _apply_result(self, result: StepExecutionResult) -> None:
        definition = STEP_DEFINITIONS[result.step_id]
        output = result.output or {}
        self.audit_logger.log_determination(
            agent_id=definition.assigned_agent,
            step_id=result.step_id.value,
            output=output,
        )
        self.audit_logger.log_status_change(
            agent_id="supervisor",
            step_id=result.step_id.value,
            from_status=StepStatus.IN_PROGRESS.value,
            to_status=result.step_status.value,
            reason=result.halt_reason,
        )
        if result.escalation_payload:
            escalation_entry = self.audit_logger.log_escalation(
                agent_id=definition.assigned_agent,
                step_id=result.step_id.value,
                payload=result.escalation_payload,
            )
            self.state.escalations.append(escalation_entry.to_dict())

        self.state.complete_step(result.step_id, result.step_status)
        self.state.audit_refs.extend(entry.entry_id for entry in self.audit_logger.entries if entry.entry_id not in self.state.audit_refs)
        self._store_output(result.step_id, output)
        self.state.overall_status = StateMachine.derive_overall_status(self.state)
        next_step = StateMachine.determine_next_step(self.state, result.step_id, result.step_status, output)
        self.state.enqueue(next_step)

    def _finalize_run(self) -> None:
        if self.state.overall_status is RunStatus.COMPLETE:
            self.audit_logger.log_run_event(
                message="Pipeline completed",
                details={"overall_status": self.state.overall_status.value},
            )
        elif self.state.overall_status is RunStatus.ESCALATED:
            self.audit_logger.log_run_event(
                message="Pipeline halted in escalated state",
                details={"overall_status": self.state.overall_status.value},
            )
        elif self.state.overall_status is RunStatus.BLOCKED:
            self.audit_logger.log_run_event(
                message="Pipeline halted in blocked state",
                details={"overall_status": self.state.overall_status.value},
            )

    def _store_output(self, step_id: StepId, output: dict[str, Any]) -> None:
        mapping = {
            StepId.STEP_01: "step_01_intake",
            StepId.STEP_02: "step_02_security_classification",
            StepId.STEP_03: "step_03_legal",
            StepId.STEP_04: "step_04_procurement",
            StepId.STEP_05: "step_05_checklist",
            StepId.STEP_06: "step_06_guidance",
        }
        self.state.determinations[mapping[step_id]] = output
