from __future__ import annotations

import os
import sys
import time
from pathlib import Path
from typing import Any

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
MOCK_DOCUMENTS = REPO_ROOT / "mock_documents"

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


# ---------------------------------------------------------------------------
# Core path fixtures (pre-existing — retained for orchestration tests)
# ---------------------------------------------------------------------------


@pytest.fixture
def repo_root() -> Path:
    return REPO_ROOT


@pytest.fixture
def mock_documents_dir() -> Path:
    return MOCK_DOCUMENTS


@pytest.fixture
def scenario_1_mock_documents_dir(repo_root: Path) -> Path:
    return repo_root / "scenarios_full_pipeline" / "scenario_1" / "source_mock_documents"


@pytest.fixture
def scenario_2_mock_documents_dir(repo_root: Path) -> Path:
    return repo_root / "scenarios_full_pipeline" / "scenario_2" / "source_mock_documents"


# ---------------------------------------------------------------------------
# API-tests gating
# ---------------------------------------------------------------------------


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    """Auto-skip ``@pytest.mark.api`` tests unless ``-m api`` was passed."""
    marker_expr = config.getoption("-m", default="") or ""
    if "api" in marker_expr:
        if not os.environ.get("ANTHROPIC_API_KEY"):
            _load_dotenv_if_available()
        if not os.environ.get("ANTHROPIC_API_KEY"):
            skip = pytest.mark.skip(reason="ANTHROPIC_API_KEY not set — cannot run @pytest.mark.api tests")
            for item in items:
                if "api" in item.keywords:
                    item.add_marker(skip)
        return

    skip = pytest.mark.skip(reason="API test — run with `pytest -m api` and ANTHROPIC_API_KEY set")
    for item in items:
        if "api" in item.keywords:
            item.add_marker(skip)


def _load_dotenv_if_available() -> None:
    try:
        from dotenv import load_dotenv  # noqa: WPS433
    except ImportError:
        return
    load_dotenv(REPO_ROOT / ".env")


# ---------------------------------------------------------------------------
# Bundle loaders
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def scenario_1_bundles() -> dict[str, dict[str, Any]]:
    from tests.support.bundle_builder import build_bundles

    return build_bundles("scenario_1")


@pytest.fixture(scope="session")
def scenario_2_bundles() -> dict[str, dict[str, Any]]:
    from tests.support.bundle_builder import build_bundles

    return build_bundles("scenario_2")


# ---------------------------------------------------------------------------
# Live monitor — wired at pytest_configure so hooks and fixtures share one
# ---------------------------------------------------------------------------


def pytest_configure(config: pytest.Config) -> None:
    from tests.support.live_monitor import LiveMonitor

    if not hasattr(config, "_live_monitor"):
        config._live_monitor = LiveMonitor()  # type: ignore[attr-defined]


@pytest.fixture(scope="session")
def live_monitor(pytestconfig: pytest.Config):
    """Session-scoped event monitor shared across tests and pytest hooks."""
    return pytestconfig._live_monitor  # type: ignore[attr-defined]


_ALLOWED_LIVE_MODEL_PREFIXES: tuple[str, ...] = ("claude-haiku",)
_DEFAULT_MAX_LIVE_CALLS = 50


def _enforce_cost_guard() -> None:
    """Reject non-Haiku live-API runs unless ``ALLOW_NON_HAIKU=1`` is set.

    The full-pipeline tests fan out into five domain-agent calls per
    scenario. Accidentally running that on Sonnet or Opus would burn
    through budget quickly, so we pin to Haiku by default and require an
    explicit env opt-in to override.
    """
    override = os.environ.get("ALLOW_NON_HAIKU") in ("1", "true", "TRUE")
    model = os.environ.get("ANTHROPIC_MODEL", "").strip()
    if not model or override:
        return
    if any(model.startswith(prefix) for prefix in _ALLOWED_LIVE_MODEL_PREFIXES):
        return
    pytest.exit(
        f"Refusing to run @pytest.mark.api tests with ANTHROPIC_MODEL={model!r}. "
        f"Default is Haiku; set ALLOW_NON_HAIKU=1 to override.",
        returncode=2,
    )


