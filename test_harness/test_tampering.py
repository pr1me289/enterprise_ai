"""Tampering tests: each test injects a known integrity violation into a
mock pipeline artifact (bundle trace or audit-entry list) and confirms the
corresponding assertion raises.

These tests do NOT run the full pipeline; they construct the minimal inputs
required by each assertion function.  They exist to prove that the integrity
checks are not silently passing when violations are present.

Run via:
    uv run python test_harness/test_tampering.py
"""

from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO_ROOT / "src"))
sys.path.insert(0, str(_REPO_ROOT))

from orchestration.audit.schemas import AuditEntry
from orchestration.models.enums import AuditEventType

from test_harness.result_assertions import (
    AssertionError as HarnessAssertionError,
    assert_bundles,
    assert_no_retrieval_in_forbidden_steps,
    assert_retrieval_lanes,
)
from test_harness.scenario_fixtures import BundleInvariant, HarnessFixture, get_fixture


def _scoped_fixture(step_id: str, scenario: str = "scenario_1_complete") -> HarnessFixture:
    """Return a fixture narrowed to a single step's invariants only."""
    base = get_fixture(scenario)
    invariants = tuple(i for i in base.bundle_invariants if i.step_id == step_id)
    return HarnessFixture(
        scenario_name=f"scoped_{base.scenario_name}_{step_id}",
        description=f"Scoped to {step_id} invariants only.",
        questionnaire_path_key=base.questionnaire_path_key,
        questionnaire_overrides=base.questionnaire_overrides,
        expected_terminal_status=base.expected_terminal_status,
        expected_terminal_step=base.expected_terminal_step,
        expected_step_statuses={step_id: "COMPLETE"},
        bundle_invariants=invariants,
        agent_signals=base.agent_signals,
        forbidden_retrieval_steps=base.forbidden_retrieval_steps,
    )


def _expect_fail(label: str, fn, *, contains: str) -> None:
    try:
        fn()
    except HarnessAssertionError as exc:
        msg = str(exc)
        if contains not in msg:
            raise SystemExit(
                f"[FAIL] {label}: assertion fired but message missing substring "
                f"{contains!r}; got {msg!r}"
            ) from None
        print(f"[OK]   {label}: caught -> {msg}")
        return
    raise SystemExit(f"[FAIL] {label}: expected assertion did not fire")


def _base_step03_trace() -> dict:
    """Minimal STEP-03 trace that satisfies all invariants."""
    return {
        "step_id": "STEP-03",
        "admissibility_status": "ADMISSIBLE",
        "admitted_count": 0,
        "excluded_count": 0,
        "admitted_chunks": [],
        "excluded_chunks": [],
        "structured_fields_keys": [
            "security_output",
            "questionnaire",
            "dpa_trigger_rows",
            "nda_clause_chunks",
            "bundle_meta",
            "source_ids",
        ],
        "source_provenance": [
            {"source_id": "VQ-OC-001", "lane": "direct_structured", "chunk_count": 0},
            {"source_id": "DPA-TM-001", "lane": "direct_structured", "chunk_count": 1},
            {"source_id": "ISP-001", "lane": "indexed_hybrid", "chunk_count": 0},
            {"source_id": "STEP-02", "lane": "runtime_read", "chunk_count": 3},
        ],
    }




def _retrieval_audit_entry(
    *,
    request_id: str,
    source: str,
    lane: str,
) -> AuditEntry:
    return AuditEntry(
        entry_id=f"audit_{request_id}",
        pipeline_run_id="run_tampering",
        agent_id="supervisor",
        event_type=AuditEventType.RETRIEVAL,
        timestamp="2026-04-14T00:00:00Z",
        source_queried=source,
        chunks_retrieved=[],
        details={
            "request_id": request_id,
            "lane": lane,
            "admitted_count": 0,
            "excluded_count": 0,
        },
    )


