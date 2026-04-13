"""Ingest questionnaire JSON into direct-access structured objects."""

from __future__ import annotations

import json
from pathlib import Path

from .models import NormalizedSource
from .source_contract import SourceContract
from .text_utils import flatten_json_to_text


def ingest_questionnaire(path: str | Path, contract: SourceContract) -> NormalizedSource:
    source_path = Path(path)
    data = json.loads(source_path.read_text(encoding="utf-8"))
    detected_version = str(data.get("version") or "") or _detect_version_from_name(source_path.name)

    return NormalizedSource(
        source_id=contract.source_id,
        source_type=contract.source_type,
        source_name=contract.source_name,
        version=contract.version,
        document_date=contract.document_date,
        freshness_status=contract.freshness_status,
        authority_tier=contract.authority_tier,
        retrieval_lane=contract.retrieval_lane,
        allowed_agents=contract.allowed_agents,
        is_primary_citable=contract.is_primary_citable,
        manifest_status=contract.manifest_status,
        owner_role=contract.owner_role,
        source_path=source_path,
        raw_text=flatten_json_to_text(data),
        structured_data=data,
        document_id=str(data.get("document_id") or contract.source_id),
        detected_version=detected_version,
        warnings=[],
    )


def _detect_version_from_name(filename: str) -> str | None:
    stem = Path(filename).stem
    tokens = stem.replace("-", "_").split("_")
    if "v" not in "".join(tokens).lower():
        return None
    values = [token.lower().lstrip("v") for token in tokens if token.lower().startswith("v") or token.isdigit()]
    if not values:
        return None
    return ".".join(values[-2:]) if len(values) >= 2 else values[0]
