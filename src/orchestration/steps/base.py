"""Common step-handler utilities."""

from __future__ import annotations

from typing import Any

from orchestration.agents.llm_agent_runner import LLMAgentRunner
from orchestration.audit.audit_logger import AuditLogger
from orchestration.models.contracts import GateDecision, StepDefinition, StepExecutionResult
from orchestration.models.enums import AgentStatus, StepId, StepStatus
from orchestration.retrieval.bundle_assembler import BundleAssembler
from orchestration.retrieval.router import RetrievalRouter
from orchestration.validation.bundle_validator import BundleValidator
from orchestration.validation.output_validator import OutputValidator


class BaseStepHandler:
    def __init__(
        self,
        *,
        definition: StepDefinition,
        router: RetrievalRouter,
        bundle_assembler: BundleAssembler,
        bundle_validator: BundleValidator,
        output_validator: OutputValidator,
        agent_runner: LLMAgentRunner | None,
        audit_logger: AuditLogger,
    ) -> None:
        self.definition = definition
        self.router = router
        self.bundle_assembler = bundle_assembler
        self.bundle_validator = bundle_validator
        self.output_validator = output_validator
        self.agent_runner = agent_runner
        self.audit_logger = audit_logger

    def check_gate(self, state: Any) -> GateDecision:
        raise NotImplementedError

    def execute(self, state: Any) -> StepExecutionResult:
        raise NotImplementedError

    @property
    def step_id(self) -> StepId:
        return self.definition.step_id

    def _step_status_from_agent_status(self, value: str) -> StepStatus:
        if value == AgentStatus.COMPLETE.value:
            return StepStatus.COMPLETE
        if value == AgentStatus.ESCALATED.value:
            return StepStatus.ESCALATED
        return StepStatus.BLOCKED
