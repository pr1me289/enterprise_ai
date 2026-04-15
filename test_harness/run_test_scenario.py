"""CLI entry point for the deterministic orchestration test harness.

Usage:
    python test_harness/run_test_scenario.py --scenario scenario_1_complete
    python test_harness/run_test_scenario.py --scenario scenario_2_escalated
    python test_harness/run_test_scenario.py --scenario scenario_blocked_missing_questionnaire

Exits 0 on PASS, 1 on FAIL.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure the src/ directory is on the path when run as a standalone script.
_REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO_ROOT / "src"))
sys.path.insert(0, str(_REPO_ROOT))

from orchestration.models.context_bundle import ContextBundle
from orchestration.models.enums import RunStatus, StepId, StepStatus
from orchestration.pipeline_state import PipelineState
from orchestration.supervisor import Supervisor

from test_harness.bundle_aware_adapter import BundleAwareMockAdapter
from test_harness.console_monitor import ConsoleMonitor
from test_harness.reporters.bundle_trace_writer import BundleTraceWriter
from test_harness.reporters.event_logger import EventLogger
from test_harness.reporters.final_state_writer import FinalStateWriter
from test_harness.result_assertions import run_all_assertions
from test_harness.scenario_fixtures import FIXTURES, HarnessFixture, get_fixture

# ---------------------------------------------------------------------------
# Questionnaire path resolution
# ---------------------------------------------------------------------------

def _resolve_questionnaire_path(fixture: HarnessFixture, repo_root: Path) -> Path | None:
    """Return the questionnaire JSON path for a fixture, or None if absent."""
    key = fixture.questionnaire_path_key
    if key == "none":
        return None
    if key == "scenario_1":
        candidates = [
            repo_root / "mock_documents" / "scenario_1" / "OptiChain_VSQ_001_v2_1.json",
            repo_root / "mock_documents" / "OptiChain_VSQ_001_v2_1.json",
        ]
    elif key == "scenario_2":
        candidates = [
            repo_root / "mock_documents" / "scenario_2" / "OptiChain_VSQ_001_v2_1.json",
            repo_root / "mock_documents" / "OptiChain_VSQ_001_v2_1.json",
        ]
    else:
        return None

    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


# ---------------------------------------------------------------------------
# Core scenario runner
# ---------------------------------------------------------------------------

def run_scenario(scenario_name: str, *, artifacts_root: Path | None = None) -> tuple[bool, PipelineState, list[dict]]:
    """Execute the named scenario and return (passed, final_state, bundle_trace).

    This is the programmatic entry point used by both the CLI and pytest.
    """
    repo_root = _REPO_ROOT
    fixture = get_fixture(scenario_name)
    artifacts_root = artifacts_root or repo_root / "artifacts"

    questionnaire_path = _resolve_questionnaire_path(fixture, repo_root)

    # For the blocked-missing-questionnaire scenario we deliberately use an
    # empty questionnaire so DirectStructuredAccessor finds no required fields,
    # causing STEP-01 to emit BLOCKED.
    if questionnaire_path is None:
        questionnaire_path = repo_root / "test_harness" / "_empty_questionnaire.json"

    adapter = BundleAwareMockAdapter(
        scenario_name=scenario_name,
        agent_signals=fixture.agent_signals,
    )

    supervisor = Supervisor(
        repo_root=repo_root,
        questionnaire_path=questionnaire_path,
        chunk_dir=repo_root / "data" / "processed" / "chunks",
        questionnaire_overrides=fixture.questionnaire_overrides if fixture.questionnaire_path_key != "none" else None,
        llm_adapter=adapter,
    )

    run_id = supervisor.state.pipeline_run_id
    monitor = ConsoleMonitor(scenario_name=scenario_name, pipeline_run_id=run_id)
    event_logger = EventLogger(scenario_name=scenario_name, run_id=run_id, artifacts_root=artifacts_root)
    bundle_trace_writer = BundleTraceWriter(run_dir=event_logger.run_dir)
    final_state_writer = FinalStateWriter(run_dir=event_logger.run_dir)

    monitor.on_run_init()
    event_logger.append("RUN_INIT", None, {"pipeline_run_id": run_id, "scenario": scenario_name})

    # Option B: wrapper loop — step through execute_next_step() one at a time.
    # We stop early on BLOCKED or ESCALATED so downstream steps are never executed.
    while supervisor.state.next_step_queue:
        # Halt if we are already in a terminal non-IN_PROGRESS state
        if supervisor.state.overall_status in (RunStatus.BLOCKED, RunStatus.ESCALATED):
            break

        step_id: StepId = supervisor.state.next_step_queue[0]
        step_str = step_id.value

        monitor.on_step_enter(step_str)
        event_logger.append("STEP_ENTER", step_str, {"step": step_str})

        # Record retrieval events via audit logger pre/post snapshot
        audit_before = len(supervisor.audit_logger.entries)

        did_continue = supervisor.execute_next_step()

        audit_after = len(supervisor.audit_logger.entries)
        new_audit_entries = supervisor.audit_logger.entries[audit_before:audit_after]

        # Emit retrieval events from new audit entries
        for entry in new_audit_entries:
            if entry.event_type.value == "RETRIEVAL":
                source = entry.source_queried or "?"
                records = entry.details.get("admitted_count", 0)
                lane = entry.details.get("lane", "?")
                monitor.on_retrieve_start(step_str, source, lane)
                monitor.on_retrieve_ok(step_str, source, records)
                event_logger.append(
                    "RETRIEVE",
                    step_str,
                    {"source": source, "lane": lane, "records": records},
                )

        # Record the bundle for this step if available
        step_status = supervisor.state.step_statuses.get(step_id, StepStatus.PENDING)

        # Try to find the bundle in the last execution result via supervisor internals
        # We use the handler's last-executed bundle if available via the step result.
        # Since Supervisor._run_step does not cache the bundle, we build the trace
        # from what the bundle_assembler would have produced (reflected in audit log).
        # For the trace we synthesise a minimal ContextBundle-like record.
        _record_bundle_trace_from_state(
            supervisor, step_id, step_str, bundle_trace_writer, monitor, event_logger
        )

        # Determine status for this step
        step_status_str = step_status.value
        monitor.on_handler_result(step_str, step_status_str)
        monitor.on_state_update(
            step_str,
            supervisor.state.overall_status.value,
            supervisor.state.next_step_queue[0].value if supervisor.state.next_step_queue else None,
        )
        event_logger.append(
            "STEP_RESULT",
            step_str,
            {"step_status": step_status_str, "overall_status": supervisor.state.overall_status.value},
        )

        if not did_continue:
            break

    # Finalize
    overall = supervisor.state.overall_status
    if overall in (RunStatus.BLOCKED, RunStatus.ESCALATED):
        halted_at = _find_terminal_step(supervisor.state)
        monitor.on_run_halt(overall.value, halted_at)
        event_logger.append("RUN_HALT", None, {"overall_status": overall.value, "halted_at": halted_at})
    else:
        monitor.on_run_complete(overall.value)
        event_logger.append("RUN_COMPLETE", None, {"overall_status": overall.value})

    # Write artifacts
    bundle_trace_writer.write()
    final_state_writer.write(supervisor.state, supervisor.audit_logger)

    # Run assertions
    failures = run_all_assertions(
        state=supervisor.state,
        bundle_trace=bundle_trace_writer.traces,
        fixture=fixture,
        audit_entries=supervisor.audit_logger.entries,
    )

    passed = len(failures) == 0
    if passed:
        monitor.on_assertion_pass("ALL ASSERTIONS")
        print(f"\nRESULT: PASS  scenario={scenario_name}  run_id={run_id}")
    else:
        for f in failures:
            monitor.on_assertion_fail("ASSERTION", f)
        print(f"\nRESULT: FAIL  scenario={scenario_name}  run_id={run_id}")
        for f in failures:
            print(f"  FAIL: {f}")

    return passed, supervisor.state, bundle_trace_writer.traces


def _record_bundle_trace_from_state(
    supervisor: Supervisor,
    step_id: StepId,
    step_str: str,
    bundle_trace_writer: BundleTraceWriter,
    monitor: ConsoleMonitor,
    event_logger: EventLogger,
) -> None:
    """Record the real ContextBundle produced by the step handler.

    Reads from ``supervisor.last_bundle_by_step`` which is populated by the
    Supervisor each time a step's ``StepExecutionResult`` carries a bundle.
    If a step BLOCKED at the gate (no handler.execute call), no bundle was
    produced — we record a minimal ``PARTIAL`` placeholder so downstream
    assertions still see a trace entry for the step.
    """
    real_bundle = supervisor.last_bundle_by_step.get(step_id)
    if real_bundle is not None:
        bundle_trace_writer.record(step_str, real_bundle)
        admitted_count = len(real_bundle.admitted_evidence)
        excluded_count = len(real_bundle.excluded_evidence)
        admissible = real_bundle.admissibility_status in ("ADMISSIBLE", "PARTIAL")
        monitor.on_bundle_ready(step_str, admitted_count, excluded_count, admissible)
        event_logger.append(
            "BUNDLE_READY",
            step_str,
            {
                "admitted": admitted_count,
                "excluded": excluded_count,
                "admissible": admissible,
                "admissibility_status": real_bundle.admissibility_status,
            },
        )
        return

    # No bundle was produced (step blocked at gate).  Emit a placeholder so
    # the trace remains complete for assertions that check status semantics.
    placeholder = ContextBundle(
        step_id=step_id,
        admitted_evidence=[],
        excluded_evidence=[],
        structured_fields={},
        source_provenance=[],
        admissibility_status="PARTIAL",
    )
    bundle_trace_writer.record(step_str, placeholder)
    monitor.on_bundle_ready(step_str, 0, 0, False)
    event_logger.append(
        "BUNDLE_READY",
        step_str,
        {"admitted": 0, "excluded": 0, "admissible": False, "admissibility_status": "PARTIAL", "placeholder": True},
    )


def _find_terminal_step(state: PipelineState) -> str:
    """Find the step that caused the halt."""
    from orchestration.config.step_definitions import STEP_ORDER
    from orchestration.models.enums import StepStatus

    for step_id in STEP_ORDER:
        s = state.step_statuses[step_id]
        if s in (StepStatus.BLOCKED, StepStatus.ESCALATED):
            return step_id.value
    return state.current_step.value if state.current_step else "UNKNOWN"


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Run deterministic orchestration test scenario.")
    parser.add_argument(
        "--scenario",
        required=True,
        choices=sorted(FIXTURES.keys()),
    )
    args = parser.parse_args()

    passed, _, _ = run_scenario(args.scenario)
    sys.exit(0 if passed else 1)
