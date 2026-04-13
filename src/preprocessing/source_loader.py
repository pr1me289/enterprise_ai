"""Dispatcher for source-specific preprocessors."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

from .matrix_ingestor import ingest_matrix
from .models import NormalizedSource, SourceType
from .policy_ingestor import ingest_policy
from .precedent_ingestor import ingest_precedent_log
from .questionnaire_ingestor import ingest_questionnaire
from .slack_ingestor import ingest_slack_threads
from .source_contract import resolve_contract_for_path


def load_source(path: str | Path) -> NormalizedSource:
    source_path = Path(path)
    contract = resolve_contract_for_path(source_path)

    if contract.source_type is SourceType.POLICY_DOCUMENT:
        return ingest_policy(source_path, contract)
    if contract.source_type in {
        SourceType.LEGAL_TRIGGER_MATRIX,
        SourceType.PROCUREMENT_APPROVAL_MATRIX,
    }:
        return ingest_matrix(source_path, contract)
    if contract.source_type is SourceType.VENDOR_QUESTIONNAIRE:
        return ingest_questionnaire(source_path, contract)
    if contract.source_type is SourceType.VENDOR_PRECEDENT:
        return ingest_precedent_log(source_path, contract)
    if contract.source_type is SourceType.SLACK_THREAD:
        return ingest_slack_threads(source_path, contract)
    raise ValueError(f"Unsupported source type for {source_path}")


def load_sources(paths: Iterable[str | Path]) -> list[NormalizedSource]:
    return [load_source(path) for path in paths]
