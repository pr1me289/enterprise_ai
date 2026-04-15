"""Helpers shared across the Layer 1 per-agent unit tests.

The unit tests are all shaped the same way:
  1. Take a scenario bundle (fixture).
  2. Invoke a domain agent against the real API via ``run_llm_agent``.
  3. Evaluate the output against a ground-truth ``ExpectationSet`` and emit a
     per-field PASS/FAIL report.
  4. Fail only after printing every field's verdict.

This conftest exposes one helper — ``invoke_and_assert`` — that wraps that
contract so each test file stays focused on *which* scenario+agent+mutations
to exercise, not plumbing.
"""

from __future__ import annotations

from typing import Any, Callable

import pytest

from tests.support.expected_outputs import EXPECTATIONS_BY_SCENARIO
from tests.support.field_reporter import (
    FieldResult,
    assert_all_passed,
    evaluate_expectations,
)


RunLLMFn = Callable[..., dict[str, Any]]


@pytest.fixture
def invoke_and_assert(run_llm_agent: RunLLMFn, live_monitor):
    """Return a helper that runs an agent and asserts every expected field.

    The helper threads the session-scoped ``live_monitor`` into the
    per-field reporter so each expectation verdict is streamed as a
    ``FIELD_VERDICT`` event on top of the human-readable block report.
    """

    def _invoke(
        *,
        scenario: str,
        agent_name: str,
        bundle: dict[str, Any],
        pipeline_run_id: str,
        extra_context: dict[str, Any] | None = None,
    ) -> tuple[dict[str, Any], list[FieldResult]]:
        expectation_set = EXPECTATIONS_BY_SCENARIO[scenario][agent_name]
        output = run_llm_agent(
            agent_name=agent_name,
            bundle=bundle,
            pipeline_run_id=pipeline_run_id,
        )
        results, _ = evaluate_expectations(
            output=output,
            expectation_set=expectation_set,
            pipeline_run_id=pipeline_run_id,
            extra_context=extra_context,
            monitor=live_monitor,
        )
        assert_all_passed(results)
        return output, results

    return _invoke


@pytest.fixture
def invoke_raw(run_llm_agent: RunLLMFn):
    """Return a helper that just runs the agent and returns the raw output.

    Used by edge-case tests that need to assert non-expectation-table facts
    (blocked status when upstream is missing, etc.).
    """

    def _invoke(
        *,
        agent_name: str,
        bundle: dict[str, Any],
        pipeline_run_id: str,
    ) -> dict[str, Any]:
        return run_llm_agent(
            agent_name=agent_name,
            bundle=bundle,
            pipeline_run_id=pipeline_run_id,
        )

    return _invoke
