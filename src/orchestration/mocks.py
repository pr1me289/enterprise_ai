"""Mock adapters for scenario-driven orchestration tests and demos."""

from __future__ import annotations

from collections import defaultdict
from copy import deepcopy
from typing import Any

from orchestration.agents.llm_agent_runner import MockLLMAdapter


def _result_key(source_id: str, search_terms: tuple[str, ...]) -> tuple[str, tuple[str, ...]]:
    return source_id, tuple(search_terms)


class ScenarioIndexedBackend:
    """Indexed backend returning fixture-controlled results by source and search terms."""

    def __init__(self, *, results: dict[tuple[str, tuple[str, ...]], list[dict[str, Any]]] | None = None) -> None:
        self.results = defaultdict(list, results or {})

    def query(
        self,
        *,
        source_id: str,
        search_terms: tuple[str, ...],
        metadata_filter: dict[str, Any] | None = None,
        top_k: int = 5,
    ) -> list[dict[str, Any]]:
        del metadata_filter
        hits = deepcopy(self.results[_result_key(source_id, search_terms)])
        return hits[:top_k]


class ScenarioLLMAdapter(MockLLMAdapter):
    """Optional scenario override layer on top of the rule-based mock adapter."""

    def __init__(self, *, outputs: dict[str, dict[str, Any]] | None = None) -> None:
        self.outputs = outputs or {}

    def generate_structured_json(
        self,
        *,
        agent_name: str,
        spec_text: str,
        prompt: str,
        bundle: dict[str, Any],
        step_metadata: dict[str, Any],
        context_bundle: Any = None,
    ) -> dict[str, Any]:
        if agent_name in self.outputs:
            payload = deepcopy(self.outputs[agent_name])
            if payload.get("pipeline_run_id") == "SCENARIO_PIPELINE_RUN_ID":
                payload["pipeline_run_id"] = bundle.get("pipeline_run_id", payload["pipeline_run_id"])
            if payload.get("vendor_name") == "SCENARIO_VENDOR_NAME":
                payload["vendor_name"] = bundle.get("vendor_name", payload["vendor_name"])
            return payload
        return super().generate_structured_json(
            agent_name=agent_name,
            spec_text=spec_text,
            prompt=prompt,
            bundle=bundle,
            step_metadata=step_metadata,
            context_bundle=context_bundle,
        )