@pytest.fixture(scope="session")
def anthropic_client(live_monitor):
    """A single Anthropic SDK client wrapped with the live-monitor interceptor.

    Every ``messages.create`` call is timed and token counts are recorded
    into the shared monitor. Tests never touch the client directly — they
    use ``run_llm_agent`` which threads it through the call layer.

    The session also enforces a Haiku-only default and a max-calls cap
    (override via ``ALLOW_NON_HAIKU=1`` / ``ANTHROPIC_MAX_CALLS=<N>``).
    """
    _load_dotenv_if_available()
    _enforce_cost_guard()
    from anthropic import Anthropic

    from tests.support.live_monitor import InstrumentedAnthropic

    cap_raw = os.environ.get("ANTHROPIC_MAX_CALLS")
    try:
        cap = int(cap_raw) if cap_raw else _DEFAULT_MAX_LIVE_CALLS
    except ValueError:
        cap = _DEFAULT_MAX_LIVE_CALLS

    instrumented = InstrumentedAnthropic(Anthropic(), live_monitor)
    return _CapCheckedClient(instrumented, cap)


class _CapCheckedClient:
    """Thin wrapper that raises once the per-session call cap is reached."""

    def __init__(self, inner: Any, cap: int) -> None:
        self._inner = inner
        self._cap = cap
        self._count = 0
        self.messages = _CapCheckedMessages(self, inner.messages)

    def _tick(self) -> None:
        self._count += 1
        if self._count > self._cap:
            raise RuntimeError(
                f"live-API call cap reached ({self._cap}); "
                f"set ANTHROPIC_MAX_CALLS to a higher value to proceed."
            )

    def __getattr__(self, name: str) -> Any:
        return getattr(self._inner, name)


class _CapCheckedMessages:
    def __init__(self, parent: _CapCheckedClient, inner: Any) -> None:
        self._parent = parent
        self._inner = inner

    def create(self, *args: Any, **kwargs: Any) -> Any:
        self._parent._tick()
        return self._inner.create(*args, **kwargs)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._inner, name)


@pytest.fixture
def run_llm_agent(anthropic_client, live_monitor, request):
    """Factory: invoke a domain agent against the real API via ``agents.llm_caller``.

    Emits ``AGENT_CALL_START`` before the call and ``AGENT_CALL_OK`` (or
    ``AGENT_CALL_ERR``) after, so the live console shows every agent
    invocation end-to-end.
    """
    from agents.llm_caller import _call_agent  # type: ignore[attr-defined]

    scenario = _scenario_from_markers(request.node.iter_markers())

    def _invoke(*, agent_name: str, bundle: dict[str, Any], pipeline_run_id: str) -> dict[str, Any]:
        live_monitor.agent_call_start(
            agent=agent_name,
            scenario=scenario,
            pipeline_run_id=pipeline_run_id,
        )
        if hasattr(live_monitor, "_last_call"):
            delattr(live_monitor, "_last_call")
        try:
            output = _call_agent(
                agent_name=agent_name,
                bundle=bundle,
                pipeline_run_id=pipeline_run_id,
                step_metadata={"step_id": _step_for_agent(agent_name), "pipeline_run_id": pipeline_run_id},
                client=anthropic_client,
            )
        except Exception as exc:  # pragma: no cover — defensive; _call_agent catches internally
            live_monitor.agent_call_err(
                agent=agent_name,
                elapsed=0.0,
                error=f"{type(exc).__name__}: {exc}",
            )
            raise
        last = getattr(live_monitor, "_last_call", {})
        live_monitor.agent_call_ok(
            agent=agent_name,
            elapsed=last.get("elapsed", 0.0),
            input_tokens=last.get("input_tokens"),
            output_tokens=last.get("output_tokens"),
            status=str(output.get("status") or output.get("overall_status") or "ok"),
        )
        return output

    return _invoke


