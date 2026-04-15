"""Helpers for Layer 2 cross-agent handoff tests.

The Layer 2 suite is more expensive than Layer 1 — each test runs between
two and five real API calls. The helpers below keep the tests focused on
the invariant under test, not on bundle-splicing mechanics.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any

import pytest


@pytest.fixture
def splice_upstream():
    """Return a helper that rewrites an upstream subtree on a bundle copy."""

    def _splice(bundle: dict[str, Any], *, path: str, value: Any) -> dict[str, Any]:
        out = deepcopy(bundle)
        segments = path.split(".")
        cursor: Any = out
        for seg in segments[:-1]:
            if not isinstance(cursor, dict):
                return out
            cursor = cursor.setdefault(seg, {})
        if isinstance(cursor, dict):
            cursor[segments[-1]] = value
        return out

    return _splice


@pytest.fixture
def report_handoff(live_monitor):
    """Return a helper that emits a ``HANDOFF`` verdict into the monitor.

    Tests should call ``report_handoff(invariant=..., upstream=..., downstream=...,
    passed=..., detail=...)`` at the point of their invariant check. The helper
    also raises ``AssertionError`` when ``passed`` is False so the test still
    fails as a normal pytest failure — the monitor event is purely an
    observability signal.
    """

    def _report(
        *,
        invariant: str,
        upstream: str,
        downstream: str,
        passed: bool,
        detail: str = "",
    ) -> None:
        live_monitor.handoff(
            invariant=invariant,
            upstream=upstream,
            downstream=downstream,
            passed=passed,
            detail=detail,
        )
        if not passed:
            raise AssertionError(
                f"handoff invariant {invariant!r} violated: {upstream}→{downstream}; {detail}"
            )

    return _report
