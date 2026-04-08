from __future__ import annotations

from pathlib import Path

import pytest

from preprocessing import load_source


@pytest.mark.parametrize(
    ("filename", "source_id", "collection_name", "expected_count"),
    [
        ("DPA_Legal_Trigger_Matrix_v1_3.xlsx", "DPA-TM-001", "rows", 27),
        ("Procurement_Approval_Matrix_v2_0.xlsx", "PAM-001", "rows", 20),
        ("OptiChain_VSQ_001_v2_1.json", "VQ-OC-001", "rows", 0),
        ("Vendor_Precedent_Log_v1_1.json", "PVD-001", "records", 4),
        ("Slack_Thread_Export_001.json", "SLK-001", "threads", 4),
        ("Slack_Thread_Export_001.md", "SLK-001", "threads", 4),
    ],
)
def test_load_source_routes_supported_mock_documents(
    mock_documents_dir: Path,
    filename: str,
    source_id: str,
    collection_name: str,
    expected_count: int,
) -> None:
    source = load_source(mock_documents_dir / filename)

    assert source.source_id == source_id
    assert len(getattr(source, collection_name)) == expected_count
    assert source.raw_text
    assert source.allowed_agents


def test_load_source_rejects_unsupported_mock_document(mock_documents_dir: Path) -> None:
    unsupported_file = mock_documents_dir / "Stakeholder_Map_PRQ_2024_0047.json"

    with pytest.raises(ValueError, match="Unsupported source file"):
        load_source(unsupported_file)