# --------------------------------------------------------------------------
# Tampering scenario 1: prohibited source appears in STEP-03 provenance
# --------------------------------------------------------------------------
def test_forbidden_source_in_step03_fires() -> None:
    trace = _base_step03_trace()
    # STEP-03 forbids PAM-001 and SLK-001 — inject PAM-001.
    trace["source_provenance"].append(
        {"source_id": "PAM-001", "lane": "direct_structured", "chunk_count": 1}
    )
    fixture = _scoped_fixture("STEP-03")
    _expect_fail(
        "forbidden_source_in_step03",
        lambda: assert_bundles([trace], fixture),
        contains="forbidden source 'PAM-001'",
    )


# --------------------------------------------------------------------------
# Tampering scenario 2: required source missing from STEP-03
# --------------------------------------------------------------------------
def test_missing_required_source_in_step03_fires() -> None:
    trace = _base_step03_trace()
    # Remove the DPA-TM-001 required source.
    trace["source_provenance"] = [
        p for p in trace["source_provenance"] if p["source_id"] != "DPA-TM-001"
    ]
    fixture = _scoped_fixture("STEP-03")
    _expect_fail(
        "missing_required_source_in_step03",
        lambda: assert_bundles([trace], fixture),
        contains="required source 'DPA-TM-001'",
    )


# --------------------------------------------------------------------------
# Tampering scenario 3: required structured field missing from STEP-03
# --------------------------------------------------------------------------
def test_missing_structured_field_fires() -> None:
    trace = _base_step03_trace()
    trace["structured_fields_keys"].remove("dpa_trigger_rows")
    fixture = _scoped_fixture("STEP-03")
    _expect_fail(
        "missing_structured_field_in_step03",
        lambda: assert_bundles([trace], fixture),
        contains="'dpa_trigger_rows' missing",
    )


# --------------------------------------------------------------------------
# Tampering scenario 4: Slack admitted as primary evidence
# --------------------------------------------------------------------------
def test_slack_primary_citable_fires() -> None:
    # Use STEP-04, where SLK-001 is allowed but must never be primary-citable.
    trace = {
        "step_id": "STEP-04",
        "admissibility_status": "ADMISSIBLE",
        "admitted_count": 1,
        "excluded_count": 0,
        "admitted_chunks": [
            {
                "source_id": "SLK-001",
                "chunk_id": "SLK-001__T1_msg1",
                "authority_tier": 3,
                "retrieval_lane": "indexed_hybrid",
                "is_primary_citable": True,
                "citation_label": "Slack T1",
                "extra_metadata": {"thread_id": "T1"},
            }
        ],
        "excluded_chunks": [],
        "structured_fields_keys": [
            "it_security_output",
            "legal_output",
            "questionnaire",
            "approval_path_matrix_rows",
            "bundle_meta",
            "source_ids",
        ],
        "source_provenance": [
            {"source_id": "VQ-OC-001", "lane": "direct_structured", "chunk_count": 0},
            {"source_id": "PAM-001", "lane": "direct_structured", "chunk_count": 1},
            {"source_id": "SLK-001", "lane": "indexed_hybrid", "chunk_count": 1},
            {"source_id": "STEP-02", "lane": "runtime_read", "chunk_count": 3},
            {"source_id": "STEP-03", "lane": "runtime_read", "chunk_count": 3},
        ],
    }
    fixture = _scoped_fixture("STEP-04")
    _expect_fail(
        "slack_primary_citable",
        lambda: assert_bundles([trace], fixture),
        contains="Slack chunk admitted as primary",
    )


