from __future__ import annotations

from pathlib import Path

from preprocessing import load_source


def test_dpa_matrix_xlsx_preserves_row_boundaries(mock_documents_dir: Path) -> None:
    source = load_source(mock_documents_dir / "DPA_Legal_Trigger_Matrix_v1_3.xlsx")

    assert source.source_id == "DPA-TM-001"
    assert source.structured_data == {
        "columns": [
            "ID",
            "Trigger Condition",
            "Data Type(s) Involved",
            "Regulation(s) Triggered",
            "DPA Required?",
            "Required DPA / Contract Clauses",
            "Additional Obligations",
            "Lichen Action / Owner",
        ],
        "row_count": 27,
    }
    assert source.rows[0].row_id == "A-01"
    assert source.rows[0].order == 1
    assert "GDPR Art. 28" in source.rows[0].text
    assert source.rows[-1].row_id == "G-02"


def test_dpa_matrix_csv_preserves_row_boundaries(scenario_1_mock_documents_dir: Path) -> None:
    source = load_source(scenario_1_mock_documents_dir / "DPA_Legal_Trigger_Matrix_v1_3.csv")

    assert source.source_id == "DPA-TM-001"
    assert source.structured_data["row_count"] == 27
    assert source.rows[0].row_id == "A-01"
    assert "GDPR Art. 28" in source.rows[0].text
    assert source.rows[-1].row_id == "G-02"


def test_procurement_matrix_xlsx_preserves_row_boundaries(mock_documents_dir: Path) -> None:
    source = load_source(mock_documents_dir / "Procurement_Approval_Matrix_v2_0.xlsx")

    assert source.source_id == "PAM-001"
    assert source.structured_data["row_count"] == 20
    assert source.rows[0].row_id == "A-T1"
    assert source.rows[0].values["Approval Path"] == "STANDARD"
    assert source.rows[-1].row_id == "E-T4"
    assert "EXECUTIVE APPROVAL" in source.rows[-1].text
