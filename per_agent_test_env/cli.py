"""CLI entry point for the per-agent live-LLM test runner.

Usage
-----
    # Single agent + scenario
    uv run python -m per_agent_test_env.cli --agent it_security_agent --scenario scenario_1

    # All scenarios for one agent (halts on first failure)
    uv run python -m per_agent_test_env.cli --agent legal_agent --all-scenarios

    # Every agent × scenario pair (halts on first failure)
    uv run python -m per_agent_test_env.cli --all

Exit codes
----------
    0 — the selected run(s) passed every hard check
    1 — at least one hard check failed; the runner halts and does not cascade
        into the next agent on its own
    2 — configuration / argument error
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from per_agent_test_env.bundle_loader import VALID_AGENTS, VALID_SCENARIOS
from per_agent_test_env.reporter import (
    print_halt_on_fail,
    print_result,
    print_run_header,
)
from per_agent_test_env.runner import RunnerError, run_agent_test


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="per_agent_test_env",
        description="Run one domain agent in isolation against the real Anthropic API.",
    )

    # Agent selection — either --agent or --all
    group_agent = parser.add_mutually_exclusive_group()
    group_agent.add_argument(
        "--agent",
        choices=sorted(VALID_AGENTS),
        help="The domain agent to run in isolation.",
    )
    group_agent.add_argument(
        "--all",
        action="store_true",
        help="Run every agent × scenario combination (halts on first failure).",
    )

    # Scenario selection
    group_scenario = parser.add_mutually_exclusive_group()
    group_scenario.add_argument(
        "--scenario",
        choices=sorted(VALID_SCENARIOS),
        help="Which demo scenario bundle to feed the agent.",
    )
    group_scenario.add_argument(
        "--all-scenarios",
        action="store_true",
        help="Run both scenarios for the selected agent (halts on first failure).",
    )

    parser.add_argument(
        "--model",
        help="Override the Anthropic model (default: ANTHROPIC_MODEL env or claude-haiku-4-5).",
    )
    parser.add_argument(
        "--max-tokens",
        type=int,
        help="Override max_tokens for the call (default: 4096).",
    )
    parser.add_argument(
        "--recorded-dir",
        type=Path,
        help="Override the recorded-responses directory "
        "(default: <repo_root>/tests/recorded_responses).",
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        help="Override the repo root (default: the directory containing per_agent_test_env/).",
    )

    return parser


def _expand_targets(args: argparse.Namespace) -> list[tuple[str, str]]:
    """Expand CLI args into an ordered list of (agent, scenario) targets."""
    if args.all:
        scenarios = VALID_SCENARIOS if (args.all_scenarios or args.scenario is None) else (args.scenario,)
        return [(agent, scenario) for agent in VALID_AGENTS for scenario in scenarios]

    if not args.agent:
        raise SystemExit("error: --agent is required (or pass --all)")

    if args.all_scenarios:
        return [(args.agent, scenario) for scenario in VALID_SCENARIOS]

    if not args.scenario:
        raise SystemExit("error: --scenario is required (or pass --all-scenarios / --all)")

    return [(args.agent, args.scenario)]


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    try:
        targets = _expand_targets(args)
    except SystemExit as exc:
        print(exc, file=sys.stderr)
        return 2

    runner_kwargs = {
        "repo_root": args.repo_root,
        "recorded_responses_dir": args.recorded_dir,
        "model": args.model,
        "max_tokens": args.max_tokens,
    }

    total = len(targets)
    for idx, (agent_name, scenario) in enumerate(targets, start=1):
        print_run_header(agent_name, scenario, stream=sys.stdout)
        sys.stdout.write(f"[{idx}/{total}]\n")
        sys.stdout.flush()

        try:
            result = run_agent_test(
                agent_name,
                scenario,
                **{k: v for k, v in runner_kwargs.items() if v is not None},
            )
        except RunnerError as exc:
            sys.stderr.write(f"RUNNER ERROR: {exc}\n")
            return 2

        print_result(result, stream=sys.stdout)

        if not result.passed:
            print_halt_on_fail(result, stream=sys.stdout)
            return 1

    sys.stdout.write(f"\nALL TARGETS PASSED: {total}/{total}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
