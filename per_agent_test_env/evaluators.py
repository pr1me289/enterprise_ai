"""Per-agent output evaluators.

Each ``evaluate_<agent>`` function takes the parsed JSON output from a
recorded call and returns a list of failure strings (empty on pass).
Rules encode the ``llm_agent_output_evaluation_checklist.md`` contract:

- Hard checks → append to ``failures`` (list of strings).
- Soft checks (e.g., scenario-expected status) → append to ``warnings``
  and include as a non-failing diagnostic on the result.

The evaluator never re-calls the model. It operates purely on the saved
response dict. A single missing required field, wrong type, or illegal
enum value is a test failure regardless of whether ``status`` looks
plausible.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from agents._validator import REQUIRED_FIELDS

# ---------------------------------------------------------------------------
# Enum/value domains per the evaluation checklist + agent specs
# ---------------------------------------------------------------------------

AGENT_STATUS_VALUES: tuple[str, ...] = ("complete", "escalated", "blocked")
OVERALL_STATUS_VALUES: tuple[str, ...] = ("COMPLETE", "ESCALATED", "BLOCKED")

DATA_CLASSIFICATION_VALUES: tuple[str, ...] = ("REGULATED", "UNREGULATED", "AMBIGUOUS")
NDA_STATUS_VALUES: tuple[str, ...] = ("EXECUTED", "PENDING", "NOT_STARTED", "UNKNOWN")
APPROVAL_PATH_VALUES: tuple[str, ...] = ("STANDARD", "FAST_TRACK", "EXECUTIVE_APPROVAL")

# Scenario-expected status signals from the checklist's final summary table.
# These are *soft* expectations: they are reported as warnings, not failures.
EXPECTED_STATUS: dict[tuple[str, str], str] = {
    ("it_security_agent", "scenario_1"): "complete",
    ("it_security_agent", "scenario_2"): "escalated",
    ("legal_agent", "scenario_1"): "complete",
    ("legal_agent", "scenario_2"): "complete",  # NDA blocker does not escalate
    ("procurement_agent", "scenario_1"): "complete",
    ("procurement_agent", "scenario_2"): "escalated",
    # Checklist Assembler uses overall_status, not status
    ("checklist_assembler", "scenario_1"): "COMPLETE",
    ("checklist_assembler", "scenario_2"): "ESCALATED",
    # Checkoff only runs when STEP-05 is COMPLETE. In isolation with the
    # scenario_2 bundle we still feed it, but expect no guarantee.
    ("checkoff_agent", "scenario_1"): "complete",
    ("checkoff_agent", "scenario_2"): "complete",
}


@dataclass
class EvaluationReport:
    failures: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return not self.failures


# ---------------------------------------------------------------------------
# General-rules block — applied to every agent before agent-specific checks
# ---------------------------------------------------------------------------


def _check_general(output: Any, agent_name: str, report: EvaluationReport) -> bool:
    """Return True if output is a dict and basic shape is OK, else False.

    Failures are appended to ``report``. A False return signals the
    caller that agent-specific checks should be skipped because the
    output is not a dict.
    """
    if output is None:
        report.failures.append("output is None — no parsed JSON was produced")
        return False
    if not isinstance(output, dict):
        report.failures.append(f"output is not a JSON object (got {type(output).__name__})")
        return False

    # Required-field presence, using the call-layer contract as source of truth.
    required = REQUIRED_FIELDS.get(agent_name, ())
    for field_name in required:
        if field_name not in output:
            report.failures.append(f"required field missing: {field_name!r}")
            continue
        value = output[field_name]
        if value is None:
            report.failures.append(f"required field is null: {field_name!r}")
        elif isinstance(value, str) and value == "":
            report.failures.append(f"required field is empty string: {field_name!r}")
        elif isinstance(value, (list, tuple)) and len(value) == 0:
            # Empty arrays are handled as failures by the agent-specific
            # checks where the checklist forbids them (citations, etc.).
            # Here we only note the general rule — agent checks will
            # promote it to a failure if content was required.
            pass

    # Status / overall_status shape (general rule)
    if agent_name == "checklist_assembler":
        overall = output.get("overall_status")
        if overall is None:
            report.failures.append("overall_status is missing")
        elif not isinstance(overall, str):
            report.failures.append(f"overall_status must be a string, got {type(overall).__name__}")
        elif overall not in OVERALL_STATUS_VALUES:
            report.failures.append(
                f"overall_status must be one of {OVERALL_STATUS_VALUES}, got {overall!r}"
            )
    else:
        status = output.get("status")
        if status is None:
            report.failures.append("status is missing")
        elif not isinstance(status, str):
            report.failures.append(f"status must be a string, got {type(status).__name__}")
        elif status not in AGENT_STATUS_VALUES:
            report.failures.append(
                f"status must be one of {AGENT_STATUS_VALUES}, got {status!r}"
            )

    return True


def _check_scenario_status(
    output: dict[str, Any],
    agent_name: str,
    scenario: str,
    report: EvaluationReport,
) -> None:
    """Soft-check the scenario-expected status signal from the checklist table."""
    expected = EXPECTED_STATUS.get((agent_name, scenario))
    if expected is None:
        return
    actual_key = "overall_status" if agent_name == "checklist_assembler" else "status"
    actual = output.get(actual_key)
    if actual != expected:
        report.warnings.append(
            f"scenario-expected {actual_key}={expected!r} (checklist table), got {actual!r}"
        )


def _check_enum(
    output: dict[str, Any],
    field_name: str,
    allowed: tuple[str, ...],
    report: EvaluationReport,
) -> None:
    value = output.get(field_name)
    if value is None:
        return  # general check already flagged missing
    if not isinstance(value, str):
        report.failures.append(f"{field_name} must be a string, got {type(value).__name__}")
        return
    if value not in allowed:
        report.failures.append(f"{field_name} must be one of {allowed}, got {value!r}")


def _check_bool(output: dict[str, Any], field_name: str, report: EvaluationReport) -> None:
    value = output.get(field_name)
    if value is None:
        return
    if not isinstance(value, bool):
        report.failures.append(
            f"{field_name} must be a boolean, got {type(value).__name__}={value!r}"
        )


def _check_non_empty_array(
    output: dict[str, Any],
    field_name: str,
    report: EvaluationReport,
    *,
    where: str = "required",
) -> None:
    value = output.get(field_name)
    if value is None:
        return
    if not isinstance(value, list):
        report.failures.append(f"{field_name} must be an array, got {type(value).__name__}")
        return
    if len(value) == 0:
        report.failures.append(f"{field_name} is empty ({where})")


def _check_citation_entries(
    output: dict[str, Any],
    field_name: str,
    required_keys: tuple[str, ...],
    report: EvaluationReport,
) -> None:
    """Check each citation entry has the required keys (non-empty strings).

    The call-layer contract (``_validator.REQUIRED_FIELDS``) only guarantees
    citation arrays *exist*. Checklist §STEP-02/§STEP-03 require each
    entry to have at minimum ``source_id``, ``version``, ``section``.
    """
    value = output.get(field_name)
    if not isinstance(value, list):
        return
    for idx, entry in enumerate(value):
        if not isinstance(entry, dict):
            report.failures.append(f"{field_name}[{idx}] is not an object")
            continue
        for key in required_keys:
            if key not in entry or entry[key] in (None, ""):
                report.failures.append(
                    f"{field_name}[{idx}] missing required key {key!r}"
                )


def _check_source_id_in(
    output: dict[str, Any],
    field_name: str,
    allowed_sources: tuple[str, ...],
    report: EvaluationReport,
) -> None:
    value = output.get(field_name)
    if not isinstance(value, list):
        return
    for idx, entry in enumerate(value):
        if isinstance(entry, dict) and "source_id" in entry:
            src = entry["source_id"]
            if src not in allowed_sources:
                report.failures.append(
                    f"{field_name}[{idx}].source_id={src!r} is outside permitted sources {allowed_sources}"
                )


# ---------------------------------------------------------------------------
# STEP-02 — IT Security Agent
# ---------------------------------------------------------------------------


def _evaluate_it_security(output: dict[str, Any], scenario: str, report: EvaluationReport) -> None:
    _check_enum(output, "data_classification", DATA_CLASSIFICATION_VALUES, report)
    _check_bool(output, "fast_track_eligible", report)

    # fast_track_eligible must be False when data_classification is REGULATED or AMBIGUOUS
    dc = output.get("data_classification")
    fte = output.get("fast_track_eligible")
    if isinstance(fte, bool) and isinstance(dc, str):
        if fte is True and dc in ("REGULATED", "AMBIGUOUS"):
            report.failures.append(
                f"fast_track_eligible=true is inconsistent with data_classification={dc!r}"
            )

    # policy_citations must be non-empty and cite ISP-001 only
    _check_non_empty_array(
        output, "policy_citations", report, where="STEP-02 must cite the ISP-001 clause(s)"
    )
    # Domain-agent policy_citations[] is machine-to-machine provenance, so
    # the required keys are source_id, version, section_id, and citation_class
    # (matches Agent Spec, ORCH-PLAN STEP-02 output contract, and CC-001 §7).
    # chunk_id is expected per the same contracts but is a soft expectation
    # here — the evaluator does not hard-fail on its absence. section (no _id)
    # is the human-facing label used only by the Checklist Assembler's
    # citations[] per Design Doc §10 — do not conflate the two.
    _check_citation_entries(
        output,
        "policy_citations",
        required_keys=("source_id", "version", "section_id", "citation_class"),
        report=report,
    )
    _check_source_id_in(output, "policy_citations", ("ISP-001",), report)

    # If data_classification is AMBIGUOUS the checklist flags status=complete
    # as a red-flag inconsistency.
    if dc == "AMBIGUOUS" and output.get("status") == "complete":
        report.failures.append(
            "status='complete' is inconsistent with data_classification='AMBIGUOUS' — should be 'escalated'"
        )


# ---------------------------------------------------------------------------
# STEP-03 — Legal Agent
# ---------------------------------------------------------------------------


def _evaluate_legal(output: dict[str, Any], scenario: str, report: EvaluationReport) -> None:
    for field_name in ("dpa_required", "dpa_blocker", "nda_blocker"):
        _check_bool(output, field_name, report)

    _check_enum(output, "nda_status", NDA_STATUS_VALUES, report)

    # dpa_blocker must not be True when dpa_required is False
    dpa_req = output.get("dpa_required")
    dpa_blk = output.get("dpa_blocker")
    if isinstance(dpa_req, bool) and isinstance(dpa_blk, bool):
        if dpa_blk is True and dpa_req is False:
            report.failures.append("dpa_blocker=true is inconsistent with dpa_required=false")

    # nda_blocker must be True when nda_status is not EXECUTED
    nda = output.get("nda_status")
    nda_blk = output.get("nda_blocker")
    if isinstance(nda_blk, bool) and isinstance(nda, str) and nda in NDA_STATUS_VALUES:
        if nda != "EXECUTED" and nda_blk is False:
            report.failures.append(
                f"nda_blocker=false is inconsistent with nda_status={nda!r} (must be true when not EXECUTED)"
            )
        if nda == "EXECUTED" and nda_blk is True:
            report.failures.append(
                "nda_blocker=true is inconsistent with nda_status='EXECUTED'"
            )

    # trigger_rule_cited: when dpa_required is True, must be a non-empty array
    # of DPA-TM-001 rows with source_id/version/row_id/trigger_condition.
    if dpa_req is True:
        _check_non_empty_array(
            output,
            "trigger_rule_cited",
            report,
            where="dpa_required=true requires DPA-TM-001 row citations",
        )
    trigger = output.get("trigger_rule_cited")
    if isinstance(trigger, list) and len(trigger) > 0:
        _check_citation_entries(
            output,
            "trigger_rule_cited",
            required_keys=("source_id", "version", "row_id", "trigger_condition"),
            report=report,
        )
        _check_source_id_in(output, "trigger_rule_cited", ("DPA-TM-001",), report)

    # policy_citations required-field is already in REQUIRED_FIELDS; if the
    # nda_blocker is True the checklist expects ISP-001 §12.1.4 cited somewhere
    # (either trigger_rule_cited or policy_citations).
    pc = output.get("policy_citations")
    if isinstance(pc, list):
        _check_citation_entries(
            output,
            "policy_citations",
            required_keys=("source_id", "version", "section"),
            report=report,
        )
        _check_source_id_in(output, "policy_citations", ("ISP-001", "DPA-TM-001"), report)

    if nda_blk is True:
        # Look for ISP-001 §12.1.4 reference in either array
        sections = []
        for bucket in (output.get("policy_citations") or [], output.get("trigger_rule_cited") or []):
            if isinstance(bucket, list):
                for entry in bucket:
                    if isinstance(entry, dict):
                        sections.append(f"{entry.get('source_id')}/{entry.get('section') or entry.get('row_id')}")
        if not any(
            isinstance(entry, dict)
            and entry.get("source_id") == "ISP-001"
            and str(entry.get("section", "")).startswith("12.1.4")
            for entry in (pc or [])
        ):
            report.warnings.append(
                "nda_blocker=true but ISP-001 §12.1.4 NDA clause not found in policy_citations "
                f"(seen: {sections})"
            )


# ---------------------------------------------------------------------------
# STEP-04 — Procurement Agent
# ---------------------------------------------------------------------------


def _evaluate_procurement(output: dict[str, Any], scenario: str, report: EvaluationReport) -> None:
    _check_enum(output, "approval_path", APPROVAL_PATH_VALUES, report)
    _check_bool(output, "fast_track_eligible", report)
    _check_bool(output, "executive_approval_required", report)

    ap = output.get("approval_path")
    fte = output.get("fast_track_eligible")
    ear = output.get("executive_approval_required")

    if isinstance(fte, bool) and isinstance(ap, str):
        if fte is False and ap == "FAST_TRACK":
            report.failures.append(
                "approval_path='FAST_TRACK' is inconsistent with fast_track_eligible=false"
            )

    if isinstance(ear, bool) and isinstance(ap, str):
        if ap == "EXECUTIVE_APPROVAL" and ear is False:
            report.failures.append(
                "executive_approval_required=false is inconsistent with approval_path='EXECUTIVE_APPROVAL'"
            )
        if ap != "EXECUTIVE_APPROVAL" and ear is True:
            report.warnings.append(
                f"executive_approval_required=true but approval_path={ap!r} — expected EXECUTIVE_APPROVAL"
            )

    status = output.get("status")
    # required_approvals must be non-empty on status=complete
    if status == "complete":
        _check_non_empty_array(
            output,
            "required_approvals",
            report,
            where="status='complete' requires at least one required_approvals entry",
        )

    # each required_approvals entry must have approver + domain
    ra = output.get("required_approvals")
    if isinstance(ra, list):
        for idx, entry in enumerate(ra):
            if not isinstance(entry, dict):
                report.failures.append(f"required_approvals[{idx}] is not an object")
                continue
            for key in ("approver", "domain"):
                if key not in entry or entry[key] in (None, ""):
                    report.failures.append(f"required_approvals[{idx}] missing {key!r}")

    # estimated_timeline required & non-empty on complete
    if status == "complete":
        et = output.get("estimated_timeline")
        if et is None or (isinstance(et, str) and et.strip() == ""):
            report.failures.append("estimated_timeline is missing or empty on status='complete'")


# ---------------------------------------------------------------------------
# STEP-05 — Checklist Assembler
# ---------------------------------------------------------------------------


_ASSEMBLER_INHERITED_FIELDS: tuple[str, ...] = (
    "data_classification",
    "dpa_required",
    "dpa_blocker",
    "fast_track_eligible",
    "approval_path",
)


def _evaluate_checklist_assembler(output: dict[str, Any], scenario: str, report: EvaluationReport) -> None:
    # pipeline_run_id and vendor_name are required; overall_status is already
    # checked in the general block (enum).
    for field_name in ("pipeline_run_id", "vendor_name"):
        val = output.get(field_name)
        if isinstance(val, str) and val.strip() == "":
            report.failures.append(f"{field_name!r} must be a non-empty string")

    overall = output.get("overall_status")

    # Inherited fields — the checklist lists these as REQUIRED for the assembler.
    for field_name in _ASSEMBLER_INHERITED_FIELDS:
        if field_name not in output:
            report.failures.append(f"inherited field missing: {field_name!r}")

    # required_approvals non-empty on COMPLETE
    if overall == "COMPLETE":
        _check_non_empty_array(
            output,
            "required_approvals",
            report,
            where="overall_status='COMPLETE' requires required_approvals entries",
        )

    # blockers array must exist; if any upstream blocker was present (per our
    # own per-scenario expectation) it must be non-empty. The evaluator does
    # not assume the upstream output — it only checks the field exists.
    blockers = output.get("blockers")
    if blockers is not None and not isinstance(blockers, list):
        report.failures.append(f"blockers must be an array if present, got {type(blockers).__name__}")

    # citations: the checklist says this must be a non-empty array with
    # {source_name, version, section, retrieval_timestamp, agent_id}.
    citations = output.get("citations")
    if citations is None:
        report.failures.append("citations array is missing — checklist must be traceable")
    else:
        _check_non_empty_array(output, "citations", report, where="checklist must be traceable")
        _check_citation_entries(
            output,
            "citations",
            required_keys=("source_name", "version", "section", "retrieval_timestamp", "agent_id"),
            report=report,
        )


# ---------------------------------------------------------------------------
# STEP-06 — Checkoff Agent
# ---------------------------------------------------------------------------


def _evaluate_checkoff(output: dict[str, Any], scenario: str, report: EvaluationReport) -> None:
    # The checkoff output contract is looser than the other agents. The
    # checklist requires: guidance documents present, stakeholder routing
    # present, escalation reasons surfaced, no raw-source retrieval evidence.
    # We look for at least one of a set of plausible field names, and we
    # demand a non-empty stakeholder-facing payload.
    guidance_candidates = (
        "guidance_documents",
        "stakeholder_guidance",
        "guidance",
        "documents",
    )
    found = False
    for name in guidance_candidates:
        value = output.get(name)
        if isinstance(value, list) and len(value) > 0:
            found = True
            break
        if isinstance(value, dict) and len(value) > 0:
            found = True
            break
    if not found:
        report.failures.append(
            f"no non-empty guidance payload found under any of {guidance_candidates}"
        )

    # Stakeholder routing — approver list or routing reference somewhere in the output.
    routing_candidates = (
        "required_approvers",
        "approver_routing",
        "stakeholder_routing",
        "routing",
    )
    if not any(output.get(name) for name in routing_candidates):
        report.warnings.append(
            f"no explicit stakeholder routing found under any of {routing_candidates}"
        )


# ---------------------------------------------------------------------------
# Dispatcher
# ---------------------------------------------------------------------------


_AGENT_EVALUATORS = {
    "it_security_agent": _evaluate_it_security,
    "legal_agent": _evaluate_legal,
    "procurement_agent": _evaluate_procurement,
    "checklist_assembler": _evaluate_checklist_assembler,
    "checkoff_agent": _evaluate_checkoff,
}


def evaluate_recorded(
    *,
    agent_name: str,
    scenario: str,
    parsed_output: Any,
    error: str | None,
) -> EvaluationReport:
    """Evaluate a recorded response against the output contract.

    ``error`` is the API/parse error string from the runner (or None).
    A non-None error is always a failure; evaluation of the parsed
    output still runs if ``parsed_output`` is non-None so partial
    outputs produce the full failure picture.
    """
    report = EvaluationReport()

    if error:
        report.failures.append(f"runtime error during call: {error}")

    if not _check_general(parsed_output, agent_name, report):
        return report

    assert isinstance(parsed_output, dict)  # for type-checkers; _check_general enforced this
    _check_scenario_status(parsed_output, agent_name, scenario, report)

    evaluator = _AGENT_EVALUATORS.get(agent_name)
    if evaluator is None:
        report.failures.append(f"no evaluator registered for agent {agent_name!r}")
        return report

    evaluator(parsed_output, scenario, report)
    return report
