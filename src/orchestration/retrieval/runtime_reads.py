"""Runtime reads against pipeline state, prior outputs, and pipeline config."""

from __future__ import annotations

from dataclasses import asdict, is_dataclass
from typing import Any

from orchestration.audit.audit_logger import AuditLogger
from orchestration.pipeline_state import PipelineState


class RuntimeReadAccessor:
    """Read non-retrieval runtime objects."""

    def __init__(self, *, pipeline_config: dict[str, Any]) -> None:
        self.pipeline_config = pipeline_config

    def read(
        self,
        *,
        target: str,
        field_map: dict[str, tuple[str, ...]],
        state: PipelineState,
        audit_logger: AuditLogger,
    ) -> tuple[dict[str, Any], list[str]]:
        if target.startswith("determination:"):
            key = target.split(":", maxsplit=1)[1]
            payload = state.determinations.get(key) or {}
        elif target == "audit_log":
            payload = {"entries": [entry.to_dict() for entry in audit_logger.entries]}
        elif target == "pipeline_state":
            payload = self._to_plain_dict(state)
        elif target == "pipeline_config":
            payload = self.pipeline_config
        else:
            raise KeyError(f"Unsupported runtime target: {target}")

        values: dict[str, Any] = {}
        missing: list[str] = []
        for output_key, candidate_paths in field_map.items():
            try:
                values[output_key] = self._get_first(payload, candidate_paths)
            except KeyError:
                missing.append(output_key)
        return values, missing

    def _get_first(self, payload: dict[str, Any], candidate_paths: tuple[str, ...]) -> Any:
        for field_path in candidate_paths:
            try:
                return self._resolve_path(payload, field_path)
            except KeyError:
                continue
        raise KeyError(candidate_paths[0])

    def _resolve_path(self, payload: dict[str, Any], field_path: str) -> Any:
        current: Any = payload
        for key in field_path.split("."):
            if isinstance(current, list):
                current = current[int(key)]
            else:
                current = current[key]
        return current

    def _to_plain_dict(self, value: Any) -> Any:
        if is_dataclass(value):
            return asdict(value)
        return value
