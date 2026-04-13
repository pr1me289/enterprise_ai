"""Direct structured access for the questionnaire lane."""

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
    """Field-level access into the questionnaire JSON object."""

    def __init__(self, questionnaire_path: str | Path, *, overrides: dict[str, Any] | None = None) -> None:
        payload = json.loads(Path(questionnaire_path).read_text(encoding="utf-8"))
        self.payload = _deep_merge(payload, overrides or {})

    def get_first(self, candidate_paths: tuple[str, ...]) -> Any:
        for field_path in candidate_paths:
            try:
                return self._resolve_path(field_path)
            except KeyError:
                continue
        raise KeyError(candidate_paths[0])

    def read_fields(self, field_map: dict[str, tuple[str, ...]]) -> tuple[dict[str, Any], list[str]]:
        values: dict[str, Any] = {}
        missing: list[str] = []
        for output_key, candidate_paths in field_map.items():
            try:
                values[output_key] = self.get_first(candidate_paths)
            except KeyError:
                missing.append(output_key)
        return values, missing

    def _resolve_path(self, field_path: str) -> Any:
        current: Any = self.payload
        for key in field_path.split("."):
            current = current[key]
        return current
