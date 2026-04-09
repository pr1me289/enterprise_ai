from __future__ import annotations

from indexing.index_registry import (
    INDEX_CONFIG,
    SOURCE_ID_TO_INDEX_NAME,
    SOURCE_STORE_CONFIG,
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


def test_build_index_registry_payload_is_source_level_and_uses_store_mapping(repo_root) -> None:
    chunks = load_chunk_artifacts_from_dir(repo_root / "data/processed/chunks")
    grouped = group_chunks_by_index_name(chunks)

    payload = build_index_registry_payload(
        chunk_groups=grouped,
        structured_store_path=repo_root / "data/structured/vq_direct_access.json",
        bm25_persist_directory=repo_root / "data/bm25",
    )

    assert payload["registry_version"] == "1.0"
    assert set(payload["sources"]) == set(SOURCE_STORE_CONFIG)
    assert payload["sources"]["ISP-001"]["logical_store_name"] == "idx_security_policy"
    assert payload["sources"]["ISP-001"]["storage_kind"] == "vector_bm25"
    assert payload["sources"]["ISP-001"]["backends"] == ["chroma", "bm25"]
    assert payload["sources"]["ISP-001"]["backend_locations"]["chroma_collection"] == "idx_security_policy"
    assert payload["sources"]["SLK-001"]["allowed_agents"] == ["procurement"]
    assert payload["sources"]["VQ-OC-001"]["logical_store_name"] == "vq_direct_access"
    assert payload["sources"]["VQ-OC-001"]["storage_kind"] == "structured_direct"
    assert payload["sources"]["VQ-OC-001"]["backend_locations"]["structured_store"].endswith(
        "data/structured/vq_direct_access.json"
    )
