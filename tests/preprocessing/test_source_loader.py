from __future__ import annotations

from pathlib import Path

import pytest

from preprocessing import (
    list_scenario_source_paths,
    load_scenario_sources,
    load_source,
    resolve_scenario_source_paths,
)


@pytest.mark.parametrize(
    ("filename", "source_id", "collection_name", "expected_count"),
    [
        ("DPA_Legal_Trigger_Matrix_v1_3.xlsx", "DPA-TM-001", "rows", 27),
        ("Procurement_Approval_Matrix_v2_0.xlsx", "PAM-001", "rows", 20),
        ("OptiChain_VSQ_001_v2_1.json", "VQ-OC-001", "rows", 0),
        ("Stakeholder_Map_PRQ_2024_0047.json", "SHM-001", "rows", 0),
        ("Slack_Thread_Export_001.json", "SLK-001", "threads", 4),
        ("Slack_Thread_Export_001.md", "SLK-001", "threads", 4),
    ],
)
def test_load_source_routes_supported_mock_documents(
    mock_documents_dir: Path,
    filename: str,
    source_id: str,
    collection_name: str,
    expected_count: int,
) -> None:
    source = load_source(mock_documents_dir / filename)

    assert source.source_id == source_id
    assert len(getattr(source, collection_name)) == expected_count
    assert source.raw_text
    assert source.allowed_agents


def test_load_source_rejects_unsupported_mock_document(mock_documents_dir: Path) -> None:
    unsupported_file = mock_documents_dir / "OptiChain_Procurement_Classification_Memo_scenario01.csv"

    with pytest.raises(ValueError, match="Unsupported source file"):
        load_source(unsupported_file)


def test_resolve_scenario_source_paths_supports_both_scenarios(repo_root: Path) -> None:
    scenario_1 = resolve_scenario_source_paths("scenario_1", repo_root=repo_root)
    scenario_2 = resolve_scenario_source_paths("scenario_2", repo_root=repo_root)

    assert scenario_1["questionnaire"].name == "OptiChain_VSQ_001_v2_1_scenario01.json"
    assert scenario_1["slack"].name == "Slack_Thread_Export_scenario01.json"
    assert scenario_1["stakeholder_map"].name == "Stakeholder_Map_PRQ_2024_0047.json"
    assert scenario_2["questionnaire"].name == "OptiChain_VSQ_001_v2_1.json"
    assert scenario_2["slack"].name == "Slack_Thread_Export_001.json"
    assert scenario_2["stakeholder_map"].name == "Stakeholder_Map_PRQ_2024_0047.json"
    assert "precedent" not in scenario_1
    assert "precedent" not in scenario_2


def test_list_scenario_source_paths_returns_active_source_set_in_order(repo_root: Path) -> None:
    paths = list_scenario_source_paths("scenario_1", repo_root=repo_root)

    assert [path.name for path in paths] == [
        "IT_Security_Policy_V4.2.md",
        "DPA_Legal_Trigger_Matrix_v1_3.csv",
        "Procurement_Approval_Matrix_v2_0.csv",
        "OptiChain_VSQ_001_v2_1_scenario01.json",
        "Slack_Thread_Export_scenario01.json",
        "Stakeholder_Map_PRQ_2024_0047.json",
    ]


def test_load_scenario_sources_loads_both_scenarios(repo_root: Path) -> None:
    scenario_1_sources = load_scenario_sources("scenario_1", repo_root=repo_root)
    scenario_2_sources = load_scenario_sources("scenario_2", repo_root=repo_root)

    assert [source.source_id for source in scenario_1_sources] == [
        "ISP-001",
        "DPA-TM-001",
        "PAM-001",
        "VQ-OC-001",
        "SLK-001",
        "SHM-001",
    ]
    assert [source.source_id for source in scenario_2_sources] == [
        "ISP-001",
        "DPA-TM-001",
        "PAM-001",
        "VQ-OC-001",
        "SLK-001",
        "SHM-001",
    ]
