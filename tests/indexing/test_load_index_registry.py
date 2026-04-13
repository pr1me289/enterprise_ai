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


def test_load_index_registry_reads_generated_sources_payload(repo_root) -> None:
    payload = load_index_registry(repo_root / "data/indexes/index_registry.json")

    assert payload["registry_version"] == "1.0"
    assert "ISP-001" in payload["sources"]
    assert "VQ-OC-001" in payload["sources"]


def test_registry_helpers_expose_canonical_source_to_store_map(repo_root) -> None:
    registry_path = repo_root / "data/indexes/index_registry.json"

    assert get_logical_store_name("ISP-001", registry_path) == "idx_security_policy"
    assert get_backends("SLK-001", registry_path) == ["chroma", "bm25"]
    assert get_allowed_agents("SLK-001", registry_path) == ["procurement"]
    assert is_indexed_source("PVD-001", registry_path) is True
    assert is_structured_source("VQ-OC-001", registry_path) is True
    assert get_registry_entry("ISP-001", registry_path)["source_type"] == "POLICY_DOCUMENT"
    assert get_entry_by_logical_store_name("vq_direct_access", registry_path)["source_id"] == "VQ-OC-001"
    assert list_indexed_sources(registry_path) == [
        "DPA-TM-001",
        "ISP-001",
        "PAM-001",
        "PVD-001",
        "SLK-001",
    ]
    assert list_structured_sources(registry_path) == ["VQ-OC-001"]
