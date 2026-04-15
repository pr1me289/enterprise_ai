from __future__ import annotations

import os
import sys
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
    return repo_root / "scenario_1_mock_documents"


@pytest.fixture
def scenario_2_mock_documents_dir(repo_root: Path) -> Path:
    return repo_root / "scenario_2_mock_documents"


# ---------------------------------------------------------------------------
# API-tests gating
# ---------------------------------------------------------------------------


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    """Auto-skip ``@pytest.mark.api`` tests unless ``-m api`` was passed.

    The default pytest behavior runs everything marked — we want the opposite:
    API tests are *opt-in* because they cost money and require a key. The
    convention: skip any test carrying the ``api`` marker unless the user
    explicitly asked for it via ``-m`` containing ``api``.
    """
    marker_expr = config.getoption("-m", default="") or ""
    if "api" in marker_expr:
        # User asked for api tests explicitly — verify the key is present.
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
# Shared LLM-testing fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def scenario_1_bundles() -> dict[str, dict[str, Any]]:
    from tests.support.bundle_builder import build_bundles

    return build_bundles("scenario_1")


@pytest.fixture(scope="session")
def scenario_2_bundles() -> dict[str, dict[str, Any]]:
    from tests.support.bundle_builder import build_bundles

    return build_bundles("scenario_2")


@pytest.fixture(scope="session")
def anthropic_client():
    """A single Anthropic SDK client reused across every API test.

    Cuts socket churn and per-test construction cost. Tests never touch the
    client directly — they use ``run_llm_agent`` which threads it into the
    call layer.
    """
    _load_dotenv_if_available()
    from anthropic import Anthropic

    return Anthropic()


@pytest.fixture
def run_llm_agent(anthropic_client):
    """Factory: invoke a domain agent against the real API via ``agents.llm_caller``.

    Uses the internal ``_call_agent`` helper so we can inject a shared client,
    avoid per-test ``Anthropic()`` construction, and still load the spec file
    from disk — identical semantics to the five public ``call_*`` functions
    but with the shared client threaded in.
    """
    from agents.llm_caller import _call_agent  # type: ignore[attr-defined]

    def _invoke(*, agent_name: str, bundle: dict[str, Any], pipeline_run_id: str) -> dict[str, Any]:
        return _call_agent(
            agent_name=agent_name,
            bundle=bundle,
            pipeline_run_id=pipeline_run_id,
            step_metadata={"step_id": _step_for_agent(agent_name), "pipeline_run_id": pipeline_run_id},
            client=anthropic_client,
        )

    return _invoke


def _step_for_agent(agent_name: str) -> str:
    mapping = {
        "it_security_agent": "STEP-02",
        "legal_agent": "STEP-03",
        "procurement_agent": "STEP-04",
        "checklist_assembler": "STEP-05",
        "checkoff_agent": "STEP-06",
    }
    return mapping.get(agent_name, "UNKNOWN")
