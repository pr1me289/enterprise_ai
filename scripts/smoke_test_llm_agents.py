"""End-to-end smoke test for the LLM call layer.

Two modes:

1. Full-pipeline run (default): spins up the Supervisor with the
   real `AnthropicLLMAdapter` against the `complete_demo` scenario
   and prints the final overall status, per-step statuses, and
   audit-entry count. This is the primary success criterion — a
   full pipeline run with real agents that completes without
   crashing.

2. Per-agent (--per-agent): runs the complete_demo scenario once
   with the mock adapter to capture each step's real ContextBundle,
   then invokes each of the five `call_*` functions from
   `agents.llm_caller` against those captured bundles. This exercises
   the per-agent entry points independently.

Both modes require `ANTHROPIC_API_KEY` in the environment or in a
`.env` file at the repo root. Model defaults to `claude-haiku-4-5`
and can be overridden via `ANTHROPIC_MODEL`.

Usage:
    PYTHONPATH=src uv run python scripts/smoke_test_llm_agents.py
    PYTHONPATH=src uv run python scripts/smoke_test_llm_agents.py --per-agent
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC = REPO_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from agents.llm_caller import (  # noqa: E402
    AnthropicLLMAdapter,
    call_checklist_assembler,
    call_checkoff_agent,
    call_it_security_agent,
    call_legal_agent,
    call_procurement_agent,
)
from orchestration.mocks import ScenarioIndexedBackend, ScenarioLLMAdapter  # noqa: E402
from orchestration.models.enums import StepId  # noqa: E402
from orchestration.scenarios import complete_demo_scenario  # noqa: E402
from orchestration.supervisor import Supervisor  # noqa: E402


def _require_api_key() -> None:
    try:
        from dotenv import load_dotenv
    except ImportError:
        pass
    else:
        load_dotenv(REPO_ROOT / ".env")
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print(
            "ERROR: ANTHROPIC_API_KEY is not set. Put it in .env at the repo root "
            "or export it in your shell before running this script.",
            file=sys.stderr,
        )
        sys.exit(2)


def run_full_pipeline() -> None:
    scenario = complete_demo_scenario()
    supervisor = Supervisor(
        repo_root=REPO_ROOT,
        questionnaire_path=REPO_ROOT / "mock_documents" / "OptiChain_VSQ_001_v2_1.json",
        questionnaire_overrides=scenario.questionnaire_overrides,
        indexed_backend=ScenarioIndexedBackend(results=scenario.indexed_results),
        llm_adapter=AnthropicLLMAdapter(repo_root=REPO_ROOT),
    )
    state = supervisor.run()
    result = {
        "pipeline_run_id": state.pipeline_run_id,
        "overall_status": state.overall_status.value,
        "step_statuses": {step.value: status.value for step, status in state.step_statuses.items()},
        "audit_entry_count": len(supervisor.audit_logger.entries),
        "step_05_overall_status": (state.determinations.get("step_05_checklist") or {}).get("overall_status"),
        "step_06_status": (state.determinations.get("step_06_guidance") or {}).get("status"),
    }
    print(json.dumps(result, indent=2))


def _capture_bundles() -> dict[StepId, dict]:
    """Run the scenario once with the mock adapter to capture each bundle."""
    scenario = complete_demo_scenario()
    supervisor = Supervisor(
        repo_root=REPO_ROOT,
        questionnaire_path=REPO_ROOT / "mock_documents" / "OptiChain_VSQ_001_v2_1.json",
        questionnaire_overrides=scenario.questionnaire_overrides,
        indexed_backend=ScenarioIndexedBackend(results=scenario.indexed_results),
        llm_adapter=ScenarioLLMAdapter(outputs=scenario.agent_outputs),
    )
    supervisor.run()
    captured: dict[StepId, dict] = {}
    for step_id, context_bundle in supervisor.last_bundle_by_step.items():
        captured[step_id] = context_bundle.structured_fields
    return captured


def run_per_agent() -> None:
    bundles = _capture_bundles()
    pipeline_run_id = "smoke_test_per_agent"

    cases = [
        (StepId.STEP_02, "it_security_agent", call_it_security_agent),
        (StepId.STEP_03, "legal_agent", call_legal_agent),
        (StepId.STEP_04, "procurement_agent", call_procurement_agent),
        (StepId.STEP_05, "checklist_assembler", call_checklist_assembler),
        (StepId.STEP_06, "checkoff_agent", call_checkoff_agent),
    ]

    report: list[dict] = []
    for step_id, agent_name, fn in cases:
        bundle = bundles.get(step_id)
        if bundle is None:
            report.append({"agent": agent_name, "skipped": True, "reason": "no captured bundle"})
            continue
        output = fn(bundle, pipeline_run_id)
        status = output.get("status") or output.get("overall_status")
        report.append(
            {
                "agent": agent_name,
                "step": step_id.value,
                "status": status,
                "keys": sorted(output.keys()),
            }
        )
    print(json.dumps(report, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--per-agent",
        action="store_true",
        help="Invoke each call_* function individually instead of a full run",
    )
    args = parser.parse_args()
    _require_api_key()
    if args.per_agent:
        run_per_agent()
    else:
        run_full_pipeline()


if __name__ == "__main__":
    main()
