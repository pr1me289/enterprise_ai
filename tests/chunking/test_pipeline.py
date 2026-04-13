from __future__ import annotations

import json
from pathlib import Path

from chunking.artifacts import scenario_chunk_artifact_dir
from chunking.pipeline import build_chunk_artifacts_from_paths, build_scenario_chunk_artifacts


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

    assert {path.name for path in written} == {"ISP-001.json"}
    assert not (tmp_path / "VQ-OC-001.json").exists()

    policy_payload = json.loads((tmp_path / "ISP-001.json").read_text(encoding="utf-8"))
    assert policy_payload[0]["chunk_type"] == "SECTION"
    assert policy_payload[0]["source_type"] == "POLICY_DOCUMENT"
    assert policy_payload[0]["section_id"] == "1"
    assert policy_payload[0]["document_date"] == "2026-04-04"
    assert policy_payload[0]["freshness_status"] == "CURRENT"
    assert policy_payload[0]["is_primary_citable"] is True
    assert all(chunk["section_id"] not in {"6.1", "6.1.1", "12.1.4"} for chunk in policy_payload)
    assert not any(chunk["text"].endswith("---") for chunk in policy_payload)
    assert any(chunk["section_id"] == "12" for chunk in policy_payload)


def test_build_scenario_chunk_artifacts_writes_scenario_specific_outputs(
    repo_root: Path,
    tmp_path: Path,
) -> None:
    output_dir = tmp_path / "scenario_1" / "chunks"

    written = build_scenario_chunk_artifacts(
        "scenario_1",
        output_dir=output_dir,
        repo_root=repo_root,
    )

    assert {path.name for path in written} == {"ISP-001.json", "SLK-001.json", "SHM-001.json"}
    assert not (output_dir / "VQ-OC-001.json").exists()

    stakeholder_payload = json.loads((output_dir / "SHM-001.json").read_text(encoding="utf-8"))
    assert stakeholder_payload[0]["source_type"] == "STAKEHOLDER_MAP"
    assert stakeholder_payload[0]["record_id"] == "SUMMARY"


def test_scenario_chunk_artifact_dir_uses_separate_paths() -> None:
    assert scenario_chunk_artifact_dir("scenario_1") == Path("data/processed/scenario_1/chunks")
    assert scenario_chunk_artifact_dir("scenario_2") == Path("data/processed/scenario_2/chunks")
