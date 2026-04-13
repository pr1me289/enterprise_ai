from __future__ import annotations

import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
MOCK_DOCUMENTS = REPO_ROOT / "mock_documents"

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


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
