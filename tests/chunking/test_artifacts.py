from __future__ import annotations

import json
from pathlib import Path

from chunking.artifacts import chunk_and_write_sources, write_chunk_artifacts
from chunking.chunker import chunk_source
from preprocessing import load_source


def test_write_chunk_artifacts_writes_per_source_json(mock_documents_dir: Path, tmp_path: Path) -> None:
    dpa_source = load_source(mock_documents_dir / "DPA_Legal_Trigger_Matrix_v1_3.xlsx")
    questionnaire_source = load_source(mock_documents_dir / "OptiChain_VSQ_001_v2_1.json")

    written = write_chunk_artifacts(
        {
            dpa_source.source_id: chunk_source(dpa_source),
            questionnaire_source.source_id: chunk_source(questionnaire_source),
        },
        output_dir=tmp_path,
    )

    assert written == [tmp_path / "DPA-TM-001.json"]
    assert not (tmp_path / "VQ-OC-001.json").exists()

    payload = json.loads((tmp_path / "DPA-TM-001.json").read_text(encoding="utf-8"))
    assert len(payload) == 27
    assert payload[0]["chunk_id"] == "DPA-TM-001__row_A-01"
    assert payload[0]["allowed_agents"] == ["legal"]


def test_chunk_and_write_sources_builds_artifacts_from_normalized_sources(
    mock_documents_dir: Path,
    tmp_path: Path,
) -> None:
    sources = [
        load_source(mock_documents_dir / "Vendor_Precedent_Log_v1_1.json"),
        load_source(mock_documents_dir / "Slack_Thread_Export_001.json"),
        load_source(mock_documents_dir / "OptiChain_VSQ_001_v2_1.json"),
    ]

    written = chunk_and_write_sources(sources, output_dir=tmp_path)

    assert {path.name for path in written} == {"PVD-001.json", "SLK-001.json"}
    assert not (tmp_path / "VQ-OC-001.json").exists()

    precedent_payload = json.loads((tmp_path / "PVD-001.json").read_text(encoding="utf-8"))
    slack_payload = json.loads((tmp_path / "SLK-001.json").read_text(encoding="utf-8"))
    assert precedent_payload[0]["record_id"] == "PVD-001-REC-001"
    assert slack_payload[0]["thread_id"] == "SLK-001-THREAD-01"
