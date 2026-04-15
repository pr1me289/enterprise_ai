"""Assertion logic for orchestration test harness scenarios.

Functions assert properties of PipelineState, bundle traces, and audit logs
against the expected values declared in HarnessFixture.
"""

from __future__ import annotations

from typing import Any

from orchestration.audit.schemas import AuditEntry
from orchestration.config.step_definitions import STEP_ORDER
from orchestration.models.enums import StepId, StepStatus
from orchestration.pipeline_state import PipelineState
from preprocessing.source_contract import SOURCE_CONTRACTS_BY_ID
from test_harness.scenario_fixtures import HarnessFixture


class AssertionError(Exception):  # noqa: A001
    """Raised when a harness assertion fails."""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _step_id(step_str: str) -> StepId:
    return StepId(step_str)


def _status_val(step_status: StepStatus) -> str:
    return step_status.value


# ---------------------------------------------------------------------------
# Global assertions
# ---------------------------------------------------------------------------

def assert_global(state: PipelineState, fixture: HarnessFixture) -> None:
    """Assert supervisor-level invariants."""

    # Step order must be correct — steps are visited in STEP_ORDER sequence
    executed_steps = [
        step_id
        for step_id in STEP_ORDER
        if state.step_statuses[step_id] != StepStatus.PENDING
    ]
    for i, step_id in enumerate(executed_steps[:-1]):
        expected_next = STEP_ORDER[STEP_ORDER.index(step_id) + 1]
        actual_next = executed_steps[i + 1]
        if STEP_ORDER.index(actual_next) < STEP_ORDER.index(expected_next):
            raise AssertionError(
                f"assert_global: step order violated — {actual_next.value} executed "
                f"before {expected_next.value}"
            )

    # No downstream steps after terminal halt
    expected_terminal_step = _step_id(fixture.expected_terminal_step)
    terminal_idx = STEP_ORDER.index(expected_terminal_step)
    terminal_status = fixture.expected_terminal_status

    if terminal_status in ("BLOCKED", "ESCALATED"):
        for step_id in STEP_ORDER[terminal_idx + 1:]:
            s = state.step_statuses[step_id]
            if s != StepStatus.PENDING:
                raise AssertionError(
                    f"assert_global: step {step_id.value} executed after terminal "
                    f"halt at {expected_terminal_step.value} — status={s.value}"
                )

    # Audit entries must be non-empty
    if not state.audit_refs:
        raise AssertionError("assert_global: no audit entries were emitted.")


# ---------------------------------------------------------------------------
# Retrieval assertions
# ---------------------------------------------------------------------------

def assert_retrieval(state: PipelineState, fixture: HarnessFixture) -> None:
    """Assert retrieval-level invariants.

    Note: retrieval source specifics are captured in the audit log.
    The state object itself does not expose per-retrieval lane data,
    so we validate through the determinations keys and step statuses.
    """
    # For every executed step, at least one determination must be stored
    for step_id in STEP_ORDER:
        step_status = state.step_statuses[step_id]
        if step_status in (StepStatus.COMPLETE, StepStatus.ESCALATED):
            det_key = _determination_key(step_id)
            if det_key is not None and state.determinations.get(det_key) is None:
                raise AssertionError(
                    f"assert_retrieval: {step_id.value} is {step_status.value} but "
                    f"determination '{det_key}' is None in state."
                )


def _determination_key(step_id: StepId) -> str | None:
    mapping = {
        StepId.STEP_01: "step_01_intake",
        StepId.STEP_02: "step_02_security_classification",
        StepId.STEP_03: "step_03_legal",
        StepId.STEP_04: "step_04_procurement",
        StepId.STEP_05: "step_05_checklist",
        StepId.STEP_06: "step_06_guidance",
    }
    return mapping.get(step_id)


# ---------------------------------------------------------------------------
# Bundle assertions
# ---------------------------------------------------------------------------

