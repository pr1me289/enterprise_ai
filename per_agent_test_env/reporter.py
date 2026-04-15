"""Explicit stdout reporter for the per-agent runner.

The prompt requires the test runner to make it explicit:
- which agent is under test
- which scenario is running
- what the raw output was
- whether it passed or failed (with failure details)
"""

from __future__ import annotations

import json
from typing import TextIO

from per_agent_test_env.runner import AgentTestResult


_BANNER = "=" * 78
_RULE = "-" * 78


def _preview(text: str | None, *, limit: int = 1200) -> str:
    if not text:
        return "<none>"
    if len(text) <= limit:
        return text
    return text[:limit] + f"\n… [truncated — full text in recorded file; {len(text)} chars]"


def print_run_header(agent_name: str, scenario: str, *, stream: TextIO) -> None:
    stream.write(_BANNER + "\n")
    stream.write(f"PER-AGENT LIVE TEST — agent={agent_name}  scenario={scenario}\n")
    stream.write(_BANNER + "\n")
    stream.flush()


def print_result(result: AgentTestResult, *, stream: TextIO) -> None:
    r = result.recorded
    stream.write(_RULE + "\n")
    stream.write(f"agent_name      : {result.agent_name}\n")
    stream.write(f"scenario        : {result.scenario}\n")
    stream.write(f"pipeline_run_id : {r.pipeline_run_id}\n")
    stream.write(f"model           : {r.model}\n")
    stream.write(f"timestamp_utc   : {r.timestamp_utc}\n")
    stream.write(f"spec_path       : {r.system_prompt_path}\n")
    stream.write(f"bundle_fixture  : {r.bundle_fixture_path}\n")
    stream.write(f"recorded_file   : {r.recorded_file}\n")
    stream.write(_RULE + "\n")

    stream.write("RAW TEXT (model response):\n")
    stream.write(_preview(r.raw_text) + "\n")
    stream.write(_RULE + "\n")

    stream.write("PARSED OUTPUT:\n")
    if r.parsed_output is None:
        stream.write("<no parsed output>\n")
    else:
        stream.write(json.dumps(r.parsed_output, indent=2, sort_keys=False) + "\n")
    stream.write(_RULE + "\n")

    if r.error:
        stream.write(f"RUNTIME ERROR: {r.error}\n")
        stream.write(_RULE + "\n")

    if result.warnings:
        stream.write("WARNINGS (soft checks):\n")
        for warn in result.warnings:
            stream.write(f"  - {warn}\n")
        stream.write(_RULE + "\n")

    if result.passed:
        stream.write(f"RESULT: PASS  agent={result.agent_name}  scenario={result.scenario}\n")
    else:
        stream.write(f"RESULT: FAIL  agent={result.agent_name}  scenario={result.scenario}\n")
        stream.write("FAILURES:\n")
        for failure in result.failures:
            stream.write(f"  - {failure}\n")
    stream.write(_BANNER + "\n")
    stream.flush()


def print_halt_on_fail(result: AgentTestResult, *, stream: TextIO) -> None:
    """Signal that the runner is halting rather than cascading to the next test."""
    stream.write(
        f"\nHALT: {result.agent_name} / {result.scenario} failed. "
        "Per per_agent_test_environment_prompt, the runner does not cascade into "
        "the next agent automatically. Inspect the recorded file and re-run manually "
        "after a deliberate code or prompt change.\n"
    )
    stream.flush()
