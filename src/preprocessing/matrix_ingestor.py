"""Ingest matrix sources while preserving row boundaries."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from .models import MatrixRow, NormalizedSource
from .source_contract import SourceContract
from .text_utils import normalize_text, parse_markdown_table, xlsx_to_rows


def ingest_matrix(path: str | Path, contract: SourceContract) -> NormalizedSource:
    source_path = Path(path)
    payload = _load_matrix_rows(source_path)
    rows = payload["rows"]
    columns = payload["columns"]
    detected_version = _detect_version_from_name(source_path.name)

    normalized_rows = [
        MatrixRow(
            row_id=_derive_row_id(contract.source_id, row_values, index),
            values=row_values,
            text=_row_to_text(row_values),
            order=index,
        )
        for index, row_values in enumerate(rows, start=1)
    ]

    raw_text = "\n\n".join(row.text for row in normalized_rows)
    structured_data = {"columns": columns, "rows": [row.values for row in normalized_rows], "row_count": len(normalized_rows)}

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
        raw_text=normalize_text(raw_text),
        structured_data=structured_data,
        rows=normalized_rows,
        document_id=contract.source_id,
        detected_version=detected_version,
        warnings=[],
    )


def _load_matrix_rows(path: Path) -> dict[str, Any]:
    suffix = path.suffix.lower()
    if suffix == ".csv":
        with path.open(encoding="utf-8", newline="") as file_handle:
            reader = csv.DictReader(file_handle)
            rows = [{key: value.strip() for key, value in row.items()} for row in reader]
            return {"rows": rows, "columns": reader.fieldnames or []}
    if suffix == ".xlsx":
        rows = xlsx_to_rows(path)
        columns = list(rows[0].keys()) if rows else []
        return {"rows": rows, "columns": columns}
    if suffix == ".json":
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            rows = data.get("rows") or data.get("records") or []
        elif isinstance(data, list):
            rows = data
        else:
            raise ValueError(f"Unsupported matrix JSON shape: {path}")
        columns = list(rows[0].keys()) if rows else []
        return {"rows": rows, "columns": columns}
    if suffix in {".md", ".markdown"}:
        text = path.read_text(encoding="utf-8")
        rows = parse_markdown_table(text)
        columns = list(rows[0].keys()) if rows else []
        return {"rows": rows, "columns": columns}
    raise ValueError(f"Unsupported matrix format: {path.suffix}")


def _derive_row_id(source_id: str, row_values: dict[str, Any], index: int) -> str:
    if source_id == "DPA-TM-001":
        candidate = row_values.get("ID") or row_values.get("Id") or row_values.get("id")
        if candidate:
            return str(candidate)

    class_value = str(row_values.get("Class", "")).strip()
    tier_value = str(row_values.get("Tier", "")).strip()
    if class_value and tier_value:
        return f"{class_value}-{tier_value}"

    return f"row-{index:03d}"


def _row_to_text(row_values: dict[str, Any]) -> str:
    return normalize_text(
        "\n".join(
            f"{column}: {value}"
            for column, value in row_values.items()
            if value not in ("", None)
        )
    )


def _detect_version_from_name(filename: str) -> str | None:
    stem = Path(filename).stem
    tokens = stem.replace("-", "_").split("_")
    version_tokens: list[str] = []
    for token in tokens:
        if token.lower().startswith("v"):
            version_tokens.append(token.lower().lstrip("v"))
            continue
        if version_tokens and token.isdigit():
            version_tokens.append(token)
            break
    if not version_tokens:
        return None
    return ".".join(part for part in version_tokens if part)
