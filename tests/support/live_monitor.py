"""Live console monitor for the real-LLM test suite.

This is the ``test_harness.console_monitor`` counterpart for tests that drive
real Anthropic API calls. It streams structured, timestamped, color-coded
events so a human watching ``pytest -m api -s`` sees every agent call, every
per-field verdict, every handoff invariant, every acceptance check, and every
pipeline step as it happens — with a summary table at the end.

Event taxonomy (stable; used in both console output and the in-memory log):

  SESSION_START    — banner: model, scenarios armed, key presence (masked)
  TEST_START       — "=== test <id> [layer=...] ==="
  AGENT_CALL_START — before an API call
  AGENT_CALL_OK    — after an API call: elapsed, input/output tokens
  AGENT_CALL_ERR   — on exception from the API path
  FIELD_VERDICT    — per-field PASS/FAIL (fed from field_reporter)
  HANDOFF          — Layer-2 invariant verdict (upstream→downstream)
  ACCEPTANCE       — Layer-3 acceptance-check verdict (A-xx)
  PIPELINE_STEP    — Layer-4 Supervisor step event (mirrors mock harness)
  TEST_RESULT      — "[PASS|FAIL] <id>" at the end of each test
  SESSION_END      — totals table

The monitor is a plain object (not a pytest plugin) so it can be used by
non-test code too. A session-scoped pytest fixture wires it up and the
pytest hooks in ``tests/conftest.py`` feed it the lifecycle events.
"""

from __future__ import annotations

import json
import os
import re
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


# ---------------------------------------------------------------------------
# ANSI palette
# ---------------------------------------------------------------------------

_GREEN = "\033[92m"
_YELLOW = "\033[93m"
_RED = "\033[91m"
_CYAN = "\033[96m"
_MAGENTA = "\033[95m"
_BLUE = "\033[94m"
_BOLD = "\033[1m"
_DIM = "\033[2m"
_RESET = "\033[0m"

_USE_COLOR = sys.stdout.isatty() and os.environ.get("NO_COLOR") is None


def _c(text: str, code: str) -> str:
    if not _USE_COLOR:
        return text
    return f"{code}{text}{_RESET}"


def _ts() -> str:
    return datetime.now().strftime("%H:%M:%S")


def _status_color(status: str) -> str:
    s = (status or "").upper()
    if s in ("PASS", "OK", "COMPLETE", "COMPLETED", "ADMISSIBLE"):
        return _GREEN
    if s in ("WARN", "PARTIAL", "IN_PROGRESS", "PENDING"):
        return _YELLOW
    if s in ("FAIL", "ERROR", "BLOCKED", "ESCALATED", "ESCALATION_REQUIRED"):
        return _RED
    return _CYAN


# ---------------------------------------------------------------------------
# Secret redaction — belt-and-suspenders guard so no event leaks the API key
# ---------------------------------------------------------------------------


_API_KEY_RE = re.compile(r"sk-ant-[A-Za-z0-9\-_]{20,}")


def _redact(text: str) -> str:
    """Replace any Anthropic-style key that may have snuck into a detail string."""
    return _API_KEY_RE.sub("sk-ant-***REDACTED***", text)


def _mask_key_presence(value: str | None) -> str:
    if not value:
        return _c("absent", _RED)
    return _c(f"present ({len(value)} chars)", _GREEN)


# ---------------------------------------------------------------------------
# Running totals
# ---------------------------------------------------------------------------


@dataclass
class _Totals:
    api_calls: int = 0
    api_errors: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    elapsed_seconds: float = 0.0
    tests_passed: int = 0
    tests_failed: int = 0
    tests_skipped: int = 0
    field_verdicts_pass: int = 0
    field_verdicts_fail: int = 0
    by_layer: dict[str, dict[str, int]] = field(default_factory=dict)

    def bump_test(self, layer: str, outcome: str) -> None:
        row = self.by_layer.setdefault(layer, {"passed": 0, "failed": 0, "skipped": 0})
        row[outcome] = row.get(outcome, 0) + 1


# ---------------------------------------------------------------------------
# The monitor
# ---------------------------------------------------------------------------


