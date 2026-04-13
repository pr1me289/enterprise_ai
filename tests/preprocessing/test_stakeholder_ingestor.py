from __future__ import annotations

from pathlib import Path

from preprocessing import load_source
from preprocessing.models import ManifestStatus, RetrievalLane, SourceType


def test_stakeholder_map_json_stays_structured(scenario_1_mock_documents_dir: Path) -> None:
    source = load_source(scenario_1_mock_documents_dir / "Stakeholder_Map_PRQ_2024_0047.json")

    assert source.source_id == "SHM-001"
    assert source.source_type is SourceType.STAKEHOLDER_MAP
    assert source.retrieval_lane is RetrievalLane.DIRECT_STRUCTURED
    assert source.manifest_status is ManifestStatus.CONFIRMED
    assert source.document_id == "STAKEHOLDER-MAP-001"
    assert source.detected_version == "1.0"
    assert source.structured_data["roles"][0]["role_label"] == "IT Security"
    assert source.structured_data["optichain_required_approvals"][0]["approver_role"] == "CISO"
    assert source.rows == []
    assert source.records == []
    assert source.threads == []
    assert "checkoff_agent_note:" in source.raw_text