def _step_for_agent(agent_name: str) -> str:
    return {
        "it_security_agent": "STEP-02",
        "legal_agent": "STEP-03",
        "procurement_agent": "STEP-04",
        "checklist_assembler": "STEP-05",
        "checkoff_agent": "STEP-06",
    }.get(agent_name, "UNKNOWN")


def _layer_from_markers(markers) -> str:
    names = {m.name for m in markers}
    for layer in ("layer_unit", "layer_handoff", "layer_acceptance", "full_pipeline"):
        if layer in names:
            return layer
    return "other"


def _scenario_from_markers(markers) -> str | None:
    names = {m.name for m in markers}
    if "scenario1" in names:
        return "scenario_1"
    if "scenario2" in names:
        return "scenario_2"
    return None


# ---------------------------------------------------------------------------
# Pytest hooks — session banner, per-test timing, session summary
# ---------------------------------------------------------------------------


def pytest_collection_finish(session: pytest.Session) -> None:
    api_items = [item for item in session.items if "api" in item.keywords]
    if not api_items:
        return
    _load_dotenv_if_available()
    monitor = session.config._live_monitor  # type: ignore[attr-defined]
    layers: set[str] = set()
    scenarios: set[str] = set()
    for item in api_items:
        layers.add(_layer_from_markers(item.iter_markers()))
        scen = _scenario_from_markers(item.iter_markers())
        if scen:
            scenarios.add(scen)
    monitor.session_start(
        model=os.environ.get("ANTHROPIC_MODEL", "<sdk default>"),
        api_key=os.environ.get("ANTHROPIC_API_KEY"),
        layers=tuple(sorted(layers)),
        scenarios=tuple(sorted(scenarios)),
        test_count=len(api_items),
    )


_TEST_START_TIMES: dict[str, float] = {}


def pytest_runtest_logstart(nodeid: str, location) -> None:
    _TEST_START_TIMES[nodeid] = time.monotonic()


def pytest_runtest_logreport(report: pytest.TestReport) -> None:
    # Fire once per test: either on call, or on setup if it was skipped.
    if not (report.when == "call" or (report.when == "setup" and report.skipped)):
        return
    if "api" not in report.keywords:
        return

    import _pytest.config as _pc

    config = getattr(_pc, "_current", None)
    # Preferred path: recover the monitor directly via the session.
    monitor = None
    if hasattr(report, "config"):
        monitor = getattr(report.config, "_live_monitor", None)  # type: ignore[attr-defined]
    if monitor is None:
        monitor = getattr(pytest, "_live_monitor", None)
    if monitor is None:
        # Fall back to the session config captured in pytest_configure.
        if config and hasattr(config, "_live_monitor"):
            monitor = config._live_monitor  # type: ignore[attr-defined]
    if monitor is None:
        return

    layer = "other"
    for candidate in ("layer_unit", "layer_handoff", "layer_acceptance", "full_pipeline"):
        if candidate in report.keywords:
            layer = candidate
            break
    duration = time.monotonic() - _TEST_START_TIMES.get(report.nodeid, time.monotonic())
    outcome = "skipped" if (report.when == "setup" and report.skipped) else report.outcome
    monitor.test_result(
        node_id=report.nodeid,
        layer=layer,
        outcome=outcome,
        duration=duration,
    )


@pytest.hookimpl(tryfirst=True)
def pytest_sessionstart(session: pytest.Session) -> None:
    """Stash the session's config on the monitor plugin for later hooks."""
    # Alias the monitor on the pytest module so report hooks (which don't
    # receive config) can reach it reliably.
    pytest._live_monitor = session.config._live_monitor  # type: ignore[attr-defined]


def pytest_sessionfinish(session: pytest.Session, exitstatus: int) -> None:
    monitor = getattr(session.config, "_live_monitor", None)
    if monitor is None:
        return
    monitor.session_end()
