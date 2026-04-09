from __future__ import annotations

from indexing.index_registry import (
    INDEX_CONFIG,
    SOURCE_ID_TO_INDEX_NAME,
    build_index_registry_payload,
    group_chunks_by_index_name,
    index_name_for_source,
)
from indexing.pipeline import load_chunk_artifacts_from_dir


def test_index_name_for_source_uses_explicit_contract_mapping() -> None:
    assert index_name_for_source("ISP-001") == "idx_security_policy"
    assert index_name_for_source("DPA-TM-001") == "idx_dpa_matrix"
    assert index_name_for_source("PAM-001") == "idx_procurement_matrix"
    assert index_name_for_source("PVD-001") == "idx_precedents"
    assert index_name_for_source("SLK-001") == "idx_slack_notes"
    assert index_name_for_source("VQ-OC-001") == "vq_direct_access"


def test_group_chunks_by_index_name_uses_per_source_logical_indices(repo_root) -> None:
    chunks = load_chunk_artifacts_from_dir(repo_root / "data/processed/chunks")

    grouped = group_chunks_by_index_name(chunks)

    assert set(grouped) == set(INDEX_CONFIG)
    assert grouped["idx_security_policy"][0].source_id == "ISP-001"
    assert grouped["idx_precedents"][0].source_id == "PVD-001"


def test_build_index_registry_payload_captures_versions_and_counts(repo_root) -> None:
    chunks = load_chunk_artifacts_from_dir(repo_root / "data/processed/chunks")
    grouped = group_chunks_by_index_name(chunks)

    payload = build_index_registry_payload(
        chunk_groups=grouped,
        embedding_model="sentence-transformers/all-MiniLM-L6-v2",
    )

    assert payload["indices"]["idx_security_policy"]["chunk_count"] == 82
    assert payload["indices"]["idx_slack_notes"]["source_id"] == "SLK-001"
    assert payload["structured_store"]["store_name"] == "vq_direct_access"
