"""Ingest precedent logs while preserving record boundaries."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .models import NormalizedSource, PrecedentRecord
from .source_contract import SourceContract
from .text_utils import flatten_json_to_text, normalize_text


def ingest_precedent_log(path: str | Path, contract: SourceContract) -> NormalizedSource:
    source_path = Path(path)
    data = json.loads(source_path.read_text(encoding="utf-8"))
    records_payload = data.get("records", [])
    detected_version = str(data.get("version") or "") or _detect_version_from_name(source_path.name)

    records = [
        PrecedentRecord(
            record_id=str(record.get("record_id") or f"record-{index:03d}"),
            text=_record_to_text(record),
            order=index,
            fields=record,
        )
        for index, record in enumerate(records_payload, start=1)
    ]

    raw_text = "\n\n".join(record.text for record in records)

    return NormalizedSource(
        source_id=contract.source_id,
        source_type=contract.source_type,
        source_name=contract.source_name,
        version=contract.version,
        authority_tier=contract.authority_tier,
        retrieval_lane=contract.retrieval_lane,
        allowed_agents=contract.allowed_agents,
        manifest_status=contract.manifest_status,
        owner_role=contract.owner_role,
        source_path=source_path,
        raw_text=normalize_text(raw_text),
        structured_data=data,
        records=records,
        document_id=str(data.get("document_id") or contract.source_id),
        detected_version=detected_version,
        warnings=[],
    )


def _record_to_text(record: dict[str, Any]) -> str:
    preferred_fields = [
        ("record_id", record.get("record_id")),
        ("key_issue", record.get("key_issue")),
        ("vendor_name", (record.get("vendor") or {}).get("name")),
        ("product_summary", record.get("product_summary")),
        ("lessons_recorded", record.get("lessons_recorded")),
    ]
    lines = [f"{key}: {value}" for key, value in preferred_fields if value]
    lines.append(flatten_json_to_text(record.get("domain_determinations", {}), "domain_determinations"))
    lines.append(flatten_json_to_text(record.get("precedents_established", []), "precedents_established"))
    return normalize_text("\n".join(line for line in lines if line))


def _detect_version_from_name(filename: str) -> str | None:
    stem = Path(filename).stem
    tokens = stem.replace("-", "_").split("_")
    version_tokens = [token.lower().lstrip("v") for token in tokens if token.lower().startswith("v") or token.isdigit()]
    if not version_tokens:
        return None
    return ".".join(version_tokens[-2:]) if len(version_tokens) >= 2 else version_tokens[0]
