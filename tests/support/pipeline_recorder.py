"""Per-agent recorder for live-LLM full-pipeline runs.

Writes one file per executed domain-agent step in a single pipeline run,
grouped by a monotonically increasing ``pipeline_run_number`` that is
shared across every file produced by that run. The naming convention is
symmetric with the per-agent suite's ``{agent}__{scenario}__{N}_{pass|fail}.json``
files but oriented around a pipeline run number rather than a per-agent
counter:

    pipeline_{N}__{agent_name}__{scenario}_{pass|fail}.json

where ``N`` is the pipeline run number (global across scenarios — a
``scenario_1`` run and a subsequent ``scenario_2`` run produce
``pipeline_1__...`` and ``pipeline_2__...`` respectively), ``agent_name``
is the domain-agent key (``it_security_agent``, ``legal_agent``,
``procurement_agent``, ``checklist_assembler``, ``checkoff_agent``), and
``scenario`` is the scenario id. The pass/fail suffix carries the
per-step verdict from the evaluator.

STEP-01 is a deterministic intake handler with no LLM involvement, so
it is intentionally not recorded — the recorder only captures agent
outputs.

Each record payload includes:
  - parsed output (the supervisor's determination for that step)
  - call record (model, timing, tokens, missing fields, error) from the
    LLM adapter's ``call_records`` list
  - pipeline run metadata (run id, scenario, timestamp)
  - step status (COMPLETE / ESCALATED / BLOCKED / PENDING)
"""

from __future__ import annotations

import datetime as _dt
import json
import re
from pathlib import Path
from typing import Any, Iterable

from orchestration.models.enums import StepId


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


_PIPELINE_PREFIX_RE = re.compile(r"^pipeline_(\d+)__")


def _utc_timestamp() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def next_pipeline_run_number(record_dir: Path) -> int:
    """Return the next pipeline-run number for ``record_dir``.

    Scans every ``pipeline_{N}__...`` file in the directory and returns
    ``max(N) + 1``. Returns ``1`` if the directory does not exist or
    contains no matching files.
    """
    if not record_dir.exists():
        return 1
    max_n = 0
    for entry in record_dir.iterdir():
        if not entry.is_file():
            continue
        match = _PIPELINE_PREFIX_RE.match(entry.name)
        if not match:
            continue
        try:
            n = int(match.group(1))
        except ValueError:
            continue
        if n > max_n:
            max_n = n
    return max_n + 1


def _match_call_record(
    call_records: Iterable[dict[str, Any]],
    agent_name: str,
) -> dict[str, Any] | None:
    matching = [r for r in call_records if r.get("agent_name") == agent_name]
    return matching[-1] if matching else None


def record_pipeline_run(
    *,
    scenario: str,
    supervisor: Any,
    record_dir: Path,
    verdicts: dict[StepId, bool] | None = None,
    pipeline_run_number: int | None = None,
) -> dict[StepId, Path]:
    """Write one record per executed domain-agent step.

    All files produced by a single call share the same ``pipeline_run_number``
    in their filename. If ``pipeline_run_number`` is not provided it is
    computed by scanning ``record_dir`` for the highest existing value.

    ``verdicts`` maps ``StepId`` → pass/fail for the filename suffix; a
    step missing from ``verdicts`` is written without a verdict suffix
    and the caller can rename via ``rename_with_verdicts``.
    """
    record_dir.mkdir(parents=True, exist_ok=True)
    verdicts = verdicts or {}
    if pipeline_run_number is None:
        pipeline_run_number = next_pipeline_run_number(record_dir)

    call_records = getattr(supervisor.llm_adapter, "call_records", []) or []
    pipeline_run_id = getattr(supervisor.state, "pipeline_run_id", "") or ""
    timestamp = _utc_timestamp()

    written: dict[StepId, Path] = {}
    for step_id, det_key in _STEP_DETERMINATION_KEY.items():
        determination = supervisor.state.determinations.get(det_key)
        if determination is None:
            continue
        agent_name = _STEP_AGENT[step_id]
        call_record = _match_call_record(call_records, agent_name)
        verdict = verdicts.get(step_id)
        suffix = "" if verdict is None else f"_{'pass' if verdict else 'fail'}"
        filename = f"pipeline_{pipeline_run_number}__{agent_name}__{scenario}{suffix}.json"

        payload = {
            "record_type": "pipeline_step",
            "pipeline_run_number": pipeline_run_number,
            "scenario": scenario,
            "step_id": step_id.value,
            "determination_key": det_key,
            "agent_name": agent_name,
            "pipeline_run_id": pipeline_run_id,
            "timestamp_utc": timestamp,
            "parsed_output": determination,
            "call_record": call_record,
            "step_status": supervisor.state.step_statuses[step_id].value,
        }
        path = record_dir / filename
        path.write_text(
            json.dumps(payload, indent=2, sort_keys=False, default=str),
            encoding="utf-8",
        )
        written[step_id] = path
    return written


def rename_with_verdicts(
    paths: dict[StepId, Path],
    verdicts: dict[StepId, bool],
) -> dict[StepId, Path]:
    """Rename staged records (no suffix) in-place to include pass/fail suffix."""
    renamed: dict[StepId, Path] = {}
    for step_id, staged in paths.items():
        if step_id not in verdicts:
            renamed[step_id] = staged
            continue
        verdict = verdicts[step_id]
        suffix = f"_{'pass' if verdict else 'fail'}"
        stem = staged.stem
        if stem.endswith("_pass") or stem.endswith("_fail"):
            renamed[step_id] = staged
            continue
        final = staged.with_name(f"{stem}{suffix}.json")
        if final.exists():
            raise FileExistsError(f"recorded-response target already exists: {final}")
        staged.rename(final)
        renamed[step_id] = final
    return renamed
