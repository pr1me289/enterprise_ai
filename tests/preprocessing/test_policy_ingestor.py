from __future__ import annotations

from pathlib import Path

from preprocessing import load_source


def test_policy_pdf_is_normalized_into_sections(mock_documents_dir: Path) -> None:
    source = load_source(mock_documents_dir / "IT_Security_Policy_v4.2.pdf")

    assert source.source_id == "ISP-001"
    assert source.sections
    assert source.sections[0].section_id
    assert source.raw_text
