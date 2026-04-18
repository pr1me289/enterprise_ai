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

# Legal Agent §9.1 blocked_reason enum values.
LEGAL_BLOCKED_REASON_VALUES: tuple[str, ...] = (
    "MISSING_UPSTREAM_IT_SECURITY_OUTPUT",
    "MISSING_QUESTIONNAIRE_EU_FIELDS",
    "MISSING_DPA_TRIGGER_MATRIX",
    "MISSING_NDA_CLAUSE",
)

# Scenario-expected status signals from the checklist's final summary table.
# These are *soft* expectations: they are reported as warnings, not failures.
EXPECTED_STATUS: dict[tuple[str, str], str] = {
    ("it_security_agent", "scenario_1"): "complete",
    ("it_security_agent", "scenario_2"): "escalated",
    ("legal_agent", "scenario_1"): "complete",
    # scenario_2: DPA required but not executed → dpa_blocker=true →
    # status=escalated per Legal Agent Spec §14 A-07 (hard rule: agent must
    # not emit complete when a DPA blocker is confirmed) and
    # demo_scenario_02_escalated.md (STEP-03 is the first step in the chain
    # to emit ESCALATED). NDA blocker alone does not escalate, but a DPA
    # blocker does.
    ("legal_agent", "scenario_2"): "escalated",
    # scenario_3: DPA required (EU data + A-01 trigger fires) AND
    # existing_dpa_status=EXECUTED → dpa_blocker=false → status=complete per
    # Legal Agent Spec §8.3 row 2 ("dpa_required=true AND executed DPA
    # confirmed on record" → false) and §8.5 terminal condition ("all
    # required evidence present and no escalation or blocked condition
    # applies"). This scenario exists to catch models that conflate
    # "DPA required" with "DPA is a blocker".
    ("legal_agent", "scenario_3"): "complete",
    # scenario_4: no upstream STEP-02 output in the bundle → inadmissible →
    # status=blocked per Legal_Agent_Spec.md §8.5 ("upstream_data_classification
    # absent" → blocked) and §12 ("data_classification absent from STEP-02
    # output | Bundle is inadmissible. Emit status: blocked. Do not proceed.").
    # Pure gate-condition test — the agent must halt rather than infer through
    # the missing input.
    ("legal_agent", "scenario_4"): "blocked",
    # scenario_5: Two DPA-TM-001 rows (A-01 and A-06) both apply to the vendor
    # profile but produce contradictory trigger outcomes (REQUIRED vs NOT
    # REQUIRED). Per CC-001 §4.1, a Tier 1 vs Tier 1 conflict cannot be
    # auto-suppressed. Per Legal_Agent_Spec.md §8.5 ("Tier 1 DPA sources
    # conflict on the same trigger question" → escalated) and §9.2 (escalated
    # output: all determination fields present, unresolvable fields set to
    # null). NDA is independently resolvable (existing_nda_status=EXECUTED).
    ("legal_agent", "scenario_5"): "escalated",
    # scenario_6: ISP-001 §12.1.4 NDA clause chunk AND existing_nda_status both
    # absent from the bundle. DPA determination fully resolved (trigger rows
    # present, existing_dpa_status=EXECUTED → dpa_blocker=false). §8.5 condition
    # 5 fires ("nda_clause_chunks absent from bundle" → escalated). NDA
    # determination unresolvable per §9.2 (both evidence sources absent →
    # nda_status=null, nda_blocker=null). Tests partial determination: DPA
    # populated, NDA null.
    ("legal_agent", "scenario_6"): "escalated",
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

    # Blocked-output allowance: when status=blocked, skip required-field
    # checks for determination fields. Per Legal Agent Spec §9.1,
    # determination fields must be entirely absent on blocked runs (the
    # agent must emit the §9.1 blocked output shape instead). The general
    # check only enforces that `status` itself is present; agent-specific
    # evaluators enforce the §9.1 shape (blocked_reason, blocked_fields)
    # and hard-fail if determination fields are present.
    is_blocked = output.get("status") == "blocked"

    # Escalated-output null-field allowance: Legal Agent Spec §9.2 permits
    # null for unresolvable determination fields on escalated runs. This is
    # specific to the Legal Agent — other agents (IT Security, Procurement)
    # do not define a null-field escalation model. The general check skips
    # the null-value failure for legal_agent escalated runs; the scenario-
    # specific evaluator (e.g., scenario_5) validates exactly which fields
    # must vs. must not be null.
    is_legal_escalated = (
        agent_name == "legal_agent" and output.get("status") == "escalated"
    )

    # Required-field presence, using the call-layer contract as source of truth.
    required = REQUIRED_FIELDS.get(agent_name, ())
    for field_name in required:
        if is_blocked and field_name != "status":
            continue
        if field_name not in output:
            report.failures.append(f"required field missing: {field_name!r}")
            continue
        value = output[field_name]
        if value is None:
            if is_legal_escalated:
                # Legal Agent Spec §9.2 permits null for unresolvable fields
                # on escalated runs. Scenario-specific evaluators validate
                # which fields should vs. should not be null.
                pass
            else:
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

    # scenario_2 non-null enforcement — scenario_2 is a resolved-escalation
    # case (dpa_blocker=true is a workflow consequence, not an evidence gap).
    # All determination fields are resolvable and must be non-null per §9.2
    # ("fields the agent can resolve carry their derived values"). The general
    # null check is bypassed for legal_agent escalated runs (to support §9.2
    # null fields in scenario_5), so this block re-establishes the non-null
    # requirement for scenario_2 specifically.
    if scenario == "scenario_2" and output.get("status") == "escalated":
        _scenario_2_required_non_null = (
            "dpa_required", "dpa_blocker", "nda_status", "nda_blocker",
            "trigger_rule_cited", "policy_citations",
        )
        for det_field in _scenario_2_required_non_null:
            if det_field in output and output[det_field] is None:
                report.failures.append(
                    f"scenario_2: {det_field} is null but all determination "
                    "fields are resolvable in this scenario — per §9.2, "
                    "resolved fields must carry their derived values"
                )

    # scenario_3 hard checks — the scenario exists to stress the
    # dpa_required-vs-dpa_blocker distinction. Bundle provides
    # eu_personal_data_flag=true + A-01 trigger row (→ dpa_required must be
    # true) AND existing_dpa_status=EXECUTED (→ dpa_blocker must be false)
    # per Legal_Agent_Spec.md §8.3 row 2. A model that collapses the two
    # concepts will emit dpa_blocker=true — the specific failure mode this
    # fixture exists to catch.
    if scenario == "scenario_3":
        if dpa_req is False:
            report.failures.append(
                "scenario_3: dpa_required=false contradicts bundle — EU personal data "
                "flagged and DPA-TM-001 row A-01 present in dpa_trigger_rows; trigger "
                "must fire"
            )
        if dpa_req is True and dpa_blk is True:
            report.failures.append(
                "scenario_3: dpa_blocker=true but questionnaire.existing_dpa_status="
                "'EXECUTED' in bundle — Legal_Agent_Spec.md §8.3 row 2 requires "
                "dpa_blocker=false when dpa_required=true AND an executed DPA is "
                "confirmed on record. Model conflated 'DPA required' with "
                "'DPA is a blocker'."
            )
        status_val = output.get("status")
        if dpa_req is True and dpa_blk is False and status_val != "complete":
            report.failures.append(
                f"scenario_3: all blockers cleared (dpa_blocker=false, nda_status="
                f"'EXECUTED' in bundle) but status={status_val!r} — expected 'complete' "
                "per §8.5 terminal condition (all evidence present, no escalation or "
                "blocked condition applies)"
            )

    # scenario_4 hard checks — bundle has no upstream STEP-02 output, so the
    # agent must emit the §9.1 blocked output shape and must NOT attempt a DPA
    # or NDA determination. Per Legal_Agent_Spec.md §8.5 ("upstream_data_
    # classification absent" → blocked, output shape switching rule) and §12
    # ("data_classification absent from STEP-02 output | Bundle is inadmissible.
    # Emit the §9.1 blocked output shape. Do not proceed.").
    #
    # §9.1 contract: determination fields must be entirely ABSENT from the
    # output — not null, not empty. Absent means the agent correctly declined
    # to produce a determination it had no basis to make. The output must
    # contain only: status, blocked_reason (enum array), blocked_fields
    # (canonical field name array).
    if scenario == "scenario_4":
        status_val = output.get("status")
        if status_val != "blocked":
            report.failures.append(
                f"scenario_4: status={status_val!r} but bundle has no upstream STEP-02 "
                "output — must emit 'blocked' per Legal_Agent_Spec.md §8.5 (upstream "
                "data_classification absent) and §12 (inadmissible bundle; do not "
                "proceed)"
            )

        # Determination fields must be entirely absent per §9.1 — not null,
        # not empty, absent. Present-with-any-value (including null) means
        # the model attempted to produce a field it had no evidentiary basis
        # to produce.
        _blocked_forbidden_fields = (
            "dpa_required", "dpa_blocker", "nda_status", "nda_blocker",
            "trigger_rule_cited", "policy_citations",
        )
        for det_field in _blocked_forbidden_fields:
            if det_field in output:
                report.failures.append(
                    f"scenario_4: {det_field} is present in output (value="
                    f"{output[det_field]!r}) but must be entirely absent on a "
                    "blocked run per §9.1 — absent means the agent declined to "
                    "produce a determination it had no basis to make"
                )

        # blocked_reason — §9.1 requires a non-empty enum array.
        blocked_reason = output.get("blocked_reason")
        if blocked_reason is None:
            report.failures.append(
                "scenario_4: blocked_reason is missing — §9.1 requires a non-empty "
                "enum array listing the gate-condition failure(s)"
            )
        elif not isinstance(blocked_reason, list):
            report.failures.append(
                f"scenario_4: blocked_reason must be an array, got "
                f"{type(blocked_reason).__name__}"
            )
        elif len(blocked_reason) == 0:
            report.failures.append(
                "scenario_4: blocked_reason is empty — must contain at least one "
                "enum value per §9.1"
            )
        else:
            for idx, reason in enumerate(blocked_reason):
                if reason not in LEGAL_BLOCKED_REASON_VALUES:
                    report.failures.append(
                        f"scenario_4: blocked_reason[{idx}]={reason!r} is not a "
                        f"valid enum value — must be one of "
                        f"{LEGAL_BLOCKED_REASON_VALUES}"
                    )
            # For this specific scenario the missing input is upstream
            # IT Security output.
            if "MISSING_UPSTREAM_IT_SECURITY_OUTPUT" not in blocked_reason:
                report.failures.append(
                    "scenario_4: blocked_reason does not contain "
                    "'MISSING_UPSTREAM_IT_SECURITY_OUTPUT' — this is the specific "
                    "gate-condition failure for this bundle (no STEP-02 output)"
                )

        # blocked_fields — §9.1 requires a non-empty array of canonical field
        # names (per CC-001 §15) that were absent from the upstream input.
        blocked_fields = output.get("blocked_fields")
        if blocked_fields is None:
            report.failures.append(
                "scenario_4: blocked_fields is missing — §9.1 requires a non-empty "
                "array of canonical field names that were absent upstream"
            )
        elif not isinstance(blocked_fields, list):
            report.failures.append(
                f"scenario_4: blocked_fields must be an array, got "
                f"{type(blocked_fields).__name__}"
            )
        elif len(blocked_fields) == 0:
            report.failures.append(
                "scenario_4: blocked_fields is empty — must name the specific "
                "upstream fields that were absent"
            )
        else:
            # data_classification is the critical missing field in this scenario.
            if "data_classification" not in blocked_fields:
                report.warnings.append(
                    "scenario_4: blocked_fields does not contain "
                    "'data_classification' — this is the primary upstream field "
                    "that was absent from the bundle"
                )

    # scenario_5 hard checks — Tier 1 DPA matrix conflict (A-01 REQUIRED vs
    # A-06 NOT REQUIRED). Both rows apply to the vendor profile. Per CC-001
    # §4.1, a Tier 1 vs Tier 1 conflict cannot be auto-suppressed — neither
    # source may be silently dropped. Per Legal_Agent_Spec.md §8.5 ("Tier 1
    # DPA sources conflict on the same trigger question" → escalated) and §9.2
    # (escalated output: all determination fields present; unresolvable fields
    # = null). The NDA determination is independently resolvable from
    # questionnaire evidence (existing_nda_status=EXECUTED, ISP-001 §12.1.4
    # present), so only the DPA fields should be null.
    if scenario == "scenario_5":
        status_val = output.get("status")
        if status_val != "escalated":
            report.failures.append(
                f"scenario_5: status={status_val!r} but bundle contains two "
                "conflicting Tier 1 DPA-TM-001 rows (A-01: REQUIRED vs A-06: "
                "NOT REQUIRED) — must emit 'escalated' per §8.5 (Tier 1 DPA "
                "sources conflict on the same trigger question)"
            )

        # §9.2 + A-10: all six determination fields must be PRESENT (not
        # absent) on an escalated run. Absent = blocked shape violation.
        _escalated_required_fields = (
            "dpa_required", "dpa_blocker", "nda_status", "nda_blocker",
            "trigger_rule_cited", "policy_citations",
        )
        for det_field in _escalated_required_fields:
            if det_field not in output:
                report.failures.append(
                    f"scenario_5: {det_field} is absent from output but must "
                    "be present on an escalated run per §9.2 and A-10 — "
                    "absent fields belong to the §9.1 blocked shape only"
                )

        # DPA fields must be null — the Tier 1 conflict makes the DPA
        # determination unresolvable per §9.2.
        if "dpa_required" in output and output["dpa_required"] is not None:
            report.failures.append(
                f"scenario_5: dpa_required={output['dpa_required']!r} but "
                "must be null — two Tier 1 rows conflict on the trigger "
                "question, making the DPA determination unresolvable per §9.2. "
                "The model silently picked one row instead of escalating the "
                "conflict (A-05 violation)."
            )
        if "dpa_blocker" in output and output["dpa_blocker"] is not None:
            report.failures.append(
                f"scenario_5: dpa_blocker={output['dpa_blocker']!r} but must "
                "be null — cannot derive a blocker from an unresolved "
                "dpa_required per §9.2"
            )
        if "trigger_rule_cited" in output and output["trigger_rule_cited"] is not None:
            report.failures.append(
                f"scenario_5: trigger_rule_cited={output['trigger_rule_cited']!r} "
                "but must be null — no citation can be made for an unresolved "
                "DPA determination per §9.2"
            )

        # NDA fields must be resolved (not null) — NDA is independently
        # resolvable from questionnaire evidence (existing_nda_status=EXECUTED)
        # and ISP-001 §12.1.4 is present in the bundle.
        nda_val = output.get("nda_status")
        if "nda_status" in output:
            if nda_val is None:
                report.failures.append(
                    "scenario_5: nda_status is null but NDA is independently "
                    "resolvable — bundle provides existing_nda_status=EXECUTED "
                    "and ISP-001 §12.1.4 clause; per §9.2, resolved fields "
                    "must carry their derived values"
                )
            elif nda_val not in NDA_STATUS_VALUES:
                report.failures.append(
                    f"scenario_5: nda_status={nda_val!r} is not a valid enum "
                    f"value — must be one of {NDA_STATUS_VALUES}"
                )
            elif nda_val != "EXECUTED":
                report.failures.append(
                    f"scenario_5: nda_status={nda_val!r} but bundle provides "
                    "existing_nda_status='EXECUTED' — agent must normalize to "
                    "'EXECUTED' per §8.4"
                )

        nda_blk_val = output.get("nda_blocker")
        if "nda_blocker" in output:
            if nda_blk_val is None:
                report.failures.append(
                    "scenario_5: nda_blocker is null but NDA is independently "
                    "resolvable — per §9.2, resolved fields carry derived values"
                )
            elif not isinstance(nda_blk_val, bool):
                report.failures.append(
                    f"scenario_5: nda_blocker must be a boolean, got "
                    f"{type(nda_blk_val).__name__}={nda_blk_val!r}"
                )
            elif nda_blk_val is True:
                report.failures.append(
                    "scenario_5: nda_blocker=true but nda_status should be "
                    "'EXECUTED' (from bundle) — per §8.4, nda_blocker must be "
                    "false when nda_status='EXECUTED'"
                )

        # policy_citations must be present and contain the resolved ISP-001
        # §12.1.4 NDA citation. The NDA determination is complete so its
        # citation must appear.
        pc_val = output.get("policy_citations")
        if "policy_citations" in output:
            if pc_val is None:
                report.failures.append(
                    "scenario_5: policy_citations is null but the NDA "
                    "determination is resolved — must contain at least the "
                    "ISP-001 §12.1.4 NDA citation per §9.2 (include citations "
                    "for resolved determinations)"
                )
            elif isinstance(pc_val, list):
                # Check for ISP-001 §12.1.4 NDA citation
                has_nda_citation = any(
                    isinstance(entry, dict)
                    and entry.get("source_id") == "ISP-001"
                    and str(entry.get("section_id", "")).startswith("12.1.4")
                    for entry in pc_val
                )
                if not has_nda_citation:
                    report.failures.append(
                        "scenario_5: policy_citations does not contain an "
                        "ISP-001 §12.1.4 NDA citation — NDA determination is "
                        "resolved and the clause is present in the bundle; the "
                        "citation must appear per §9.2 and §11"
                    )

                # Soft check: §9 note says "policy_citations array on an
                # escalated output must cite both conflicting chunks when the
                # escalation is clause-level." However, §9 output field
                # constraints say "on escalated runs, omit citations for
                # determinations that could not be resolved." These two rules
                # are in tension. The §9 note is the specific rule for Tier 1
                # conflicts; the output field constraint is the general rule.
                # We warn rather than hard-fail because the LLM may reasonably
                # follow either interpretation.
                conflict_row_ids = {"A-01", "A-06"}
                found_conflict_rows = {
                    entry.get("row_id")
                    for entry in pc_val
                    if isinstance(entry, dict)
                    and entry.get("source_id") == "DPA-TM-001"
                    and entry.get("row_id") in conflict_row_ids
                }
                if found_conflict_rows != conflict_row_ids:
                    missing = conflict_row_ids - found_conflict_rows
                    report.warnings.append(
                        f"scenario_5: policy_citations is missing DPA-TM-001 "
                        f"conflicting row(s) {missing} — §9 note says "
                        "'policy_citations must cite both conflicting chunks "
                        "when the escalation is clause-level', but §9 output "
                        "field constraints say 'omit citations for "
                        "determinations that could not be resolved'. Spec "
                        "tension — logged as warning, not failure."
                    )

        # blocked_reason and blocked_fields must be ABSENT — those belong to
        # the §9.1 blocked shape only, not the §9.2 escalated shape.
        if "blocked_reason" in output:
            report.failures.append(
                f"scenario_5: blocked_reason is present in output "
                f"(value={output['blocked_reason']!r}) but must be absent on "
                "an escalated run — blocked_reason belongs to the §9.1 blocked "
                "output shape only"
            )
        if "blocked_fields" in output:
            report.failures.append(
                f"scenario_5: blocked_fields is present in output "
                f"(value={output['blocked_fields']!r}) but must be absent on "
                "an escalated run — blocked_fields belongs to the §9.1 blocked "
                "output shape only"
            )

    # scenario_6 hard checks — ISP-001 §12.1.4 NDA clause chunk AND
    # existing_nda_status both absent from the bundle. DPA determination is
    # fully resolved (trigger rows present, existing_dpa_status=EXECUTED →
    # dpa_blocker=false per §8.3). The NDA determination is unresolvable per
    # §9.2: both questionnaire NDA evidence and NDA clause citation evidence
    # are absent, leaving no basis to assess → nda_status=null,
    # nda_blocker=null. §8.5 condition 5 fires ("nda_clause_chunks absent
    # from bundle" → escalated).
    #
    # Build prompt pivot: the build prompt expected nda_status="UNKNOWN" per
    # §8.4 (absent → UNKNOWN normalization). However, §9.2 per-field null
    # rules explicitly describe the dual-absence case ("questionnaire
    # existing_nda_status absent AND nda_clause_chunks absent, leaving no
    # evidence to assess") as producing null. §9.2 is the specific escalated-
    # output rule and takes precedence over §8.4's general normalization.
    if scenario == "scenario_6":
        status_val = output.get("status")
        if status_val != "escalated":
            report.failures.append(
                f"scenario_6: status={status_val!r} but bundle is missing "
                "nda_clause_chunks (ISP-001 §12.1.4) — must emit 'escalated' "
                "per §8.5 condition 5 (nda_clause_chunks absent from bundle)"
            )

        # §9.2 + A-10: all six determination fields must be PRESENT (not
        # absent) on an escalated run. Absent = blocked shape violation.
        _escalated_required_fields = (
            "dpa_required", "dpa_blocker", "nda_status", "nda_blocker",
            "trigger_rule_cited", "policy_citations",
        )
        for det_field in _escalated_required_fields:
            if det_field not in output:
                report.failures.append(
                    f"scenario_6: {det_field} is absent from output but must "
                    "be present on an escalated run per §9.2 and A-10 — "
                    "absent fields belong to the §9.1 blocked shape only"
                )

        # DPA fields must be resolved (not null) — DPA determination is
        # fully completable. Trigger rows present, existing_dpa_status=EXECUTED.
        if "dpa_required" in output:
            if output["dpa_required"] is None:
                report.failures.append(
                    "scenario_6: dpa_required is null but DPA determination "
                    "is fully resolvable — bundle provides DPA-TM-001 trigger "
                    "rows and EU personal data flags; per §9.2, resolved "
                    "fields must carry their derived values (A-10 violation: "
                    "model discarded a completed determination)"
                )
            elif output["dpa_required"] is not True:
                report.failures.append(
                    f"scenario_6: dpa_required={output['dpa_required']!r} but "
                    "must be true — bundle contains DPA-TM-001 row A-01 "
                    "(EU personal data processing → REQUIRED) and EU flags "
                    "are set"
                )

        if "dpa_blocker" in output:
            if output["dpa_blocker"] is None:
                report.failures.append(
                    "scenario_6: dpa_blocker is null but dpa_required is "
                    "resolvable — per §9.2, resolved fields carry their "
                    "derived values"
                )
            elif not isinstance(output["dpa_blocker"], bool):
                report.failures.append(
                    f"scenario_6: dpa_blocker must be a boolean, got "
                    f"{type(output['dpa_blocker']).__name__}="
                    f"{output['dpa_blocker']!r}"
                )
            elif output["dpa_blocker"] is not False:
                report.failures.append(
                    "scenario_6: dpa_blocker=true but "
                    "existing_dpa_status='EXECUTED' in bundle — per §8.3, "
                    "dpa_blocker must be false when dpa_required=true AND "
                    "existing_dpa_status='EXECUTED'"
                )

        # NDA fields must be null — both existing_nda_status AND
        # nda_clause_chunks are absent from the bundle, leaving no NDA
        # evidence to assess. Per §9.2 per-field null rules: "questionnaire
        # existing_nda_status absent AND nda_clause_chunks absent, leaving
        # no evidence to assess" → nda_status=null. And "nda_status is
        # null → cannot derive a blocker" → nda_blocker=null.
        if "nda_status" in output and output["nda_status"] is not None:
            report.failures.append(
                f"scenario_6: nda_status={output['nda_status']!r} but must "
                "be null — both existing_nda_status and nda_clause_chunks "
                "are absent from the bundle; per §9.2 per-field null rules, "
                "dual absence leaves no evidence to assess the NDA "
                "determination"
            )
        if "nda_blocker" in output and output["nda_blocker"] is not None:
            report.failures.append(
                f"scenario_6: nda_blocker={output['nda_blocker']!r} but must "
                "be null — cannot derive a blocker from an unresolved "
                "nda_status per §9.2"
            )

        # trigger_rule_cited must be non-empty — DPA is resolved, so the
        # matching trigger rows must be cited.
        trc_val = output.get("trigger_rule_cited")
        if "trigger_rule_cited" in output:
            if trc_val is None:
                report.failures.append(
                    "scenario_6: trigger_rule_cited is null but DPA "
                    "determination is resolved (dpa_required=true) — per §9 "
                    "output field constraints, must contain at least one "
                    "PRIMARY DPA-TM-001 entry"
                )
            elif isinstance(trc_val, list):
                if len(trc_val) == 0:
                    report.failures.append(
                        "scenario_6: trigger_rule_cited is empty but "
                        "dpa_required=true — must cite at least one "
                        "DPA-TM-001 trigger row"
                    )
                else:
                    has_primary_dpa = any(
                        isinstance(e, dict)
                        and e.get("source_id") == "DPA-TM-001"
                        and e.get("citation_class") == "PRIMARY"
                        and e.get("row_id") not in (None, "")
                        and e.get("trigger_condition") not in (None, "")
                        for e in trc_val
                    )
                    if not has_primary_dpa:
                        report.failures.append(
                            "scenario_6: trigger_rule_cited has no PRIMARY "
                            "DPA-TM-001 entry with row_id and "
                            "trigger_condition — required when "
                            "dpa_required=true per §11"
                        )

        # policy_citations: must include DPA-TM-001 citation (DPA resolved),
        # must NOT include ISP-001 §12.1.4 (absent from bundle — including
        # it would be a hallucination).
        pc_val = output.get("policy_citations")
        if "policy_citations" in output:
            if pc_val is None:
                report.failures.append(
                    "scenario_6: policy_citations is null but DPA "
                    "determination is resolved — per §9.2, include citations "
                    "for resolved determinations; must contain at least the "
                    "DPA-TM-001 PRIMARY citation"
                )
            elif isinstance(pc_val, list):
                # DPA-TM-001 citation must be present (DPA resolved)
                has_dpa_citation = any(
                    isinstance(e, dict)
                    and e.get("source_id") == "DPA-TM-001"
                    for e in pc_val
                )
                if not has_dpa_citation:
                    report.failures.append(
                        "scenario_6: policy_citations does not contain a "
                        "DPA-TM-001 citation — DPA determination is resolved "
                        "and must be cited per §9.2 and §11"
                    )

                # ISP-001 §12.1.4 must NOT be present — it was absent from
                # the bundle. Citing it is a hallucination.
                has_fabricated_nda = any(
                    isinstance(e, dict)
                    and e.get("source_id") == "ISP-001"
                    and str(e.get("section_id", "")).startswith("12.1.4")
                    for e in pc_val
                )
                if has_fabricated_nda:
                    report.failures.append(
                        "scenario_6: policy_citations contains an ISP-001 "
                        "§12.1.4 entry but nda_clause_chunks was absent from "
                        "the bundle — the model fabricated a citation for a "
                        "source it was never given (hallucination)"
                    )

        # blocked_reason and blocked_fields must be ABSENT — those belong to
        # the §9.1 blocked shape only.
        if "blocked_reason" in output:
            report.failures.append(
                f"scenario_6: blocked_reason is present in output "
                f"(value={output['blocked_reason']!r}) but must be absent on "
                "an escalated run — blocked_reason belongs to the §9.1 "
                "blocked output shape only"
            )
        if "blocked_fields" in output:
            report.failures.append(
                f"scenario_6: blocked_fields is present in output "
                f"(value={output['blocked_fields']!r}) but must be absent on "
                "an escalated run — blocked_fields belongs to the §9.1 "
                "blocked output shape only"
            )

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
        # Legal Agent Spec §11 specifies per-source-id required keys for
        # policy_citations entries (the §9 output-contract template shows a
        # generic shape; §11 is authoritative on *which* keys are required
        # per source type):
        #   - ISP-001 (section-indexed): source_id, version, chunk_id,
        #     section_id, citation_class
        #   - DPA-TM-001 (row-indexed):  source_id, version, row_id,
        #     trigger_condition, citation_class
        # A single uniform required-keys tuple does not fit because the two
        # sources have different primary identifiers. Do not confuse
        # section_id with the Checklist Assembler's human-facing `section`
        # label (Design Doc §10).
        _legal_policy_citation_required_keys_by_source = {
            "ISP-001": ("source_id", "version", "chunk_id", "section_id", "citation_class"),
            "DPA-TM-001": ("source_id", "version", "row_id", "trigger_condition", "citation_class"),
        }
        for idx, entry in enumerate(pc):
            if not isinstance(entry, dict):
                report.failures.append(f"policy_citations[{idx}] is not an object")
                continue
            src = entry.get("source_id")
            required = _legal_policy_citation_required_keys_by_source.get(src)
            if required is None:
                # Unknown/missing source_id is handled by _check_source_id_in
                # below — don't double-report a key-schema failure here.
                continue
            for key in required:
                if key not in entry or entry[key] in (None, ""):
                    report.failures.append(
                        f"policy_citations[{idx}] (source_id={src!r}) missing required key {key!r}"
                    )
        _check_source_id_in(output, "policy_citations", ("ISP-001", "DPA-TM-001"), report)

    if nda_blk is True:
        # Look for ISP-001 §12.1.4 reference in either array.
        # Domain-agent citations carry ``section_id`` (machine-to-machine provenance)
        # per the Agent Spec, ORCH-PLAN STEP-03 output contract, and CC-001 §7 —
        # not ``section`` (the Checklist Assembler's human-facing label per
        # Design Doc §10). Match on the *value* of ``section_id`` so this check
        # validates the proper clause, not just the presence of any section id.
        sections = []
        for bucket in (output.get("policy_citations") or [], output.get("trigger_rule_cited") or []):
            if isinstance(bucket, list):
                for entry in bucket:
                    if isinstance(entry, dict):
                        sections.append(
                            f"{entry.get('source_id')}/{entry.get('section_id') or entry.get('row_id')}"
                        )
        if not any(
            isinstance(entry, dict)
            and entry.get("source_id") == "ISP-001"
            and str(entry.get("section_id", "")).startswith("12.1.4")
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

    # policy_citations: per Procurement Agent Spec §9 output contract and §11
    # provenance, Procurement cites PAM-001 rows (and optionally SLK-001 as
    # SUPPLEMENTARY). Required keys are source_id, version, row_id,
    # approval_path_condition, citation_class — this is row-indexed, not
    # section-indexed, so section_id is not part of the Procurement contract.
    # chunk_id is expected per the spec but is a soft expectation here.
    # ISP-001 and DPA-TM-001 are explicitly outside Procurement's retrieval
    # lane (spec §5, §11) and are never re-cited in Procurement's output.
    pc = output.get("policy_citations")
    if isinstance(pc, list):
        # Non-empty on complete runs — §14 A-01 requires a PRIMARY PAM-001 row
        # citation for every COMPLETE approval_path determination.
        if status == "complete" and len(pc) == 0:
            report.failures.append(
                "policy_citations empty on status='complete' — §14 A-01 requires "
                "at least one PRIMARY PAM-001 row citation"
            )
        _check_citation_entries(
            output,
            "policy_citations",
            required_keys=(
                "source_id",
                "version",
                "row_id",
                "approval_path_condition",
                "citation_class",
            ),
            report=report,
        )
        _check_source_id_in(output, "policy_citations", ("PAM-001", "SLK-001"), report)

        # On COMPLETE runs, the matched matrix row must appear as PRIMARY PAM-001
        # per §14 A-01. SUPPLEMENTARY-only or SLK-001-only citations are not
        # sufficient for a COMPLETE determination.
        if status == "complete":
            primary_pam = any(
                isinstance(entry, dict)
                and entry.get("source_id") == "PAM-001"
                and entry.get("citation_class") == "PRIMARY"
                and entry.get("row_id") not in (None, "")
                for entry in pc
            )
            if not primary_pam:
                report.failures.append(
                    "status='complete' requires at least one PRIMARY PAM-001 citation "
                    "with a non-empty row_id (Procurement Agent Spec §14 A-01)"
                )


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
