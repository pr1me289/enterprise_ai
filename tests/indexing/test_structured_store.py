from __future__ import annotations

from indexing.build_structured_store import StructuredStore, build_structured_store


def test_build_structured_store_writes_questionnaire_payload(repo_root, tmp_path) -> None:
    output_path = build_structured_store(
        repo_root / "mock_documents/OptiChain_VSQ_001_v2_1.json",
        store=StructuredStore(output_dir=tmp_path),
    )

    store = StructuredStore(output_dir=tmp_path)
    payload = store.load("vq_direct_access")

    assert output_path.name == "vq_direct_access.json"
    assert payload["source_id"] == "VQ-OC-001"
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
