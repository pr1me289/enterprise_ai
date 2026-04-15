"""BundleAwareMockAdapter — dispatches to test_harness/mock_agents.

This adapter is used by the deterministic test harness.  It satisfies the
``LLMAdapter`` protocol but does not invoke any LLM.  Instead, for each
agent call it:

1. Receives the real ``ContextBundle`` (via ``context_bundle=`` kwarg).
2. Delegates to the corresponding bundle-aware mock agent, which
   validates the bundle against the governing agent_bundle_integrity_checklist
   and fires the pre-determined signal mapped to that agent in the
   scenario fixture.
3. Returns the output dict in the flat shape ``LLMAgentRunner`` expects.

Signal mapping is supplied via ``agent_signals`` in the constructor; missing
entries default to ``"complete"``.
"""

from __future__ import annotations

from typing import Any

from orchestration.models.context_bundle import ContextBundle

from test_harness.mock_agents import (
    mock_step_02_security,
    mock_step_03_legal,
    mock_step_04_procurement,
    mock_step_05_checklist,
    mock_step_06_checkoff,
)


_AGENT_DISPATCH = {
    "it_security_agent": mock_step_02_security,
    "legal_agent": mock_step_03_legal,
    "procurement_agent": mock_step_04_procurement,
    "checklist_assembler": mock_step_05_checklist,
    "checkoff_agent": mock_step_06_checkoff,
}


class BundleAwareMockAdapter:
    """Dispatches to bundle-aware mock agents under a pre-determined signal map.

    Each agent in the map maps to "complete" | "escalated" | "blocked".  The
    adapter calls the mock agent's ``run(bundle, scenario_name, signal)``
    function, which raises ``ValueError`` on structural violations and
    otherwise returns an output dict carrying the requested status.
    """

    def __init__(
        self,
        scenario_name: str,
        *,
        agent_signals: dict[str, str] | None = None,
    ) -> None:
        self.scenario_name = scenario_name
        self.agent_signals = agent_signals or {}
        self._calls: list[dict[str, Any]] = []

    @property
    def calls(self) -> list[dict[str, Any]]:
        """Recorded agent invocations, useful for harness-level assertions."""
        return list(self._calls)

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
        del spec_text, prompt, step_metadata, bundle
        if not isinstance(context_bundle, ContextBundle):
            raise ValueError(
                "BundleAwareMockAdapter requires a ContextBundle (context_bundle=); "
                f"got {type(context_bundle).__name__}.  Ensure LLMAgentRunner "
                "is passing context_bundle to the adapter."
            )
        module = _AGENT_DISPATCH.get(agent_name)
        if module is None:
            raise KeyError(
                f"BundleAwareMockAdapter has no mock agent for {agent_name!r}. "
                f"Known: {sorted(_AGENT_DISPATCH)}"
            )
        signal = self.agent_signals.get(agent_name, "complete")
        output, _step_status, _escalation = module.run(
            bundle=context_bundle,
            scenario_name=self.scenario_name,
            signal=signal,
        )
        self._calls.append(
            {
                "agent_name": agent_name,
                "signal": signal,
                "status": output.get("status"),
            }
        )
        return output