class LiveMonitor:
    """Streaming + aggregating monitor for real-LLM tests."""

    def __init__(self) -> None:
        self._events: list[dict[str, Any]] = []
        self._totals = _Totals()
        self._call_stack: list[tuple[str, float]] = []  # (agent, start_time)
        self._session_started = False
        self._started_at = time.monotonic()

    # ------------------------------------------------------------------
    # Event plumbing
    # ------------------------------------------------------------------

    def _emit(self, event_type: str, parts: dict[str, Any]) -> None:
        ts = _ts()
        tag = _c(f"{event_type:<18}", _BOLD)
        # Render values; redact anything that looks like a key.
        rendered_parts = []
        for k, v in parts.items():
            val = v if isinstance(v, str) else json.dumps(v, default=str)
            val = _redact(val)
            rendered_parts.append(f"{k}={val}")
        detail = "  ".join(rendered_parts)
        print(f"[{ts}] {tag} {detail}", flush=True)
        self._events.append({"ts": ts, "event_type": event_type, **parts})

    @property
    def events(self) -> list[dict[str, Any]]:
        return list(self._events)

    @property
    def totals(self) -> _Totals:
        return self._totals

    # ------------------------------------------------------------------
    # Session lifecycle
    # ------------------------------------------------------------------

    def session_start(
        self,
        *,
        model: str,
        api_key: str | None,
        layers: tuple[str, ...],
        scenarios: tuple[str, ...],
        test_count: int,
    ) -> None:
        if self._session_started:
            return
        self._session_started = True
        self._started_at = time.monotonic()
        banner = _c(
            "====================  Real-LLM Test Session  ====================",
            _BOLD + _MAGENTA,
        )
        print(banner, flush=True)
        self._emit(
            "SESSION_START",
            {
                "model": _c(model, _CYAN),
                "api_key": _mask_key_presence(api_key),
                "layers": ",".join(layers) or "none",
                "scenarios": ",".join(scenarios) or "none",
                "test_count": test_count,
            },
        )

    def session_end(self) -> None:
        if not self._session_started:
            return
        elapsed = time.monotonic() - self._started_at
        t = self._totals
        # Block banner
        banner = _c(
            "====================  Session Summary  ====================",
            _BOLD + _MAGENTA,
        )
        print(banner, flush=True)
        # Coverage by layer
        layer_order = ("layer_unit", "layer_handoff", "layer_acceptance", "full_pipeline")
        header = _c(
            f"  {'layer':<20} {'passed':>8} {'failed':>8} {'skipped':>8}",
            _BOLD,
        )
        print(header, flush=True)
        for layer in layer_order:
            row = t.by_layer.get(layer, {"passed": 0, "failed": 0, "skipped": 0})
            pc = _c(f"{row.get('passed', 0):>8}", _GREEN)
            fc = _c(f"{row.get('failed', 0):>8}", _RED if row.get("failed") else _DIM)
            sc = _c(f"{row.get('skipped', 0):>8}", _YELLOW if row.get("skipped") else _DIM)
            print(f"  {layer:<20}{pc}{fc}{sc}", flush=True)
        # Aggregate row
        print(
            f"  {'TOTAL':<20}"
            f"{_c(f'{t.tests_passed:>8}', _GREEN)}"
            f"{_c(f'{t.tests_failed:>8}', _RED if t.tests_failed else _DIM)}"
            f"{_c(f'{t.tests_skipped:>8}', _YELLOW if t.tests_skipped else _DIM)}",
            flush=True,
        )
        # API totals
        self._emit(
            "SESSION_END",
            {
                "elapsed": f"{elapsed:.2f}s",
                "api_calls": t.api_calls,
                "api_errors": t.api_errors,
                "input_tokens": t.input_tokens,
                "output_tokens": t.output_tokens,
                "fields_pass": t.field_verdicts_pass,
                "fields_fail": t.field_verdicts_fail,
            },
        )
        if t.api_errors or t.tests_failed or t.field_verdicts_fail:
            print(_c("  >>> Session ended with failures — see FIELD_VERDICT/AGENT_CALL_ERR above.", _RED), flush=True)
        else:
            print(_c("  >>> All armed layers passed.", _GREEN), flush=True)

    # ------------------------------------------------------------------
    # Test-level events
    # ------------------------------------------------------------------

    def test_start(self, *, node_id: str, layer: str, scenario: str | None) -> None:
        self._emit(
            "TEST_START",
            {
                "layer": _c(layer, _BLUE),
                "scenario": scenario or "-",
                "node": node_id,
            },
        )

    def test_result(self, *, node_id: str, layer: str, outcome: str, duration: float) -> None:
        colored = _c(outcome.upper(), _status_color(outcome))
        self._emit(
            "TEST_RESULT",
            {
                "verdict": colored,
                "layer": layer,
                "node": node_id,
                "duration": f"{duration:.2f}s",
            },
        )
        if outcome == "passed":
            self._totals.tests_passed += 1
            self._totals.bump_test(layer, "passed")
        elif outcome == "failed":
            self._totals.tests_failed += 1
            self._totals.bump_test(layer, "failed")
        elif outcome == "skipped":
            self._totals.tests_skipped += 1
            self._totals.bump_test(layer, "skipped")

    # ------------------------------------------------------------------
    # Agent-call events (fed by the instrumented Anthropic wrapper)
    # ------------------------------------------------------------------

    def agent_call_start(self, *, agent: str, scenario: str | None, pipeline_run_id: str) -> None:
        self._call_stack.append((agent, time.monotonic()))
        self._emit(
            "AGENT_CALL_START",
            {
                "agent": _c(agent, _CYAN),
                "scenario": scenario or "-",
                "run_id": pipeline_run_id,
            },
        )

    def agent_call_ok(
        self,
        *,
        agent: str,
        elapsed: float,
        input_tokens: int | None,
        output_tokens: int | None,
        status: str | None,
    ) -> None:
        self._totals.api_calls += 1
        if input_tokens:
            self._totals.input_tokens += input_tokens
        if output_tokens:
            self._totals.output_tokens += output_tokens
        self._totals.elapsed_seconds += elapsed
        colored_status = _c(status or "ok", _status_color(status or "OK"))
        self._emit(
            "AGENT_CALL_OK",
            {
                "agent": _c(agent, _CYAN),
                "elapsed": f"{elapsed:.2f}s",
                "in_tokens": input_tokens or "?",
                "out_tokens": output_tokens or "?",
                "output_status": colored_status,
            },
        )

    def agent_call_err(self, *, agent: str, elapsed: float, error: str) -> None:
        self._totals.api_errors += 1
        self._emit(
            "AGENT_CALL_ERR",
            {
                "agent": _c(agent, _RED),
                "elapsed": f"{elapsed:.2f}s",
                "error": error[:240],
            },
        )

    # ------------------------------------------------------------------
    # Assertion / verdict events
    # ------------------------------------------------------------------

    def field_verdict(
        self,
        *,
        path: str,
        description: str,
        passed: bool,
        observed: Any,
        reason: str,
    ) -> None:
        flag = _c("PASS", _GREEN) if passed else _c("FAIL", _RED)
        preview = json.dumps(observed, default=str)
        if len(preview) > 80:
            preview = preview[:77] + "..."
        self._emit(
            "FIELD_VERDICT",
            {
                "verdict": flag,
                "path": path,
                "desc": description,
                "observed": preview,
                "reason": reason,
            },
        )
        if passed:
            self._totals.field_verdicts_pass += 1
        else:
            self._totals.field_verdicts_fail += 1

    def handoff(
        self,
        *,
        invariant: str,
        upstream: str,
        downstream: str,
        passed: bool,
        detail: str = "",
    ) -> None:
        flag = _c("PASS", _GREEN) if passed else _c("FAIL", _RED)
        self._emit(
            "HANDOFF",
            {
                "verdict": flag,
                "invariant": invariant,
                "chain": f"{upstream}→{downstream}",
                "detail": detail,
            },
        )

    def acceptance(
        self,
        *,
        check_id: str,
        agent: str,
        passed: bool,
        detail: str = "",
    ) -> None:
        flag = _c("PASS", _GREEN) if passed else _c("FAIL", _RED)
        self._emit(
            "ACCEPTANCE",
            {
                "verdict": flag,
                "check": check_id,
                "agent": agent,
                "detail": detail,
            },
        )

    # ------------------------------------------------------------------
    # Full-pipeline step events (Layer 4 — mirrors the mock harness shape)
    # ------------------------------------------------------------------

    def pipeline_step(self, *, step_id: str, event: str, **details: Any) -> None:
        self._emit(
            f"PIPELINE_{event.upper()}",
            {"step": _c(step_id, _CYAN), **{k: v for k, v in details.items()}},
        )


