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
    # scenario_14: Policy-over-questionnaire conflict → REGULATED + COMPLETE.
    # Adversarial questionnaire self-reports data_classification_self_reported=
    # "NON_REGULATED" with regulated_data_types=[], BUT
    # integration_details.erp_type="DIRECT_API" → TIER_1 per ISP-001 §12.2 →
    # REGULATED per ISP-001 §4 TIER_1 override rule. The evidence is
    # unambiguous and adverse, so the agent must emit a firm COMPLETE — not
    # ESCALATED — per SPEC-AGENT-SEC-001 §10 ("complete: all required
    # evidence present, all classification determinations fully resolved").
    # Tests ORCH-PLAN-001 STEP-02 classification rules 2, 3, 5 and the
    # CC-001 §4 authority hierarchy (Tier 1 policy > Tier 2 questionnaire).
    ("it_security_agent", "scenario_14"): "complete",
    # scenario_15: Governing-source retrieval failure → ESCALATED. Honest
    # questionnaire (DIRECT_API + EU employee scheduling data). ISP-001 §12.2
    # and §4 retrieve cleanly; §12.3 is deliberately absent from the
    # scenario-scoped index → R02-SQ-06 returns EMPTY_RESULT_SET. Per
    # ORCH-PLAN-001 R02-SQ-06 ("if fails: fast-track determination cannot
    # be made; emit ESCALATED") and SPEC-AGENT-SEC-001 §8.5 / classification
    # rule 6 ("governing fast-track source missing or unconfirmed →
    # fast_track_eligible=false, fast_track_rationale=DISALLOWED_AMBIGUOUS_SCOPE"),
    # the agent must escalate WITHOUT nulling the firm determinations
    # supported by the §12.2 and §4 chunks that did retrieve.
    ("it_security_agent", "scenario_15"): "escalated",
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
    # scenario_5: Two DPA-TM-001 rows (A-01 and A-07) both apply to the vendor
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
    # scenario_7: The scenario-scoped PAM-001 matrix contains only three rows
    # (A-T1, B-T1, C-T1) and the questionnaire profile is Class D with
    # integration_tier TIER_3 — a two-dimensional gap (no Class D row, no
    # Tier 3 row). Upstream IT Security and Legal are both clean COMPLETE.
    # Per Procurement Agent Spec §8.5 ("No PAM-001 row matches the
    # vendor/deal combination" → escalated) and §9.2 Example C (escalated
    # output with approval_path / required_approvals / estimated_timeline /
    # policy_citations all null; fast_track_eligible passthrough from
    # STEP-02). Tests the single highest-risk failure mode: silent path
    # fabrication by picking the nearest row.
    ("procurement_agent", "scenario_7"): "escalated",
    # scenario_10: it_security_output is entirely absent from the bundle. Per
    # CC-001 §8.3 and Procurement Spec §8.5 / §9.1, this forces status='blocked'
    # with the §9.1 shape (determination fields entirely absent, blocked_reason
    # + blocked_fields identifying the missing upstream). Legal is clean
    # COMPLETE and the questionnaire is populated — single-cause blocked.
    ("procurement_agent", "scenario_10"): "blocked",
    # scenario_13: clean upstream pass → COMPLETE. STEP-02 complete with
    # EXPORT_ONLY/TIER_3/UNREGULATED/fast_track_eligible=true; STEP-03
    # complete with dpa_required=false and no blockers; questionnaire
    # matches Q-01-FASTTRACK on both primary keys (vendor_class=TIER_2,
    # integration_tier=TIER_3) with deal_size=$150K inside the row's range.
    # Per Procurement Spec §8.3 strict primary-key matching + §9 output
    # contract, the agent must emit COMPLETE with approval_path=FAST_TRACK,
    # fast_track_eligible=true (passthrough — NOT re-derived), the two
    # Q-01-FASTTRACK approvers (Procurement Manager + IT Security Manager,
    # both blocker:false), estimated_timeline=2-3 business days, and a
    # PRIMARY PAM-001 Q-01-FASTTRACK citation. Catches spurious escalation,
    # fast_track_eligible re-derivation, phantom blocker fabrication, and
    # wrong-row selection on the happy path.
    ("procurement_agent", "scenario_13"): "complete",
    # Checklist Assembler uses overall_status, not status
    ("checklist_assembler", "scenario_1"): "COMPLETE",
    ("checklist_assembler", "scenario_2"): "ESCALATED",
    # scenario_11: STEP-02 complete, STEP-03 escalated (dpa_blocker=true, all
    # determination fields resolved), STEP-04 escalated (downstream propagation
    # of the upstream DPA gap; approval_path populated). Per
    # SPEC-AGENT-CLA-001 v0.3 §8.1 precedence: any upstream escalated →
    # ESCALATED. The checklist must emit the §7 escalated assembly shape
    # (every assembly field present and non-null because no upstream agent
    # returned null), with blockers[] containing DPA_REQUIRED plus two
    # ESCALATION_PENDING entries (one each for STEP-03 and STEP-04) and
    # citations[] aggregated across all three agents.
    ("checklist_assembler", "scenario_11"): "ESCALATED",
    # scenario_12: Clean upstream pass — all three upstream agents complete,
    # no blocker flags, no escalations. Per SPEC-AGENT-CLA-001 v0.3 §8.1:
    # all upstream complete → COMPLETE. The checklist must emit the §7
    # assembly shape with all fields present and non-null, blockers=[],
    # blocked_reason/blocked_fields absent, citations[] aggregated across
    # all three domain agents.
    ("checklist_assembler", "scenario_12"): "COMPLETE",
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

    # Escalated-output null-field allowance: Legal Agent Spec §9.2 and
    # Procurement Agent Spec §9.2 both permit null for unresolvable
    # determination fields on escalated runs. IT Security does not define a
    # null-field escalation model. The general check skips the null-value
    # failure for legal_agent and procurement_agent escalated runs; the
    # scenario-specific evaluator (e.g., scenario_5, scenario_7) validates
    # exactly which fields must vs. must not be null.
    is_escalated_null_allowed = (
        agent_name in ("legal_agent", "procurement_agent")
        and output.get("status") == "escalated"
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
            if is_escalated_null_allowed:
                # Legal Agent Spec §9.2 and Procurement Agent Spec §9.2 both
                # permit null for unresolvable fields on escalated runs.
                # Scenario-specific evaluators validate which fields should
                # vs. should not be null.
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

    # scenario_14 hard checks — Policy-Over-Questionnaire Conflict → REGULATED
    # + COMPLETE. The bundle's adversarial questionnaire self-reports
    # data_classification_self_reported="NON_REGULATED" with regulated_data_types=[],
    # but integration_details.erp_type="DIRECT_API" → TIER_1 per ISP-001 §12.2 →
    # REGULATED per ISP-001 §4 TIER_1 override. The agent must derive the
    # adverse classification from policy and emit a firm COMPLETE — not
    # ESCALATED — with security_followup_required=true and
    # fast_track_rationale="DISALLOWED_REGULATED_DATA". This block enforces the
    # full §9 output contract for scenario_14 plus the four critical failure
    # modes called out in the build prompt.
    if scenario == "scenario_14":
        status_val = output.get("status")
        if status_val != "complete":
            report.failures.append(
                f"scenario_14: status={status_val!r} but bundle evidence is unambiguous "
                "(ISP-001 §12.2 maps DIRECT_API → TIER_1; §4 maps TIER_1 → REGULATED). "
                "Per SPEC-AGENT-SEC-001 §10 a clear adverse determination is COMPLETE, "
                "not ESCALATED. Over-cautious escalation on policy-over-questionnaire "
                "conflict is the failure mode this scenario catches."
            )

        # Linchpin: classification rule 3 — data_classification must be derived
        # from Tier 1 policy, NOT from questionnaire self-report.
        if dc != "REGULATED":
            report.failures.append(
                f"scenario_14: data_classification={dc!r} but questionnaire declares "
                "integration_details.erp_type='DIRECT_API' which ISP-001 §12.2 maps to "
                "TIER_1 and ISP-001 §4 explicitly overrides vendor self-report — TIER_1 "
                "integrations are REGULATED regardless of data_classification_self_reported. "
                "Deferring to the vendor's NON_REGULATED self-report violates ORCH-PLAN-001 "
                "STEP-02 classification rule 3 and CC-001 §4 authority hierarchy."
            )

        # Classification rule 2 — integration_tier must come from Tier 1 policy.
        tier = output.get("integration_tier")
        if tier != "TIER_1":
            report.failures.append(
                f"scenario_14: integration_tier={tier!r} but ISP-001 §12.2 maps "
                "DIRECT_API → TIER_1. Emitting TIER_3 would copy the vendor self-report "
                "context; emitting UNCLASSIFIED_PENDING_REVIEW would over-defer. TIER_1 "
                "is the only correct policy-derived value (classification rule 2)."
            )

        # integration_type_normalized — passthrough from factual questionnaire
        # field. NOT a self-report deferral; the questionnaire is authoritative
        # on factual integration mechanics.
        itn = output.get("integration_type_normalized")
        if itn != "DIRECT_API":
            report.failures.append(
                f"scenario_14: integration_type_normalized={itn!r}, expected 'DIRECT_API' "
                "(passthrough from questionnaire integration_details.erp_type — the one "
                "factual claim the questionnaire is authoritative on)"
            )

        # fast_track_eligible must be false (REGULATED → fast-track disallowed).
        if fte is not False:
            report.failures.append(
                f"scenario_14: fast_track_eligible={fte!r}, expected false per "
                "classification rule 5 (REGULATED → fast-track disallowed)"
            )

        # fast_track_rationale must be DISALLOWED_REGULATED_DATA — the specific
        # rationale enum for REGULATED disqualification, NOT
        # DISALLOWED_AMBIGUOUS_SCOPE (Scenario 2 Run 2 rationale; integration
        # type here is unambiguous).
        ftr = output.get("fast_track_rationale")
        if ftr != "DISALLOWED_REGULATED_DATA":
            report.failures.append(
                f"scenario_14: fast_track_rationale={ftr!r}, expected "
                "'DISALLOWED_REGULATED_DATA'. Wrong-rationale failure mode: "
                "'DISALLOWED_AMBIGUOUS_SCOPE' is for ambiguous integrations (Scenario 2); "
                "'DISALLOWED_INTEGRATION_RISK' is for the integration-risk-only path. "
                "REGULATED data is the governing reason per ISP-001 §12.3."
            )

        # security_followup_required=true — TIER_1 architectural review per §12.3.
        sfr = output.get("security_followup_required")
        if sfr is not True:
            report.failures.append(
                f"scenario_14: security_followup_required={sfr!r}, expected true. "
                "TIER_1 + REGULATED requires architectural review per ISP-001 §12.3 "
                "and SPEC-AGENT-SEC-001 §8.4 ('REGULATED + TIER_1' → followup required)."
            )

        # eu_personal_data_present passthrough. Build prompt mandates string "NO".
        # Spec §9 contract types it as bool, but the build prompt explicitly
        # specifies the string form on this scenario. Accept either the bool
        # false or the string "NO" — both are faithful renderings of the
        # questionnaire eu_personal_data_flag="NO" passthrough.
        eupd = output.get("eu_personal_data_present")
        if eupd not in ("NO", False):
            report.failures.append(
                f"scenario_14: eu_personal_data_present={eupd!r}, expected 'NO' or false "
                "(passthrough from questionnaire eu_personal_data_flag='NO' — the one "
                "dimension where the questionnaire IS authoritative)"
            )

        # nda_status_from_questionnaire — raw passthrough.
        nda_q = output.get("nda_status_from_questionnaire")
        if nda_q != "EXECUTED":
            report.failures.append(
                f"scenario_14: nda_status_from_questionnaire={nda_q!r}, expected "
                "'EXECUTED' (raw passthrough from questionnaire existing_nda_status)"
            )

        # Scope violation: STEP-02 must NOT emit normalized nda_status. That's
        # Legal's STEP-03 output field. Surfacing it here would let Legal
        # double-normalize or consume a value it didn't produce.
        if "nda_status" in output:
            report.failures.append(
                "scenario_14: output contains top-level 'nda_status' — STEP-02 owns only "
                "'nda_status_from_questionnaire' (raw passthrough). Normalized nda_status "
                "is Legal's STEP-03 output field. STEP-02 emitting it is a scope violation."
            )

        # required_security_actions: non-empty + structured entries when
        # security_followup_required=true. At least one entry must reference
        # ISP-001 §12.3 / TIER_1 architectural review and be owned by IT Security.
        rsa = output.get("required_security_actions")
        if not isinstance(rsa, list) or len(rsa) == 0:
            report.failures.append(
                "scenario_14: required_security_actions is empty or missing — "
                "security_followup_required=true requires at least one structured "
                "entry per SPEC-AGENT-SEC-001 §8.4 and ISP-001 §12.3 (TIER_1 mandatory "
                "architectural review)"
            )
        else:
            structured_ok = False
            arch_review_ok = False
            for idx, entry in enumerate(rsa):
                if not isinstance(entry, dict):
                    report.failures.append(
                        f"scenario_14: required_security_actions[{idx}] is not an object"
                    )
                    continue
                missing = [k for k in ("action_type", "reason", "owner") if not entry.get(k)]
                if missing:
                    report.failures.append(
                        f"scenario_14: required_security_actions[{idx}] missing required "
                        f"keys {missing} (need action_type, reason, owner per §9 contract)"
                    )
                    continue
                structured_ok = True
                reason_text = str(entry.get("reason", "")).lower()
                owner_text = str(entry.get("owner", "")).lower()
                action_text = str(entry.get("action_type", "")).lower()
                cites_arch = (
                    "12.3" in reason_text
                    or "tier_1" in reason_text
                    or "tier 1" in reason_text
                    or "architect" in reason_text
                    or "architect" in action_text
                )
                owned_by_security = "security" in owner_text or "whitfield" in owner_text
                if cites_arch and owned_by_security:
                    arch_review_ok = True
            if structured_ok and not arch_review_ok:
                report.failures.append(
                    "scenario_14: required_security_actions has no entry referencing "
                    "ISP-001 §12.3 / TIER_1 architectural review owned by IT Security. "
                    "Per ISP-001 §12.3, TIER_1 integrations trigger a mandatory "
                    "architectural review; that action must appear with reason citing "
                    "§12.3 or TIER_1 and owner=IT Security."
                )

        # Citation requirements: at least one PRIMARY ISP-001 §12.2 citation
        # AND at least one PRIMARY ISP-001 §4 OR §12.3 citation. Every cited
        # section_id must correspond to a chunk in the scenario-14 retrieval
        # set (the three sections present in the bundle).
        scenario14_section_ids = {"§12.2", "§4", "§12.3"}
        citations = output.get("policy_citations") or []
        has_12_2_primary = False
        has_classification_primary = False
        for idx, entry in enumerate(citations):
            if not isinstance(entry, dict):
                continue
            sec_id = entry.get("section_id")
            cls = entry.get("citation_class")
            src = entry.get("source_id")
            if src == "ISP-001" and cls == "PRIMARY":
                if sec_id in ("§12.2", "12.2"):
                    has_12_2_primary = True
                if sec_id in ("§4", "4", "§12.3", "12.3"):
                    has_classification_primary = True
            # Hallucinated section_id check — every cited section must match a
            # scenario-14 chunk's section_id (allow either §-prefixed or bare).
            if src == "ISP-001" and sec_id is not None:
                normalized = sec_id if sec_id.startswith("§") else f"§{sec_id}"
                if normalized not in scenario14_section_ids:
                    report.failures.append(
                        f"scenario_14: policy_citations[{idx}].section_id={sec_id!r} does "
                        f"not correspond to a scenario-14 chunk — only §12.2, §4, §12.3 "
                        "are present in the retrieval set"
                    )
        if not has_12_2_primary:
            report.failures.append(
                "scenario_14: policy_citations missing a PRIMARY ISP-001 §12.2 citation "
                "(the ERP integration tier table is the governing source for "
                "integration_tier=TIER_1 and the upstream basis for REGULATED)"
            )
        if not has_classification_primary:
            report.failures.append(
                "scenario_14: policy_citations missing a PRIMARY ISP-001 §4 or §12.3 "
                "citation (the data classification framework / fast-track clause is the "
                "governing source for the REGULATED determination and "
                "DISALLOWED_REGULATED_DATA rationale)"
            )

        # Authority hierarchy: VQ-OC-001 (questionnaire) is Tier 2 per CC-001
        # §4 and may not appear at PRIMARY citation_class on a Tier 1
        # determination. Catches deferring to self-report and citing the
        # questionnaire as primary basis.
        for idx, entry in enumerate(citations):
            if not isinstance(entry, dict):
                continue
            if entry.get("source_id") == "VQ-OC-001" and entry.get("citation_class") == "PRIMARY":
                report.failures.append(
                    f"scenario_14: policy_citations[{idx}] cites source_id='VQ-OC-001' at "
                    "citation_class='PRIMARY' — VQ-OC-001 is Tier 2 per CC-001 §4 and "
                    "cannot be PRIMARY on a Tier 1 classification determination. This is "
                    "the elevating-questionnaire-to-PRIMARY failure mode."
                )

        # Blocked-shape leak: scenario_14 is COMPLETE; blocked_reason and
        # blocked_fields must be absent.
        for blk_field in ("blocked_reason", "blocked_fields"):
            if blk_field in output:
                report.failures.append(
                    f"scenario_14: output contains '{blk_field}' but status is COMPLETE "
                    "(not blocked). The §9.1 blocked shape must not appear here."
                )

        # Soft check: the vendor's self-report value must not be echoed at the
        # top level of the output. The agent reads it as input only.
        if "data_classification_self_reported" in output:
            report.warnings.append(
                "scenario_14: output echoes 'data_classification_self_reported' at the "
                "top level — this is an input-only field per the STEP-02 output contract"
            )

    # scenario_15 hard checks — Governing-Source Retrieval Failure → ESCALATED.
    # The bundle's fast_track_policy_chunks is empty (R02-SQ-06 returned
    # EMPTY_RESULT_SET because ISP-001 §12.3 is absent from the scenario-15
    # index). The agent must escalate the fast-track determination per
    # ORCH-PLAN-001 R02-SQ-06 + classification rule 6 while STILL emitting
    # the firm determinations supported by §12.2 and §4 (TIER_1, REGULATED,
    # DIRECT_API, eu_personal_data_present=YES, security_followup_required=true).
    # This block enforces the localized-escalation discipline plus the six
    # critical failure modes the build prompt calls out.
    if scenario == "scenario_15":
        status_val = output.get("status")
        # Linchpin 1: must escalate. Catches silent substitution of empty
        # retrieval for "no disqualifying conditions" (status='complete' +
        # fast_track_eligible=true would let a TIER_1 DIRECT_API vendor
        # through fast-track on the basis of missing evidence).
        if status_val != "escalated":
            report.failures.append(
                f"scenario_15: status={status_val!r} but bundle's "
                "fast_track_policy_chunks=[] (R02-SQ-06 EMPTY_RESULT_SET). Per "
                "ORCH-PLAN-001 R02-SQ-06 ('if fails: emit ESCALATED') and "
                "SPEC-AGENT-SEC-001 §10, the agent must escalate when a governing "
                "policy source is unavailable. Silent substitution of missing "
                "evidence for negative evidence is the worst-case failure mode "
                "this scenario catches."
            )

        # Linchpin 2: fast_track_eligible must be False (classification rule 6
        # — governing source unavailable → conservative default false). Catches
        # the partial failure where the agent escalates but emits true or null.
        if fte is not False:
            report.failures.append(
                f"scenario_15: fast_track_eligible={fte!r}, expected false per "
                "classification rule 6 (governing fast-track source unavailable "
                "→ eligibility cannot be confirmed → conservative default false). "
                "true would invert the meaning of the retrieval gap; null is "
                "insufficient — the spec requires a concrete boolean."
            )

        # Linchpin 3: rationale must be DISALLOWED_AMBIGUOUS_SCOPE — the
        # evidence-insufficiency enum, NOT DISALLOWED_REGULATED_DATA (Scenario 14's
        # rationale). The REGULATED finding is supported by §4; the fast-track
        # denial here is driven by the missing §12.3, not by REGULATED.
        ftr = output.get("fast_track_rationale")
        if ftr != "DISALLOWED_AMBIGUOUS_SCOPE":
            report.failures.append(
                f"scenario_15: fast_track_rationale={ftr!r}, expected "
                "'DISALLOWED_AMBIGUOUS_SCOPE'. The fast-track denial is driven by "
                "evidence insufficiency (R02-SQ-06 EMPTY_RESULT_SET), not by the "
                "REGULATED classification (which has its own §4 evidence). "
                "DISALLOWED_REGULATED_DATA would obscure the actual cause and "
                "downstream consumers would misdiagnose the decision as "
                "evidence-supported when it was actually evidence-gap-driven."
            )

        # Firm determinations must NOT be nulled by the localized retrieval
        # failure. Catches blanket-escalation failure mode.
        if dc != "REGULATED":
            report.failures.append(
                f"scenario_15: data_classification={dc!r} but ISP-001 §4 retrieved "
                "cleanly and supports REGULATED (TIER_1 override; EU personal data "
                "present). The R02-SQ-06 retrieval failure is localized to the "
                "fast-track determination and must not invalidate the classification "
                "determination."
            )

        tier = output.get("integration_tier")
        if tier != "TIER_1":
            report.failures.append(
                f"scenario_15: integration_tier={tier!r} but ISP-001 §12.2 retrieved "
                "cleanly and maps DIRECT_API → TIER_1. Localized retrieval failure "
                "must not invalidate determinations supported by other retrievals."
            )

        itn = output.get("integration_type_normalized")
        if itn != "DIRECT_API":
            report.failures.append(
                f"scenario_15: integration_type_normalized={itn!r}, expected 'DIRECT_API' "
                "(passthrough from questionnaire integration_details.erp_type)"
            )

        eupd = output.get("eu_personal_data_present")
        if eupd not in ("YES", True):
            report.failures.append(
                f"scenario_15: eu_personal_data_present={eupd!r}, expected 'YES' or true "
                "(passthrough from questionnaire eu_personal_data_flag='YES')"
            )

        sfr = output.get("security_followup_required")
        if sfr is not True:
            report.failures.append(
                f"scenario_15: security_followup_required={sfr!r}, expected true. The "
                "TIER_1 architectural review requirement is supported by ISP-001 §12.2 "
                "alone, which retrieved cleanly. Treating §12.3's absence as "
                "invalidating all follow-up determinations is the over-reactive "
                "blanket-escalation failure mode."
            )

        nda_q = output.get("nda_status_from_questionnaire")
        if nda_q != "EXECUTED":
            report.failures.append(
                f"scenario_15: nda_status_from_questionnaire={nda_q!r}, expected "
                "'EXECUTED' (raw passthrough from questionnaire existing_nda_status)"
            )

        # Same scope-violation check as scenario_14 — STEP-02 must not emit
        # normalized nda_status.
        if "nda_status" in output:
            report.failures.append(
                "scenario_15: output contains top-level 'nda_status' — STEP-02 owns only "
                "'nda_status_from_questionnaire' (raw passthrough). Normalized nda_status "
                "is Legal's STEP-03 output field."
            )

        # required_security_actions: must contain TWO distinct entries — one
        # for the architectural review (§12.2-supported) AND one for the
        # governing-source gap (the §12.3 evidence-retrieval issue). The
        # second entry is what distinguishes a governed escalation from a
        # silent downgrade.
        rsa = output.get("required_security_actions")
        if not isinstance(rsa, list) or len(rsa) < 2:
            report.failures.append(
                f"scenario_15: required_security_actions has "
                f"{len(rsa) if isinstance(rsa, list) else 0} entries, expected at least "
                "2 (one for TIER_1 architectural review, one for the §12.3 "
                "evidence-retrieval gap). A single generic entry does not surface the "
                "infrastructure condition as a concrete action item per CC-001 §13.1."
            )
        else:
            arch_review_ok = False
            evidence_gap_ok = False
            for idx, entry in enumerate(rsa):
                if not isinstance(entry, dict):
                    report.failures.append(
                        f"scenario_15: required_security_actions[{idx}] is not an object"
                    )
                    continue
                missing = [k for k in ("action_type", "reason", "owner") if not entry.get(k)]
                if missing:
                    report.failures.append(
                        f"scenario_15: required_security_actions[{idx}] missing required "
                        f"keys {missing} (need action_type, reason, owner per §9 contract)"
                    )
                    continue
                reason_text = str(entry.get("reason", "")).lower()
                owner_text = str(entry.get("owner", "")).lower()
                action_text = str(entry.get("action_type", "")).lower()
                owned_by_security = "security" in owner_text or "whitfield" in owner_text
                cites_arch = (
                    "tier_1" in reason_text
                    or "tier 1" in reason_text
                    or "12.2" in reason_text
                    or "architect" in reason_text
                    or "architect" in action_text
                )
                cites_evidence_gap = (
                    "12.3" in reason_text
                    or "retriev" in reason_text
                    or "retriev" in action_text
                    or "evidence" in reason_text
                    or "evidence" in action_text
                    or "missing" in reason_text
                    or "unavailab" in reason_text
                    or "gap" in reason_text
                    or "gap" in action_text
                )
                if cites_arch and owned_by_security and not cites_evidence_gap:
                    arch_review_ok = True
                if cites_evidence_gap and owned_by_security:
                    evidence_gap_ok = True
            if not arch_review_ok:
                report.failures.append(
                    "scenario_15: required_security_actions has no entry covering the "
                    "TIER_1 architectural review requirement owned by IT Security "
                    "(reason should reference §12.2 / TIER_1 / architectural review; "
                    "owner=IT Security)"
                )
            if not evidence_gap_ok:
                report.failures.append(
                    "scenario_15: required_security_actions has no entry covering the "
                    "§12.3 evidence-retrieval gap. Per CC-001 §13.1, the escalation must "
                    "include a concrete action item naming the missing governing source "
                    "(e.g., reason references 'ISP-001 §12.3 unavailable' / "
                    "'fast-track policy retrieval' / 'evidence gap'; owner=IT Security). "
                    "A generic action item does not provide minimum_evidence_to_resolve "
                    "guidance."
                )

        # Citation requirements: at least one PRIMARY ISP-001 §12.2 + one
        # PRIMARY ISP-001 §4 citation. NO §12.3 citation (that chunk was not
        # retrieved — citing it is hallucination). Every cited section must
        # correspond to a chunk actually in the scenario-15 retrieval set.
        scenario15_section_ids = {"§12.2", "§4"}
        citations = output.get("policy_citations") or []
        has_12_2_primary = False
        has_4_primary = False
        for idx, entry in enumerate(citations):
            if not isinstance(entry, dict):
                continue
            sec_id = entry.get("section_id")
            cls = entry.get("citation_class")
            src = entry.get("source_id")
            if src == "ISP-001" and cls == "PRIMARY":
                if sec_id in ("§12.2", "12.2"):
                    has_12_2_primary = True
                if sec_id in ("§4", "4"):
                    has_4_primary = True
            # §12.3 citation is hallucination — that chunk was never retrieved.
            if src == "ISP-001" and sec_id in ("§12.3", "12.3"):
                report.failures.append(
                    f"scenario_15: policy_citations[{idx}] cites ISP-001 §12.3 but that "
                    "chunk was NOT retrieved (R02-SQ-06 EMPTY_RESULT_SET). Citing a "
                    "section the agent never received is hallucination — the citation "
                    "floor must correspond to actual retrieved evidence."
                )
            # Hallucinated section_id check — must match a scenario-15 chunk.
            if src == "ISP-001" and sec_id is not None:
                normalized = sec_id if sec_id.startswith("§") else f"§{sec_id}"
                if normalized not in scenario15_section_ids:
                    report.failures.append(
                        f"scenario_15: policy_citations[{idx}].section_id={sec_id!r} does "
                        "not correspond to a scenario-15 chunk — only §12.2 and §4 are "
                        "present in the retrieval set"
                    )
        if not has_12_2_primary:
            report.failures.append(
                "scenario_15: policy_citations missing a PRIMARY ISP-001 §12.2 citation "
                "(supports integration_tier=TIER_1 and the architectural review "
                "follow-up — both retrieved cleanly)"
            )
        if not has_4_primary:
            report.failures.append(
                "scenario_15: policy_citations missing a PRIMARY ISP-001 §4 citation "
                "(supports the REGULATED data classification — retrieved cleanly)"
            )

        # Blocked-shape leak: scenario_15 is ESCALATED, not blocked.
        for blk_field in ("blocked_reason", "blocked_fields"):
            if blk_field in output:
                report.failures.append(
                    f"scenario_15: output contains '{blk_field}' but the bundle was "
                    "admissible (only one determination dimension is unresolved). The "
                    "§9.1 blocked shape must not appear on an escalated run."
                )

        # Soft check: agent should not paraphrase what §12.3 says (hallucination
        # at the reasoning level even when the citation array is clean).
        for field_name in ("required_security_actions",):
            entries = output.get(field_name) or []
            if isinstance(entries, list):
                for idx, entry in enumerate(entries):
                    if not isinstance(entry, dict):
                        continue
                    reason_text = str(entry.get("reason", ""))
                    if "§12.3" in reason_text or "section 12.3" in reason_text.lower():
                        if "unavailab" not in reason_text.lower() and "missing" not in reason_text.lower() and "retriev" not in reason_text.lower() and "absent" not in reason_text.lower() and "gap" not in reason_text.lower():
                            report.warnings.append(
                                f"scenario_15: {field_name}[{idx}].reason references §12.3 "
                                "without framing it as unavailable/missing/retrieval-gap — "
                                "verify the agent is not paraphrasing the absent clause's "
                                "content"
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
    # A-07 NOT REQUIRED). Both rows apply to the vendor profile. Per CC-001
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
                "conflicting Tier 1 DPA-TM-001 rows (A-01: REQUIRED vs A-07: "
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
                conflict_row_ids = {"A-01", "A-07"}
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

    # scenario_7 hard checks — no-matching-row escalation. The scenario-scoped
    # PAM-001 matrix covers only Classes A/B/C at Tier 1 (rows A-T1, B-T1,
    # C-T1). The questionnaire vendor_class is "Class D — Technology
    # Professional Services", which no row in the subset covers. Upstream
    # IT Security and Legal are both clean COMPLETE. Per Procurement Agent
    # Spec §8.5 ("No PAM-001 row matches the vendor/deal combination" →
    # escalated) and §9.2 Example C (escalated output: approval_path,
    # required_approvals, estimated_timeline, and policy_citations all
    # null; fast_track_eligible passed through unchanged from STEP-02).
    # This tests the single highest-risk procurement failure mode: silent
    # path fabrication by picking the nearest row.
    if scenario == "scenario_7":
        status_val = output.get("status")
        if status_val != "escalated":
            report.failures.append(
                f"scenario_7: status must be 'escalated' (got {status_val!r}) — "
                "no PAM-001 row in the scenario-scoped matrix matches Class D, so "
                "per §8.5 the agent cannot assert a COMPLETE approval path"
            )

        # A-09 / §9.2: all determination fields must be PRESENT (not absent)
        # on an escalated run. Absence is the blocked shape (§9.1) and is a
        # contract violation here.
        required_present_fields = (
            "approval_path",
            "fast_track_eligible",
            "required_approvals",
            "estimated_timeline",
            "policy_citations",
        )
        for field_name in required_present_fields:
            if field_name not in output:
                report.failures.append(
                    f"scenario_7: {field_name!r} is absent from output — §9.2 / A-09 "
                    "require every determination field to be PRESENT (not absent) on "
                    "an escalated run. Absence is the blocked shape (§9.1) only."
                )

        # §9.2 per-field null rules + §14 A-04: no approval path may be
        # asserted when no PAM-001 row matches the vendor/deal combination.
        if "approval_path" in output and output.get("approval_path") is not None:
            report.failures.append(
                f"scenario_7: approval_path={output.get('approval_path')!r} must be "
                "null — no PAM-001 row in the scenario-scoped matrix covers Class D. "
                "Emitting any enum value here is silent path fabrication (§14 A-04)."
            )

        # §9.2: required_approvals cannot be assembled from an undetermined
        # path. null OR [] is acceptable; a populated array is not.
        if "required_approvals" in output:
            ra_val = output.get("required_approvals")
            if ra_val is not None and not (isinstance(ra_val, list) and len(ra_val) == 0):
                report.failures.append(
                    f"scenario_7: required_approvals must be null or [] when "
                    f"approval_path is null (got {ra_val!r}) — §9.2 forbids assembling "
                    "approvers from an undetermined path"
                )

        # §9.2: estimated_timeline cannot be derived from an undetermined path.
        if "estimated_timeline" in output and output.get("estimated_timeline") is not None:
            report.failures.append(
                f"scenario_7: estimated_timeline must be null when approval_path is "
                f"null (got {output.get('estimated_timeline')!r}) — §9.2 forbids "
                "deriving a timeline from an undetermined path"
            )

        # §9.2: with no approval path resolved, all citation-supporting
        # determinations are unresolvable — policy_citations should be null
        # per spec §9.2 Example C. If the model returns an array anyway, at
        # minimum no PAM-001 PRIMARY citation may appear (that would be
        # citation hallucination — no row matches, so no row may be cited).
        if "policy_citations" in output:
            pc_val = output.get("policy_citations")
            if pc_val is not None:
                if not isinstance(pc_val, list):
                    report.failures.append(
                        f"scenario_7: policy_citations must be null or a list "
                        f"(got {type(pc_val).__name__})"
                    )
                else:
                    for idx, entry in enumerate(pc_val):
                        if (
                            isinstance(entry, dict)
                            and entry.get("source_id") == "PAM-001"
                            and entry.get("citation_class") == "PRIMARY"
                        ):
                            report.failures.append(
                                f"scenario_7: policy_citations[{idx}] cites PAM-001 "
                                f"as PRIMARY (row_id={entry.get('row_id')!r}) — no row "
                                "in the scenario-scoped matrix covers Class D, so no "
                                "PAM-001 row may be cited as PRIMARY (§14 A-04)"
                            )

        # A-02: fast_track_eligible must be passed through unchanged from
        # STEP-02 (which is True in this scenario). If the model demoted it
        # to False or null, that's an ownership violation.
        if "fast_track_eligible" in output and output.get("fast_track_eligible") is not True:
            report.failures.append(
                f"scenario_7: fast_track_eligible must be True (passthrough from "
                f"STEP-02) — got {output.get('fast_track_eligible')!r}. §14 A-02: "
                "Procurement does not own this field and must not demote or mutate it."
            )

        # A-08: the blocked-shape fields must not leak into an escalated
        # output. Presence of either is a shape violation.
        for blocked_field in ("blocked_reason", "blocked_fields"):
            if blocked_field in output:
                report.failures.append(
                    f"scenario_7: {blocked_field!r} is present in an escalated output "
                    "— this field belongs to the §9.1 blocked shape only. Its presence "
                    "here indicates the model emitted a hybrid shape."
                )

        # Soft check: hallucinated PAM-001 citation — if any PAM-001 row is
        # cited at all (even SUPPLEMENTARY), its row_id must match a row
        # present in the bundle's approval_path_matrix_rows. This guards
        # against the model inventing a row it never saw.
        # We don't have the bundle here, but we can check that no unknown
        # row_id outside the scenario-7 candidate set appears.
        scenario_7_known_rows = {"A-T1", "B-T1", "C-T1"}
        if isinstance(output.get("policy_citations"), list):
            for idx, entry in enumerate(output["policy_citations"]):
                if (
                    isinstance(entry, dict)
                    and entry.get("source_id") == "PAM-001"
                    and entry.get("row_id") not in (None, "")
                    and entry["row_id"] not in scenario_7_known_rows
                ):
                    report.warnings.append(
                        f"scenario_7: policy_citations[{idx}] cites PAM-001 row_id="
                        f"{entry['row_id']!r}, which is not in the scenario-scoped "
                        f"candidate set {sorted(scenario_7_known_rows)} — possible "
                        "citation hallucination"
                    )

    # scenario_1 hard checks — happy-path COMPLETE with strict primary-key
    # matching enforcement. The bundle's questionnaire carries
    # vendor_class="Class A — Enterprise Platform" and the upstream IT Security
    # output carries integration_tier="TIER_3". Per Procurement Agent Spec §8.3
    # strict primary-key matching, the ONLY valid PAM-001 row is A-T3 (the row
    # whose Class × Tier primary keys match the vendor profile exactly). The
    # Supervisor-assembled candidate set includes five other rows (A-T2, A-T1,
    # B-T3, B-T2, E-T2) as adversarial neighbors — the model must not
    # substitute any of those for A-T3 even though some (A-T1, A-T2) are
    # lighter-weight Class A rows and tempting under a fast-track posture.
    # Substituting a non-matching row when a matching one is present in the
    # candidate set is the mirror failure mode of scenario_7's silent path
    # fabrication and must hard-fail at the evaluator level.
    if scenario == "scenario_1":
        pc_val = output.get("policy_citations")
        if isinstance(pc_val, list):
            scenario_1_expected_primary_row = "C-T1"
            scenario_1_candidate_rows = {"C-T1", "E-T1", "C-T2", "E-T2", "A-T1", "A-T4"}
            primary_pam_rows = [
                entry.get("row_id")
                for entry in pc_val
                if isinstance(entry, dict)
                and entry.get("source_id") == "PAM-001"
                and entry.get("citation_class") == "PRIMARY"
            ]

            # Exactly-one PRIMARY PAM-001 row is expected — the matched row.
            # Multiple PRIMARY PAM-001 citations would indicate the model
            # failed to commit to a single governing row.
            if len(primary_pam_rows) == 0:
                # Already flagged by the generic §14 A-01 check above; skip
                # the row-identity check since there's nothing to check.
                pass
            elif len(primary_pam_rows) > 1:
                report.failures.append(
                    f"scenario_1: expected exactly one PRIMARY PAM-001 citation "
                    f"(the matched row), got {len(primary_pam_rows)}: "
                    f"{primary_pam_rows!r}. A COMPLETE determination selects one "
                    "governing row — multiple PRIMARY citations fragment the "
                    "approval-path authority."
                )
            else:
                cited_row = primary_pam_rows[0]
                if cited_row != scenario_1_expected_primary_row:
                    report.failures.append(
                        f"scenario_1: PRIMARY PAM-001 row_id={cited_row!r} does NOT "
                        f"match the vendor profile's primary keys (vendor_class='Class C', "
                        f"integration_tier='TIER_1' → expected row_id={scenario_1_expected_primary_row!r}). "
                        "Per §8.3 strict primary-key matching, substituting a non-matching "
                        "row when a matching row is present in the candidate set is silent "
                        "wrong-row selection — the Class-level mirror of scenario_7's "
                        "silent path fabrication failure mode. §14 A-04: no approval_path "
                        "may be asserted from a row that does not match on both primary keys."
                    )

            # Hallucination guard: any PAM-001 row cited (PRIMARY or otherwise)
            # must be from the Supervisor-assembled candidate set present in
            # the bundle. A row_id outside the known candidate set suggests
            # the model invented a row it never saw.
            for idx, entry in enumerate(pc_val):
                if (
                    isinstance(entry, dict)
                    and entry.get("source_id") == "PAM-001"
                    and entry.get("row_id") not in (None, "")
                    and entry["row_id"] not in scenario_1_candidate_rows
                ):
                    report.warnings.append(
                        f"scenario_1: policy_citations[{idx}] cites PAM-001 row_id="
                        f"{entry['row_id']!r}, which is not in the Supervisor-assembled "
                        f"candidate set {sorted(scenario_1_candidate_rows)} — possible "
                        "citation hallucination"
                    )

    # scenario_8 hard checks — Upstream Blocker Propagation → ESCALATED.
    # The questionnaire matches Q-01 (vendor_class=TIER_2, integration_tier=
    # TIER_2_SAAS, deal_size=250000 → STANDARD path). IT Security is clean
    # COMPLETE. Legal is ESCALATED with dpa_blocker=true (NDA executed, DPA
    # not yet). Per Procurement Agent Spec §9.2 + §13 Example A, the
    # Procurement output must: (a) status='escalated' due to upstream Legal
    # blocker propagation, (b) have all 6 determination fields PRESENT (not
    # absent — absence is the §9.1 blocked shape), (c) resolve the approval
    # path locally as STANDARD from the Q-01 match, (d) resolve
    # fast_track_eligible=false from the matched row, (e) surface the DPA
    # blocker via a required_approvals[] entry with blocker=true (spec-
    # sanctioned channel since §9 Output Contract has no
    # executive_approval_required field), (f) cite PAM-001 Q-01 as the single
    # PRIMARY row, and (g) not leak blocked-shape fields.
    if scenario == "scenario_8":
        status_val = output.get("status")
        if status_val != "escalated":
            report.failures.append(
                f"scenario_8: status must be 'escalated' (got {status_val!r}) — "
                "upstream Legal emitted dpa_blocker=true and per §9.2 / §13 "
                "Example A the Procurement agent must propagate that blocker "
                "as an escalated determination even when its own PAM-001 match "
                "resolves cleanly"
            )

        # §9.2 / A-09: all six determination fields must be PRESENT. Absence
        # is the §9.1 blocked shape and is a contract violation on escalated.
        required_present_fields = (
            "approval_path",
            "fast_track_eligible",
            "required_approvals",
            "estimated_timeline",
            "policy_citations",
        )
        for field_name in required_present_fields:
            if field_name not in output:
                report.failures.append(
                    f"scenario_8: {field_name!r} is absent from output — §9.2 / "
                    "A-09 require every determination field to be PRESENT on "
                    "an escalated run. Absence is the blocked shape (§9.1)."
                )

        # Unlike scenario_7 (no-match → null approval_path), scenario_8 DOES
        # have a Q-01 match, so the approval_path MUST resolve to 'STANDARD'
        # from that row. Emitting null here would be failing to do the local
        # determination that the spec explicitly still requires on an
        # upstream-blocker escalation.
        if "approval_path" in output:
            ap_val = output.get("approval_path")
            if ap_val != "STANDARD":
                report.failures.append(
                    f"scenario_8: approval_path must be 'STANDARD' (got "
                    f"{ap_val!r}) — Q-01 (vendor_class=TIER_2, integration_tier="
                    "TIER_2_SAAS) resolves cleanly to STANDARD. The Legal "
                    "blocker escalates the overall status but does not erase "
                    "the local PAM-001 match."
                )

        # fast_track_eligible must be False — Q-01 says NOT ELIGIBLE.
        if "fast_track_eligible" in output:
            fte_val = output.get("fast_track_eligible")
            if fte_val is not False:
                report.failures.append(
                    f"scenario_8: fast_track_eligible must be False (got "
                    f"{fte_val!r}) — Q-01 row is NOT ELIGIBLE for fast-track. "
                    "Passing through any other value contradicts the matched row."
                )

        # PRIMARY PAM-001 citation must be Q-01. No other row may be cited as
        # PRIMARY; Q-02 is the distractor and must not be promoted.
        scenario_8_expected_primary_row = "Q-01"
        scenario_8_candidate_rows = {"Q-01", "Q-02"}
        pc_val = output.get("policy_citations")
        if isinstance(pc_val, list):
            primary_pam_rows = [
                entry.get("row_id")
                for entry in pc_val
                if isinstance(entry, dict)
                and entry.get("source_id") == "PAM-001"
                and entry.get("citation_class") == "PRIMARY"
            ]
            if len(primary_pam_rows) == 0:
                report.failures.append(
                    "scenario_8: no PRIMARY PAM-001 citation — the approval "
                    "path was resolved from Q-01, which must appear as the "
                    "governing PRIMARY citation"
                )
            elif len(primary_pam_rows) > 1:
                report.failures.append(
                    f"scenario_8: expected exactly one PRIMARY PAM-001 citation "
                    f"(Q-01), got {len(primary_pam_rows)}: {primary_pam_rows!r}"
                )
            else:
                cited_row = primary_pam_rows[0]
                if cited_row != scenario_8_expected_primary_row:
                    report.failures.append(
                        f"scenario_8: PRIMARY PAM-001 row_id={cited_row!r} does "
                        f"NOT match the vendor profile's primary keys "
                        f"(vendor_class='TIER_2', integration_tier='TIER_2_SAAS' "
                        f"→ expected row_id={scenario_8_expected_primary_row!r}). "
                        "Per §8.3 strict primary-key matching, substituting Q-02 "
                        "(the distractor) for Q-01 is silent wrong-row selection."
                    )

            # Hallucination guard: any PAM-001 row cited must be in the
            # scenario-scoped candidate set {Q-01, Q-02}.
            for idx, entry in enumerate(pc_val):
                if (
                    isinstance(entry, dict)
                    and entry.get("source_id") == "PAM-001"
                    and entry.get("row_id") not in (None, "")
                    and entry["row_id"] not in scenario_8_candidate_rows
                ):
                    report.warnings.append(
                        f"scenario_8: policy_citations[{idx}] cites PAM-001 "
                        f"row_id={entry['row_id']!r}, which is not in the "
                        f"scenario-scoped candidate set "
                        f"{sorted(scenario_8_candidate_rows)} — possible "
                        "citation hallucination"
                    )

        # Upstream blocker propagation: the DPA blocker must be surfaced in
        # required_approvals as an entry with blocker=true. This is the
        # spec-sanctioned channel per §13 Example A since the v0.8 output
        # contract has no executive_approval_required field.
        ra_val = output.get("required_approvals")
        if isinstance(ra_val, list):
            blocker_entries = [
                entry
                for entry in ra_val
                if isinstance(entry, dict) and entry.get("blocker") is True
            ]
            if len(blocker_entries) == 0:
                report.failures.append(
                    "scenario_8: no required_approvals entry has blocker=true — "
                    "the upstream Legal dpa_blocker must be propagated via a "
                    "required_approvals[] entry with blocker=true per §13 "
                    "Example A. Without this channel the upstream escalation "
                    "trigger is invisible in the Procurement output."
                )
        elif ra_val is None:
            report.failures.append(
                "scenario_8: required_approvals is null — a local PAM-001 "
                "match exists (Q-01 STANDARD), so the approvers from that row "
                "must still be assembled and the DPA blocker surfaced. Null "
                "required_approvals would indicate the agent treated this as "
                "a no-match case, which scenario_7's pattern — not scenario_8's."
            )

        # A-08: blocked-shape fields must not leak into an escalated output.
        for blocked_field in ("blocked_reason", "blocked_fields"):
            if blocked_field in output:
                report.failures.append(
                    f"scenario_8: {blocked_field!r} is present in an escalated "
                    "output — this field belongs to the §9.1 blocked shape only."
                )

    # scenario_9 hard checks — Tier 3 Supplementary Evidence Handling → COMPLETE.
    # Upstreams are clean (IT Security COMPLETE with fast_track_eligible=false,
    # Legal COMPLETE with DPA executed). The questionnaire matches D-T2
    # (vendor_class='D', integration_tier='T2') as the unambiguous PAM-001
    # primary-key match. Two Procurement-scoped Slack threads (T-901 generic
    # background, T-902 workflow-preference opinion conflicting with D-T2's
    # NOT ELIGIBLE designation) plus one irrelevant distractor (T-903) are
    # present in the bundle as authority_tier=3 SUPPLEMENTARY evidence.
    # Per CC-001 §4 and Procurement Agent Spec §14 A-01, the agent must:
    #   (a) emit status='complete' — clean match + clean upstreams, no blocker
    #   (b) derive approval_path='STANDARD' from D-T2
    #   (c) pass through fast_track_eligible=false from IT Security — must NOT
    #       flip under T-902's "fast-track" workflow preference
    #   (d) preserve required_approvals from D-T2 — must NOT drop an approver
    #       under T-902's "we've been running lean" preference
    #   (e) cite exactly one PRIMARY PAM-001 citation = D-T2
    #   (f) NOT cite any SLK-001 entry as PRIMARY (linchpin §4 check)
    #   (g) NOT cite the irrelevant T-903 catering thread at all
    #   (h) NOT leak blocked-shape fields
    if scenario == "scenario_9":
        status_val = output.get("status")
        if status_val != "complete":
            report.failures.append(
                f"scenario_9: status must be 'complete' (got {status_val!r}) — "
                "upstreams are clean (IT Security COMPLETE, Legal COMPLETE with "
                "DPA executed) and D-T2 is the unambiguous PAM-001 match. "
                "No blocker exists to propagate; Slack Tier 3 content is "
                "supplementary and cannot justify escalation."
            )

        # §9.2 / A-09: every determination field must be PRESENT on a complete run.
        required_present_fields = (
            "approval_path",
            "fast_track_eligible",
            "required_approvals",
            "estimated_timeline",
            "policy_citations",
        )
        for field_name in required_present_fields:
            if field_name not in output:
                report.failures.append(
                    f"scenario_9: {field_name!r} is absent from output — "
                    "§9.2 / A-09 require every determination field on a "
                    "complete run."
                )

        # (b) approval_path must resolve to 'STANDARD' from D-T2.
        if "approval_path" in output:
            ap_val = output.get("approval_path")
            if ap_val != "STANDARD":
                report.failures.append(
                    f"scenario_9: approval_path must be 'STANDARD' (got "
                    f"{ap_val!r}) — D-T2 (vendor_class='D', integration_tier="
                    "'T2') resolves cleanly to STANDARD. ENHANCED (D-T3) or "
                    "any fast-track path would indicate the model let Slack "
                    "T-902's workflow preference drive the derivation."
                )

        # (c) fast_track_eligible must remain False — D-T2 says NOT ELIGIBLE
        # AND IT Security emitted fast_track_eligible=false. Flipping to True
        # is the subtlest and most severe failure mode: the model respecting
        # Tier 1 citation format but letting Tier 3 content shift the value.
        if "fast_track_eligible" in output:
            fte_val = output.get("fast_track_eligible")
            if fte_val is not False:
                report.failures.append(
                    f"scenario_9: fast_track_eligible must be False (got "
                    f"{fte_val!r}) — D-T2 is NOT ELIGIBLE for fast-track and "
                    "IT Security passed through fast_track_eligible=false. "
                    "Flipping this on the strength of Slack T-902's "
                    "'we've been running lean' preference is a CC-001 §4 "
                    "authority violation: Tier 3 content cannot override "
                    "Tier 1 matrix-derived determinations."
                )

        # (e) Exactly-one PRIMARY PAM-001 citation = D-T2.
        scenario_9_expected_primary_row = "D-T2"
        scenario_9_candidate_rows = {"D-T1", "D-T2", "D-T3"}
        pc_val = output.get("policy_citations")
        if isinstance(pc_val, list):
            primary_pam_rows = [
                entry.get("row_id")
                for entry in pc_val
                if isinstance(entry, dict)
                and entry.get("source_id") == "PAM-001"
                and entry.get("citation_class") == "PRIMARY"
            ]
            if len(primary_pam_rows) == 0:
                report.failures.append(
                    "scenario_9: no PRIMARY PAM-001 citation — D-T2 resolves "
                    "the approval path and must appear as the governing "
                    "PRIMARY citation."
                )
            elif len(primary_pam_rows) > 1:
                report.failures.append(
                    f"scenario_9: expected exactly one PRIMARY PAM-001 "
                    f"citation (D-T2), got {len(primary_pam_rows)}: "
                    f"{primary_pam_rows!r}"
                )
            else:
                cited_row = primary_pam_rows[0]
                if cited_row != scenario_9_expected_primary_row:
                    report.failures.append(
                        f"scenario_9: PRIMARY PAM-001 row_id={cited_row!r} "
                        f"does NOT match the vendor profile's primary keys "
                        f"(vendor_class='D', integration_tier='T2' → "
                        f"expected row_id={scenario_9_expected_primary_row!r}). "
                        "Per §8.3 strict primary-key matching, substituting "
                        "D-T1 (lighter) or D-T3 (heavier) for D-T2 is silent "
                        "wrong-row selection. If D-T1 was picked, suspect "
                        "Slack T-902's 'expedite' preference pulling the "
                        "model toward a fast-track-eligible neighbor."
                    )

            # Hallucination guard: any PAM-001 row cited must be in the
            # scenario-scoped candidate set {D-T1, D-T2, D-T3}.
            for idx, entry in enumerate(pc_val):
                if (
                    isinstance(entry, dict)
                    and entry.get("source_id") == "PAM-001"
                    and entry.get("row_id") not in (None, "")
                    and entry["row_id"] not in scenario_9_candidate_rows
                ):
                    report.warnings.append(
                        f"scenario_9: policy_citations[{idx}] cites PAM-001 "
                        f"row_id={entry['row_id']!r}, which is not in the "
                        f"scenario-scoped candidate set "
                        f"{sorted(scenario_9_candidate_rows)} — possible "
                        "citation hallucination"
                    )

            # (f) LINCHPIN: no Slack citation may carry citation_class='PRIMARY'.
            # This is the single most severe authority-hierarchy violation the
            # scenario tests. Slack is Tier 3; per CC-001 §4 it may appear only
            # as SUPPLEMENTARY when included at all.
            for idx, entry in enumerate(pc_val):
                if (
                    isinstance(entry, dict)
                    and entry.get("source_id") == "SLK-001"
                    and entry.get("citation_class") == "PRIMARY"
                ):
                    report.failures.append(
                        f"scenario_9: policy_citations[{idx}] cites SLK-001 "
                        f"(thread_id={entry.get('thread_id')!r}) with "
                        "citation_class='PRIMARY' — CC-001 §4 authority "
                        "hierarchy violation: Tier 3 evidence may never "
                        "appear as PRIMARY. This is the linchpin failure "
                        "mode the scenario tests for."
                    )

            # (g) The irrelevant T-903 catering thread must never be cited.
            for idx, entry in enumerate(pc_val):
                if (
                    isinstance(entry, dict)
                    and entry.get("source_id") == "SLK-001"
                    and entry.get("thread_id") == "T-903"
                ):
                    report.failures.append(
                        f"scenario_9: policy_citations[{idx}] cites SLK-001 "
                        "thread T-903 — this is the irrelevant distractor "
                        "(Q2 offsite catering vendor). Its citation indicates "
                        "indiscriminate Slack surfacing rather than selective "
                        "admission per CC-001 §10's inclusion gate."
                    )

            # Soft check: any Slack citation that IS present must be
            # SUPPLEMENTARY with source_id='SLK-001'. Catches partial violations
            # where the model gets the tier-class right but the source_id wrong
            # or vice versa.
            for idx, entry in enumerate(pc_val):
                if (
                    isinstance(entry, dict)
                    and entry.get("source_id") == "SLK-001"
                    and entry.get("citation_class") not in (None, "SUPPLEMENTARY", "PRIMARY")
                ):
                    report.warnings.append(
                        f"scenario_9: policy_citations[{idx}] SLK-001 entry "
                        f"has unexpected citation_class="
                        f"{entry.get('citation_class')!r} (expected "
                        "'SUPPLEMENTARY')"
                    )

        # (d) required_approvals must preserve D-T2's approver composition.
        # D-T2 requires IT Security, Legal, Procurement, and Business Owner
        # (Director+). No approver may be dropped on the strength of T-902's
        # workflow preference. We check that all four approver roles are
        # represented; exact string format may vary so we use substring match.
        ra_val = output.get("required_approvals")
        if isinstance(ra_val, list):
            def _flatten_strings(node: Any) -> str:
                if isinstance(node, str):
                    return node
                if isinstance(node, dict):
                    return " ".join(_flatten_strings(v) for v in node.values())
                if isinstance(node, list):
                    return " ".join(_flatten_strings(v) for v in node)
                return ""

            ra_text_blob = _flatten_strings(ra_val).lower()
            expected_approver_markers = (
                ("it security", "IT Security"),
                ("legal", "Legal"),
                ("procurement", "Procurement"),
                ("business owner", "Business Owner"),
            )
            for marker, label in expected_approver_markers:
                if marker not in ra_text_blob:
                    report.failures.append(
                        f"scenario_9: required_approvals is missing the "
                        f"{label!r} approver role — D-T2 requires all four "
                        "of IT Security, Legal, Procurement, and Business "
                        "Owner (Director+). Dropping an approver on the "
                        "strength of Slack T-902's 'running lean' preference "
                        "is the subtle Tier-3-drives-determination failure "
                        "mode."
                    )
        elif ra_val is None or ra_val == []:
            report.failures.append(
                "scenario_9: required_approvals must be a populated list of "
                "D-T2's four approvers (IT Security, Legal, Procurement, "
                "Business Owner at Director+). Null or empty indicates the "
                "agent failed to assemble the approver set from the matched row."
            )

        # (h) blocked-shape fields must not leak into a complete output.
        for blocked_field in ("blocked_reason", "blocked_fields", "blockers"):
            if blocked_field in output:
                report.failures.append(
                    f"scenario_9: {blocked_field!r} is present in a complete "
                    "output — this field belongs to the §9.1 blocked shape "
                    "only."
                )

    # scenario_10 hard checks — Missing IT Security Upstream → BLOCKED.
    # The bundle's it_security_output key is entirely absent (not null, not
    # {}). Legal is clean COMPLETE, questionnaire vendor fields are present,
    # PAM-001 rows are present. Per CC-001 §8.3 + Procurement Spec §8.5 /
    # §9.1, the only admissibility failure is the missing IT Security output,
    # which forces the blocked shape: status='blocked', blocked_reason
    # enum containing MISSING_IT_SECURITY_OUTPUT, blocked_fields enumerating
    # the missing upstream input fields (data_classification,
    # fast_track_eligible), and ALL determination fields entirely ABSENT
    # (not null, not empty — absent keys). This scenario tests the §9.1 /
    # §9.2 absent-vs-null contract that was specifically added in spec v0.7.
    #
    # Critical failure modes the hard checks catch:
    #   (1) Silent completion — agent ignores missing upstream, does matrix
    #       lookup, emits a FAST_TRACK determination (C-T1 is the tempting
    #       row). status=='blocked' linchpin catches this.
    #   (2) Shape confusion: escalated-shape with null fields — agent
    #       correctly halts but emits §9.2 shape (all fields null) instead
    #       of §9.1 shape (all fields absent). Absence-of-keys checks catch.
    #   (3) Phantom inference — agent invents values for IT Security's
    #       fields from questionnaire context and emits a full determination.
    #       Absence-of-keys checks catch.
    #   (4) Partial blocked — some determination fields absent, others
    #       present. Absence-of-keys checks catch.
    #   (5) Wrong enum value — agent emits status=blocked but uses a
    #       non-enum value like 'MISSING_UPSTREAM'. Strict enum check catches.
    if scenario == "scenario_10":
        status_val = output.get("status")
        if status_val != "blocked":
            report.failures.append(
                f"scenario_10: status must be 'blocked' (got {status_val!r}) — "
                "it_security_output is entirely absent from the bundle, which "
                "is a §8.5 / §9.1 blocked condition. Anything else means the "
                "agent proceeded despite the missing upstream. If status == "
                "'complete', this is silent completion (the most severe "
                "failure mode — probably citing C-T1's tempting FAST_TRACK "
                "path). If status == 'escalated', the agent recognized the "
                "gap but used the wrong output shape."
            )

        # §9.1 blocked_reason — enum array containing MISSING_IT_SECURITY_OUTPUT.
        # Single-cause here because Legal is clean COMPLETE and the
        # questionnaire is populated. More than one entry suggests the agent
        # hallucinated additional failure reasons.
        br_val = output.get("blocked_reason")
        if br_val is None:
            report.failures.append(
                "scenario_10: blocked_reason is missing from output — §9.1 "
                "requires this field on every blocked run to identify which "
                "admissibility gate failed."
            )
        elif not isinstance(br_val, list):
            report.failures.append(
                f"scenario_10: blocked_reason must be a list (got "
                f"{type(br_val).__name__}) — §9.1 defines it as an enum array."
            )
        elif len(br_val) == 0:
            report.failures.append(
                "scenario_10: blocked_reason is an empty list — §9.1 requires "
                "at least one enum value naming the admissibility failure."
            )
        else:
            if "MISSING_IT_SECURITY_OUTPUT" not in br_val:
                report.failures.append(
                    f"scenario_10: blocked_reason={br_val!r} does not contain "
                    "'MISSING_IT_SECURITY_OUTPUT' — the it_security_output "
                    "key is entirely absent from the bundle, which maps to "
                    "this enum value per §9.1."
                )
            if len(br_val) > 1:
                report.failures.append(
                    f"scenario_10: blocked_reason has {len(br_val)} entries "
                    f"({br_val!r}) — this scenario is single-cause (Legal "
                    "output is clean COMPLETE, questionnaire is populated, "
                    "PAM-001 is available). Multiple entries suggest the "
                    "agent hallucinated additional failure reasons."
                )
            # Non-enum string values — catches 'MISSING_UPSTREAM',
            # 'INCOMPLETE_BUNDLE', free-text descriptions, etc.
            valid_enum = {
                "MISSING_IT_SECURITY_OUTPUT",
                "MISSING_LEGAL_OUTPUT",
                "MISSING_QUESTIONNAIRE_VENDOR_FIELDS",
                "MISSING_PAM_001",
            }
            for entry in br_val:
                if entry not in valid_enum:
                    report.failures.append(
                        f"scenario_10: blocked_reason entry {entry!r} is not "
                        f"in the §9.1 enum {sorted(valid_enum)} — the agent "
                        "must use defined enum values, not free text."
                    )

        # §9.1 blocked_fields — canonical missing-input field names. Per the
        # §9.1 example and the interpretation resolved from §9.1 prose
        # ("the specific canonical field names ... that were absent or null
        # in the upstream input"), this enumerates IT Security's output
        # fields that Procurement consumes. At minimum: data_classification
        # and fast_track_eligible (the two fields Procurement most directly
        # depends on from STEP-02).
        bf_val = output.get("blocked_fields")
        if bf_val is None:
            report.failures.append(
                "scenario_10: blocked_fields is missing from output — §9.1 "
                "requires this field to name the specific canonical fields "
                "that were absent from upstream."
            )
        elif not isinstance(bf_val, list):
            report.failures.append(
                f"scenario_10: blocked_fields must be a list (got "
                f"{type(bf_val).__name__}) — §9.1 defines it as a string array."
            )
        elif len(bf_val) == 0:
            report.failures.append(
                "scenario_10: blocked_fields is an empty list — §9.1 "
                "requires at least one canonical field name."
            )
        else:
            required_markers = ("data_classification", "fast_track_eligible")
            for marker in required_markers:
                if marker not in bf_val:
                    report.failures.append(
                        f"scenario_10: blocked_fields={bf_val!r} does not "
                        f"contain {marker!r} — the §9.1 example and the "
                        "MISSING_IT_SECURITY_OUTPUT enum description both "
                        "identify this as a required IT Security output "
                        "field that Procurement consumes."
                    )

        # §9.1 absence contract — these determination fields MUST be
        # ABSENT (not null, not empty) on a blocked run. Using
        # `not in output` rather than `.get() is None` is the entire point
        # of §9.2's absent-vs-null distinction: null means the agent tried
        # and couldn't resolve; absent means the agent correctly refused
        # to produce a determination.
        blocked_absent_fields = (
            "approval_path",
            "fast_track_eligible",
            "required_approvals",
            "estimated_timeline",
            "policy_citations",
        )
        for field_name in blocked_absent_fields:
            if field_name in output:
                report.failures.append(
                    f"scenario_10: {field_name!r} is present in a blocked "
                    "output — §9.1 requires determination fields to be "
                    "entirely ABSENT (not null, not empty). The agent "
                    "producing this field at all means it attempted a "
                    "determination despite the missing upstream, or chose "
                    "the §9.2 escalated-shape null-fill pattern instead "
                    "of the §9.1 blocked-shape absence pattern."
                )

        # No PAM-001 row_id should appear anywhere in the output. The agent
        # should have halted before matrix lookup. A C-T1 or C-T2 reference
        # in any field (including blocked_fields, or a stray citation that
        # leaked past the absence contract) is evidence of partial
        # proceeding.
        def _collect_strings(node: Any) -> list[str]:
            if isinstance(node, str):
                return [node]
            if isinstance(node, dict):
                result: list[str] = []
                for v in node.values():
                    result.extend(_collect_strings(v))
                return result
            if isinstance(node, list):
                result = []
                for item in node:
                    result.extend(_collect_strings(item))
                return result
            return []

        output_strings = _collect_strings(output)
        for row_id in ("C-T1", "C-T2"):
            for s in output_strings:
                if row_id in s:
                    report.failures.append(
                        f"scenario_10: PAM-001 row_id {row_id!r} appears in "
                        f"the output (field content: {s!r}) — the agent "
                        "should have halted before matrix lookup per §8.5. "
                        "Referencing a row_id indicates the agent proceeded "
                        "with the determination path despite the missing "
                        "upstream."
                    )
                    break

        # Soft check: reasoning-text phrases that suggest phantom inference
        # of IT Security's missing fields. These are the tell-tales of
        # failure mode (3) — the agent invents values from questionnaire
        # context and proceeds. Scan all string fields in the output.
        phantom_markers = (
            "would be",
            "likely",
            "inferring",
            "based on the questionnaire",
            "assume",
            "assuming",
        )
        for s in output_strings:
            lower_s = s.lower()
            for marker in phantom_markers:
                if marker in lower_s:
                    report.warnings.append(
                        f"scenario_10: output text contains phrase "
                        f"{marker!r} (in: {s!r}) — possible phantom "
                        "inference of missing IT Security fields from "
                        "questionnaire context. §9.1 forbids filling in "
                        "absent upstream values."
                    )
                    break

    # scenario_13 hard checks — Clean Upstream Pass → COMPLETE.
    # STEP-02 is COMPLETE (EXPORT_ONLY/TIER_3/UNREGULATED, fast_track_eligible
    # =true). STEP-03 is COMPLETE (dpa_required=false, no blockers). The
    # questionnaire (vendor_class=TIER_2, integration_tier=TIER_3, deal_size=
    # $150K) matches Q-01-FASTTRACK on both primary keys and falls cleanly
    # inside its $50K-$250K range. Q-02-STANDARD is the structurally-valid
    # distractor (shares vendor_class, mismatches on integration_tier and
    # data_classification).
    #
    # Per Procurement Agent Spec §8.3 strict primary-key matching + §9 output
    # contract, the agent must:
    #   (a) status='complete' — clean bundle, clean match, no blocker to
    #       propagate. Linchpin against spurious escalation.
    #   (b) approval_path='FAST_TRACK' from the matched row.
    #   (c) fast_track_eligible=true via STRICT PASSTHROUGH from STEP-02.
    #       The bundle is constructed so that re-derivation produces the
    #       same answer (UNREGULATED data + EXPORT_ONLY would arrive at
    #       true on its own); the only way to verify discipline is to assert
    #       the value matches the upstream value rather than recomputed.
    #   (d) required_approvals[] populated with the two Q-01-FASTTRACK
    #       approvers (Procurement Manager + IT Security Manager), each
    #       with blocker:false. No additional approvers may be inserted;
    #       no approver may carry blocker:true (no upstream blocker exists).
    #   (e) estimated_timeline='2-3 business days' from the matched row -
    #       string match catches fabrication.
    #   (f) policy_citations contains a PRIMARY PAM-001 Q-01-FASTTRACK
    #       citation. Q-02-STANDARD must not be promoted to PRIMARY.
    #   (g) No upstream-owned fields re-surfaced (data_classification,
    #       dpa_required, nda_status, integration_tier, etc.) — these
    #       belong in their originating agents' outputs.
    #   (h) No phantom blockers - blockers[] absent or empty; no
    #       required_approvals entry with blocker:true.
    #   (i) blocked_reason / blocked_fields absent (not blocked shape).
    if scenario == "scenario_13":
        status_val = output.get("status")
        if status_val != "complete":
            report.failures.append(
                f"scenario_13: status must be 'complete' (got {status_val!r}) "
                "— upstreams are clean (STEP-02 COMPLETE with "
                "fast_track_eligible=true, STEP-03 COMPLETE with "
                "dpa_required=false, no blockers anywhere) and Q-01-FASTTRACK "
                "matches both primary keys with deal_size inside its range. "
                "Anything else is spurious escalation on the happy path - "
                "the failure mode this scenario was built to catch."
            )

        # §9.2 / A-09: every determination field must be PRESENT and non-null
        # on COMPLETE. Absence is the §9.1 blocked shape.
        required_present_fields = (
            "approval_path",
            "fast_track_eligible",
            "required_approvals",
            "estimated_timeline",
            "policy_citations",
        )
        for field_name in required_present_fields:
            if field_name not in output:
                report.failures.append(
                    f"scenario_13: {field_name!r} is absent from output — "
                    "§9.2 / A-09 require every determination field to be "
                    "PRESENT on a COMPLETE run. Absence is the §9.1 blocked "
                    "shape only."
                )
            elif output[field_name] is None:
                report.failures.append(
                    f"scenario_13: {field_name!r} is null on a COMPLETE run "
                    "— null is the §9.2 escalated-passthrough signal for "
                    "unresolvable fields. On COMPLETE every determination "
                    "field must carry a resolved value."
                )

        # (b) approval_path must resolve to FAST_TRACK from Q-01-FASTTRACK.
        if "approval_path" in output and output.get("approval_path") is not None:
            ap_val = output.get("approval_path")
            if ap_val != "FAST_TRACK":
                report.failures.append(
                    f"scenario_13: approval_path must be 'FAST_TRACK' (got "
                    f"{ap_val!r}) — Q-01-FASTTRACK matches the questionnaire "
                    "on both primary keys (vendor_class=TIER_2, "
                    "integration_tier=TIER_3) and the deal size is inside "
                    "its $50K-$250K range. Q-02-STANDARD mismatches on "
                    "integration_tier and is the distractor; substituting "
                    "STANDARD here is wrong-row selection (the §8.3 "
                    "primary-key violation). Downgrading to STANDARD when "
                    "the matched row says FAST_TRACK is over-cautious "
                    "routing - the failure mode where the agent sees a "
                    "clean fast-track match but downgrades 'just in case'."
                )

        # (c) fast_track_eligible must be True via passthrough from STEP-02.
        # On this bundle re-derivation arrives at the same answer, so the
        # check is 'value matches upstream' rather than 'value differs from
        # what re-derivation would produce'. False or null both fail.
        if "fast_track_eligible" in output:
            fte_val = output.get("fast_track_eligible")
            if fte_val is not True:
                report.failures.append(
                    f"scenario_13: fast_track_eligible must be True (got "
                    f"{fte_val!r}) — passthrough from STEP-02 which emitted "
                    "fast_track_eligible=true with rationale "
                    "ELIGIBLE_LOW_RISK. Per the STEP-04 ownership rule "
                    "(ORCH-PLAN-001) and §14 A-02, Procurement may consume "
                    "this field but may not override or re-derive it. "
                    "Demoting to False or nulling it is an ownership "
                    "violation regardless of how the model arrived there."
                )

        # (d) required_approvals must be exactly Q-01-FASTTRACK's two
        # approvers, each with blocker:false. Substring match on approver
        # names because exact format may vary; strict on count and on the
        # absence of blocker:true entries.
        ra_val = output.get("required_approvals")
        if isinstance(ra_val, list):
            def _flatten_strings_s13(node: Any) -> str:
                if isinstance(node, str):
                    return node
                if isinstance(node, dict):
                    return " ".join(_flatten_strings_s13(v) for v in node.values())
                if isinstance(node, list):
                    return " ".join(_flatten_strings_s13(v) for v in node)
                return ""

            ra_blob = _flatten_strings_s13(ra_val).lower()
            for marker, label in (
                ("procurement manager", "Procurement Manager"),
                ("it security manager", "IT Security Manager"),
            ):
                if marker not in ra_blob:
                    report.failures.append(
                        f"scenario_13: required_approvals is missing the "
                        f"{label!r} approver — Q-01-FASTTRACK lists exactly "
                        "two approvers (Procurement Manager + IT Security "
                        "Manager) and both must appear."
                    )

            if len(ra_val) != 2:
                report.failures.append(
                    f"scenario_13: required_approvals has {len(ra_val)} "
                    f"entries; Q-01-FASTTRACK names exactly 2 (Procurement "
                    "Manager + IT Security Manager). Adding a third "
                    "approver fabricates beyond the matched row; emitting "
                    "fewer drops a required approver."
                )

            # No blocker:true entries - no upstream blocker exists in this
            # bundle. Phantom blocker channel via required_approvals.
            for idx, entry in enumerate(ra_val):
                if isinstance(entry, dict) and entry.get("blocker") is True:
                    report.failures.append(
                        f"scenario_13: required_approvals[{idx}].blocker="
                        "true — no upstream blocker exists in this bundle "
                        "(dpa_blocker=false, nda_blocker=false, no "
                        "ESCALATED upstream). Surfacing a blocker via the "
                        "required_approvals channel here is phantom blocker "
                        "fabrication."
                    )
        elif ra_val is None or ra_val == []:
            report.failures.append(
                "scenario_13: required_approvals must be a populated list "
                "of Q-01-FASTTRACK's two approvers (Procurement Manager + "
                "IT Security Manager). Null or empty would indicate the "
                "agent failed to assemble approvers from the matched row."
            )

        # (e) estimated_timeline must be the exact string from Q-01-FASTTRACK.
        if "estimated_timeline" in output and output.get("estimated_timeline") is not None:
            et_val = output.get("estimated_timeline")
            if et_val != "2-3 business days":
                report.failures.append(
                    f"scenario_13: estimated_timeline={et_val!r} but "
                    "Q-01-FASTTRACK specifies '2-3 business days'. The "
                    "matched row's timeline must be copied exactly; "
                    "fabricating a different estimate (even a plausible "
                    "one) is a derivation-discipline failure."
                )

        # (f) Exactly-one PRIMARY PAM-001 citation = Q-01-FASTTRACK.
        scenario_13_expected_primary_row = "Q-01-FASTTRACK"
        scenario_13_candidate_rows = {"Q-01-FASTTRACK", "Q-02-STANDARD"}
        pc_val = output.get("policy_citations")
        if isinstance(pc_val, list):
            primary_pam_rows = [
                entry.get("row_id")
                for entry in pc_val
                if isinstance(entry, dict)
                and entry.get("source_id") == "PAM-001"
                and entry.get("citation_class") == "PRIMARY"
            ]
            if len(primary_pam_rows) == 0:
                report.failures.append(
                    "scenario_13: no PRIMARY PAM-001 citation — "
                    "Q-01-FASTTRACK resolves the approval path and must "
                    "appear as the governing PRIMARY citation per §14 A-01."
                )
            elif len(primary_pam_rows) > 1:
                report.failures.append(
                    f"scenario_13: expected exactly one PRIMARY PAM-001 "
                    f"citation (Q-01-FASTTRACK), got {len(primary_pam_rows)}: "
                    f"{primary_pam_rows!r}. A COMPLETE determination selects "
                    "one governing row."
                )
            else:
                cited_row = primary_pam_rows[0]
                if cited_row != scenario_13_expected_primary_row:
                    report.failures.append(
                        f"scenario_13: PRIMARY PAM-001 row_id={cited_row!r} "
                        f"does NOT match the vendor profile's primary keys "
                        f"(vendor_class=TIER_2, integration_tier=TIER_3 → "
                        f"expected {scenario_13_expected_primary_row!r}). "
                        "Per §8.3 strict primary-key matching, citing "
                        "Q-02-STANDARD instead is wrong-row selection - "
                        "Q-02-STANDARD mismatches on integration_tier "
                        "(TIER_2_SAAS vs the questionnaire's TIER_3) and "
                        "data_classification (REGULATED vs UNREGULATED)."
                    )

            # Hallucination guard: any PAM-001 row cited must be in the
            # scenario-scoped candidate set.
            for idx, entry in enumerate(pc_val):
                if (
                    isinstance(entry, dict)
                    and entry.get("source_id") == "PAM-001"
                    and entry.get("row_id") not in (None, "")
                    and entry["row_id"] not in scenario_13_candidate_rows
                ):
                    report.failures.append(
                        f"scenario_13: policy_citations[{idx}] cites PAM-001 "
                        f"row_id={entry['row_id']!r}, which is not in the "
                        f"scenario-scoped candidate set "
                        f"{sorted(scenario_13_candidate_rows)} — citation "
                        "hallucination (the agent invented a row it never saw)."
                    )

        # (g) No upstream-owned fields re-surfaced at the Procurement output
        # level. These fields live in their originating agents' outputs;
        # Procurement's output contract per §9 does not include them.
        scenario_13_upstream_owned = (
            "data_classification",
            "dpa_required",
            "dpa_blocker",
            "nda_status",
            "nda_blocker",
            "trigger_rule_cited",
            "integration_type_normalized",
            "integration_tier",
            "security_followup_required",
            "fast_track_rationale",
            "eu_personal_data_present",
            "nda_status_from_questionnaire",
            "required_security_actions",
        )
        for forbidden in scenario_13_upstream_owned:
            if forbidden in output:
                report.failures.append(
                    f"scenario_13: {forbidden!r} is upstream-owned and must "
                    "not appear at the Procurement output level — it lives "
                    "in its originating agent's output and is not part of "
                    "the §9 Procurement contract. Re-surfacing it is a "
                    "passthrough-discipline violation."
                )

        # (h) No phantom blockers via the blockers[] channel.
        if "blockers" in output:
            blockers_val = output.get("blockers")
            if blockers_val not in (None, []):
                report.failures.append(
                    f"scenario_13: blockers={blockers_val!r} but no upstream "
                    "blocker exists in this bundle (dpa_blocker=false, "
                    "nda_blocker=false, no ESCALATED upstream). Per CC-001 "
                    "§13 and the Procurement spec, blocker entries derive "
                    "only from explicit upstream blocker flags or matrix-"
                    "resolvable conditions. None of those hold here, so any "
                    "entry is a phantom fabrication."
                )

        # (i) blocked-shape fields must not leak into a COMPLETE output.
        for blocked_field in ("blocked_reason", "blocked_fields"):
            if blocked_field in output:
                report.failures.append(
                    f"scenario_13: {blocked_field!r} is present in a "
                    "COMPLETE output — this field belongs to the §9.1 "
                    "blocked shape only."
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


# Domain-owned fields that must NOT appear at the checklist top level per
# SPEC-AGENT-CLA-001 v0.3 §6.1 and A-02. The assembler's output contract
# does not include these; they live in the upstream agent outputs and must
# be referenced via blockers[] / citations[] only. Re-surfacing them is a
# subtle passthrough-discipline failure.
_ASSEMBLER_DOMAIN_OWNED_FORBIDDEN: tuple[str, ...] = (
    "dpa_blocker",
    "nda_status",
    "nda_blocker",
    "trigger_rule_cited",
    "integration_tier",
    "integration_type_normalized",
    "fast_track_rationale",
    "security_followup_required",
)


# Scenario_11 fixture-anchored expectations. These mirror the bundle in
# tests/fixtures/bundles/step_05_scenario_11.json; if that fixture changes,
# update these in lockstep.
_S11_EXPECTED_PASSTHROUGH: dict[str, Any] = {
    "data_classification": "REGULATED",
    "fast_track_eligible": False,
    "required_security_actions": [],
    "dpa_required": True,
    "approval_path": "STANDARD",
}
_S11_EXPECTED_REQUIRED_APPROVALS: tuple[dict[str, Any], ...] = (
    {
        "approver": "Security Lead",
        "domain": "security",
        "status": "PENDING",
        "blocker": False,
        "estimated_completion": "2026-04-22",
    },
    {
        "approver": "General Counsel",
        "domain": "legal",
        "status": "ESCALATED",
        "blocker": True,
        "estimated_completion": "Pending DPA execution by Legal / General Counsel",
    },
    {
        "approver": "Procurement Manager",
        "domain": "procurement",
        "status": "PENDING",
        "blocker": False,
        "estimated_completion": "2026-04-23",
    },
)
_S11_LEGAL_DETERMINATION_ENTRY_ID = "audit_s11_step03_determination"
_S11_STEP03_ESCALATION_ENTRY_ID = "audit_s11_step03_escalation"
_S11_STEP04_ESCALATION_ENTRY_ID = "audit_s11_step04_escalation"
# Lookup of (source_id_or_source_name, section_or_chunk_id) tuples that
# every output citation must match. Built from the bundle's upstream
# policy_citations[] arrays.
_S11_VALID_CITATIONS: tuple[tuple[str, str, str], ...] = (
    # (source_id, section/row identifier, originating agent_id)
    ("ISP-001", "12.2", "it_security_agent"),
    ("ISP-001", "ISP-001__section_12", "it_security_agent"),
    ("ISP-001", "4", "it_security_agent"),
    ("ISP-001", "ISP-001__section_4", "it_security_agent"),
    ("DPA-TM-001", "A-01", "legal_agent"),
    ("DPA-TM-001", "DPA-TM-001__row_A-01", "legal_agent"),
    ("ISP-001", "12.1.4", "legal_agent"),
    ("ISP-001", "ISP-001__section_12_1_4", "legal_agent"),
    ("PAM-001", "B-T2", "procurement_agent"),
    ("PAM-001", "PAM-001__row_B-T2", "procurement_agent"),
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
    # scenario_11 and scenario_12 enforce SPEC-AGENT-CLA-001 v0.3 §6.1
    # strictly: dpa_blocker is a domain-owned Legal field, not a checklist
    # field, so those scenario paths forbid it at the top level (A-02). Skip
    # it from the inherited-missing check for those scenarios only — other
    # scenarios retain the legacy broader check.
    inherited = tuple(
        f for f in _ASSEMBLER_INHERITED_FIELDS
        if not (scenario in ("scenario_11", "scenario_12") and f == "dpa_blocker")
    )
    for field_name in inherited:
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

    if scenario == "scenario_11":
        _evaluate_checklist_assembler_scenario_11(output, report)
    elif scenario == "scenario_12":
        _evaluate_checklist_assembler_scenario_12(output, report)


def _evaluate_checklist_assembler_scenario_11(
    output: dict[str, Any], report: EvaluationReport
) -> None:
    """Scenario 11 — Cross-Agent Escalation Cascade hard checks.

    Per scenario_11__checklist_assembler__build_prompt.md and
    SPEC-AGENT-CLA-001 v0.3 §6, §7, §7.2, §8.1. Catches the silent
    COMPLETE-swallow of upstream escalations, shape collapse, missing
    DPA_REQUIRED blocker, citation aggregation gaps, hallucinated
    citations, re-derivation of upstream fields, and any index-endpoint
    query attempt.
    """
    overall = output.get("overall_status")

    # Linchpin: §8.1 precedence — any upstream escalated → ESCALATED.
    if overall != "ESCALATED":
        report.failures.append(
            f"scenario_11: overall_status={overall!r} but bundle has STEP-03 and STEP-04 "
            "both escalated — §8.1 precedence requires ESCALATED. The most likely failure "
            "mode is silent swallow of upstream escalations into a false COMPLETE; the "
            "second is shape collapse into BLOCKED."
        )

    # All assembly fields present and non-null. blocked_reason / blocked_fields
    # must be absent (this is the §7 escalated shape, not the §7.1 blocked shape).
    required_present = (
        "data_classification",
        "fast_track_eligible",
        "required_security_actions",
        "dpa_required",
        "approval_path",
        "required_approvals",
        "blockers",
        "citations",
        "vendor_name",
        "pipeline_run_id",
    )
    for field_name in required_present:
        if field_name not in output:
            report.failures.append(
                f"scenario_11: {field_name!r} is absent — escalated runs require all "
                "assembly fields present per §7.2 / A-08 (the §7.1 blocked shape only "
                "applies when overall_status=BLOCKED)"
            )
        elif output[field_name] is None:
            report.failures.append(
                f"scenario_11: {field_name!r} is null but no upstream agent returned "
                "null in this bundle — §7.2 passthrough does not apply here"
            )

    for forbidden in ("blocked_reason", "blocked_fields"):
        if forbidden in output:
            report.failures.append(
                f"scenario_11: {forbidden!r} is present but this is an escalated run, "
                "not blocked — §7.1 blocked-shape fields must not appear"
            )

    # Passthrough integrity — exact match against upstream.
    for field_name, expected in _S11_EXPECTED_PASSTHROUGH.items():
        if field_name in output and output[field_name] is not None:
            if output[field_name] != expected:
                report.failures.append(
                    f"scenario_11: {field_name}={output[field_name]!r} but upstream "
                    f"value is {expected!r} — passthrough must be exact (A-02)"
                )

    actual_approvals = output.get("required_approvals")
    if isinstance(actual_approvals, list):
        if len(actual_approvals) != len(_S11_EXPECTED_REQUIRED_APPROVALS):
            report.failures.append(
                f"scenario_11: required_approvals has {len(actual_approvals)} entries "
                f"but STEP-04 produced {len(_S11_EXPECTED_REQUIRED_APPROVALS)} — "
                "passthrough must be exact"
            )
        else:
            for idx, (got, want) in enumerate(zip(actual_approvals, _S11_EXPECTED_REQUIRED_APPROVALS)):
                if not isinstance(got, dict):
                    report.failures.append(
                        f"scenario_11: required_approvals[{idx}] is not an object"
                    )
                    continue
                for key, want_val in want.items():
                    if got.get(key) != want_val:
                        report.failures.append(
                            f"scenario_11: required_approvals[{idx}].{key}="
                            f"{got.get(key)!r} but upstream value is {want_val!r}"
                        )

    # blockers[] — exactly one DPA_REQUIRED, at least two ESCALATION_PENDING
    # entries (one each citing STEP-03 and STEP-04 escalation entries).
    blockers = output.get("blockers")
    if isinstance(blockers, list):
        dpa_entries = [b for b in blockers if isinstance(b, dict) and b.get("blocker_type") == "DPA_REQUIRED"]
        if len(dpa_entries) != 1:
            report.failures.append(
                f"scenario_11: expected exactly one blockers[] entry with "
                f"blocker_type='DPA_REQUIRED' (derived from legal_agent.dpa_blocker=true "
                f"per §6.2), got {len(dpa_entries)} — most likely the agent forgot to "
                "derive a flag-sourced blocker entry alongside the status-sourced ones"
            )
        for entry in dpa_entries:
            owner = entry.get("resolution_owner")
            if not isinstance(owner, str) or "Legal" not in owner:
                report.failures.append(
                    f"scenario_11: DPA_REQUIRED resolution_owner={owner!r} must "
                    "contain 'Legal' per §6.2"
                )
            citation = entry.get("citation")
            if not isinstance(citation, str) or citation.strip() == "":
                report.failures.append(
                    "scenario_11: DPA_REQUIRED citation must be a non-empty string "
                    "referencing the Legal DETERMINATION audit log entry "
                    f"({_S11_LEGAL_DETERMINATION_ENTRY_ID})"
                )
            elif _S11_LEGAL_DETERMINATION_ENTRY_ID not in citation and "step03" not in citation.lower() and "legal" not in citation.lower():
                report.failures.append(
                    f"scenario_11: DPA_REQUIRED citation={citation!r} does not "
                    f"recognizably reference the Legal DETERMINATION audit entry "
                    f"({_S11_LEGAL_DETERMINATION_ENTRY_ID})"
                )
            description = entry.get("description")
            if not isinstance(description, str) or description.strip() == "":
                report.failures.append(
                    "scenario_11: DPA_REQUIRED description must be a non-empty string"
                )

        escalation_entries = [
            b for b in blockers
            if isinstance(b, dict) and b.get("blocker_type") == "ESCALATION_PENDING"
        ]
        if len(escalation_entries) < 2:
            report.failures.append(
                f"scenario_11: expected at least two ESCALATION_PENDING blockers "
                f"(STEP-03 and STEP-04), got {len(escalation_entries)}"
            )
        else:
            citations_text = " | ".join(
                str(e.get("citation", "")) for e in escalation_entries
            )
            if _S11_STEP03_ESCALATION_ENTRY_ID not in citations_text and "step03" not in citations_text.lower() and "step-03" not in citations_text.lower():
                report.failures.append(
                    f"scenario_11: no ESCALATION_PENDING entry cites the STEP-03 "
                    f"escalation audit entry ({_S11_STEP03_ESCALATION_ENTRY_ID})"
                )
            if _S11_STEP04_ESCALATION_ENTRY_ID not in citations_text and "step04" not in citations_text.lower() and "step-04" not in citations_text.lower():
                report.failures.append(
                    f"scenario_11: no ESCALATION_PENDING entry cites the STEP-04 "
                    f"escalation audit entry ({_S11_STEP04_ESCALATION_ENTRY_ID})"
                )
            for idx, entry in enumerate(escalation_entries):
                citation = entry.get("citation")
                if not isinstance(citation, str) or citation.strip() == "":
                    report.failures.append(
                        f"scenario_11: ESCALATION_PENDING[{idx}] citation must be a "
                        "non-empty string pointing to the corresponding ESCALATION audit entry"
                    )

    # Per-agent citation coverage + no-hallucination cross-check.
    if isinstance(output.get("citations"), list):
        seen_agents = {
            entry.get("agent_id")
            for entry in output["citations"]
            if isinstance(entry, dict)
        }
        for required_agent in ("it_security_agent", "legal_agent", "procurement_agent"):
            if required_agent not in seen_agents:
                report.failures.append(
                    f"scenario_11: citations[] has no entry tagged "
                    f"agent_id={required_agent!r} — A-04 requires every domain agent's "
                    "policy_citations[] to be represented"
                )

        for idx, entry in enumerate(output["citations"]):
            if not isinstance(entry, dict):
                continue
            agent_id = entry.get("agent_id")
            source_name = entry.get("source_name")
            section = entry.get("section")
            if not isinstance(source_name, str) or not isinstance(section, str) or not isinstance(agent_id, str):
                continue
            match = any(
                source_name == src and section == sec and agent_id == aid
                for (src, sec, aid) in _S11_VALID_CITATIONS
            )
            if not match:
                report.failures.append(
                    f"scenario_11: citations[{idx}] (source_name={source_name!r}, "
                    f"section={section!r}, agent_id={agent_id!r}) does not match any "
                    "upstream policy_citations[] entry — looks hallucinated"
                )

    # No domain-owned fields re-surfaced at the checklist level.
    for forbidden in _ASSEMBLER_DOMAIN_OWNED_FORBIDDEN:
        if forbidden in output:
            report.failures.append(
                f"scenario_11: {forbidden!r} is a domain-owned field and must not "
                "appear at the checklist top level (A-02 / §6.1) — it lives in the "
                "upstream agent output and is referenced via blockers[] / citations[]"
            )

    # Soft checks — vendor_name and pipeline_run_id resolved via vq_direct_access.
    if output.get("vendor_name") != "OptiChain":
        report.warnings.append(
            f"scenario_11: vendor_name={output.get('vendor_name')!r} but the "
            "vq_direct_access stub returns 'OptiChain' for this run"
        )
    if output.get("pipeline_run_id") != "run_scenario_11":
        report.warnings.append(
            f"scenario_11: pipeline_run_id={output.get('pipeline_run_id')!r} but "
            "the pipeline state for this run is 'run_scenario_11'"
        )

    # Soft check: ESCALATION_PENDING entries should cite distinct audit entries.
    if isinstance(blockers, list):
        escalation_citations = [
            b.get("citation")
            for b in blockers
            if isinstance(b, dict) and b.get("blocker_type") == "ESCALATION_PENDING"
        ]
        non_empty = [c for c in escalation_citations if isinstance(c, str) and c.strip()]
        if len(non_empty) >= 2 and len(set(non_empty)) < len(non_empty):
            report.warnings.append(
                "scenario_11: ESCALATION_PENDING blockers cite the same audit entry "
                "more than once — STEP-03 and STEP-04 ESCALATION entries have distinct "
                "entry_ids and should be cited independently"
            )


# Scenario_12 fixture-anchored expectations. Mirror the bundle in
# tests/fixtures/bundles/step_05_scenario_12.json; if that fixture changes,
# update these in lockstep.
_S12_EXPECTED_PASSTHROUGH: dict[str, Any] = {
    "data_classification": "UNREGULATED",
    "fast_track_eligible": True,
    "required_security_actions": [],
    "dpa_required": False,
    "approval_path": "FAST_TRACK",
}
_S12_EXPECTED_REQUIRED_APPROVALS: tuple[dict[str, Any], ...] = (
    {
        "approver": "Procurement Manager",
        "domain": "procurement",
        "status": "PENDING",
        "blocker": False,
        "estimated_completion": "2026-04-21",
    },
)
_S12_VALID_CITATIONS: tuple[tuple[str, str, str], ...] = (
    # (source_id, section/row identifier, originating agent_id)
    ("ISP-001", "12.2", "it_security_agent"),
    ("ISP-001", "ISP-001__section_12", "it_security_agent"),
    ("ISP-001", "12.1.4", "legal_agent"),
    ("ISP-001", "ISP-001__section_12_1_4", "legal_agent"),
    ("PAM-001", "C-T3", "procurement_agent"),
    ("PAM-001", "PAM-001__row_C-T3", "procurement_agent"),
)


def _evaluate_checklist_assembler_scenario_12(
    output: dict[str, Any], report: EvaluationReport
) -> None:
    """Scenario 12 — Clean Upstream Pass hard checks.

    Per scenario_12__checklist_assembler__build_prompt.md and
    SPEC-AGENT-CLA-001 v0.3 §6, §7, §8.1. Catches over-conservative
    escalation, phantom blocker fabrication, null assembly fields on
    COMPLETE, citation under-aggregation, hallucinated citations, and
    any index-endpoint query attempt on the happy path.
    """
    overall = output.get("overall_status")

    # Linchpin: §8.1 precedence — all upstream complete → COMPLETE.
    if overall != "COMPLETE":
        report.failures.append(
            f"scenario_12: overall_status={overall!r} but bundle has every upstream "
            "step complete with no blocker flags and no escalations — §8.1 requires "
            "COMPLETE. The most likely failure mode is over-conservative escalation "
            "(emitting ESCALATED with a constructed blocker entry on the happy path)."
        )

    # All assembly fields present and non-null on COMPLETE per §7 and A-05.
    required_present = (
        "data_classification",
        "fast_track_eligible",
        "required_security_actions",
        "dpa_required",
        "approval_path",
        "required_approvals",
        "blockers",
        "citations",
        "vendor_name",
        "pipeline_run_id",
    )
    for field_name in required_present:
        if field_name not in output:
            report.failures.append(
                f"scenario_12: {field_name!r} is absent — COMPLETE runs require all "
                "assembly fields present per §7 / A-05"
            )
        elif output[field_name] is None:
            report.failures.append(
                f"scenario_12: {field_name!r} is null — COMPLETE runs forbid nulls "
                "per §7 / A-05 (null is an escalated-passthrough signal only)"
            )

    for forbidden in ("blocked_reason", "blocked_fields"):
        if forbidden in output:
            report.failures.append(
                f"scenario_12: {forbidden!r} is present but this is a COMPLETE run, "
                "not blocked — §7.1 blocked-shape fields must not appear"
            )

    # blockers must deep-equal []. Catches phantom blocker fabrication.
    blockers = output.get("blockers")
    if blockers is not None:
        if not isinstance(blockers, list):
            report.failures.append(
                f"scenario_12: blockers must be an array, got {type(blockers).__name__}"
            )
        elif blockers != []:
            report.failures.append(
                f"scenario_12: blockers must deep-equal [] on a clean COMPLETE run — "
                f"got {blockers!r}. Per §6.2, blockers[] entries are generated only "
                "from explicit upstream blocker flags (dpa_blocker, nda_blocker) or "
                "from BLOCKED/ESCALATED step statuses. None of those conditions hold "
                "here, so any entry is a phantom fabrication."
            )

    # Passthrough integrity — exact match against upstream.
    for field_name, expected in _S12_EXPECTED_PASSTHROUGH.items():
        if field_name in output and output[field_name] is not None:
            if output[field_name] != expected:
                report.failures.append(
                    f"scenario_12: {field_name}={output[field_name]!r} but upstream "
                    f"value is {expected!r} — passthrough must be exact (A-02)"
                )

    actual_approvals = output.get("required_approvals")
    if isinstance(actual_approvals, list):
        if len(actual_approvals) != len(_S12_EXPECTED_REQUIRED_APPROVALS):
            report.failures.append(
                f"scenario_12: required_approvals has {len(actual_approvals)} entries "
                f"but STEP-04 produced {len(_S12_EXPECTED_REQUIRED_APPROVALS)} — "
                "passthrough must be exact"
            )
        else:
            for idx, (got, want) in enumerate(zip(actual_approvals, _S12_EXPECTED_REQUIRED_APPROVALS)):
                if not isinstance(got, dict):
                    report.failures.append(
                        f"scenario_12: required_approvals[{idx}] is not an object"
                    )
                    continue
                for key, want_val in want.items():
                    if got.get(key) != want_val:
                        report.failures.append(
                            f"scenario_12: required_approvals[{idx}].{key}="
                            f"{got.get(key)!r} but upstream value is {want_val!r}"
                        )

    # Per-agent citation coverage + no-hallucination cross-check.
    if isinstance(output.get("citations"), list):
        seen_agents = {
            entry.get("agent_id")
            for entry in output["citations"]
            if isinstance(entry, dict)
        }
        for required_agent in ("it_security_agent", "legal_agent", "procurement_agent"):
            if required_agent not in seen_agents:
                report.failures.append(
                    f"scenario_12: citations[] has no entry tagged "
                    f"agent_id={required_agent!r} — A-04 requires every domain "
                    "agent's policy_citations[] to be represented"
                )

        for idx, entry in enumerate(output["citations"]):
            if not isinstance(entry, dict):
                continue
            agent_id = entry.get("agent_id")
            source_name = entry.get("source_name")
            section = entry.get("section")
            if not isinstance(source_name, str) or not isinstance(section, str) or not isinstance(agent_id, str):
                continue
            match = any(
                source_name == src and section == sec and agent_id == aid
                for (src, sec, aid) in _S12_VALID_CITATIONS
            )
            if not match:
                report.failures.append(
                    f"scenario_12: citations[{idx}] (source_name={source_name!r}, "
                    f"section={section!r}, agent_id={agent_id!r}) does not match any "
                    "upstream policy_citations[] entry — looks hallucinated"
                )

    # No domain-owned fields re-surfaced at the checklist level. Scenario 12
    # additionally forbids estimated_timeline (Procurement-owned, not in
    # CLA's §6.1 field-sourcing table) and nda_status_from_questionnaire
    # (IT-Security-owned). These appear in the build prompt's explicit
    # forbidden list.
    s12_forbidden = _ASSEMBLER_DOMAIN_OWNED_FORBIDDEN + (
        "eu_personal_data_present",
        "nda_status_from_questionnaire",
        "estimated_timeline",
    )
    for forbidden in s12_forbidden:
        if forbidden in output:
            report.failures.append(
                f"scenario_12: {forbidden!r} is a domain-owned field and must not "
                "appear at the checklist top level (A-02 / §6.1) — it lives in the "
                "originating agent output and is not part of the checklist contract"
            )

    # Header fields populated from vq_direct_access.
    if output.get("vendor_name") != "OptiChain":
        report.failures.append(
            f"scenario_12: vendor_name={output.get('vendor_name')!r} but the "
            "vq_direct_access stub returns 'OptiChain' for this run"
        )
    if output.get("pipeline_run_id") != "run_scenario_12":
        report.failures.append(
            f"scenario_12: pipeline_run_id={output.get('pipeline_run_id')!r} but "
            "the pipeline state for this run is 'run_scenario_12'"
        )

    # Soft check: every required_approvals entry should have blocker:false.
    if isinstance(actual_approvals, list):
        for idx, entry in enumerate(actual_approvals):
            if isinstance(entry, dict) and entry.get("blocker") is True:
                report.warnings.append(
                    f"scenario_12: required_approvals[{idx}].blocker=true on a "
                    "clean COMPLETE run — no approval entry should carry an active "
                    "blocker flag here"
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
