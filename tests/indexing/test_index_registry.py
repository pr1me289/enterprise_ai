from __future__ import annotations

from indexing.build_structured_store import StructuredStore, build_structured_stores
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
    assert index_name_for_source("DPA-TM-001") == "dpa_matrix_direct"
    assert index_name_for_source("PAM-001") == "procurement_matrix_direct"
    assert index_name_for_source("PVD-001") == "idx_precedents"
    assert index_name_for_source("SLK-001") == "idx_slack_notes"
    assert index_name_for_source("VQ-OC-001") == "vq_direct_access"
    assert index_name_for_source("SHM-001") == "stakeholder_map_direct_access"


def test_group_chunks_by_index_name_uses_per_source_logical_indices(repo_root) -> None:
    chunks = load_chunk_artifacts_from_dir(repo_root / "data/processed/scenario_1/chunks")

    grouped = group_chunks_by_index_name(chunks)

    assert set(grouped) == {
        "idx_security_policy",
        "idx_slack_notes",
    }
    assert grouped["idx_security_policy"][0].source_id == "ISP-001"
    assert grouped["idx_slack_notes"][0].source_id == "SLK-001"


def test_build_index_registry_payload_is_source_level_and_uses_store_mapping(repo_root, tmp_path) -> None:
    chunks = load_chunk_artifacts_from_dir(repo_root / "data/processed/scenario_1/chunks")
    grouped = group_chunks_by_index_name(chunks)
    structured_store_paths = build_structured_stores(
        [
            repo_root / "scenarios/scenario_1/source_mock_documents/OptiChain_VSQ_001_v2_1_scenario01.json",
            repo_root / "scenarios/scenario_1/source_mock_documents/Stakeholder_Map_PRQ_2024_0047.json",
        ],
        store=StructuredStore(output_dir=tmp_path / "structured"),
    )

    payload = build_index_registry_payload(
        chunk_groups=grouped,
        structured_store_paths=list(structured_store_paths.values()),
        bm25_persist_directory=repo_root / "data/bm25/scenario_1",
    )

    assert payload["registry_version"] == "1.0"
    assert set(payload["sources"]) == {
        "ISP-001",
        "SLK-001",
        "VQ-OC-001",
        "SHM-001",
    }
    assert payload["sources"]["ISP-001"]["logical_store_name"] == "idx_security_policy"
    assert payload["sources"]["ISP-001"]["storage_kind"] == "vector_bm25"
    assert payload["sources"]["ISP-001"]["backends"] == ["chroma", "bm25"]
    assert payload["sources"]["ISP-001"]["manifest_status"] == "CONFIRMED"
    assert payload["sources"]["ISP-001"]["backend_locations"]["chroma_collection"] == "idx_security_policy"
    assert payload["sources"]["SLK-001"]["allowed_agents"] == ["procurement"]
    assert payload["sources"]["SLK-001"]["authority_tier"] == 3
    assert payload["sources"]["VQ-OC-001"]["logical_store_name"] == "vq_direct_access"
    assert payload["sources"]["VQ-OC-001"]["storage_kind"] == "structured_direct"
    assert payload["sources"]["SHM-001"]["logical_store_name"] == "stakeholder_map_direct_access"
    assert payload["sources"]["SHM-001"]["storage_kind"] == "structured_direct"