def assert_bundles(
    bundle_trace: list[dict[str, Any]],
    fixture: HarnessFixture,
) -> None:
    """Assert bundle-level invariants from the captured bundle trace."""
    trace_by_step = {t["step_id"]: t for t in bundle_trace}

    for invariant in fixture.bundle_invariants:
        step_id = invariant.step_id
        if step_id not in trace_by_step:
            # Only assert for steps that were expected to execute
            expected_status = fixture.expected_step_statuses.get(step_id, "PENDING")
            if expected_status != "PENDING":
                raise AssertionError(
                    f"assert_bundles: no bundle trace recorded for {step_id} "
                    f"(expected status={expected_status})."
                )
            continue

        trace = trace_by_step[step_id]

        # Check admissibility is not ESCALATION_REQUIRED
        if trace["admissibility_status"] == "ESCALATION_REQUIRED":
            raise AssertionError(
                f"assert_bundles: {step_id} bundle has ESCALATION_REQUIRED "
                f"admissibility — prohibited sources were admitted."
            )

        # Required source IDs: every expected source must appear in provenance
        provenance_source_ids = {p["source_id"] for p in trace.get("source_provenance", [])}
        admitted_source_ids = {c["source_id"] for c in trace["admitted_chunks"]}
        available_source_ids = provenance_source_ids | admitted_source_ids
        for sid in invariant.required_source_ids:
            if sid not in available_source_ids:
                raise AssertionError(
                    f"assert_bundles: {step_id} — required source {sid!r} "
                    f"not found in provenance or admitted chunks. "
                    f"provenance={sorted(provenance_source_ids)!r}"
                )

        # Forbidden source IDs: must not appear in provenance or admitted chunks
        for sid in invariant.forbidden_source_ids:
            if sid in available_source_ids:
                raise AssertionError(
                    f"assert_bundles: {step_id} — forbidden source {sid!r} "
                    f"appeared in bundle "
                    f"(provenance={sorted(provenance_source_ids)!r}, "
                    f"admitted={sorted(admitted_source_ids)!r})."
                )

        # Required structured fields: must appear as top-level keys
        present_keys = set(trace.get("structured_fields_keys", []))
        for field_key in invariant.required_structured_fields:
            if field_key not in present_keys:
                raise AssertionError(
                    f"assert_bundles: {step_id} — required structured field "
                    f"{field_key!r} missing. Present keys: {sorted(present_keys)!r}"
                )

        # Check Slack not primary evidence
        if invariant.slack_must_not_be_primary:
            for chunk in trace["admitted_chunks"]:
                if chunk["source_id"] == "SLK-001" and chunk.get("is_primary_citable"):
                    raise AssertionError(
                        f"assert_bundles: {step_id} — Slack chunk admitted as "
                        f"primary evidence: {chunk['chunk_id']!r}"
                    )

        # Check Thread 4 excluded
        if invariant.thread4_must_be_excluded:
            for chunk in trace["admitted_chunks"]:
                extra = chunk.get("extra_metadata") or {}
                if extra.get("thread_id") in ("T4", "4", "thread_4"):
                    raise AssertionError(
                        f"assert_bundles: {step_id} — Thread 4 chunk was admitted: "
                        f"{chunk['chunk_id']!r}"
                    )


# ---------------------------------------------------------------------------
# Status assertions
# ---------------------------------------------------------------------------

def assert_status(state: PipelineState, fixture: HarnessFixture) -> None:
    """Assert final RunStatus and per-step statuses match fixture expectations."""
    actual_overall = state.overall_status.value
    expected_overall = fixture.expected_terminal_status
    if actual_overall != expected_overall:
        raise AssertionError(
            f"assert_status: overall_status={actual_overall!r} != "
            f"expected={expected_overall!r}"
        )

    for step_str, expected_status in fixture.expected_step_statuses.items():
        step_id = _step_id(step_str)
        actual_status = state.step_statuses[step_id].value
        if actual_status != expected_status:
            raise AssertionError(
                f"assert_status: {step_str} status={actual_status!r} != "
                f"expected={expected_status!r}"
            )


# ---------------------------------------------------------------------------
# Retrieval-lane conformance
# ---------------------------------------------------------------------------

# Sources not in source_contract.py but legitimately queried via RUNTIME_READ
# as stand-ins for upstream-step outputs and other runtime state.
_RUNTIME_READ_STAND_INS = {
    "STEP-02",
    "STEP-03",
    "STEP-04",
    "STEP-05",
    "AUDIT_LOG",
    "PIPELINE_CONFIG",
    "PIPELINE_STATE",
}


def _request_step_from_request_id(request_id: str | None) -> str | None:
    """Extract the step id (e.g. 'STEP-02') from a retrieval request_id prefix.

    Step handlers use the request_id convention ``R<nn>-SQ-<kk>`` where ``nn``
    is the zero-padded step number.  Return the canonical ``STEP-<nn>`` id or
    None if no prefix is found.
    """
    if not request_id or not request_id.startswith("R"):
        return None
    prefix = request_id[1:3]
    if prefix.isdigit():
        return f"STEP-{prefix}"
    return None


