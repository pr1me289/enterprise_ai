from __future__ import annotations

from pathlib import Path

from preprocessing import load_source
from preprocessing.models import ManifestStatus, SourceType


def test_precedent_log_preserves_record_boundaries(mock_documents_dir: Path) -> None:
    source = load_source(mock_documents_dir / "Vendor_Precedent_Log_v1_1.json")

    assert source.source_id == "PVD-001"
    assert source.source_type is SourceType.VENDOR_PRECEDENT
    assert source.manifest_status is ManifestStatus.CONFIRMED
    assert source.document_id == "PRECEDENT-LOG-001"
    assert source.detected_version == "1.1"
    assert len(source.records) == 4
    assert source.records[0].record_id == "PVD-001-REC-001"
    assert source.records[1].fields["vendor"]["name"] == "Fortbridge Systems, Inc."
    assert "key_issue: EU employee personal data in scope" in source.records[0].text
    assert "precedents_established[0]:" in source.records[0].text
    assert "Fortbridge Systems, Inc." in source.raw_text
