"""Shared orchestration enums."""

from __future__ import annotations

from enum import Enum


class StepId(str, Enum):
    STEP_01 = "STEP-01"
    STEP_02 = "STEP-02"
    STEP_03 = "STEP-03"
    STEP_04 = "STEP-04"
    STEP_05 = "STEP-05"
    STEP_06 = "STEP-06"


class StepStatus(str, Enum):
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETE = "COMPLETE"
    ESCALATED = "ESCALATED"
    BLOCKED = "BLOCKED"


class RunStatus(str, Enum):
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETE = "COMPLETE"
    ESCALATED = "ESCALATED"
    BLOCKED = "BLOCKED"


class AgentStatus(str, Enum):
    COMPLETE = "complete"
    ESCALATED = "escalated"
    BLOCKED = "blocked"


class RetrievalLane(str, Enum):
    DIRECT_STRUCTURED = "direct_structured"
    INDEXED_HYBRID = "indexed_hybrid"
    RUNTIME_READ = "runtime_read"


class AuditEventType(str, Enum):
    RETRIEVAL = "RETRIEVAL"
    DETERMINATION = "DETERMINATION"
    STATUS_CHANGE = "STATUS_CHANGE"
    ESCALATION = "ESCALATION"
    RUN_EVENT = "RUN_EVENT"
