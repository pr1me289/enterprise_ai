"""Scenario-specific source-path helpers for the preprocessing layer."""

from __future__ import annotations

from pathlib import Path


SCENARIO_DIRS: dict[str, str] = {
    "scenario_1": "scenarios_full_pipeline/scenario_1/source_mock_documents",
    "scenario_2": "scenarios_full_pipeline/scenario_2/source_mock_documents",
    "scenario_blocked_demo": "scenarios_full_pipeline/scenario_blocked_demo/source_mock_documents",
    "scenario_escalated_step4_demo": "scenarios_full_pipeline/scenario_escalated_step4_demo/source_mock_documents",
}


SCENARIO_SOURCE_CANDIDATES: dict[str, dict[str, tuple[str, ...]]] = {
    "scenario_1": {
        "policy": ("IT_Security_Policy_V4.2.md",),
        "dpa_matrix": ("DPA_Legal_Trigger_Matrix_v1_3.csv", "DPA_Legal_Trigger_Matrix_v1_3.xlsx"),
        "procurement_matrix": ("Procurement_Approval_Matrix_v2_0.xlsx", "Procurement_Approval_Matrix_v2_0.csv"),
        "questionnaire": ("OptiChain_VSQ_001_v2_1_scenario01.json", "OptiChain_VSQ_001_v2_1.json"),
        "slack": ("Slack_Thread_Export_scenario01.json", "Slack_Thread_Export_scenario01.md"),
        "stakeholder_map": ("Stakeholder_Map_PRQ_2024_0047.json",),
    },
    "scenario_2": {
        "policy": ("IT_Security_Policy_V4.2.md",),
        "dpa_matrix": ("DPA_Legal_Trigger_Matrix_v1_3.csv", "DPA_Legal_Trigger_Matrix_v1_3.xlsx"),
        "procurement_matrix": ("Procurement_Approval_Matrix_v2_0.xlsx", "Procurement_Approval_Matrix_v2_0.csv"),
        "questionnaire": ("OptiChain_VSQ_001_v2_1.json",),
        "slack": ("Slack_Thread_Export_001.json", "Slack_Thread_Export_001.md"),
        "stakeholder_map": ("Stakeholder_Map_PRQ_2024_0047.json",),
    },
    "scenario_blocked_demo": {
        "policy": ("IT_Security_Policy_V4.2.md",),
        "dpa_matrix": ("DPA_Legal_Trigger_Matrix_v1_3.csv", "DPA_Legal_Trigger_Matrix_v1_3.xlsx"),
        "procurement_matrix": ("Procurement_Approval_Matrix_v2_0.csv",),
        "questionnaire": ("OptiChain_VSQ_001_v2_1_blocked_demo.json",),
        "slack": ("Slack_Thread_Export_scenario01.json", "Slack_Thread_Export_scenario01.md"),
        "stakeholder_map": ("Stakeholder_Map_PRQ_2024_0047.json",),
    },
    "scenario_escalated_step4_demo": {
        "policy": ("IT_Security_Policy_V4.2.md",),
        "dpa_matrix": ("DPA_Legal_Trigger_Matrix_v1_3.csv", "DPA_Legal_Trigger_Matrix_v1_3.xlsx"),
        "procurement_matrix": ("Procurement_Approval_Matrix_v2_0.csv",),
        "questionnaire": ("OptiChain_VSQ_001_v2_1_escalated_step4_demo.json",),
        "slack": ("Slack_Thread_Export_scenario01.json", "Slack_Thread_Export_scenario01.md"),
        "stakeholder_map": ("Stakeholder_Map_PRQ_2024_0047.json",),
    },
}


def resolve_scenario_source_paths(
    scenario_name: str,
    *,
    repo_root: str | Path | None = None,
) -> dict[str, Path]:
    """Return the active preprocessing source paths for a scenario.

    The active scenario set intentionally excludes the legacy precedent document.
    Each source selects the first existing candidate path in priority order.
    """

    root = Path(repo_root) if repo_root is not None else Path(__file__).resolve().parents[2]
    try:
        scenario_dir = root / SCENARIO_DIRS[scenario_name]
        candidates = SCENARIO_SOURCE_CANDIDATES[scenario_name]
    except KeyError as exc:
        raise KeyError(f"Unsupported scenario name: {scenario_name}") from exc

    resolved: dict[str, Path] = {}
    missing: list[str] = []
    for source_key, filenames in candidates.items():
        for filename in filenames:
            path = scenario_dir / filename
            if path.exists():
                resolved[source_key] = path
                break
        else:
            missing.append(source_key)

    if missing:
        missing_text = ", ".join(sorted(missing))
        raise FileNotFoundError(
            f"Scenario '{scenario_name}' is missing required preprocessing sources: {missing_text}"
        )
    return resolved


def list_scenario_source_paths(
    scenario_name: str,
    *,
    repo_root: str | Path | None = None,
) -> list[Path]:
    resolved = resolve_scenario_source_paths(scenario_name, repo_root=repo_root)
    return [
        resolved["policy"],
        resolved["dpa_matrix"],
        resolved["procurement_matrix"],
        resolved["questionnaire"],
        resolved["slack"],
        resolved["stakeholder_map"],
    ]
