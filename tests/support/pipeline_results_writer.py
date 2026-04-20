"""Append a structured markdown block to ``results/full_pipeline_test_results.md``.

The per-agent live suite writes one block per (agent, scenario) run to
``results/test_results.md``. The full-pipeline suite has a wider surface —
a single run exercises five domain agents across six supervisor steps —
so it gets its own results file with a richer block that captures the
per-step status + verdict grid, agent-call telemetry, and pointers back
to the recorded-response files.

Block shape:

    ## Pipeline Run #{N} — {scenario} — {YYYY-MM-DD}
    **Overall verdict:** PASS|FAIL
    **Supervisor status:** COMPLETE|ESCALATED|BLOCKED
    **Pipeline run id:** {uuid}
    **Halted at:** STEP-XX (if ESCALATED/BLOCKED before STEP-06)

    | Step | Agent | Status | Verdict | Elapsed | In tokens | Out tokens |
    |------|-------|--------|---------|---------|-----------|------------|
    | STEP-01 | intake (deterministic) | COMPLETE | n/a | — | — | — |
    | STEP-02 | it_security_agent | COMPLETE | PASS | 1.42s | 2340 | 512 |
    ...

    **Totals:** 5 agent calls, 11920 in, 2430 out, 9.3s cumulative.

    **Per-step failures:**
    - [STEP-03] {failure 1}
    - [STEP-04] {failure 2}

    **Recorded responses:**
    - STEP-02 → tests/recorded_responses/full_pipeline/pipeline_1__it_security_agent__scenario_1_pass.json
    - ...

    **Notes:** {optional free-text notes}
"""

from __future__ import annotations

import datetime as _dt
from pathlib import Path
from typing import Any, Iterable

from orchestration.models.enums import StepId


_STEP_AGENT: dict[StepId, str] = {
    StepId.STEP_01: "intake (deterministic)",
    StepId.STEP_02: "it_security_agent",
    StepId.STEP_03: "legal_agent",
    StepId.STEP_04: "procurement_agent",
    StepId.STEP_05: "checklist_assembler",
    StepId.STEP_06: "checkoff_agent",
}

_STEP_ORDER: tuple[StepId, ...] = (
    StepId.STEP_01,
    StepId.STEP_02,
    StepId.STEP_03,
    StepId.STEP_04,
    StepId.STEP_05,
    StepId.STEP_06,
)


def _today() -> str:
    return _dt.date.today().isoformat()


def _fmt_tokens(value: Any) -> str:
    if value is None or value == "":
        return "—"
    try:
        return f"{int(value):,}"
    except (TypeError, ValueError):
        return str(value)


def _fmt_elapsed(value: Any) -> str:
    if value is None:
        return "—"
    try:
        return f"{float(value):.2f}s"
    except (TypeError, ValueError):
        return str(value)


def _halted_step(supervisor: Any) -> StepId | None:
    from orchestration.models.enums import StepStatus

    for step_id in _STEP_ORDER:
        status = supervisor.state.step_statuses.get(step_id)
        if status in (StepStatus.ESCALATED, StepStatus.BLOCKED):
            return step_id
    return None


def _relative_to_repo(path: Path, repo_root: Path) -> str:
    try:
        return str(path.relative_to(repo_root))
    except ValueError:
        return str(path)


