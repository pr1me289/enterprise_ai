"""Base interfaces for orchestration-owned agent execution."""

from __future__ import annotations

from typing import Any, Protocol


class LLMAdapter(Protocol):
    def generate_structured_json(
        self,
        *,
        agent_name: str,
        spec_text: str,
        prompt: str,
        bundle: dict[str, Any],
        step_metadata: dict[str, Any],
        context_bundle: Any = None,
    ) -> dict[str, Any]: ...
