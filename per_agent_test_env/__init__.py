"""Per-agent isolated live-LLM test environment.

Runs exactly one domain agent against the real Anthropic API using its
spec file as the system prompt and a pre-assembled context bundle as
the user message. Records the raw response to disk before any
evaluation runs, then evaluates the saved response against the output
contract in ``llm_agent_output_evaluation_checklist.md``.

No supervisor, no pipeline state, no cascading — one agent, one call,
one recorded response, one evaluation.
"""

import sys as _sys
from pathlib import Path as _Path

# Ensure ``agents`` (under ``src/``) and ``per_agent_test_env`` resolve when
# the package is imported as a script (``python -m per_agent_test_env.cli``).
# Pytest's conftest already wires these paths so this is a no-op in test runs.
_REPO_ROOT = _Path(__file__).resolve().parent.parent
for _candidate in (_REPO_ROOT / "src", _REPO_ROOT):
    _candidate_str = str(_candidate)
    if _candidate_str not in _sys.path:
        _sys.path.insert(0, _candidate_str)

from per_agent_test_env.bundle_loader import (
    AGENT_TO_STEP,
    SCENARIOS_BY_AGENT,
    VALID_AGENTS,
    VALID_SCENARIOS,
    BundleError,
    fixture_path,
    load_bundle,
)
from per_agent_test_env.evaluators import EXPECTED_STATUS, evaluate_recorded
from per_agent_test_env.runner import (
    AgentTestResult,
    RecordedCall,
    RunnerError,
    run_agent_test,
)

__all__ = [
    "AGENT_TO_STEP",
    "SCENARIOS_BY_AGENT",
    "VALID_AGENTS",
    "VALID_SCENARIOS",
    "AgentTestResult",
    "BundleError",
    "EXPECTED_STATUS",
    "RecordedCall",
    "RunnerError",
    "evaluate_recorded",
    "fixture_path",
    "load_bundle",
    "run_agent_test",
]
