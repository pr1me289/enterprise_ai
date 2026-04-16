"""Per-agent isolated live-LLM test runner.

One call per invocation. No supervisor. No pipeline state. No cascading.

Flow:
    1. Load the agent spec file as system prompt.
    2. Load the pre-assembled context bundle fixture.
    3. Make one real Anthropic ``messages.create`` call.
    4. **Record the raw response to disk before any evaluation runs.**
    5. Run the evaluator against the saved parsed output.
    6. Return a structured result with pass/fail, failures, and the
       absolute path to the recorded-responses file.

If the API call raises, if the response fails to parse, or if the
evaluator flags any failure, the run is marked as failed. Re-running
the failing agent is not automatic — the caller must decide to re-run,
which matches the checklist's "Do not re-run an agent to fix a failed
evaluation" rule.
"""

from __future__ import annotations

import datetime as _dt
import json
import os
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parent.parent

# Ensure ``agents`` and ``per_agent_test_env`` imports resolve when the
# runner is invoked as a script (``python -m per_agent_test_env.cli`` or
# ``python per_agent_test_env/cli.py``). Pytest's conftest already wires
# these paths so this is a no-op in test runs.
for _candidate in (_REPO_ROOT / "src", _REPO_ROOT):
    if str(_candidate) not in sys.path:
        sys.path.insert(0, str(_candidate))

from agents._prompts import SPEC_PATHS, load_system_prompt  # noqa: E402
from agents.llm_caller import (  # noqa: E402
    DEFAULT_MAX_TOKENS,
    DEFAULT_MODEL,
    _build_client,
    _extract_text,
    _parse_json_response,
    _user_message_from_bundle,
)

from per_agent_test_env.bundle_loader import fixture_path, load_bundle  # noqa: E402
from per_agent_test_env.evaluators import EvaluationReport, evaluate_recorded  # noqa: E402


class RunnerError(Exception):
    """Raised for configuration failures the runner cannot proceed through."""


@dataclass
class RecordedCall:
    """A single recorded agent call, written to disk before any evaluation."""

    agent_name: str
    scenario: str
    pipeline_run_id: str
    model: str
    timestamp_utc: str
    system_prompt_path: str
    bundle_fixture_path: str
    raw_text: str | None
    parsed_output: dict[str, Any] | None
    error: str | None
    recorded_file: str  # absolute path to the written record JSON


@dataclass
class AgentTestResult:
    """The complete outcome of one per-agent isolated test run."""

    agent_name: str
    scenario: str
    passed: bool
    failures: list[str]
    warnings: list[str]
    recorded: RecordedCall


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _utc_timestamp() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _next_run_number(record_dir: Path, agent_name: str, scenario: str) -> int:
    """Find the next run number for an ``(agent, scenario)`` pair.

    Convention: ``{agent}__{scenario}__{N}[_pass|_fail].json`` where ``N``
    is a positive integer. Starts at 1 for a new ``(agent, scenario)``
    pair. Legacy timestamp-named files (non-digit leading chars after the
    prefix) are ignored so they do not pollute the counter.
    """
    prefix = f"{agent_name}__{scenario}__"
    max_n = 0
    if not record_dir.exists():
        return 1
    for entry in record_dir.iterdir():
        name = entry.name
        if not name.startswith(prefix):
            continue
        tail = name[len(prefix):].removesuffix(".json")
        digits = ""
        for ch in tail:
            if ch.isdigit():
                digits += ch
            else:
                break
        if not digits:
            continue
        try:
            n = int(digits)
        except ValueError:
            continue
        if n > max_n:
            max_n = n
    return max_n + 1


def _staging_filename(agent_name: str, scenario: str, run_number: int) -> str:
    """Filename used for the pre-evaluation write.

    Intentionally has no ``_pass``/``_fail`` suffix — that suffix is
    applied by renaming after the evaluator runs. Keeping the suffix out
    of the initial write preserves the record-before-evaluate contract:
    the payload is on disk before the evaluator is invoked, and only the
    filename is updated after the verdict is known.
    """
    return f"{agent_name}__{scenario}__{run_number}.json"


