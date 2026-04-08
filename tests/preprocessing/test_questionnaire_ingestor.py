from __future__ import annotations

from pathlib import Path

from preprocessing import load_source
from preprocessing.models import ManifestStatus, RetrievalLane, SourceType


def test_questionnaire_json_stays_structured(mock_documents_dir: Path) -> None:
    source = load_source(mock_documents_dir / "OptiChain_VSQ_001_v2_1.json")

    assert source.source_id == "VQ-OC-001"
    assert source.source_type is SourceType.QUESTIONNAIRE
    assert source.retrieval_lane is RetrievalLane.DIRECT_STRUCTURED
    assert source.status is ManifestStatus.PENDING
    assert source.document_id == "VSQ-001"
    assert source.detected_version == "2.1"
    assert source.structured_data["vendor_profile"]["vendor_legal_name"] == "OptiChain, Inc."
    assert source.structured_data["product_and_integration"]["erp_integration"]["erp_tier_status"] == "PROVISIONAL"
    assert source.rows == []
    assert source.records == []
    assert source.threads == []
    assert "vendor_profile.vendor_legal_name: OptiChain, Inc." in source.raw_text
