"""Structured-store persistence for questionnaire access outside retrieval indices."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from preprocessing import load_source

from .index_registry import DEFAULT_STRUCTURED_STORE_DIR, DEFAULT_STRUCTURED_STORE_NAME


class StructuredStore:
    """Plain JSON direct-access store for structured questionnaire data."""

    def __init__(self, *, output_dir: str | Path = DEFAULT_STRUCTURED_STORE_DIR) -> None:
        self.output_dir = Path(output_dir)

    def build(self, store_name: str, payload: dict[str, Any]) -> Path:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        output_path = self.output_dir / f"{store_name}.json"
        output_path.write_text(
            json.dumps(payload, indent=2, ensure_ascii=True) + "\n",
            encoding="utf-8",
        )
        return output_path

    def load(self, store_name: str) -> dict[str, Any]:
        return json.loads((self.output_dir / f"{store_name}.json").read_text(encoding="utf-8"))

    def get_field(self, store_name: str, field_path: str) -> Any:
        payload = self.load(store_name)
        current: Any = payload["data"]
        for key in field_path.split("."):
            current = current[key]
        return current


def build_structured_store(
    questionnaire_path: str | Path,
    *,
    store: StructuredStore | None = None,
    store_name: str = DEFAULT_STRUCTURED_STORE_NAME,
) -> Path:
    questionnaire = load_source(questionnaire_path)
    if questionnaire.source_id != "VQ-OC-001":
        raise ValueError("Structured store build expects the questionnaire source.")

    payload = {
        "store_name": store_name,
        "source_id": questionnaire.source_id,
        "source_name": questionnaire.source_name,
        "source_type": questionnaire.source_type.value,
        "version": questionnaire.version,
        "document_date": questionnaire.document_date,
        "freshness_status": questionnaire.freshness_status,
        "allowed_agents": list(questionnaire.allowed_agents),
        "is_primary_citable": questionnaire.is_primary_citable,
        "manifest_status": questionnaire.manifest_status.value,
        "data": questionnaire.structured_data,
    }
    structured_store = store or StructuredStore()
    return structured_store.build(store_name, payload)
