"""Tampering tests: verify the harness assertions actually fire on violations.

Each test injects a known integrity violation into a mock pipeline artifact
(bundle trace or audit-entry list) and confirms the corresponding assertion
raises ``HarnessAssertionError`` with the expected message fragment.

These tests do NOT run the full pipeline; they construct the minimal inputs
required by each assertion function. They exist to prove the integrity
checks are not silently passing when violations are present.

Moved here from ``test_harness/test_tampering.py`` so pytest discovers them
natively. The original file used a ``SystemExit``-based harness; this
version uses ``pytest.raises``.
"""

from __future__ import annotations

import pytest

from orchestration.audit.schemas import AuditEntry
from orchestration.models.enums import AuditEventType

from test_harness.result_assertions import (
    HarnessAssertionError,
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


def test_forbidden_source_in_step03_fires() -> None:
    trace = _base_step03_trace()
    trace["source_provenance"].append(
        {"source_id": "PAM-001", "lane": "direct_structured", "chunk_count": 1}
    )
    fixture = _scoped_fixture("STEP-03")
    with pytest.raises(HarnessAssertionError, match="forbidden source 'PAM-001'"):
        assert_bundles([trace], fixture)


def test_missing_required_source_in_step03_fires() -> None:
    trace = _base_step03_trace()
    trace["source_provenance"] = [
        p for p in trace["source_provenance"] if p["source_id"] != "DPA-TM-001"
    ]
    fixture = _scoped_fixture("STEP-03")
    with pytest.raises(HarnessAssertionError, match="required source 'DPA-TM-001'"):
        assert_bundles([trace], fixture)


def test_missing_structured_field_fires() -> None:
    trace = _base_step03_trace()
    trace["structured_fields_keys"].remove("dpa_trigger_rows")
    fixture = _scoped_fixture("STEP-03")
    with pytest.raises(HarnessAssertionError, match="'dpa_trigger_rows' missing"):
        assert_bundles([trace], fixture)


def test_slack_primary_citable_fires() -> None:
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
    with pytest.raises(HarnessAssertionError, match="Slack chunk admitted as primary"):
        assert_bundles([trace], fixture)


def test_thread4_admitted_fires() -> None:
    # STEP-04 permits SLK-001, but T4 (Greenbrook Catering) must still be
    # excluded from OptiChain bundles. Isolate the thread4 rule so the
    # forbidden-source check does not fire first.
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
    with pytest.raises(HarnessAssertionError, match="Thread 4 chunk was admitted"):
        assert_bundles([trace], fixture)


def test_retrieval_lane_divergence_fires() -> None:
    entries = [
        _retrieval_audit_entry(
            request_id="R03-SQ-04",
            source="DPA-TM-001",  # expected lane: indexed_hybrid
            lane="direct_structured",
        )
    ]
    fixture = _scoped_fixture("STEP-03")
    with pytest.raises(HarnessAssertionError, match="expected 'indexed_hybrid'"):
        assert_retrieval_lanes(entries, fixture)


def test_forbidden_retrieval_in_step05_fires() -> None:
    entries = [
        _retrieval_audit_entry(
            request_id="R05-SQ-99",
            source="ISP-001",
            lane="indexed_hybrid",
        )
    ]
    fixture = _scoped_fixture("STEP-03")
    with pytest.raises(HarnessAssertionError, match="STEP-05 performed forbidden retrieval"):
        assert_no_retrieval_in_forbidden_steps(entries, fixture)


def test_escalation_required_admissibility_fires() -> None:
    trace = _base_step03_trace()
    trace["admissibility_status"] = "ESCALATION_REQUIRED"
    fixture = _scoped_fixture("STEP-03")
    with pytest.raises(HarnessAssertionError, match="ESCALATION_REQUIRED"):
        assert_bundles([trace], fixture)