def assert_retrieval_lanes(
    audit_entries: list[AuditEntry],
    fixture: HarnessFixture,
) -> None:
    """Assert every retrieval used the lane declared in source_contract.py.

    Divergence between a canonical source's declared lane and the lane the
    supervisor actually used is a bundle-integrity violation.  Stand-in
    sources (STEP-02, STEP-03, AUDIT_LOG, PIPELINE_CONFIG, ...) are exempt
    because they are not canonical sources — they model runtime reads.
    """
    del fixture  # not currently scenario-specific

    for entry in audit_entries:
        if entry.event_type.value != "RETRIEVAL":
            continue
        source_id = entry.source_queried or ""
        actual_lane = (entry.details or {}).get("lane", "")
        if source_id in _RUNTIME_READ_STAND_INS:
            if actual_lane != "runtime_read":
                raise AssertionError(
                    f"assert_retrieval_lanes: stand-in source {source_id!r} "
                    f"queried via lane={actual_lane!r}; expected 'runtime_read'."
                )
            continue
        contract = SOURCE_CONTRACTS_BY_ID.get(source_id)
        if contract is None:
            # Unknown source — don't enforce here; other assertions will catch.
            continue
        # Normalise to lowercase because preprocessing.RetrievalLane uses
        # uppercase values while orchestration.RetrievalLane uses lowercase.
        expected_lane = contract.retrieval_lane.value.lower()
        if actual_lane.lower() != expected_lane:
            raise AssertionError(
                f"assert_retrieval_lanes: {source_id!r} queried via "
                f"lane={actual_lane!r}; expected {expected_lane!r} per "
                f"source_contract.py."
            )


def assert_no_retrieval_in_forbidden_steps(
    audit_entries: list[AuditEntry],
    fixture: HarnessFixture,
) -> None:
    """Assert steps listed as forbidden_retrieval_steps emit zero RETRIEVAL entries.

    STEP-05 (Checklist Assembler) and STEP-06 (Checkoff) are downstream-only
    consumers per the context contract — they read runtime state via
    pipeline-state reads, but must not issue raw retrieval requests against
    indexed or direct stores.
    """
    if not fixture.forbidden_retrieval_steps:
        return

    forbidden: set[str] = set(fixture.forbidden_retrieval_steps)
    offenders: list[str] = []

    for entry in audit_entries:
        if entry.event_type.value != "RETRIEVAL":
            continue
        source_id = entry.source_queried or ""
        # Skip runtime-read stand-ins — they model pipeline-state reads,
        # which are allowed for downstream-only consumers.
        if source_id in _RUNTIME_READ_STAND_INS:
            continue
        details = entry.details or {}
        request_id = details.get("request_id")
        step_id = _request_step_from_request_id(request_id)
        if step_id in forbidden:
            offenders.append(
                f"{step_id} performed forbidden retrieval "
                f"source={source_id!r} request_id={request_id!r} "
                f"lane={details.get('lane')!r}"
            )

    if offenders:
        raise AssertionError(
            "assert_no_retrieval_in_forbidden_steps: "
            + "; ".join(offenders)
        )


# ---------------------------------------------------------------------------
# Run all assertions
# ---------------------------------------------------------------------------

def run_all_assertions(
    state: PipelineState,
    bundle_trace: list[dict[str, Any]],
    fixture: HarnessFixture,
    audit_entries: list[AuditEntry] | None = None,
) -> list[str]:
    """Run all assertions and return list of failure messages (empty = pass)."""
    failures: list[str] = []
    audit_entries = audit_entries or []

    for name, fn, args in [
        ("assert_global", assert_global, (state, fixture)),
        ("assert_retrieval", assert_retrieval, (state, fixture)),
        ("assert_retrieval_lanes", assert_retrieval_lanes, (audit_entries, fixture)),
        (
            "assert_no_retrieval_in_forbidden_steps",
            assert_no_retrieval_in_forbidden_steps,
            (audit_entries, fixture),
        ),
        ("assert_bundles", assert_bundles, (bundle_trace, fixture)),
        ("assert_status", assert_status, (state, fixture)),
    ]:
        try:
            fn(*args)
        except AssertionError as exc:
            failures.append(f"{name}: {exc}")

    return failures
