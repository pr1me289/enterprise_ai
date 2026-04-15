"""Shared helpers for Layer 3 acceptance-check tests.

The prompt's Layer-3 table names agent-specific acceptance checks (A-01..A-07)
drawn from the per-agent spec documents. These helpers let each acceptance
test express its pre-condition and its single invariant without boilerplate.
"""

from __future__ import annotations

from typing import Any, Iterable

import pytest


def _iter_citations(output: dict[str, Any]) -> Iterable[dict[str, Any]]:
    cites = output.get("policy_citations")
    if isinstance(cites, list):
        for c in cites:
            if isinstance(c, dict):
                yield c


@pytest.fixture
def assert_no_primary_tier3_citation():
    """A-04 (shared) — no PRIMARY citation may come from a Tier-3 source.

    We interpret "Tier-3 source_id" by convention: Slack exports and other
    operational artifacts are Tier 3. The enterprise policy sources ISP-001,
    DPA-TM-001, PAM-001 are Tier 1/2. The guard list below is the concrete
    set of Tier-3 source_ids surfaced in this repo's policy corpus.
    """
    TIER_3_SOURCE_IDS = {
        "SLACK-EXPORT-001",  # Slack #vendor-intake thread
    }

    def _check(output: dict[str, Any]) -> None:
        offenders = [
            c for c in _iter_citations(output)
            if c.get("citation_class") == "PRIMARY"
            and c.get("source_id") in TIER_3_SOURCE_IDS
        ]
        assert not offenders, (
            f"A-04 violated: PRIMARY citation from Tier-3 source(s) "
            f"{[c.get('source_id') for c in offenders]!r} present in output"
        )

    return _check


@pytest.fixture
def report_acceptance(live_monitor):
    """Return a helper that emits an ``ACCEPTANCE`` verdict and asserts.

    Using this helper instead of a bare ``assert`` causes each A-xx result
    to surface in the live console stream *and* be tallied in the session
    summary — you can see at a glance which acceptance checks are passing
    on the current run.
    """

    def _report(
        *,
        check_id: str,
        agent: str,
        passed: bool,
        detail: str = "",
    ) -> None:
        live_monitor.acceptance(
            check_id=check_id,
            agent=agent,
            passed=passed,
            detail=detail,
        )
        if not passed:
            raise AssertionError(
                f"acceptance check {check_id} violated for {agent}: {detail}"
            )

    return _report
