from __future__ import annotations

from indexing.build_structured_store import StructuredStore, build_structured_store, build_structured_stores


def test_build_structured_store_writes_questionnaire_payload(repo_root, tmp_path) -> None:
    output_path = build_structured_store(
        repo_root / "mock_documents/OptiChain_VSQ_001_v2_1.json",
        store=StructuredStore(output_dir=tmp_path),
    )

    store = StructuredStore(output_dir=tmp_path)
    payload = store.load("vq_direct_access")

    assert output_path.name == "vq_direct_access.json"
    assert payload["source_id"] == "VQ-OC-001"
    assert payload["source_type"] == "VENDOR_QUESTIONNAIRE"
    assert payload["authority_tier"] == 2
    assert payload["retrieval_lane"] == "DIRECT_STRUCTURED"
    assert payload["document_date"] == "2026-04-04"
    assert payload["freshness_status"] == "CURRENT"
    assert "vendor_profile" in payload["data"]


def test_structured_store_get_field_reads_nested_questionnaire_value(repo_root, tmp_path) -> None:
    build_structured_store(
        repo_root / "mock_documents/OptiChain_VSQ_001_v2_1.json",
        store=StructuredStore(output_dir=tmp_path),
    )

    store = StructuredStore(output_dir=tmp_path)
    value = store.get_field("vq_direct_access", "vendor_profile.vendor_legal_name")

    assert value == "OptiChain, Inc."


def test_build_structured_store_writes_stakeholder_map_payload(repo_root, tmp_path) -> None:
    output_path = build_structured_store(
        repo_root / "scenarios_full_pipeline/scenario_1/source_mock_documents/Stakeholder_Map_PRQ_2024_0047.json",
        store=StructuredStore(output_dir=tmp_path),
    )

    store = StructuredStore(output_dir=tmp_path)
    payload = store.load("stakeholder_map_direct_access")

    assert output_path.name == "stakeholder_map_direct_access.json"
    assert payload["source_id"] == "SHM-001"
    assert payload["source_type"] == "STAKEHOLDER_MAP"
    assert payload["retrieval_lane"] == "DIRECT_STRUCTURED"
    assert payload["allowed_agents"] == ["checkoff"]
    assert payload["data"]["roles"][0]["role_label"] == "IT Security"


def test_build_structured_stores_returns_both_direct_structured_source_paths(repo_root, tmp_path) -> None:
    paths = build_structured_stores(
        [
            repo_root / "scenarios_full_pipeline/scenario_1/source_mock_documents/OptiChain_VSQ_001_v2_1_scenario01.json",
            repo_root / "scenarios_full_pipeline/scenario_1/source_mock_documents/Stakeholder_Map_PRQ_2024_0047.json",
        ],
        store=StructuredStore(output_dir=tmp_path),
    )

    assert set(paths) == {"VQ-OC-001", "SHM-001"}
    assert paths["VQ-OC-001"].name == "vq_direct_access.json"
    assert paths["SHM-001"].name == "stakeholder_map_direct_access.json"
