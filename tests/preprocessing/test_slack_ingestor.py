from __future__ import annotations

from pathlib import Path

from preprocessing import load_source
from preprocessing.models import ManifestStatus, SourceType


def test_slack_json_preserves_threads_and_messages(mock_documents_dir: Path) -> None:
    source = load_source(mock_documents_dir / "Slack_Thread_Export_001.json")

    assert source.source_id == "SLK-001"
    assert source.source_type is SourceType.SUPPLEMENTAL_NOTE
    assert source.status is ManifestStatus.CONFIRMED
    assert source.document_id == "SLACK-EXPORT-001"
    assert source.detected_version == "1.0"
    assert len(source.threads) == 4
    assert source.threads[0].thread_id == "SLK-001-THREAD-01"
    assert source.threads[0].channel == "#vendor-eval-optichain"
    assert source.threads[0].message_count == 9
    assert len(source.threads[0].messages) == 9
    assert source.threads[0].messages[0].author == "P. Horak"
    assert "Questionnaire received" not in source.threads[0].text
    assert "questionnaire submission through the vendor portal" in source.threads[0].text


def test_slack_markdown_preserves_thread_boundaries(mock_documents_dir: Path) -> None:
    source = load_source(mock_documents_dir / "Slack_Thread_Export_001.md")

    assert source.source_id == "SLK-001"
    assert source.structured_data is None
    assert len(source.threads) == 4
    assert source.threads[0].thread_id == "SLK-001-THREAD-01"
    assert source.threads[0].channel == "#vendor-eval-optichain"
    assert source.threads[0].message_count == 9
    assert source.threads[0].messages == []
    assert "Thread 01" in source.threads[0].text
