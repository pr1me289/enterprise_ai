"""Endpoint access control for governed retrieval."""

from __future__ import annotations

from pathlib import Path

from indexing.load_index_registry import get_entry_by_logical_store_name, load_index_registry


class UnauthorizedRetrieval(PermissionError):
    """Raised when an agent attempts to query an unauthorized index endpoint."""

    def __init__(self, index_name: str, agent_name: str) -> None:
        super().__init__(f"Agent '{agent_name}' is not authorized to query '{index_name}'.")
        self.index_name = index_name
        self.agent_name = agent_name


def build_access_matrix(registry_path: str | Path | None = None) -> dict[str, tuple[str, ...]]:
    payload = load_index_registry(registry_path) if registry_path else load_index_registry()
    return {
        entry["logical_store_name"]: tuple(entry["allowed_agents"])
        for entry in payload["sources"].values()
        if entry["storage_kind"] == "vector_bm25"
    }


def assert_endpoint_access(
    agent_name: str,
    index_name: str,
    access_matrix: dict[str, tuple[str, ...]] | None = None,
    registry_path: str | Path | None = None,
) -> None:
    if access_matrix is None:
        entry = get_entry_by_logical_store_name(index_name, path=registry_path) if registry_path else get_entry_by_logical_store_name(index_name)
        allowed_agents = tuple(entry["allowed_agents"]) if entry["storage_kind"] == "vector_bm25" else ()
    else:
        allowed_agents = access_matrix.get(index_name, ())
    if agent_name not in allowed_agents:
        raise UnauthorizedRetrieval(index_name, agent_name)
