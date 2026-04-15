from __future__ import annotations

from pathlib import Path

import pytest

from chunking.chunker import chunk_source, chunk_sources
from preprocessing import load_source
from preprocessing.models import ManifestStatus, NormalizedSource, RetrievalLane, SourceType


def test_policy_source_chunks_by_section(mock_documents_dir: Path) -> None:
    source = load_source(mock_documents_dir / "IT_Security_Policy_V4.2.md")

    chunks = chunk_source(source)

    assert chunks
    assert all(chunk.chunk_type == "SECTION" for chunk in chunks)
    assert all(chunk.source_id == "ISP-001" for chunk in chunks)
    assert all(chunk.section_id for chunk in chunks)
    assert all(chunk.row_id is None for chunk in chunks)
    assert chunks[0].citation_label.startswith("ISP-001")
    assert chunks[0].allowed_agents == ("it_security", "legal", "procurement")
    assert chunks[0].manifest_status == "CONFIRMED"
    assert chunks[0].document_date == "2026-04-04"
    assert chunks[0].freshness_status == "CURRENT"
    assert chunks[0].is_primary_citable is True
    assert chunks[0].section_id == "1"
    assert chunks[0].text.startswith("1 Purpose")
    assert not chunks[0].text.endswith("---")
    assert chunks[0].chunk_order == 1
    section_ids = {chunk.section_id for chunk in chunks}
    assert "6" in section_ids
    assert "6.1" not in section_ids
    assert "6.1.1" not in section_ids
    assert any(chunk.section_id == "12" for chunk in chunks)
    nda_chunk = next(chunk for chunk in chunks if chunk.section_id == "12")
    assert "Onboarding may not proceed to the information-exchange phase" in nda_chunk.text


def test_dpa_matrix_chunks_by_row(scenario_1_mock_documents_dir: Path) -> None:
    source = load_source(scenario_1_mock_documents_dir / "DPA_Legal_Trigger_Matrix_v1_3.csv")

    chunks = chunk_source(source)

    assert source.retrieval_lane.value == "INDEXED_HYBRID"
    assert source.structured_data is not None
    assert "rows" in source.structured_data
    assert len(source.structured_data["rows"]) == 27
    assert len(chunks) == 27
    assert all(chunk.chunk_type == "ROW" for chunk in chunks)
    assert all(chunk.source_id == "DPA-TM-001" for chunk in chunks)
    assert chunks[0].citation_label.startswith("DPA-TM-001 row")


def test_procurement_matrix_chunks_by_row(scenario_1_mock_documents_dir: Path) -> None:
    source = load_source(scenario_1_mock_documents_dir / "Procurement_Approval_Matrix_v2_0.csv")

    chunks = chunk_source(source)

    assert source.retrieval_lane.value == "INDEXED_HYBRID"
    assert source.structured_data is not None
    assert "rows" in source.structured_data
    assert len(source.structured_data["rows"]) == 20
    assert len(chunks) == 20
    assert all(chunk.chunk_type == "ROW" for chunk in chunks)
    assert all(chunk.source_id == "PAM-001" for chunk in chunks)
    assert chunks[0].citation_label.startswith("PAM-001 row")


def test_precedent_source_chunks_by_record(mock_documents_dir: Path) -> None:
    source = load_source(mock_documents_dir / "Vendor_Precedent_Log_v1_1.json")

    chunks = chunk_source(source)

    assert len(chunks) == 4
    assert all(chunk.chunk_type == "RECORD" for chunk in chunks)
    assert all(chunk.source_type == "VENDOR_PRECEDENT" for chunk in chunks)
    assert chunks[0].record_id == "PVD-001-REC-001"
    assert chunks[0].citation_label == "PVD-001 record PVD-001-REC-001"
    assert chunks[0].document_date == "2026-04-04"
    assert chunks[0].is_primary_citable is False
    assert chunks[0].domain_scope == "legal"
    assert chunks[1].domain_scope == "security"
    assert chunks[2].domain_scope == "legal"
    assert chunks[3].domain_scope == "procurement"
    assert "Meridian Analytics, Ltd." in chunks[0].text


