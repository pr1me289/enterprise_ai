"""Endpoint access control for governed retrieval."""

from __future__ import annotations

from indexing.index_registry import ACCESS_MATRIX


class UnauthorizedRetrieval(PermissionError):
    """Raised when an agent attempts to query an unauthorized index endpoint."""

    def __init__(self, index_name: str, agent_name: str) -> None:
        super().__init__(f"Agent '{agent_name}' is not authorized to query '{index_name}'.")
        self.index_name = index_name
        self.agent_name = agent_name


def assert_endpoint_access(agent_name: str, index_name: str, access_matrix: dict[str, tuple[str, ...]] | None = None) -> None:
    matrix = access_matrix or ACCESS_MATRIX
    allowed_agents = matrix.get(index_name, ())
    if agent_name not in allowed_agents:
        raise UnauthorizedRetrieval(index_name, agent_name)
