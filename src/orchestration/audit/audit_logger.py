"""Append-only audit logger owned by the Supervisor."""

from __future__ import annotations

from uuid import uuid4

from orchestration.audit.schemas import AuditEntry
from orchestration.models.enums import AuditEventType
from orchestration.models.escalation import EscalationPayload
from orchestration.pipeline_state import utc_now


class AuditLogger:
    """Runtime append-only audit log."""

    def __init__(self, pipeline_run_id: str) -> None:
        self.pipeline_run_id = pipeline_run_id
        self._entries: list[AuditEntry] = []

    @property
    def entries(self) -> list[AuditEntry]:
        return list(self._entries)

    def append(
        self,
        *,
        agent_id: str,
        event_type: AuditEventType,
        source_queried: str | None = None,
        chunks_retrieved: list[dict] | None = None,
        details: dict | None = None,
    ) -> AuditEntry:
        entry = AuditEntry(
            entry_id=f"audit_{uuid4().hex[:10]}",
            pipeline_run_id=self.pipeline_run_id,
            agent_id=agent_id,
            event_type=event_type,
            timestamp=utc_now(),
            source_queried=source_queried,
            chunks_retrieved=list(chunks_retrieved or []),
            details=dict(details or {}),
        )
        self._entries.append(entry)
        return entry

    def log_retrieval(
        self,
        *,
        agent_id: str,
        source_queried: str,
        request_id: str,
        lane: str,
        admitted_items: list[dict],
        excluded_items: list[dict],
        details: dict | None = None,
    ) -> AuditEntry:
        payload = {
            "request_id": request_id,
            "lane": lane,
            "admitted_count": len(admitted_items),
            "excluded_count": len(excluded_items),
        }
        if details:
            payload.update(details)
        return self.append(
            agent_id=agent_id,
            event_type=AuditEventType.RETRIEVAL,
            source_queried=source_queried,
            chunks_retrieved=admitted_items + excluded_items,
            details=payload,
        )

    def log_status_change(
        self,
        *,
        agent_id: str,
        step_id: str,
        from_status: str,
        to_status: str,
        reason: str | None = None,
    ) -> AuditEntry:
        return self.append(
            agent_id=agent_id,
            event_type=AuditEventType.STATUS_CHANGE,
            details={
                "step_id": step_id,
                "from_status": from_status,
                "to_status": to_status,
                "reason": reason,
            },
        )

    def log_determination(self, *, agent_id: str, step_id: str, output: dict) -> AuditEntry:
        return self.append(
            agent_id=agent_id,
            event_type=AuditEventType.DETERMINATION,
            details={"step_id": step_id, "output": output},
        )

    def log_escalation(self, *, agent_id: str, step_id: str, payload: EscalationPayload) -> AuditEntry:
        return self.append(
            agent_id=agent_id,
            event_type=AuditEventType.ESCALATION,
            details={"step_id": step_id, **payload.to_dict()},
        )

    def log_run_event(self, *, message: str, details: dict | None = None) -> AuditEntry:
        payload = {"message": message}
        if details:
            payload.update(details)
        return self.append(
            agent_id="supervisor",
            event_type=AuditEventType.RUN_EVENT,
            details=payload,
        )
