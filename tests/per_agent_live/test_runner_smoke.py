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
        {"source_id": "ISP-001", "version": "4.2", "section": "12.1.4"}
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
        {"source_id": "PAM-001", "version": "3.0", "section": "4"}
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


@pytest.mark.parametrize("agent", VALID_AGENTS)
@pytest.mark.parametrize("scenario", VALID_SCENARIOS)
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