# ---------------------------------------------------------------------------
# Anthropic client instrumentation
# ---------------------------------------------------------------------------


class InstrumentedMessages:
    """Forwards ``messages.create`` to the real SDK and records timing + tokens."""

    def __init__(self, inner: Any, monitor: LiveMonitor) -> None:
        self._inner = inner
        self._monitor = monitor

    def __getattr__(self, name: str) -> Any:  # pragma: no cover — passthrough
        return getattr(self._inner, name)

    def create(self, **kwargs: Any) -> Any:
        t0 = time.monotonic()
        try:
            response = self._inner.create(**kwargs)
        except Exception as exc:  # noqa: BLE001
            elapsed = time.monotonic() - t0
            self._monitor.agent_call_err(
                agent=kwargs.get("model", "unknown"),
                elapsed=elapsed,
                error=f"{type(exc).__name__}: {exc}",
            )
            raise
        elapsed = time.monotonic() - t0
        usage = getattr(response, "usage", None)
        in_tokens = getattr(usage, "input_tokens", None)
        out_tokens = getattr(usage, "output_tokens", None)
        # Stash last-call telemetry on the monitor so the caller can pull it
        # into an AGENT_CALL_OK line. Counters are bumped by `agent_call_ok`
        # to avoid double-counting when the conftest fixture emits the event.
        self._monitor._last_call = {  # type: ignore[attr-defined]
            "elapsed": elapsed,
            "input_tokens": in_tokens,
            "output_tokens": out_tokens,
        }
        return response


class InstrumentedAnthropic:
    """Transparent wrapper around an Anthropic client."""

    def __init__(self, inner: Any, monitor: LiveMonitor) -> None:
        self._inner = inner
        self._monitor = monitor

    def __getattr__(self, name: str) -> Any:
        return getattr(self._inner, name)

    @property
    def messages(self) -> InstrumentedMessages:
        return InstrumentedMessages(self._inner.messages, self._monitor)
