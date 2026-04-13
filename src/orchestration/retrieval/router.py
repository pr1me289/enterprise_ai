"""Central routing entrypoint for all Supervisor-owned retrieval."""

from __future__ import annotations

from typing import Any

from indexing.load_index_registry import get_allowed_agents
from orchestration.audit.audit_logger import AuditLogger
from orchestration.models.contracts import RetrievalRequest, RetrievalResult
from orchestration.models.enums import RetrievalLane
from orchestration.pipeline_state import PipelineState
from orchestration.retrieval.direct_structured import DirectStructuredAccessor
from orchestration.retrieval.hybrid_indexed import MockHybridIndexedBackend
from orchestration.retrieval.runtime_reads import RuntimeReadAccessor


class RetrievalRouter:
    """Route every retrieval request through the locked lane model."""

    def __init__(
        self,
        *,
        direct_accessor: DirectStructuredAccessor,
        indexed_backend: MockHybridIndexedBackend,
        runtime_accessor: RuntimeReadAccessor,
        audit_logger: AuditLogger,
    ) -> None:
        self.direct_accessor = direct_accessor
        self.indexed_backend = indexed_backend
        self.runtime_accessor = runtime_accessor
        self.audit_logger = audit_logger

    def route(self, request: RetrievalRequest, *, state: PipelineState) -> RetrievalResult:
        if request.lane is RetrievalLane.DIRECT_STRUCTURED:
            payload, missing = self.direct_accessor.read_fields(request.field_map)
            result = RetrievalResult(
                request=request,
                payload=payload,
                missing_fields=missing,
                admitted_items=[
                    {"field_path": key, "value_present": key not in missing}
                    for key in request.field_map
                ],
            )
        elif request.lane is RetrievalLane.INDEXED_HYBRID:
            self._assert_index_access(request.access_role, request.source_id)
            hits = self.indexed_backend.query(
                source_id=request.source_id,
                search_terms=request.search_terms,
                metadata_filter=request.metadata_filter,
                top_k=request.top_k,
            )
            result = RetrievalResult(
                request=request,
                payload=hits,
                admitted_items=hits,
            )
        elif request.lane is RetrievalLane.RUNTIME_READ:
            payload, missing = self.runtime_accessor.read(
                target=request.runtime_target or "",
                field_map=request.field_map,
                state=state,
                audit_logger=self.audit_logger,
            )
            result = RetrievalResult(
                request=request,
                payload=payload,
                missing_fields=missing,
                admitted_items=[
                    {"field_path": key, "value_present": key not in missing}
                    for key in request.field_map
                ],
            )
        else:
            raise ValueError(f"Unsupported retrieval lane: {request.lane}")

        self.audit_logger.log_retrieval(
            agent_id="supervisor",
            source_queried=request.source_id,
            request_id=request.request_id,
            lane=request.lane.value,
            admitted_items=result.admitted_items,
            excluded_items=result.excluded_items,
            details={
                "output_name": request.output_name,
                "missing_fields": result.missing_fields,
                "search_terms": list(request.search_terms),
            },
        )
        return result

    def _assert_index_access(self, access_role: str, source_id: str) -> None:
        allowed_agents = get_allowed_agents(source_id)
        if access_role not in allowed_agents:
            raise PermissionError(f"Access role '{access_role}' is not permitted to query {source_id}.")
