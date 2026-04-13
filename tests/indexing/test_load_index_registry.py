from __future__ import annotations

from indexing.load_index_registry import (
    get_allowed_agents,
    get_backends,
    get_entry_by_logical_store_name,
    get_logical_store_name,
    get_registry_entry,
    is_indexed_source,
    is_structured_source,
    list_indexed_sources,
    list_structured_sources,
    load_index_registry,
)
from indexing.pipeline import build_storage_indices_for_scenario


def test_load_index_registry_reads_generated_sources_payload(repo_root) -> None:
    payload = load_index_registry(repo_root / "data/indexes/index_registry.json")

    assert payload["registry_version"] == "1.0"
    assert "ISP-001" in payload["sources"]
    assert "VQ-OC-001" in payload["sources"]


def test_registry_helpers_expose_canonical_source_to_store_map(repo_root, tmp_path) -> None:
    result = build_storage_indices_for_scenario(
        "scenario_1",
        repo_root=repo_root,
        chroma_persist_directory=tmp_path / "scenario_1/chroma",
        vector_registry_directory=tmp_path / "scenario_1/vector_registry",
        bm25_persist_directory=tmp_path / "scenario_1/bm25",
        structured_store_directory=tmp_path / "scenario_1/structured",
        index_registry_path=tmp_path / "scenario_1/index_registry.json",
        embed_texts=lambda texts: [[float(index)] for index, _ in enumerate(texts, start=1)],
    )
    registry_path = result["index_registry_path"]

    assert get_logical_store_name("ISP-001", registry_path) == "idx_security_policy"
    assert get_backends("SLK-001", registry_path) == ["chroma", "bm25"]
    assert get_allowed_agents("SLK-001", registry_path) == ["procurement"]
    assert is_indexed_source("SLK-001", registry_path) is True
    assert is_structured_source("VQ-OC-001", registry_path) is True
    assert is_structured_source("SHM-001", registry_path) is True
    assert get_registry_entry("ISP-001", registry_path)["source_type"] == "POLICY_DOCUMENT"
    assert get_registry_entry("ISP-001", registry_path)["manifest_status"] == "CONFIRMED"
    assert get_registry_entry("SLK-001", registry_path)["authority_tier"] == 3
    assert get_entry_by_logical_store_name("vq_direct_access", registry_path)["source_id"] == "VQ-OC-001"
    assert get_entry_by_logical_store_name("stakeholder_map_direct_access", registry_path)["source_id"] == "SHM-001"
    assert list_indexed_sources(registry_path) == [
        "ISP-001",
        "SLK-001",
    ]
    assert list_structured_sources(registry_path) == ["SHM-001", "VQ-OC-001"]
