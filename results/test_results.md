## IT Security Agent — scenario_1 — 2026-04-16
**Status:** FAIL
**Required fields present:** NO — `policy_citations[*].section` missing (agent emitted `section_id`, `chunk_id`, `citation_class` per the IT Security Agent Spec and ORCH-PLAN STEP-02 output contract). All other required fields present (`data_classification`, `fast_track_eligible`, `policy_citations[]`, `status`).
**Status signal:** complete / complete — matches scenario-expected.
**Semantic validity:** PASS — `data_classification: UNREGULATED` is consistent with the export-only questionnaire inputs; `fast_track_eligible: true` is consistent with UNREGULATED; both `policy_citations` reference `ISP-001` only (no out-of-lane source citations).
**Notes:** Failure is a governance-doc drift, not a model or prompt failure. `llm_agent_output_evaluation_checklist.md:31` and `per_agent_test_env/evaluators.py:256` require key `section`; `agent_spec_docs/IT_Security_Agent_Spec.md:258`, ORCH-PLAN STEP-02 output contract, and CC-001 §7 provenance require `section_id` (plus `chunk_id`, `citation_class`). Raw recorded at `tests/recorded_responses/it_security_agent__scenario_1__1_fail.json`. Halted per procedure — no re-run.

## IT Security Agent — scenario_1 — 2026-04-16
**Status:** PASS
**Required fields present:** YES — `data_classification`, `fast_track_eligible`, `policy_citations[]`, `status` all present; each `policy_citations` entry carries `source_id`, `version`, `section_id`, `citation_class` (hard), plus `chunk_id` (soft).
**Status signal:** complete / complete — matches scenario-expected.
**Semantic validity:** PASS — `data_classification: UNREGULATED` consistent with EXPORT_ONLY questionnaire inputs; `fast_track_eligible: true` consistent with UNREGULATED; both `policy_citations` reference `ISP-001` only (no out-of-lane sources); `chunk_id` values (`ISP-001__section_12`, `ISP-001__section_17`) match the bundle verbatim; `citation_class: PRIMARY` valid for a Tier 1 source.
**Notes:** Re-run after the evaluator + checklist realignment in session #38 (required keys on `policy_citations` → `section_id` + `citation_class`, `chunk_id` soft). Fixture, spec, and model unchanged. Two minor model drifts vs. run #1 worth flagging but not hard-failed: `eu_personal_data_present` came back as the string `"NO"` instead of a boolean `false` (run #1 returned the boolean), and `fast_track_rationale` came back as the token `"ELIGIBLE_LOW_RISK"` instead of a free-text sentence — both are outside the current hard-check set. Raw recorded at `tests/recorded_responses/it_security_agent__scenario_1__2_pass.json`.
