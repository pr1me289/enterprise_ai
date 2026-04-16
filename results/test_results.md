## IT Security Agent — scenario_1 — 2026-04-16
**Status:** FAIL
**Required fields present:** NO — `policy_citations[*].section` missing (agent emitted `section_id`, `chunk_id`, `citation_class` per the IT Security Agent Spec and ORCH-PLAN STEP-02 output contract). All other required fields present (`data_classification`, `fast_track_eligible`, `policy_citations[]`, `status`).
**Status signal:** complete / complete — matches scenario-expected.
**Semantic validity:** PASS — `data_classification: UNREGULATED` is consistent with the export-only questionnaire inputs; `fast_track_eligible: true` is consistent with UNREGULATED; both `policy_citations` reference `ISP-001` only (no out-of-lane source citations).
**Notes:** Failure is a governance-doc drift, not a model or prompt failure. `llm_agent_output_evaluation_checklist.md:31` and `per_agent_test_env/evaluators.py:256` require key `section`; `agent_spec_docs/IT_Security_Agent_Spec.md:258`, ORCH-PLAN STEP-02 output contract, and CC-001 §7 provenance require `section_id` (plus `chunk_id`, `citation_class`). Raw recorded at `tests/recorded_responses/it_security_agent__scenario_1__1_fail.json`. Halted per procedure — no re-run.