def test_slack_source_chunks_by_thread(mock_documents_dir: Path) -> None:
    source = load_source(mock_documents_dir / "Slack_Thread_Export_001.json")

    chunks = chunk_source(source)

    assert len(chunks) == 4
    assert all(chunk.chunk_type == "THREAD" for chunk in chunks)
    assert all(chunk.source_type == "SLACK_THREAD" for chunk in chunks)
    assert chunks[0].thread_id == "SLK-001-THREAD-01"
    assert chunks[0].citation_label == "SLK-001 thread SLK-001-THREAD-01"
    assert chunks[0].document_date == "2026-04-04"
    assert chunks[0].is_primary_citable is False
    assert chunks[0].authority_tier == 3
    assert all(chunk.allowed_agents == ("procurement",) for chunk in chunks)
    assert "vendor-eval-optichain" in chunks[0].text


def test_stakeholder_map_chunks_by_structured_entry(scenario_1_mock_documents_dir: Path) -> None:
    source = load_source(scenario_1_mock_documents_dir / "Stakeholder_Map_PRQ_2024_0047.json")

    chunks = chunk_source(source)

    assert len(chunks) == 15
    assert all(chunk.chunk_type == "RECORD" for chunk in chunks)
    assert all(chunk.source_type == "STAKEHOLDER_MAP" for chunk in chunks)
    assert chunks[0].record_id == "SUMMARY"
    assert chunks[0].citation_label == "SHM-001 summary"
    assert chunks[0].allowed_agents == ("checkoff",)
    assert chunks[0].text.startswith("stakeholder_map.document_id: STAKEHOLDER-MAP-001")
    assert chunks[1].record_id == "ROLE-IT-SECURITY"
    assert "role.role_label: IT Security" in chunks[1].text
    approval_chunk = next(chunk for chunk in chunks if chunk.record_id == "APPROVAL-02")
    assert approval_chunk.citation_label == "SHM-001 approval General Counsel"
    assert "approval.status: ESCALATED" in approval_chunk.text
    escalation_chunk = next(chunk for chunk in chunks if chunk.record_id == "ESC-002")
    assert "escalation.resolution_owner: General Counsel" in escalation_chunk.text
    assert chunks[-1].record_id == "VENDOR-CONTACT"
    assert "vendor_contact.email: j.levi@optichain.io" in chunks[-1].text


def test_questionnaire_source_is_not_chunked(mock_documents_dir: Path) -> None:
    source = load_source(mock_documents_dir / "OptiChain_VSQ_001_v2_1.json")

    chunks = chunk_source(source)

    assert chunks == []


def test_chunk_sources_returns_source_id_keyed_map(
    mock_documents_dir: Path,
    scenario_1_mock_documents_dir: Path,
) -> None:
    sources = [
        load_source(scenario_1_mock_documents_dir / "DPA_Legal_Trigger_Matrix_v1_3.csv"),
        load_source(mock_documents_dir / "OptiChain_VSQ_001_v2_1.json"),
        load_source(mock_documents_dir / "Slack_Thread_Export_001.json"),
        load_source(scenario_1_mock_documents_dir / "Stakeholder_Map_PRQ_2024_0047.json"),
    ]

    chunk_map = chunk_sources(sources)

    assert set(chunk_map) == {"DPA-TM-001", "VQ-OC-001", "SLK-001", "SHM-001"}
    assert len(chunk_map["DPA-TM-001"]) == 27
    assert chunk_map["VQ-OC-001"] == []
    assert len(chunk_map["SLK-001"]) == 4
    assert len(chunk_map["SHM-001"]) == 15


def test_chunk_source_rejects_unsupported_source_type() -> None:
    source = NormalizedSource(
        source_id="BAD-001",
        source_type="UNKNOWN",  # type: ignore[arg-type]
        source_name="Bad Source",
        version="0",
        document_date=None,
        freshness_status="CURRENT",
        authority_tier=0,
        retrieval_lane=RetrievalLane.INDEXED_HYBRID,
        allowed_agents=(),
        is_primary_citable=False,
        manifest_status=ManifestStatus.PENDING,
        owner_role="None",
        source_path=Path("/tmp/bad.txt"),
        raw_text="bad",
    )

    with pytest.raises(ValueError, match="Unsupported source type"):
        chunk_source(source)