def _final_filename(agent_name: str, scenario: str, run_number: int, passed: bool) -> str:
    return f"{agent_name}__{scenario}__{run_number}_{'pass' if passed else 'fail'}.json"


def _write_record(
    record_dir: Path,
    filename: str,
    payload: dict[str, Any],
) -> Path:
    """Write the record to disk synchronously before any evaluation runs."""
    record_dir.mkdir(parents=True, exist_ok=True)
    path = record_dir / filename
    # Use default=str as a last-resort fallback; the payload is already
    # JSON-safe except for the bundle fixture which we serialize as a path.
    path.write_text(json.dumps(payload, indent=2, sort_keys=False, default=str), encoding="utf-8")
    return path


def _ensure_api_key_loaded() -> None:
    """Best-effort ``.env`` load so the SDK client sees ``ANTHROPIC_API_KEY``."""
    if os.environ.get("ANTHROPIC_API_KEY"):
        return
    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    load_dotenv(_REPO_ROOT / ".env")


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def run_agent_test(
    agent_name: str,
    scenario: str,
    *,
    repo_root: Path | None = None,
    recorded_responses_dir: Path | None = None,
    client: Any = None,
    model: str | None = None,
    max_tokens: int | None = None,
) -> AgentTestResult:
    """Invoke one agent against the real API in isolation.

    Parameters
    ----------
    agent_name : one of ``VALID_AGENTS``.
    scenario   : one of ``VALID_SCENARIOS``.
    repo_root  : override for the repo root. Defaults to the directory
                 containing ``per_agent_test_env/``.
    recorded_responses_dir : override for where the raw record is
                             written. Defaults to ``<repo_root>/tests/recorded_responses``.
    client     : optional Anthropic-compatible client. If omitted the
                 SDK client is built from ``ANTHROPIC_API_KEY``. Pass a
                 stub here for smoke tests that must not hit the API.
    model, max_tokens : optional overrides. Defaults come from the call
                        layer (``DEFAULT_MODEL`` / ``DEFAULT_MAX_TOKENS``)
                        and the ``ANTHROPIC_MODEL`` env var.
    """
    root = repo_root or _REPO_ROOT
    record_dir = recorded_responses_dir or (root / "tests" / "recorded_responses")
    model_name = model or os.environ.get("ANTHROPIC_MODEL") or DEFAULT_MODEL
    max_tokens_value = max_tokens or DEFAULT_MAX_TOKENS

    # Step 1 — load the bundle fixture before touching the API. Any
    # mismatch halts the run here with a clear error.
    bundle, pipeline_run_id, bundle_path = load_bundle(agent_name, scenario, repo_root=root)

    # Step 2 — load the agent spec as the system prompt.
    try:
        system_prompt = load_system_prompt(agent_name, repo_root=root)
    except (KeyError, FileNotFoundError) as exc:
        raise RunnerError(f"could not load spec for {agent_name!r}: {exc}") from exc

    spec_path = SPEC_PATHS[agent_name]

    # Step 3 — build the user message exactly the way the call layer does.
    step_metadata = {
        "pipeline_run_id": pipeline_run_id,
        "scenario": scenario,
        "agent": agent_name,
        "step_id": _STEP_ID_FOR_AGENT[agent_name],
        "isolated_per_agent_test": True,
    }
    user_message = _user_message_from_bundle(bundle, step_metadata)

    # Step 4 — real API call. We do NOT reuse ``_call_agent`` because that
    # swallows exceptions and discards the raw text. For test purposes we
    # need both the raw text and the structured error capture.
    raw_text: str | None = None
    parsed: dict[str, Any] | None = None
    error: str | None = None
    used_client = client

    timestamp = _utc_timestamp()

    try:
        if used_client is None:
            _ensure_api_key_loaded()
            if not os.environ.get("ANTHROPIC_API_KEY"):
                raise RunnerError(
                    "ANTHROPIC_API_KEY is not set — cannot make live API call. "
                    "Set it in the environment or in a .env file at the repo root."
                )
            used_client = _build_client()

        response = used_client.messages.create(
            model=model_name,
            max_tokens=max_tokens_value,
            system=system_prompt,
            messages=[{"role": "user", "content": user_message}],
        )
        try:
            raw_text = _extract_text(response)
        except Exception as exc:  # noqa: BLE001 — test layer captures all
            error = f"text-extraction failure: {type(exc).__name__}: {exc}"
    except RunnerError:
        raise
    except Exception as exc:  # noqa: BLE001 — API errors captured for the record
        error = f"{type(exc).__name__}: {exc}"

    if raw_text is not None and error is None:
        try:
            parsed = _parse_json_response(raw_text)
        except Exception as exc:  # noqa: BLE001
            error = f"JSON parse failure: {type(exc).__name__}: {exc}"

    # Step 5 — RECORD TO DISK BEFORE EVALUATION. This is a strict ordering
    # requirement from the per-agent prompt. Do not move the evaluator
    # call above this block. The file is written under a staging name
    # (no pass/fail suffix); the suffix is applied by renaming after the
    # evaluator returns. The payload on disk is identical either way —
    # only the filename changes post-eval.
    run_number = _next_run_number(record_dir, agent_name, scenario)
    staging_name = _staging_filename(agent_name, scenario, run_number)
    record_payload: dict[str, Any] = {
        "agent_name": agent_name,
        "scenario": scenario,
        "pipeline_run_id": pipeline_run_id,
        "run_number": run_number,
        "model": model_name,
        "max_tokens": max_tokens_value,
        "timestamp_utc": timestamp,
        "system_prompt_path": str(spec_path),
        "bundle_fixture_path": str(bundle_path.relative_to(root) if bundle_path.is_absolute() else bundle_path),
        "raw_text": raw_text,
        "parsed_output": parsed,
        "error": error,
    }
    staged_path = _write_record(record_dir, staging_name, record_payload)

    # Step 6 — evaluate the recorded response. Never re-call the model here.
    report: EvaluationReport = evaluate_recorded(
        agent_name=agent_name,
        scenario=scenario,
        parsed_output=parsed,
        error=error,
    )

    # Step 6.5 — rename the staged file to include the pass/fail verdict.
    # This is a pure filename change; the recorded payload is unchanged.
    final_name = _final_filename(agent_name, scenario, run_number, report.passed)
    record_file = record_dir / final_name
    if record_file.exists():
        # Extremely unlikely (would require a race on the same run_number),
        # but do not silently overwrite a prior record.
        raise RunnerError(
            f"recorded-response target already exists: {record_file}"
        )
    staged_path.rename(record_file)

    recorded = RecordedCall(
        agent_name=agent_name,
        scenario=scenario,
        pipeline_run_id=pipeline_run_id,
        model=model_name,
        timestamp_utc=timestamp,
        system_prompt_path=str(spec_path),
        bundle_fixture_path=str(bundle_path),
        raw_text=raw_text,
        parsed_output=parsed,
        error=error,
        recorded_file=str(record_file),
    )

    return AgentTestResult(
        agent_name=agent_name,
        scenario=scenario,
        passed=report.passed,
        failures=list(report.failures),
        warnings=list(report.warnings),
        recorded=recorded,
    )


# Step IDs used in step_metadata for traceability — mirrors the orchestrator.
_STEP_ID_FOR_AGENT: dict[str, str] = {
    "it_security_agent": "STEP-02",
    "legal_agent": "STEP-03",
    "procurement_agent": "STEP-04",
    "checklist_assembler": "STEP-05",
    "checkoff_agent": "STEP-06",
}


def result_as_dict(result: AgentTestResult) -> dict[str, Any]:
    """Convenience: flatten an ``AgentTestResult`` into a JSON-safe dict."""
    return asdict(result)