# --------------------------------------------------------------------------
# Tampering scenario 5: Thread 4 admitted in a bundle where SLK is allowed
# --------------------------------------------------------------------------
def test_thread4_admitted_fires() -> None:
    # STEP-04 permits SLK-001, but T4 (Greenbrook Catering) must still be
    # excluded from OptiChain bundles.  Build a focused fixture whose only
    # invariant tests the thread4 rule so we reach that check rather than
    # a forbidden-source check.
    custom_invariant = BundleInvariant(
        step_id="STEP-04",
        required_source_ids=(),
        required_structured_fields=(),
        forbidden_source_ids=(),
        slack_must_not_be_primary=True,
        thread4_must_be_excluded=True,
    )
    fixture = HarnessFixture(
        scenario_name="tampering_thread4",
        description="Custom fixture isolating the thread4 exclusion rule at STEP-04.",
        questionnaire_path_key="scenario_1",
        questionnaire_overrides={},
        expected_terminal_status="COMPLETE",
        expected_terminal_step="STEP-04",
        expected_step_statuses={"STEP-04": "COMPLETE"},
        bundle_invariants=(custom_invariant,),
    )
    trace = {
        "step_id": "STEP-04",
        "admissibility_status": "ADMISSIBLE",
        "admitted_count": 1,
        "excluded_count": 0,
        "admitted_chunks": [
            {
                "source_id": "SLK-001",
                "chunk_id": "SLK-001__T4_msg1",
                "authority_tier": 3,
                "retrieval_lane": "indexed_hybrid",
                "is_primary_citable": False,
                "citation_label": "Slack T4",
                "extra_metadata": {"thread_id": "T4"},
            }
        ],
        "excluded_chunks": [],
        "structured_fields_keys": [
            "it_security_output",
            "legal_output",
            "questionnaire",
            "approval_path_matrix_rows",
            "bundle_meta",
            "source_ids",
        ],
        "source_provenance": [
            {"source_id": "SLK-001", "lane": "indexed_hybrid", "chunk_count": 1},
        ],
    }
    _expect_fail(
        "thread4_admitted_in_step04",
        lambda: assert_bundles([trace], fixture),
        contains="Thread 4 chunk was admitted",
    )


# --------------------------------------------------------------------------
# Tampering scenario 6: retrieval lane divergence from source contract
# --------------------------------------------------------------------------
def test_retrieval_lane_divergence_fires() -> None:
    entries = [
        _retrieval_audit_entry(
            request_id="R03-SQ-04",
            source="DPA-TM-001",  # expected lane: indexed_hybrid
            lane="direct_structured",
        )
    ]
    fixture = _scoped_fixture("STEP-03")
    _expect_fail(
        "retrieval_lane_divergence",
        lambda: assert_retrieval_lanes(entries, fixture),
        contains="expected 'indexed_hybrid'",
    )


# --------------------------------------------------------------------------
# Tampering scenario 7: STEP-05 issues a forbidden raw retrieval
# --------------------------------------------------------------------------
def test_forbidden_retrieval_in_step05_fires() -> None:
    entries = [
        _retrieval_audit_entry(
            request_id="R05-SQ-99",
            source="ISP-001",
            lane="indexed_hybrid",
        )
    ]
    fixture = _scoped_fixture("STEP-03")
    _expect_fail(
        "forbidden_retrieval_in_step05",
        lambda: assert_no_retrieval_in_forbidden_steps(entries, fixture),
        contains="STEP-05 performed forbidden retrieval",
    )


# --------------------------------------------------------------------------
# Tampering scenario 8: bundle admissibility_status = ESCALATION_REQUIRED
# --------------------------------------------------------------------------
def test_escalation_required_admissibility_fires() -> None:
    trace = _base_step03_trace()
    trace["admissibility_status"] = "ESCALATION_REQUIRED"
    fixture = _scoped_fixture("STEP-03")
    _expect_fail(
        "escalation_required_admissibility",
        lambda: assert_bundles([trace], fixture),
        contains="ESCALATION_REQUIRED",
    )


def main() -> int:
    tests = [
        test_forbidden_source_in_step03_fires,
        test_missing_required_source_in_step03_fires,
        test_missing_structured_field_fires,
        test_slack_primary_citable_fires,
        test_thread4_admitted_fires,
        test_retrieval_lane_divergence_fires,
        test_forbidden_retrieval_in_step05_fires,
        test_escalation_required_admissibility_fires,
    ]
    print(f"Running {len(tests)} tampering tests...")
    for t in tests:
        t()
    print(f"\nAll {len(tests)} tampering tests fired their expected assertions.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
