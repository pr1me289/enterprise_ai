"""Dataclasses shared by the orchestration runtime."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .enums import AgentStatus, RetrievalLane, StepId, StepStatus
from .escalation import EscalationPayload


@dataclass(frozen=True, slots=True)
class StepDefinition:
    step_id: StepId
    label: str
    assigned_agent: str
    access_role: str
    next_step: StepId | None


@dataclass(frozen=True, slots=True)
class RetrievalRequest:
    request_id: str
    lane: RetrievalLane
    source_id: str
    access_role: str
    output_name: str
    field_map: dict[str, tuple[str, ...]] = field(default_factory=dict)
    search_terms: tuple[str, ...] = field(default_factory=tuple)
    metadata_filter: dict[str, Any] = field(default_factory=dict)
    runtime_target: str | None = None
    top_k: int = 5


@dataclass(slots=True)
class RetrievalResult:
    request: RetrievalRequest
    payload: Any
    missing_fields: list[str] = field(default_factory=list)
    admitted_items: list[dict[str, Any]] = field(default_factory=list)
    excluded_items: list[dict[str, Any]] = field(default_factory=list)
    # Typed chunk objects populated for INDEXED_HYBRID lane results.
    retrieved_chunks: list[Any] = field(default_factory=list)


@dataclass(slots=True)
class BundleValidationResult:
    admissible: bool
    missing_fields: list[str] = field(default_factory=list)
    prohibited_sources: list[str] = field(default_factory=list)
    escalation_required: bool = False


@dataclass(slots=True)
class OutputValidationResult:
    valid: bool
    errors: list[str] = field(default_factory=list)


@dataclass(slots=True)
class GateDecision:
    allowed: bool
    reason: str | None = None
    resolution_owner: str | None = None


@dataclass(slots=True)
class StepExecutionResult:
    step_id: StepId
    step_status: StepStatus
    output: dict[str, Any] | None = None
    bundle: Any = None  # ContextBundle or dict[str, Any]
    retrieval_results: dict[str, RetrievalResult] = field(default_factory=dict)
    agent_status: AgentStatus | None = None
    halt_reason: str | None = None
    escalation_payload: EscalationPayload | None = None