def build_results_block(
    *,
    pipeline_run_number: int,
    scenario: str,
    supervisor: Any,
    reports: dict[StepId, Any],  # EvaluationReport — typed loosely to avoid import cycles
    record_paths: dict[StepId, Path],
    repo_root: Path,
    notes: str | None = None,
) -> str:
    """Build one markdown block for a completed pipeline run."""
    call_records: list[dict[str, Any]] = (
        getattr(supervisor.llm_adapter, "call_records", []) or []
    )
    call_by_agent: dict[str, dict[str, Any]] = {}
    for rec in call_records:
        agent = rec.get("agent_name")
        if agent:
            call_by_agent[agent] = rec  # last wins — re-run within pipeline uses most recent

    overall = supervisor.state.overall_status.value
    run_id = getattr(supervisor.state, "pipeline_run_id", "") or "—"

    all_passed = all(r.passed for r in reports.values()) if reports else True
    verdict = "PASS" if all_passed else "FAIL"

    halted = _halted_step(supervisor)
    halted_line = ""
    if halted is not None and halted != StepId.STEP_06:
        halted_line = f"\n**Halted at:** {halted.value}"

    lines: list[str] = []
    lines.append(f"## Pipeline Run #{pipeline_run_number} — {scenario} — {_today()}")
    lines.append(f"**Overall verdict:** {verdict}")
    lines.append(f"**Supervisor status:** {overall}")
    lines.append(f"**Pipeline run id:** {run_id}{halted_line}")
    lines.append("")
    lines.append("| Step | Agent | Status | Verdict | Elapsed | In tokens | Out tokens |")
    lines.append("|------|-------|--------|---------|---------|-----------|------------|")

    total_in = 0
    total_out = 0
    total_elapsed = 0.0
    total_calls = 0
    for step_id in _STEP_ORDER:
        agent = _STEP_AGENT[step_id]
        step_status = supervisor.state.step_statuses.get(step_id)
        status_str = step_status.value if step_status is not None else "—"
        if step_id == StepId.STEP_01:
            verdict_str = "n/a"
            elapsed_str = "—"
            in_str = "—"
            out_str = "—"
        else:
            report = reports.get(step_id)
            if report is None:
                verdict_str = "—"
            else:
                verdict_str = "PASS" if report.passed else "FAIL"
            rec = call_by_agent.get(agent)
            if rec is None:
                elapsed_str = "—"
                in_str = "—"
                out_str = "—"
            else:
                total_calls += 1
                elapsed = rec.get("elapsed_seconds") or rec.get("elapsed")
                in_tok = rec.get("input_tokens")
                out_tok = rec.get("output_tokens")
                try:
                    total_elapsed += float(elapsed) if elapsed is not None else 0.0
                except (TypeError, ValueError):
                    pass
                try:
                    total_in += int(in_tok) if in_tok is not None else 0
                except (TypeError, ValueError):
                    pass
                try:
                    total_out += int(out_tok) if out_tok is not None else 0
                except (TypeError, ValueError):
                    pass
                elapsed_str = _fmt_elapsed(elapsed)
                in_str = _fmt_tokens(in_tok)
                out_str = _fmt_tokens(out_tok)
        lines.append(
            f"| {step_id.value} | {agent} | {status_str} | {verdict_str} | "
            f"{elapsed_str} | {in_str} | {out_str} |"
        )

    lines.append("")
    lines.append(
        f"**Totals:** {total_calls} agent call(s), "
        f"{_fmt_tokens(total_in)} input tokens, "
        f"{_fmt_tokens(total_out)} output tokens, "
        f"{_fmt_elapsed(total_elapsed)} cumulative."
    )

    failure_lines: list[str] = []
    for step_id in _STEP_ORDER:
        report = reports.get(step_id)
        if report is None or report.passed:
            continue
        for failure in report.failures:
            failure_lines.append(f"- [{step_id.value}] {failure}")
    if failure_lines:
        lines.append("")
        lines.append("**Per-step failures:**")
        lines.extend(failure_lines)

    if record_paths:
        lines.append("")
        lines.append("**Recorded responses:**")
        for step_id in _STEP_ORDER:
            path = record_paths.get(step_id)
            if path is None:
                continue
            lines.append(f"- {step_id.value} → `{_relative_to_repo(path, repo_root)}`")

    if notes:
        lines.append("")
        lines.append(f"**Notes:** {notes}")

    lines.append("")  # trailing blank line
    return "\n".join(lines)


def append_results_block(
    *,
    results_path: Path,
    pipeline_run_number: int,
    scenario: str,
    supervisor: Any,
    reports: dict[StepId, Any],
    record_paths: dict[StepId, Path],
    repo_root: Path,
    notes: str | None = None,
) -> str:
    """Build the block and append it to ``results_path`` (created if absent).

    Returns the block text that was appended.
    """
    block = build_results_block(
        pipeline_run_number=pipeline_run_number,
        scenario=scenario,
        supervisor=supervisor,
        reports=reports,
        record_paths=record_paths,
        repo_root=repo_root,
        notes=notes,
    )
    results_path.parent.mkdir(parents=True, exist_ok=True)
    if results_path.exists():
        existing = results_path.read_text(encoding="utf-8")
        if existing and not existing.endswith("\n"):
            existing += "\n"
        results_path.write_text(existing + block, encoding="utf-8")
    else:
        # Seed a minimal header if the file does not yet exist.
        header = _default_header()
        results_path.write_text(header + block, encoding="utf-8")
    return block


def _default_header() -> str:
    return (
        "# Full Pipeline Test Results\n\n"
        "Per-run log of `tests/full_pipeline/test_end_to_end.py` runs against the "
        "real Anthropic API. Each block captures overall verdict, supervisor "
        "status, per-step status + verdict + telemetry, per-step evaluator "
        "failures, and pointers to the recorded-response files under "
        "`tests/recorded_responses/full_pipeline/`.\n\n"
        "Sibling file: `results/test_results.md` captures per-agent isolated "
        "runs (one block per agent/scenario). This file captures full-pipeline "
        "runs (one block per pipeline run across all six supervisor steps).\n\n"
        "---\n\n"
    )


def ensure_results_header(results_path: Path) -> None:
    """Create ``results_path`` with the default header if it does not exist."""
    if results_path.exists():
        return
    results_path.parent.mkdir(parents=True, exist_ok=True)
    results_path.write_text(_default_header(), encoding="utf-8")
