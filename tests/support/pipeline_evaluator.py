"""Lift per-agent evaluators into per-step assertions for live pipeline runs.

``per_agent_test_env.evaluators.evaluate_recorded`` encodes the output
contract for each domain agent: required fields, enum domains, scenario
status expectations, and agent-specific rules. In the live full-pipeline
run we want the *same* per-step verdicts, otherwise a drift between the
per-agent suite and the end-to-end run can hide a regression.

This module walks the supervisor's executed steps and produces one
``EvaluationReport`` per step — keyed by ``StepId`` — so pytest can
aggregate them into a single pass/fail verdict. STEP-01 is skipped
because it is a deterministic intake handler, not an LLM agent, and has
no evaluator.
"""

from __future__ import annotations

from typing import Any

from orchestration.models.enums import StepId

from per_agent_test_env.evaluators import EvaluationReport, evaluate_recorded


_STEP_DETERMINATION_KEY: dict[StepId, str] = {
    StepId.STEP_02: "step_02_security_classification",
    StepId.STEP_03: "step_03_legal",
    StepId.STEP_04: "step_04_procurement",
    StepId.STEP_05: "step_05_checklist",
    StepId.STEP_06: "step_06_guidance",
}

_STEP_AGENT: dict[StepId, str] = {
    StepId.STEP_02: "it_security_agent",
    StepId.STEP_03: "legal_agent",
    StepId.STEP_04: "procurement_agent",
    StepId.STEP_05: "checklist_assembler",
    StepId.STEP_06: "checkoff_agent",
}


def evaluate_pipeline_run(
    *,
    scenario: str,
    supervisor: Any,
) -> dict[StepId, EvaluationReport]:
    """Evaluate every executed step's output against its per-agent contract.

    Only steps that actually executed (determination present) are
    evaluated. A halted pipeline — e.g., STEP-03 ESCALATED in scenario_2
    → STEP-04..06 PENDING — produces reports only for the steps that
    ran. The caller derives the aggregate pass/fail.
    """
    reports: dict[StepId, EvaluationReport] = {}
    adapter = getattr(getattr(supervisor, "agent_runner", None), "adapter", None)
    call_records = getattr(adapter, "call_records", []) or []
    error_by_agent: dict[str, str] = {}
    for rec in call_records:
        if rec.get("outcome") == "error" and rec.get("agent_name"):
            error_by_agent[rec["agent_name"]] = rec.get("error", "unknown")

    for step_id, det_key in _STEP_DETERMINATION_KEY.items():
        determination = supervisor.state.determinations.get(det_key)
        if determination is None:
            continue
        agent_name = _STEP_AGENT[step_id]
        reports[step_id] = evaluate_recorded(
            agent_name=agent_name,
            scenario=scenario,
            parsed_output=determination,
            error=error_by_agent.get(agent_name),
        )
    return reports


def format_failures(reports: dict[StepId, EvaluationReport]) -> str:
    """Flatten per-step failures into a single human-readable block."""
    lines: list[str] = []
    for step_id, report in reports.items():
        if report.passed:
            continue
        lines.append(f"[{step_id.value}] {len(report.failures)} failure(s):")
        for failure in report.failures:
            lines.append(f"    - {failure}")
    return "\n".join(lines) if lines else ""


def verdicts_from_reports(
    reports: dict[StepId, EvaluationReport],
) -> dict[StepId, bool]:
    return {step_id: report.passed for step_id, report in reports.items()}
