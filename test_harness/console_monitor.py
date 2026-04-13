"""Realtime console event streaming monitor for orchestration test harness.

Prints colored, timestamped event lines as the pipeline executes.
"""

from __future__ import annotations

import sys
from datetime import datetime, UTC
from typing import Any

# ANSI color codes
_GREEN = "\033[92m"
_YELLOW = "\033[93m"
_RED = "\033[91m"
_CYAN = "\033[96m"
_BOLD = "\033[1m"
_RESET = "\033[0m"

# Check if stdout supports color
_USE_COLOR = sys.stdout.isatty()


def _color(text: str, code: str) -> str:
    if not _USE_COLOR:
        return text
    return f"{code}{text}{_RESET}"


def _ts() -> str:
    return datetime.now(UTC).strftime("%H:%M:%S")


def _status_color(status: str) -> str:
    s = status.upper()
    if s in ("COMPLETE", "ADMISSIBLE"):
        return _GREEN
    if s in ("IN_PROGRESS", "PARTIAL"):
        return _YELLOW
    if s in ("BLOCKED", "ESCALATED", "ESCALATION_REQUIRED"):
        return _RED
    return _CYAN


def _fmt_event(event_type: str, parts: dict[str, Any]) -> str:
    """Format a console event line."""
    ts = _ts()
    tag = _color(f"{event_type:<16}", _BOLD)
    detail = "  ".join(f"{k}={v}" for k, v in parts.items())
    return f"[{ts}] {tag} {detail}"


class ConsoleMonitor:
    """Hooks into the harness event loop and prints events to console."""

    def __init__(self, scenario_name: str, pipeline_run_id: str) -> None:
        self.scenario_name = scenario_name
        self.pipeline_run_id = pipeline_run_id
        self._events: list[dict[str, Any]] = []

    @property
    def events(self) -> list[dict[str, Any]]:
        return list(self._events)

    def _emit(self, event_type: str, parts: dict[str, Any]) -> None:
        line = _fmt_event(event_type, parts)
        print(line)
        self._events.append(
            {
                "timestamp": _ts(),
                "event_type": event_type,
                **parts,
            }
        )

    def on_run_init(self) -> None:
        self._emit(
            "RUN_INIT",
            {
                "pipeline_run_id": self.pipeline_run_id,
                "scenario": self.scenario_name,
            },
        )

    def on_step_enter(self, step: str) -> None:
        self._emit("STEP_ENTER", {"step": _color(step, _CYAN)})

    def on_retrieve_start(self, step: str, source: str, lane: str) -> None:
        self._emit(
            "RETRIEVE_START",
            {"step": step, "source": source, "lane": lane},
        )

    def on_retrieve_ok(self, step: str, source: str, records: int) -> None:
        self._emit(
            "RETRIEVE_OK",
            {"step": step, "source": source, "records": records},
        )

    def on_bundle_ready(self, step: str, admitted: int, excluded: int, admissible: bool) -> None:
        adm_str = _color("true", _GREEN) if admissible else _color("false", _RED)
        self._emit(
            "BUNDLE_READY",
            {
                "step": step,
                "admitted": admitted,
                "excluded": excluded,
                "admissible": adm_str,
            },
        )

    def on_handler_start(self, step: str, handler: str) -> None:
        self._emit("HANDLER_START", {"step": step, "handler": handler})

    def on_handler_ok(self, step: str, status: str) -> None:
        colored_status = _color(status, _status_color(status))
        self._emit("HANDLER_OK", {"step": step, "status": colored_status})

    def on_handler_result(self, step: str, status: str, reason: str | None = None) -> None:
        colored_status = _color(status, _status_color(status))
        parts: dict[str, Any] = {"step": step, "status": colored_status}
        if reason:
            parts["reason"] = reason
        self._emit("HANDLER_RESULT", parts)

    def on_state_update(self, step: str, overall_status: str, next_step: str | None) -> None:
        colored = _color(overall_status, _status_color(overall_status))
        parts: dict[str, Any] = {"step": step, "overall_status": colored}
        if next_step:
            parts["next_step"] = next_step
        self._emit("STATE_UPDATE", parts)

    def on_run_halt(self, overall_status: str, halted_at: str) -> None:
        colored = _color(overall_status, _status_color(overall_status))
        self._emit("RUN_HALT", {"overall_status": colored, "halted_at": halted_at})

    def on_run_complete(self, overall_status: str) -> None:
        colored = _color(overall_status, _status_color(overall_status))
        self._emit("RUN_COMPLETE", {"overall_status": colored})

    def on_assertion_pass(self, label: str) -> None:
        self._emit("ASSERT_PASS", {"check": _color(label, _GREEN)})

    def on_assertion_fail(self, label: str, reason: str) -> None:
        self._emit("ASSERT_FAIL", {"check": _color(label, _RED), "reason": reason})
