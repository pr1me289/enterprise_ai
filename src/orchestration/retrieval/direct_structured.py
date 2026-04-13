"""Direct structured access for direct-structured lane sources."""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any


def _deep_merge(base: dict[str, Any], overrides: dict[str, Any]) -> dict[str, Any]:
    merged = deepcopy(base)
    for key, value in overrides.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = deepcopy(value)
    return merged


class DirectStructuredAccessor:
    """Field-level access into direct-structured source payloads."""

    def __init__(
        self,
        questionnaire_path: str | Path,
        *,
        overrides: dict[str, Any] | None = None,
        additional_sources: dict[str, dict[str, Any]] | None = None,
    ) -> None:
        questionnaire_payload = json.loads(Path(questionnaire_path).read_text(encoding="utf-8"))
        self._payloads: dict[str, dict[str, Any]] = {
            "VQ-OC-001": _deep_merge(questionnaire_payload, overrides or {}),
        }
        if additional_sources:
            self._payloads.update(additional_sources)

    def get_first(self, source_id: str, candidate_paths: tuple[str, ...]) -> Any:
        payload = self._payloads.get(source_id, {})
        for field_path in candidate_paths:
            try:
                current: Any = payload
                for key in field_path.split("."):
                    current = current[key]
                return current
            except (KeyError, TypeError):
                continue
        raise KeyError(candidate_paths[0])

    def read_fields(self, source_id: str, field_map: dict[str, tuple[str, ...]]) -> tuple[dict[str, Any], list[str]]:
        if source_id not in self._payloads:
            return {}, list(field_map.keys())
        values: dict[str, Any] = {}
        missing: list[str] = []
        for output_key, candidate_paths in field_map.items():
            try:
                values[output_key] = self.get_first(source_id, candidate_paths)
            except KeyError:
                missing.append(output_key)
        return values, missing
