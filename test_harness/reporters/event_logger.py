"""EventLogger: writes JSONL events to artifacts/test_runs/<scenario>/<run_id>/events.jsonl."""

from __future__ import annotations

import json
from datetime import datetime, UTC
from pathlib import Path
from typing import Any


class EventLogger:
    """Appends one JSON event per line to the run artifact directory."""

    def __init__(self, scenario_name: str, run_id: str, artifacts_root: Path) -> None:
        self.scenario_name = scenario_name
        self.run_id = run_id
        self._run_dir = artifacts_root / "test_runs" / scenario_name / run_id
        self._run_dir.mkdir(parents=True, exist_ok=True)
        self._path = self._run_dir / "events.jsonl"

    @property
    def run_dir(self) -> Path:
        return self._run_dir

    def append(self, event_type: str, step: str | None, payload: dict[str, Any]) -> None:
        event: dict[str, Any] = {
            "timestamp": datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
            "event_type": event_type,
            "step": step,
            "payload": payload,
        }
        with self._path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(event) + "\n")

    def events(self) -> list[dict[str, Any]]:
        if not self._path.exists():
            return []
        with self._path.open(encoding="utf-8") as fh:
            return [json.loads(line) for line in fh if line.strip()]
