from __future__ import annotations

import json
from pathlib import Path

from chunking.pipeline import build_chunk_artifacts_from_paths


def test_build_chunk_artifacts_from_paths_uses_preprocessing_and_writes_json(
    mock_documents_dir: Path,
    tmp_path: Path,
) -> None:
    written = build_chunk_artifacts_from_paths(
        [
            mock_documents_dir / "IT_Security_Policy_V4.2.md",
            mock_documents_dir / "DPA_Legal_Trigger_Matrix_v1_3.xlsx",
            mock_documents_dir / "OptiChain_VSQ_001_v2_1.json",
        ],
        output_dir=tmp_path,
    )

    assert {path.name for path in written} == {"ISP-001.json", "DPA-TM-001.json"}
    assert not (tmp_path / "VQ-OC-001.json").exists()

    policy_payload = json.loads((tmp_path / "ISP-001.json").read_text(encoding="utf-8"))
    dpa_payload = json.loads((tmp_path / "DPA-TM-001.json").read_text(encoding="utf-8"))
    assert policy_payload[0]["chunk_type"] == "SECTION"
    assert policy_payload[0]["source_type"] == "POLICY_DOCUMENT"
    assert policy_payload[0]["section_id"] == "1"
    assert policy_payload[0]["document_date"] == "2026-04-04"
    assert policy_payload[0]["freshness_status"] == "CURRENT"
    assert policy_payload[0]["is_primary_citable"] is True
    assert all(chunk["section_id"] not in {"6", "6.1", "6.2"} for chunk in policy_payload)
    assert not any(chunk["text"].endswith("---") for chunk in policy_payload)
    assert any(chunk["section_id"] == "12.1.4" for chunk in policy_payload)
    assert dpa_payload[0]["freshness_status"] == "CURRENT"
    assert dpa_payload[0]["source_type"] == "LEGAL_TRIGGER_MATRIX"
    assert dpa_payload[0]["document_date"] == "2026-04-04"
    assert dpa_payload[0]["is_primary_citable"] is True
    assert dpa_payload[0]["chunk_type"] == "ROW"
