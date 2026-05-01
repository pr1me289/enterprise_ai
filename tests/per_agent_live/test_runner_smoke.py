"""Smoke tests for ``per_agent_test_env`` — use a stub client, no real API.

These tests verify the runner's invariants without consuming Anthropic
credits:
- bundle loader validates the (agent, scenario) match
- the record is written to disk BEFORE the evaluator runs
- the evaluator correctly flags valid and invalid outputs
- the CLI exits 0 on pass, 1 on fail, 2 on arg error
- one agent per invocation — no supervisor is imported
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import pytest

from per_agent_test_env import (
    SCENARIOS_BY_AGENT,
    VALID_AGENTS,
    VALID_SCENARIOS,
    bundle_loader,
    evaluators,
    run_agent_test,
)
from per_agent_test_env.bundle_loader import BundleError, load_bundle
from per_agent_test_env.cli import main as cli_main


REPO_ROOT = Path(__file__).resolve().parents[2]


# ---------------------------------------------------------------------------
# Stub client — mimics the Anthropic SDK's response shape with no network call
# ---------------------------------------------------------------------------


class _StubContentPart:
    def __init__(self, text: str) -> None:
        self.text = text


class _StubResponse:
    def __init__(self, text: str) -> None:
        self.content = [_StubContentPart(text)]


class _StubMessages:
    """Replays a prepared JSON payload on every ``.create`` call.

    Captures the last call's kwargs so tests can assert on model, system
    prompt, and user message shape without a real API call.
    """

    def __init__(self, payload: Any, *, raise_with: Exception | None = None) -> None:
        self._payload = payload
        self._raise_with = raise_with
        self.last_call: dict[str, Any] | None = None

    def create(self, **kwargs: Any) -> _StubResponse:
        self.last_call = kwargs
        if self._raise_with is not None:
            raise self._raise_with
        if isinstance(self._payload, str):
            return _StubResponse(self._payload)
        return _StubResponse(json.dumps(self._payload))


class _StubClient:
    def __init__(self, payload: Any, *, raise_with: Exception | None = None) -> None:
        self.messages = _StubMessages(payload, raise_with=raise_with)


# ---------------------------------------------------------------------------
# Canonical passing payloads per agent — constructed to satisfy the evaluator
# ---------------------------------------------------------------------------


_VALID_IT_SECURITY = {
    "integration_type_normalized": "EXPORT_ONLY",
    "integration_tier": "TIER_3",
    "data_classification": "UNREGULATED",
    "eu_personal_data_present": False,
    "fast_track_eligible": True,
    "fast_track_rationale": "Export-only, no EU personal data.",
    "security_followup_required": False,
    "nda_status_from_questionnaire": "EXECUTED",
    "required_security_actions": [],
    "policy_citations": [
        {"source_id": "ISP-001", "version": "4.2", "section_id": "12", "citation_class": "PRIMARY"},
        {"source_id": "ISP-001", "version": "4.2", "section_id": "17", "citation_class": "PRIMARY"},
    ],
    "status": "complete",
}

_VALID_LEGAL = {
    "dpa_required": False,
    "dpa_blocker": False,
    "nda_status": "EXECUTED",
    "nda_blocker": False,
    "trigger_rule_cited": [],
    "policy_citations": [
        {
            "source_id": "ISP-001",
            "version": "4.2",
            "section_id": "12.1.4",
            "citation_class": "PRIMARY",
        }
    ],
    "status": "complete",
}

_VALID_PROCUREMENT = {
    "approval_path": "STANDARD",
    "fast_track_eligible": False,
    "executive_approval_required": False,
    "required_approvals": [
        {"approver": "Security Lead", "domain": "security"},
        {"approver": "Procurement Manager", "domain": "procurement"},
    ],
    "estimated_timeline": "5 business days",
    "policy_citations": [
        {
            "source_id": "PAM-001",
            "version": "3.0",
            "chunk_id": "PAM-001__row_P-01",
            "row_id": "P-01",
            "approval_path_condition": "Class A vendor, deal_size > 100k → STANDARD path",
            "citation_class": "PRIMARY",
        }
    ],
    "status": "complete",
}

_VALID_ASSEMBLER = {
    "pipeline_run_id": "run_smoke_test",
    "vendor_name": "OptiChain",
    "overall_status": "COMPLETE",
    "data_classification": "UNREGULATED",
    "dpa_required": False,
    "dpa_blocker": False,
    "fast_track_eligible": True,
    "approval_path": "STANDARD",
    "required_approvals": [
        {
            "approver": "Security Lead",
            "domain": "security",
            "status": "pending",
            "blocker": False,
            "estimated_completion": "2026-04-20",
        }
    ],
    "blockers": [],
    "citations": [
        {
            "source_name": "IT Security Policy",
            "version": "4.2",
            "section": "12",
            "retrieval_timestamp": "2026-04-15T15:00:00Z",
            "agent_id": "it_security_agent",
        },
        {
            "source_name": "DPA Legal Trigger Matrix",
            "version": "2.1",
            "section": "row_1",
            "retrieval_timestamp": "2026-04-15T15:01:00Z",
            "agent_id": "legal_agent",
        },
        {
            "source_name": "Procurement Approval Matrix",
            "version": "3.0",
            "section": "4",
            "retrieval_timestamp": "2026-04-15T15:02:00Z",
            "agent_id": "procurement_agent",
        },
    ],
}

_VALID_CHECKOFF = {
    "status": "complete",
    "guidance_documents": [
        {
            "title": "Security approver briefing",
            "audience": "Security Lead",
            "body": "Proceed with standard onboarding.",
        }
    ],
    "required_approvers": [
        {"approver": "Security Lead", "domain": "security"}
    ],
}


_VALID_PAYLOADS: dict[str, dict[str, Any]] = {
    "it_security_agent": _VALID_IT_SECURITY,
    "legal_agent": _VALID_LEGAL,
    "procurement_agent": _VALID_PROCUREMENT,
    "checklist_assembler": _VALID_ASSEMBLER,
    "checkoff_agent": _VALID_CHECKOFF,
}


# ---------------------------------------------------------------------------
# Bundle loader
# ---------------------------------------------------------------------------


_AGENT_SCENARIO_PAIRS: tuple[tuple[str, str], ...] = tuple(
    (agent, scenario)
    for agent in VALID_AGENTS
    for scenario in SCENARIOS_BY_AGENT.get(agent, ())
)


@pytest.mark.parametrize(("agent", "scenario"), _AGENT_SCENARIO_PAIRS)
def test_load_bundle_all_pairs(agent: str, scenario: str) -> None:
    bundle, run_id, path = load_bundle(agent, scenario, repo_root=REPO_ROOT)
    assert isinstance(bundle, dict)
    assert isinstance(run_id, str)
    assert path.exists()


def test_load_bundle_rejects_unknown_agent() -> None:
    with pytest.raises(BundleError, match="unknown agent"):
        load_bundle("not_an_agent", "scenario_1", repo_root=REPO_ROOT)


def test_load_bundle_rejects_unknown_scenario() -> None:
    with pytest.raises(BundleError, match="unknown scenario"):
        load_bundle("it_security_agent", "scenario_9", repo_root=REPO_ROOT)


# ---------------------------------------------------------------------------
# Runner — record before evaluate
# ---------------------------------------------------------------------------


def test_runner_records_before_evaluate_on_pass(tmp_path: Path) -> None:
    client = _StubClient(_VALID_IT_SECURITY)
    result = run_agent_test(
        "it_security_agent",
        "scenario_1",
        repo_root=REPO_ROOT,
        recorded_responses_dir=tmp_path,
        client=client,
    )
    # A record file exists and contains the parsed output
    record_path = Path(result.recorded.recorded_file)
    assert record_path.exists(), "record must be written to disk"
    with record_path.open() as handle:
        record = json.load(handle)
    assert record["agent_name"] == "it_security_agent"
    assert record["scenario"] == "scenario_1"
    assert record["parsed_output"] == _VALID_IT_SECURITY
    assert record["raw_text"] == json.dumps(_VALID_IT_SECURITY)
    assert record["error"] is None
    assert result.passed, f"expected pass, got failures: {result.failures}"


def test_runner_records_even_on_api_error(tmp_path: Path) -> None:
    client = _StubClient(None, raise_with=RuntimeError("simulated API outage"))
    result = run_agent_test(
        "it_security_agent",
        "scenario_1",
        repo_root=REPO_ROOT,
        recorded_responses_dir=tmp_path,
        client=client,
    )
    record_path = Path(result.recorded.recorded_file)
    assert record_path.exists(), "record must be written even when the call fails"
    with record_path.open() as handle:
        record = json.load(handle)
    assert record["error"] is not None
    assert "simulated API outage" in record["error"]
    assert record["parsed_output"] is None
    assert not result.passed
    assert any("simulated API outage" in f for f in result.failures)


def test_runner_records_even_on_parse_error(tmp_path: Path) -> None:
    client = _StubClient("this is not JSON")
    result = run_agent_test(
        "legal_agent",
        "scenario_2",
        repo_root=REPO_ROOT,
        recorded_responses_dir=tmp_path,
        client=client,
    )
    record_path = Path(result.recorded.recorded_file)
    assert record_path.exists()
    with record_path.open() as handle:
        record = json.load(handle)
    assert record["raw_text"] == "this is not JSON"
    assert record["parsed_output"] is None
    assert "JSON parse failure" in (record["error"] or "")
    assert not result.passed


def test_runner_does_not_import_supervisor() -> None:
    # The orchestration supervisor module must not be loaded as a side
    # effect of running a per-agent isolated test. The test-harness's
    # mock_adapter also must not leak in.
    assert "orchestration.supervisor" not in sys.modules, (
        "per-agent runner must not import the Supervisor — it indicates "
        "pipeline-level coupling crept into an isolated run"
    )


def test_runner_passes_spec_as_system_prompt(tmp_path: Path) -> None:
    client = _StubClient(_VALID_LEGAL)
    run_agent_test(
        "legal_agent",
        "scenario_1",
        repo_root=REPO_ROOT,
        recorded_responses_dir=tmp_path,
        client=client,
    )
    last = client.messages.last_call
    assert last is not None
    # The spec file should be embedded in the system prompt
    spec_text = (REPO_ROOT / "agent_spec_docs" / "Legal_Agent_Spec.md").read_text(encoding="utf-8")
    assert spec_text.splitlines()[0] in last["system"]
    # The output instruction is also appended
    assert "Return a single valid JSON object" in last["system"]


def test_runner_serializes_bundle_into_user_message(tmp_path: Path) -> None:
    client = _StubClient(_VALID_IT_SECURITY)
    run_agent_test(
        "it_security_agent",
        "scenario_1",
        repo_root=REPO_ROOT,
        recorded_responses_dir=tmp_path,
        client=client,
    )
    last = client.messages.last_call
    assert last is not None
    user_msg = last["messages"][0]["content"]
    assert "evidence_bundle" in user_msg
    assert "step_metadata" in user_msg
    assert "isolated_per_agent_test" in user_msg


# ---------------------------------------------------------------------------
# Evaluator — failure cases
# ---------------------------------------------------------------------------


def test_evaluator_flags_missing_required_fields() -> None:
    report = evaluators.evaluate_recorded(
        agent_name="it_security_agent",
        scenario="scenario_1",
        parsed_output={"status": "complete"},  # missing almost everything
        error=None,
    )
    assert not report.passed
    # Expect at least the big-ticket missing fields
    joined = "\n".join(report.failures)
    assert "data_classification" in joined
    assert "policy_citations" in joined


def test_evaluator_flags_invalid_enum_values() -> None:
    bad = dict(_VALID_IT_SECURITY, data_classification="PARTIALLY_REGULATED")
    report = evaluators.evaluate_recorded(
        agent_name="it_security_agent",
        scenario="scenario_1",
        parsed_output=bad,
        error=None,
    )
    assert not report.passed
    assert any("data_classification" in f for f in report.failures)


def test_evaluator_flags_fast_track_inconsistency() -> None:
    bad = dict(_VALID_IT_SECURITY, data_classification="REGULATED", fast_track_eligible=True)
    report = evaluators.evaluate_recorded(
        agent_name="it_security_agent",
        scenario="scenario_1",
        parsed_output=bad,
        error=None,
    )
    assert not report.passed
    assert any("fast_track_eligible=true" in f.lower() or "fast_track_eligible" in f for f in report.failures)


def test_evaluator_flags_empty_policy_citations() -> None:
    bad = dict(_VALID_IT_SECURITY, policy_citations=[])
    report = evaluators.evaluate_recorded(
        agent_name="it_security_agent",
        scenario="scenario_1",
        parsed_output=bad,
        error=None,
    )
    assert not report.passed
    assert any("policy_citations" in f for f in report.failures)


def test_evaluator_flags_dpa_blocker_contradiction() -> None:
    bad = dict(_VALID_LEGAL, dpa_required=False, dpa_blocker=True)
    report = evaluators.evaluate_recorded(
        agent_name="legal_agent",
        scenario="scenario_1",
        parsed_output=bad,
        error=None,
    )
    assert not report.passed
    assert any("dpa_blocker" in f for f in report.failures)


def test_evaluator_flags_nda_blocker_contradiction() -> None:
    bad = dict(_VALID_LEGAL, nda_status="PENDING", nda_blocker=False)
    report = evaluators.evaluate_recorded(
        agent_name="legal_agent",
        scenario="scenario_2",
        parsed_output=bad,
        error=None,
    )
    assert not report.passed
    assert any("nda_blocker" in f for f in report.failures)


def test_evaluator_flags_fast_track_path_without_eligibility() -> None:
    bad = dict(_VALID_PROCUREMENT, fast_track_eligible=False, approval_path="FAST_TRACK")
    report = evaluators.evaluate_recorded(
        agent_name="procurement_agent",
        scenario="scenario_1",
        parsed_output=bad,
        error=None,
    )
    assert not report.passed
    assert any("FAST_TRACK" in f for f in report.failures)


def test_evaluator_flags_assembler_missing_citations() -> None:
    bad = dict(_VALID_ASSEMBLER)
    bad.pop("citations")
    report = evaluators.evaluate_recorded(
        agent_name="checklist_assembler",
        scenario="scenario_1",
        parsed_output=bad,
        error=None,
    )
    assert not report.passed
    assert any("citations" in f for f in report.failures)


def test_evaluator_flags_checkoff_missing_guidance() -> None:
    bad = {"status": "complete"}
    report = evaluators.evaluate_recorded(
        agent_name="checkoff_agent",
        scenario="scenario_1",
        parsed_output=bad,
        error=None,
    )
    assert not report.passed
    assert any("guidance" in f.lower() for f in report.failures)


def test_evaluator_soft_warns_on_unexpected_scenario_status() -> None:
    # it_security_agent scenario_2 is expected to be escalated — if the
    # model returns complete the evaluator should still pass the hard
    # checks (as long as the payload is valid) but emit a warning.
    payload = dict(_VALID_IT_SECURITY, data_classification="UNREGULATED", status="complete")
    report = evaluators.evaluate_recorded(
        agent_name="it_security_agent",
        scenario="scenario_2",
        parsed_output=payload,
        error=None,
    )
    assert report.passed, f"should pass hard checks; failures={report.failures}"
    assert any("scenario-expected" in w for w in report.warnings)


# ---------------------------------------------------------------------------
# Evaluator — proper ID-value checks (not just key presence)
# ---------------------------------------------------------------------------


def test_evaluator_flags_wrong_nda_section_id_value() -> None:
    # nda_blocker=true demands the ISP-001 §12.1.4 NDA clause specifically.
    # A citation with a different section_id value (e.g. "99") must surface
    # the warning even though the section_id KEY is present and non-empty —
    # this exercises the section→section_id drift fix and proves the check
    # is validating the *value*, not just the presence of the key.
    bad = dict(
        _VALID_LEGAL,
        nda_status="PENDING",
        nda_blocker=True,
        policy_citations=[
            {
                "source_id": "ISP-001",
                "version": "4.2",
                "section_id": "99",
                "citation_class": "PRIMARY",
            }
        ],
    )
    report = evaluators.evaluate_recorded(
        agent_name="legal_agent",
        scenario="scenario_2",
        parsed_output=bad,
        error=None,
    )
    assert any("12.1.4" in w for w in report.warnings), (
        f"expected a §12.1.4 warning when section_id value does not match; "
        f"warnings={report.warnings}"
    )


def test_evaluator_clears_nda_warning_with_correct_section_id_value() -> None:
    # The complementary case: when section_id VALUE starts with "12.1.4",
    # no §12.1.4 warning should fire — confirming the check reads section_id,
    # not the legacy "section" key.
    good = dict(
        _VALID_LEGAL,
        nda_status="PENDING",
        nda_blocker=True,
        policy_citations=[
            {
                "source_id": "ISP-001",
                "version": "4.2",
                "section_id": "12.1.4",
                "citation_class": "PRIMARY",
            }
        ],
    )
    report = evaluators.evaluate_recorded(
        agent_name="legal_agent",
        scenario="scenario_2",
        parsed_output=good,
        error=None,
    )
    assert not any("12.1.4" in w for w in report.warnings), (
        f"§12.1.4 warning should not fire when section_id value matches; "
        f"warnings={report.warnings}"
    )


def test_evaluator_flags_procurement_missing_citation_keys() -> None:
    # Procurement policy_citations entries must carry row_id,
    # approval_path_condition, and citation_class per Agent Spec §9/§11.
    # An entry missing row_id is a failure even if source_id and version
    # are present — i.e. the check verifies the *proper row_id value*
    # is emitted, not just a partial citation.
    bad = dict(
        _VALID_PROCUREMENT,
        policy_citations=[
            {"source_id": "PAM-001", "version": "3.0"}  # missing row_id, etc.
        ],
    )
    report = evaluators.evaluate_recorded(
        agent_name="procurement_agent",
        scenario="scenario_1",
        parsed_output=bad,
        error=None,
    )
    assert not report.passed
    joined = "\n".join(report.failures)
    assert "row_id" in joined
    assert "approval_path_condition" in joined
    assert "citation_class" in joined


def test_evaluator_flags_procurement_empty_row_id_value() -> None:
    # A row_id that is present but empty-string must fail the same way a
    # missing row_id does — the check validates the *value*, not just
    # the presence of the key.
    bad = dict(
        _VALID_PROCUREMENT,
        policy_citations=[
            {
                "source_id": "PAM-001",
                "version": "3.0",
                "row_id": "",
                "approval_path_condition": "Class A vendor, deal_size > 100k",
                "citation_class": "PRIMARY",
            }
        ],
    )
    report = evaluators.evaluate_recorded(
        agent_name="procurement_agent",
        scenario="scenario_1",
        parsed_output=bad,
        error=None,
    )
    assert not report.passed
    assert any("row_id" in f for f in report.failures)


def test_evaluator_flags_procurement_citing_out_of_lane_source() -> None:
    # Procurement's retrieval lane is PAM-001 and SLK-001 only — ISP-001
    # or DPA-TM-001 citations are a contract violation per Agent Spec §5/§11.
    bad = dict(
        _VALID_PROCUREMENT,
        policy_citations=[
            {
                "source_id": "ISP-001",
                "version": "4.2",
                "row_id": "P-01",
                "approval_path_condition": "Class A vendor",
                "citation_class": "PRIMARY",
            }
        ],
    )
    report = evaluators.evaluate_recorded(
        agent_name="procurement_agent",
        scenario="scenario_1",
        parsed_output=bad,
        error=None,
    )
    assert not report.passed
    assert any("ISP-001" in f and "outside permitted sources" in f for f in report.failures)


def test_evaluator_accepts_legal_dpa_tm_001_citation_with_row_id() -> None:
    # Per Legal Agent Spec §11: DPA-TM-001 entries in policy_citations are
    # row-indexed and carry source_id, version, row_id, trigger_condition,
    # citation_class — NOT section_id. This must pass the key-schema check.
    payload = dict(
        _VALID_LEGAL,
        dpa_required=True,
        dpa_blocker=True,
        status="escalated",
        trigger_rule_cited=[
            {
                "source_id": "DPA-TM-001",
                "version": "1.3",
                "row_id": "A-01",
                "trigger_condition": "EU/EEA data subjects processed on behalf of Lichen",
            }
        ],
        policy_citations=[
            {
                "source_id": "ISP-001",
                "version": "4.2",
                "chunk_id": "ISP-001__section_12",
                "section_id": "12.1.4",
                "citation_class": "PRIMARY",
            },
            {
                "source_id": "DPA-TM-001",
                "version": "1.3",
                "row_id": "A-01",
                "trigger_condition": "EU/EEA data subjects processed on behalf of Lichen",
                "citation_class": "PRIMARY",
            },
        ],
    )
    report = evaluators.evaluate_recorded(
        agent_name="legal_agent",
        scenario="scenario_2",
        parsed_output=payload,
        error=None,
    )
    assert report.passed, f"row-indexed DPA-TM-001 entry must pass; failures={report.failures}"


def test_evaluator_flags_legal_dpa_tm_001_missing_row_id() -> None:
    # A DPA-TM-001 entry lacking row_id must hard-fail per §11 — the
    # per-source-id schema requires row_id for row-indexed sources.
    bad = dict(
        _VALID_LEGAL,
        dpa_required=True,
        dpa_blocker=True,
        status="escalated",
        trigger_rule_cited=[
            {
                "source_id": "DPA-TM-001",
                "version": "1.3",
                "row_id": "A-01",
                "trigger_condition": "EU/EEA data subjects",
            }
        ],
        policy_citations=[
            {
                "source_id": "DPA-TM-001",
                "version": "1.3",
                # row_id intentionally missing
                "trigger_condition": "EU/EEA data subjects",
                "citation_class": "PRIMARY",
            }
        ],
    )
    report = evaluators.evaluate_recorded(
        agent_name="legal_agent",
        scenario="scenario_2",
        parsed_output=bad,
        error=None,
    )
    assert not report.passed
    assert any("DPA-TM-001" in f and "row_id" in f for f in report.failures), (
        f"expected per-source-id failure naming DPA-TM-001 and row_id; "
        f"failures={report.failures}"
    )


def test_evaluator_flags_legal_isp_001_missing_section_id() -> None:
    # The complementary case — ISP-001 entries are section-indexed and
    # must still fail when section_id is missing. This guards against a
    # regression where the per-source-id refactor accidentally relaxes
    # the ISP-001 contract.
    bad = dict(
        _VALID_LEGAL,
        policy_citations=[
            {
                "source_id": "ISP-001",
                "version": "4.2",
                "chunk_id": "ISP-001__section_12",
                # section_id intentionally missing
                "citation_class": "PRIMARY",
            }
        ],
    )
    report = evaluators.evaluate_recorded(
        agent_name="legal_agent",
        scenario="scenario_1",
        parsed_output=bad,
        error=None,
    )
    assert not report.passed
    assert any("ISP-001" in f and "section_id" in f for f in report.failures)


def test_evaluator_scenario_2_legal_soft_expects_escalated() -> None:
    # Per spec §14 A-07 and scenarios_full_pipeline/scenario_2/narrative.md, Legal's
    # scenario_2 must emit ESCALATED. If the model returns 'complete'
    # the scenario-status soft check must fire a warning naming
    # 'escalated' as the expected value.
    payload = dict(
        _VALID_LEGAL,
        dpa_required=True,
        dpa_blocker=True,
        status="complete",  # deliberately wrong vs spec §14 A-07
        trigger_rule_cited=[
            {
                "source_id": "DPA-TM-001",
                "version": "1.3",
                "row_id": "A-01",
                "trigger_condition": "EU/EEA data subjects",
            }
        ],
        policy_citations=[
            {
                "source_id": "DPA-TM-001",
                "version": "1.3",
                "row_id": "A-01",
                "trigger_condition": "EU/EEA data subjects",
                "citation_class": "PRIMARY",
            }
        ],
    )
    report = evaluators.evaluate_recorded(
        agent_name="legal_agent",
        scenario="scenario_2",
        parsed_output=payload,
        error=None,
    )
    assert any("scenario-expected" in w and "escalated" in w for w in report.warnings), (
        f"expected soft warning naming 'escalated' as scenario_2 expectation; "
        f"warnings={report.warnings}"
    )


# ---------------------------------------------------------------------------
# Scenario 3 — Legal Agent: dpa_required=true AND dpa_blocker=false
# (executed DPA already on file). Stress-tests the required-vs-blocker
# distinction per Legal_Agent_Spec.md §8.3 row 2.
# ---------------------------------------------------------------------------


def _scenario_3_valid_legal_payload() -> dict[str, Any]:
    """Canonical passing scenario_3 Legal output: trigger fires, blocker cleared."""
    return {
        "dpa_required": True,
        "dpa_blocker": False,  # the distinction under test
        "nda_status": "EXECUTED",
        "nda_blocker": False,
        "trigger_rule_cited": [
            {
                "source_id": "DPA-TM-001",
                "version": "1.3",
                "row_id": "A-01",
                "trigger_condition": "Vendor will process personal data of EU/EEA data subjects on behalf of Lichen.",
                "citation_class": "PRIMARY",
            }
        ],
        "policy_citations": [
            {
                "source_id": "DPA-TM-001",
                "version": "1.3",
                "row_id": "A-01",
                "trigger_condition": "Vendor will process personal data of EU/EEA data subjects on behalf of Lichen.",
                "citation_class": "PRIMARY",
            },
            {
                "source_id": "ISP-001",
                "version": "4.2",
                "chunk_id": "ISP-001__section_12",
                "section_id": "12",
                "citation_class": "PRIMARY",
            },
        ],
        "status": "complete",
    }


def test_evaluator_scenario_3_legal_accepts_valid_output() -> None:
    report = evaluators.evaluate_recorded(
        agent_name="legal_agent",
        scenario="scenario_3",
        parsed_output=_scenario_3_valid_legal_payload(),
        error=None,
    )
    assert report.passed, f"expected scenario_3 valid payload to pass; failures={report.failures}"


def test_evaluator_scenario_3_legal_hard_fails_when_dpa_blocker_true() -> None:
    # The specific failure mode scenario_3 exists to catch: model returns
    # dpa_required=true AND dpa_blocker=true despite existing_dpa_status=
    # EXECUTED in the bundle. Must be a hard failure with a message that
    # names the conflation.
    bad = dict(
        _scenario_3_valid_legal_payload(),
        dpa_blocker=True,
        status="escalated",  # natural downstream consequence of blocker=true
    )
    report = evaluators.evaluate_recorded(
        agent_name="legal_agent",
        scenario="scenario_3",
        parsed_output=bad,
        error=None,
    )
    assert not report.passed
    assert any(
        "scenario_3" in f and "dpa_blocker=true" in f and "EXECUTED" in f
        for f in report.failures
    ), f"expected scenario_3 blocker-conflation failure; failures={report.failures}"


def test_evaluator_scenario_3_legal_hard_fails_when_dpa_required_false() -> None:
    # Guard-rail: if the model misses the DPA trigger entirely (returns
    # dpa_required=false) despite EU data + A-01 row in the bundle, that is
    # also a scenario_3 hard failure — the whole test is premised on the
    # trigger firing.
    bad = dict(
        _scenario_3_valid_legal_payload(),
        dpa_required=False,
        dpa_blocker=False,
        trigger_rule_cited=[],
    )
    report = evaluators.evaluate_recorded(
        agent_name="legal_agent",
        scenario="scenario_3",
        parsed_output=bad,
        error=None,
    )
    assert not report.passed
    assert any(
        "scenario_3" in f and "dpa_required=false" in f for f in report.failures
    ), f"expected scenario_3 missed-trigger failure; failures={report.failures}"


def test_evaluator_scenario_3_legal_hard_fails_when_status_not_complete() -> None:
    # When both blockers are cleared (dpa_blocker=false, nda executed),
    # §8.5 terminal condition requires status=complete. Anything else is a
    # scenario_3 hard failure.
    bad = dict(
        _scenario_3_valid_legal_payload(),
        status="escalated",
    )
    report = evaluators.evaluate_recorded(
        agent_name="legal_agent",
        scenario="scenario_3",
        parsed_output=bad,
        error=None,
    )
    assert not report.passed
    assert any(
        "scenario_3" in f and "expected 'complete'" in f for f in report.failures
    ), f"expected scenario_3 status-not-complete failure; failures={report.failures}"


# ---------------------------------------------------------------------------
# Scenario 4 — Legal Agent: blocked on missing upstream input (pure gate
# condition). No IT Security output in the bundle → inadmissible → must
# emit the §9.1 blocked output shape with no determination fields present.
# ---------------------------------------------------------------------------


def test_evaluator_scenario_4_legal_accepts_valid_blocked_output() -> None:
    # Valid §9.1 blocked output: status + blocked_reason + blocked_fields.
    # Determination fields entirely absent. Must pass.
    report = evaluators.evaluate_recorded(
        agent_name="legal_agent",
        scenario="scenario_4",
        parsed_output={
            "status": "blocked",
            "blocked_reason": ["MISSING_UPSTREAM_IT_SECURITY_OUTPUT"],
            "blocked_fields": ["data_classification"],
        },
        error=None,
    )
    assert report.passed, f"valid §9.1 blocked output must pass; failures={report.failures}"


def test_evaluator_scenario_4_legal_hard_fails_when_determination_fields_present_as_null() -> None:
    # Per §9.1: determination fields must be entirely ABSENT on blocked
    # runs — not null, not empty. Null implies the field exists but has
    # no value; absent means the agent declined to produce a determination.
    # Even with correct blocked_reason/blocked_fields, the presence of
    # null determination fields is a hard failure.
    report = evaluators.evaluate_recorded(
        agent_name="legal_agent",
        scenario="scenario_4",
        parsed_output={
            "status": "blocked",
            "blocked_reason": ["MISSING_UPSTREAM_IT_SECURITY_OUTPUT"],
            "blocked_fields": ["data_classification"],
            "dpa_required": None,
            "dpa_blocker": None,
            "nda_status": None,
            "nda_blocker": None,
            "trigger_rule_cited": [],
            "policy_citations": [],
        },
        error=None,
    )
    assert not report.passed, f"null determination fields on blocked run must fail; failures={report.failures}"
    # Each present determination field should produce its own failure.
    for field in ("dpa_required", "dpa_blocker", "nda_status", "nda_blocker",
                  "trigger_rule_cited", "policy_citations"):
        assert any(
            field in f and "absent" in f for f in report.failures
        ), f"expected absent-field failure for {field!r}; failures={report.failures}"


def test_evaluator_scenario_4_legal_hard_fails_when_blocked_reason_missing() -> None:
    # §9.1 requires blocked_reason. Output with only status=blocked and
    # no blocked_reason must fail.
    report = evaluators.evaluate_recorded(
        agent_name="legal_agent",
        scenario="scenario_4",
        parsed_output={"status": "blocked"},
        error=None,
    )
    assert not report.passed
    assert any(
        "blocked_reason" in f and "missing" in f for f in report.failures
    ), f"expected blocked_reason missing failure; failures={report.failures}"
    assert any(
        "blocked_fields" in f and "missing" in f for f in report.failures
    ), f"expected blocked_fields missing failure; failures={report.failures}"


def test_evaluator_scenario_4_legal_hard_fails_when_status_not_blocked() -> None:
    # The canonical failure: model infers a determination from downstream
    # evidence (questionnaire EU flag, A-01 trigger row) despite missing
    # upstream STEP-02 output. Must hard-fail.
    bad = {
        "status": "escalated",
        "dpa_required": True,
        "dpa_blocker": True,
        "nda_status": "PENDING",
        "nda_blocker": True,
        "trigger_rule_cited": [
            {
                "source_id": "DPA-TM-001",
                "version": "1.3",
                "row_id": "A-01",
                "trigger_condition": "EU/EEA data subjects",
                "citation_class": "PRIMARY",
            }
        ],
        "policy_citations": [
            {
                "source_id": "DPA-TM-001",
                "version": "1.3",
                "row_id": "A-01",
                "trigger_condition": "EU/EEA data subjects",
                "citation_class": "PRIMARY",
            }
        ],
    }
    report = evaluators.evaluate_recorded(
        agent_name="legal_agent",
        scenario="scenario_4",
        parsed_output=bad,
        error=None,
    )
    assert not report.passed
    assert any(
        "scenario_4" in f and "blocked" in f for f in report.failures
    ), f"expected scenario_4 status-not-blocked failure; failures={report.failures}"


def test_evaluator_scenario_4_legal_hard_fails_when_determination_attempted_on_blocked() -> None:
    # Edge case: model sets status=blocked but also emits determination
    # fields alongside the blocked status. Per §9.1, determination fields
    # must be entirely absent on a blocked run — present-with-any-value
    # (including null) is a contract violation.
    bad = {
        "status": "blocked",
        "blocked_reason": ["MISSING_UPSTREAM_IT_SECURITY_OUTPUT"],
        "blocked_fields": ["data_classification"],
        "dpa_required": True,  # determination attempted despite blocked
        "trigger_rule_cited": [
            {
                "source_id": "DPA-TM-001",
                "version": "1.3",
                "row_id": "A-01",
                "trigger_condition": "EU/EEA data subjects",
                "citation_class": "PRIMARY",
            }
        ],
    }
    report = evaluators.evaluate_recorded(
        agent_name="legal_agent",
        scenario="scenario_4",
        parsed_output=bad,
        error=None,
    )
    assert not report.passed
    assert any(
        "scenario_4" in f and "dpa_required" in f and "absent" in f
        for f in report.failures
    ), f"expected scenario_4 determination-present failure per §9.1; failures={report.failures}"
    assert any(
        "scenario_4" in f and "trigger_rule_cited" in f and "absent" in f
        for f in report.failures
    ), f"expected scenario_4 trigger-present failure per §9.1; failures={report.failures}"


def test_general_rules_allow_blocked_minimal_output() -> None:
    # Cross-agent sanity check: the _check_general blocked-minimal-output
    # allowance must not force determination-field presence on blocked runs
    # for any domain agent. Parallels each spec's §9-equivalent minimal-
    # blocked language (Legal §9, Procurement §9, Checklist Assembler §9,
    # Checkoff §9).
    report = evaluators.evaluate_recorded(
        agent_name="procurement_agent",
        scenario="scenario_1",
        parsed_output={"status": "blocked"},
        error=None,
    )
    # General-rule required-field checks must be skipped on blocked; the
    # scenario-expected status for procurement scenario_1 is complete, so a
    # soft warning is expected, but no hard failures from required-field
    # presence.
    required_field_failures = [
        f for f in report.failures if f.startswith("required field missing")
    ]
    assert not required_field_failures, (
        f"blocked minimal output must not trigger required-field failures; "
        f"got: {required_field_failures}"
    )


def test_evaluator_flags_procurement_complete_missing_primary_pam() -> None:
    # §14 A-01 acceptance check: a COMPLETE approval_path determination
    # requires at least one PRIMARY PAM-001 citation with a non-empty row_id.
    # SUPPLEMENTARY-only or SLK-001-only citations must fail on complete.
    bad = dict(
        _VALID_PROCUREMENT,
        policy_citations=[
            {
                "source_id": "SLK-001",
                "version": "1.0",
                "row_id": "thread_42",
                "approval_path_condition": "Procurement thread context",
                "citation_class": "SUPPLEMENTARY",
            }
        ],
    )
    report = evaluators.evaluate_recorded(
        agent_name="procurement_agent",
        scenario="scenario_1",
        parsed_output=bad,
        error=None,
    )
    assert not report.passed
    assert any("PRIMARY PAM-001" in f for f in report.failures)


# ---------------------------------------------------------------------------
# CLI — exit codes & argument handling
# ---------------------------------------------------------------------------


def _patch_client_into_runner(monkeypatch: pytest.MonkeyPatch, payload: Any) -> _StubClient:
    """Make the runner use a stub client when invoked via the CLI."""
    stub = _StubClient(payload)
    from per_agent_test_env import runner as runner_module

    monkeypatch.setattr(runner_module, "_build_client", lambda: stub)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "stub-key-for-smoke-test")
    return stub


def test_cli_exit_zero_on_pass(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_client_into_runner(monkeypatch, _VALID_IT_SECURITY)
    code = cli_main([
        "--agent", "it_security_agent",
        "--scenario", "scenario_1",
        "--recorded-dir", str(tmp_path),
    ])
    assert code == 0


def test_cli_exit_one_on_fail(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    bad = dict(_VALID_IT_SECURITY, data_classification="INVALID_VALUE")
    _patch_client_into_runner(monkeypatch, bad)
    code = cli_main([
        "--agent", "it_security_agent",
        "--scenario", "scenario_1",
        "--recorded-dir", str(tmp_path),
    ])
    assert code == 1


def test_cli_exit_two_on_missing_args(tmp_path: Path) -> None:
    code = cli_main(["--agent", "it_security_agent"])  # missing --scenario
    assert code == 2


def test_cli_halts_on_first_failure_not_cascading(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """When --all is used and the first run fails, the second must not execute."""

    # We use a stub that fails evaluation on the very first call. Count
    # .create invocations to prove the runner halted.
    from per_agent_test_env import runner as runner_module

    bad_payload = dict(_VALID_IT_SECURITY, data_classification="INVALID_VALUE")
    stub = _StubClient(bad_payload)
    monkeypatch.setattr(runner_module, "_build_client", lambda: stub)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "stub-key-for-smoke-test")

    call_count = {"n": 0}
    original_create = stub.messages.create

    def _counting_create(**kwargs: Any) -> _StubResponse:
        call_count["n"] += 1
        return original_create(**kwargs)

    stub.messages.create = _counting_create  # type: ignore[assignment]

    code = cli_main(["--all", "--recorded-dir", str(tmp_path)])
    assert code == 1
    assert call_count["n"] == 1, (
        f"expected halt after first failure, got {call_count['n']} API calls"
    )
