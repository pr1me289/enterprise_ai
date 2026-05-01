"""Print the catalog of every prepared testing scenario.

Two test environments live in this repo:

* ``scenarios_full_pipeline/`` — drives the full Supervisor STEP-01 -> STEP-06
  state machine end-to-end. Source mocks + captured run artefacts per scenario.
* ``scenarios_per_agent/``     — scenario-scoped retrieval data + bundle
  fixtures (under ``tests/fixtures/bundles/``) for replaying a single domain
  agent in isolation, no supervisor involved.

Usage:
    uv run python scripts/scenarios.py
    uv run python scripts/scenarios.py --agent legal_agent
    uv run python scripts/scenarios.py --env per_agent

The catalog below is hand-curated against the per-agent expected-status table
(``per_agent_test_env/evaluators.py``) and the full-pipeline scenario cases
(``tests/full_pipeline/test_end_to_end.py``). Update both this file and those
when a new scenario is added.
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass


@dataclass(frozen=True)
class FullPipelineScenario:
    name: str
    expected_status: str
    halt_step: str
    pytest_marker: str
    purpose: str


@dataclass(frozen=True)
class PerAgentScenario:
    scenario: str
    agent: str
    step: str
    expected_status: str
    purpose: str


FULL_PIPELINE: tuple[FullPipelineScenario, ...] = (
    FullPipelineScenario(
        name="scenario_1",
        expected_status="COMPLETE",
        halt_step="(runs all 6 steps)",
        pytest_marker="scenario_1",
        purpose=(
            "Clean governed completion. Class C non-regulated vendor, "
            "fast-track approval. Proves sequential orchestration, scoped "
            "retrieval, audit logging, and a useful final checklist."
        ),
    ),
    FullPipelineScenario(
        name="scenario_2",
        expected_status="ESCALATED",
        halt_step="STEP-03 (Legal)",
        pytest_marker="scenario_2",
        purpose=(
            "First-escalated-status halt. EU employee data + DPA required "
            "but not executed + NDA unconfirmed. Pipeline preserves the "
            "distinction between provisional ambiguity and human-owned "
            "blockers, then stops."
        ),
    ),
    FullPipelineScenario(
        name="scenario_blocked_demo",
        expected_status="BLOCKED",
        halt_step="STEP-04 (Procurement)",
        pytest_marker="scenario_blocked_demo",
        purpose=(
            "Procurement Approval Matrix is missing from the index. No "
            "evidence base for STEP-04 to begin work — blocked, not "
            "escalated."
        ),
    ),
    FullPipelineScenario(
        name="scenario_escalated_step4_demo",
        expected_status="ESCALATED",
        halt_step="STEP-04 (Procurement)",
        pytest_marker="scenario_escalated_step4_demo",
        purpose=(
            "Curated 3-row PAM-001 matrix; Class D vendor profile matches "
            "no row. Evidence is present but unresolvable — distinct from "
            "BLOCKED."
        ),
    ),
)


PER_AGENT: tuple[PerAgentScenario, ...] = (
    # IT Security agent — STEP-02
    PerAgentScenario("scenario_1", "it_security_agent", "STEP-02", "complete",
        "Clean baseline: EXPORT_ONLY/TIER_3/UNREGULATED, fast_track_eligible=true."),
    PerAgentScenario("scenario_2", "it_security_agent", "STEP-02", "escalated/complete",
        "Ambiguous ERP integration — agent may resolve to provisional COMPLETE or escalate; downstream tests don't pin the halt step."),
    PerAgentScenario("scenario_14", "it_security_agent", "STEP-02", "complete",
        "Policy-over-questionnaire conflict. Adversarial self-report (NON_REGULATED) vs DIRECT_API integration -> agent must derive REGULATED from ISP-001 and emit firm COMPLETE."),
    PerAgentScenario("scenario_15", "it_security_agent", "STEP-02", "escalated",
        "Governing source absent (ISP-001 §12.3 missing from index). Tests retrieval-failure discipline — escalate while still emitting firm determinations from chunks that did retrieve."),

    # Legal agent — STEP-03
    PerAgentScenario("scenario_1", "legal_agent", "STEP-03", "complete",
        "No DPA trigger, NDA executed."),
    PerAgentScenario("scenario_2", "legal_agent", "STEP-03", "escalated",
        "DPA required but not executed; NDA unconfirmed — both blockers pair on the same step."),
    PerAgentScenario("scenario_3", "legal_agent", "STEP-03", "complete",
        "DPA required AND not a blocker (executed DPA on file). Catches models that conflate 'DPA required' with 'DPA is a blocker'."),
    PerAgentScenario("scenario_4", "legal_agent", "STEP-03", "blocked",
        "Upstream STEP-02 output absent from bundle. Pure gate-condition test — agent must emit status=blocked, not infer through the missing input."),
    PerAgentScenario("scenario_5", "legal_agent", "STEP-03", "escalated",
        "Tier-1 DPA matrix conflict (DPA-TM-001 rows A-01 and A-07 both apply but disagree). Cannot auto-suppress per CC-001 §4.1."),
    PerAgentScenario("scenario_6", "legal_agent", "STEP-03", "escalated",
        "ISP-001 §12.1.4 NDA clause AND existing_nda_status both absent. Tests partial-determination output: DPA populated, NDA null."),

    # Procurement agent — STEP-04
    PerAgentScenario("scenario_1", "procurement_agent", "STEP-04", "complete",
        "FAST_TRACK match on clean upstream."),
    PerAgentScenario("scenario_2", "procurement_agent", "STEP-04", "escalated",
        "Standard-path classification under regulated upstream."),
    PerAgentScenario("scenario_7", "procurement_agent", "STEP-04", "escalated",
        "PAM-001 has only A-T1/B-T1/C-T1 rows; vendor is Class D / TIER_3 — two-dimensional gap. Highest-risk failure mode tested: silent path fabrication by picking the nearest row."),
    PerAgentScenario("scenario_8", "procurement_agent", "STEP-04", "escalated",
        "Upstream Legal blocker propagation. Q-01 match resolves locally but Legal escalated with dpa_blocker=true; Procurement must propagate the escalation while still populating its own determination fields."),
    PerAgentScenario("scenario_9", "procurement_agent", "STEP-04", "complete",
        "Tier-3 Slack supplementary handling. D-T2 is unambiguous PAM match; Slack threads (incl. workflow-preference distractor) must NOT flip fast_track_eligible or be cited as PRIMARY."),
    PerAgentScenario("scenario_10", "procurement_agent", "STEP-04", "blocked",
        "it_security_output entirely absent from bundle. Forces §9.1 blocked shape (determination fields absent, blocked_reason + blocked_fields populated)."),
    PerAgentScenario("scenario_13", "procurement_agent", "STEP-04", "complete",
        "Clean fast-track happy path — counterpart to scenario_8 with opposite upstream state. Catches spurious escalation, fast_track_eligible re-derivation, phantom blocker fabrication."),

    # Checklist Assembler — STEP-05
    PerAgentScenario("scenario_1", "checklist_assembler", "STEP-05", "COMPLETE",
        "Clean roll-up of all upstream determinations."),
    PerAgentScenario("scenario_2", "checklist_assembler", "STEP-05", "ESCALATED",
        "Roll-up under upstream escalation."),
    PerAgentScenario("scenario_11", "checklist_assembler", "STEP-05", "ESCALATED",
        "Cross-agent escalation cascade. STEP-03 escalated (DPA blocker, fields resolved) + STEP-04 escalated (workflow propagation). Stresses §8.1 status precedence and §6.2 multi-source blocker assembly."),
    PerAgentScenario("scenario_12", "checklist_assembler", "STEP-05", "COMPLETE",
        "Clean COMPLETE baseline (counterpart to scenario_11). Catches over-conservative escalation and phantom blocker fabrication on the happy path."),

    # Checkoff agent — STEP-06
    PerAgentScenario("scenario_1", "checkoff_agent", "STEP-06", "complete",
        "Stakeholder guidance generation on a green pipeline."),
    PerAgentScenario("scenario_2", "checkoff_agent", "STEP-06", "complete",
        "Stakeholder guidance under upstream-escalated state (still feedable in isolation)."),
)


AGENT_LABELS: dict[str, str] = {
    "it_security_agent": "IT Security agent",
    "legal_agent": "Legal agent",
    "procurement_agent": "Procurement agent",
    "checklist_assembler": "Checklist Assembler",
    "checkoff_agent": "Checkoff agent",
}


def _wrap(text: str, width: int, indent: str) -> str:
    """Word-wrap to ``width`` cols, prefixing wrapped lines with ``indent``."""
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if len(candidate) > width and current:
            lines.append(current)
            current = word
        else:
            current = candidate
    if current:
        lines.append(current)
    return ("\n" + indent).join(lines)


def _print_full_pipeline(scenarios: tuple[FullPipelineScenario, ...]) -> None:
    print("Full-pipeline scenarios  (scenarios_full_pipeline/)")
    print("-" * 60)
    print('  Run:  uv run pytest tests/full_pipeline/test_end_to_end.py \\')
    print('          -m "api and <marker>" -v')
    print()
    for case in scenarios:
        header = f"  {case.name}  ->  {case.expected_status}  (halt: {case.halt_step})"
        print(header)
        print(f"      marker: {case.pytest_marker}")
        print(f"      {_wrap(case.purpose, width=68, indent='      ')}")
        print()


def _print_per_agent(scenarios: tuple[PerAgentScenario, ...]) -> None:
    print("Per-agent scenarios  (scenarios_per_agent/  +  tests/fixtures/bundles/)")
    print("-" * 60)
    print("  Run:  uv run python -m per_agent_test_env.cli \\")
    print("          --agent <agent> --scenario <scenario>")
    print()
    grouped: dict[str, list[PerAgentScenario]] = {}
    for case in scenarios:
        grouped.setdefault(case.agent, []).append(case)

    for agent in ("it_security_agent", "legal_agent", "procurement_agent", "checklist_assembler", "checkoff_agent"):
        entries = grouped.get(agent)
        if not entries:
            continue
        print(f"  {AGENT_LABELS[agent]}  ({entries[0].step})")
        for case in entries:
            print(f"    {case.scenario:<14}  {case.expected_status:<22}  ", end="")
            print(_wrap(case.purpose, width=44, indent=" " * 44))
        print()


def _filter_per_agent(
    scenarios: tuple[PerAgentScenario, ...],
    agent: str | None,
) -> tuple[PerAgentScenario, ...]:
    if agent is None:
        return scenarios
    if agent not in AGENT_LABELS:
        valid = ", ".join(sorted(AGENT_LABELS))
        raise SystemExit(f"unknown --agent {agent!r}. valid: {valid}")
    return tuple(s for s in scenarios if s.agent == agent)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="List every prepared testing scenario in this repo.",
    )
    parser.add_argument(
        "--env",
        choices=("full_pipeline", "per_agent", "all"),
        default="all",
        help="Which test environment to list (default: all).",
    )
    parser.add_argument(
        "--agent",
        choices=tuple(AGENT_LABELS),
        default=None,
        help="Restrict per-agent listing to one agent.",
    )
    args = parser.parse_args(argv)

    print()
    print("Enterprise-AI testing scenarios")
    print("=" * 60)
    print()

    if args.env in ("full_pipeline", "all") and args.agent is None:
        _print_full_pipeline(FULL_PIPELINE)

    if args.env in ("per_agent", "all"):
        filtered = _filter_per_agent(PER_AGENT, args.agent)
        _print_per_agent(filtered)

    print(
        "Spec references:\n"
        "  - per-agent expected statuses : per_agent_test_env/evaluators.py\n"
        "  - full-pipeline scenario cases: tests/full_pipeline/test_end_to_end.py\n"
        "  - bundle fixtures             : tests/fixtures/bundles/\n"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
