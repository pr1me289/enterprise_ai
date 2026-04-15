# Necessary Fixes — Deterministic Orchestration Test Harness

**Branch:** `feature/supervisor-orchestration-retrieval`
**Audit date:** 2026-04-14
**Auditor:** Claude (Opus 4.6)
**Source of truth for expectations:** `agent_bundle_integrity_checklist.md`, `core_documents/context_contract.md`, `core_documents/design_doc.md`, `core_documents/supervisor_orchestration_plan.md`

---

## Purpose

This checklist captures integrity gaps found in the deterministic test harness built from `deterministic_orchestration_test_harness_prompt.md`. The harness runs end-to-end and emits PASS/FAIL, but several assertions are structurally incapable of firing, several fixtures are weaker than the checklist requires, and status-signal coverage is thin.

A future agent should work through this file top-to-bottom. Each fix has:

- **Location** — file and, where relevant, line numbers.
- **What is wrong** — observed behavior.
- **What should happen** — target behavior.
- **Why it matters** — the invariant from the checklist / governing docs.
- **Acceptance criteria** — how to know the fix is complete.

Do not consider the harness "thorough" until every item below is checked off.

---

## Priority 1 — Bundle capture is fake (blocks every bundle assertion)

### [ ] 1.1 Capture the real `ContextBundle` produced inside each step handler

- **Location:** `test_harness/run_test_scenario.py`, function `_record_bundle_trace_from_state` (around lines 354–400), called from the main loop at ~line 298.
- **What is wrong:** The function synthesises an empty `ContextBundle`:
  ```python
  synthetic_bundle = ContextBundle(
      step_id=step_id,
      admitted_evidence=[],
      excluded_evidence=[],
      structured_fields={},
      source_provenance=[],
      admissibility_status="ADMISSIBLE" if admissible else "PARTIAL",
  )
  ```
  The actual bundle assembled inside each step handler by `BundleAssembler.assemble_stepNN()` is never retained.
- **What should happen:** The real `ContextBundle` used for the just-executed step must be captured and passed to `BundleTraceWriter.record()`. Two reasonable approaches:
  1. Add a `last_bundle_by_step: dict[StepId, ContextBundle]` cache on `Supervisor` (populated inside `_run_step` after the assembler returns) and read from it in the harness.
  2. Return the bundle from `Supervisor.execute_next_step()` as part of a result object (breaking signature change — coordinate with any other callers).
- **Why it matters:** With an empty synthetic bundle, the Slack-primary check, the Thread-4 exclusion check, the forbidden-source check (once added), and the ESCALATION_REQUIRED admissibility check in `result_assertions.assert_bundles` all pass vacuously. This single gap neuters the majority of the harness.
- **Acceptance criteria:**
  - `bundle_trace.json` artifact contains non-empty `admitted_chunks` for STEP-02/03/04 on a complete scenario.
  - Unit-level spot check: for scenario_1_complete, STEP-03 trace shows at least one `DPA-TM-001` row chunk and the `ISP-001 §12.1.4` NDA chunk; STEP-04 shows at least one `PAM-001` row chunk.
  - Temporarily injecting a `SLK-001` chunk marked `is_primary_citable=True` into a STEP-04 bundle causes `assert_bundles` to fail.

---

## Priority 2 — Dead code: bundle-aware mock agents are never used

### [ ] 2.1 Wire up or remove the `test_harness/mock_agents/*.py` files

- **Location:** `test_harness/mock_agents/mock_step_01_intake.py` through `mock_step_06_checkoff.py`.
- **What is wrong:** These six files implement bundle-aware mock agents with exactly the validation logic the checklist requires (required fields, forbidden sources, Slack-primary violations, Thread 4 exclusion). They are **not imported anywhere** — `grep -r "from test_harness.mock_agents"` returns zero matches. The harness instead routes all agent calls through `_ScenarioMockAdapter` → `MockLLMAdapter` (in `src/orchestration/agents/llm_agent_runner.py`), which does not reproduce these validations.
- **What should happen:** Choose one of the following, and document the choice:
  - **Option A (recommended):** Make the harness's adapter delegate to the bundle-aware mock agents for each step, so their `_validate_bundle` guards actually run. This likely means `_ScenarioMockAdapter.generate_structured_json` dispatches on `agent_name` into the corresponding `mock_step_NN_*.run(bundle, scenario_name)`.
  - **Option B:** Port the `_validate_bundle` logic from each mock agent into `result_assertions.assert_bundles` (and delete the unused files). Keep a single source of truth.
- **Why it matters:** Right now the checklist's validation logic exists in the repo but is unreachable. The harness only proves that the step-sequencing state machine works, not that agents would reject a malformed bundle.
- **Acceptance criteria:**
  - Running any scenario exercises at least one `_validate_bundle` call path per step (Option A) or one bundle-contents assertion per step (Option B).
  - Deleting required fields from a bundle (e.g., removing `ISP-001 §12.1.4` from the STEP-03 bundle via a temporary patch) causes the run to FAIL rather than PASS.

---

## Priority 3 — Fixture `bundle_invariants` are weaker than the checklist

### [ ] 3.1 Tighten STEP-03 Legal invariants

- **Location:** `test_harness/scenario_fixtures.py`, the `bundle_invariants` entries for STEP-03 in `SCENARIO_1_COMPLETE` and `SCENARIO_2_ESCALATED`.
- **What is wrong:** STEP-03 currently asserts presence of `VQ-OC-001` plus two VQ fields only. The checklist requires:
  - STEP-02 structured upstream output (`data_classification` at minimum).
  - `DPA-TM-001` row-targeted chunks.
  - `VQ-OC-001` fields: `eu_personal_data_flag`, `data_subjects_eu`, `existing_nda_status`.
  - `ISP-001` §12.1.4 NDA clause chunk.
- **What should happen:** Add `required_source_ids=["DPA-TM-001", "ISP-001", "VQ-OC-001"]`, `required_structured_fields=["it_security_output.data_classification"]`, and `forbidden_source_ids=["PAM-001", "SLK-001"]`. Also add a section-specific assertion that `ISP-001__section_12_1_4` (or equivalent chunk id) appears in admitted evidence.
- **Acceptance criteria:** An intentionally-degraded bundle (any single required item removed) causes FAIL.

### [ ] 3.2 Tighten STEP-04 Procurement invariants

- **Location:** Same file, STEP-04 invariants in both complete/escalated fixtures.
- **What is wrong:** Only `VQ-OC-001` is required; checklist requires STEP-02 full output, STEP-03 full output, required VQ procurement fields (`vendor_class`, `deal_size`, `existing_nda_status`), and `PAM-001` rows. Conditional `SLK-001` supplementary is allowed only when flagged and must never be primary.
- **What should happen:** Add `required_source_ids=["PAM-001", "VQ-OC-001"]`, `required_structured_fields=["it_security_output", "legal_output"]`, `forbidden_source_ids=["DPA-TM-001"]`, `slack_must_not_be_primary=True`.
- **Acceptance criteria:** Same pattern as 3.1.

### [ ] 3.3 Add real STEP-05 Checklist Assembler invariants

- **Location:** Same file, STEP-05 invariants.
- **What is wrong:** `required_source_ids=[]` and `required_structured_fields=[]`. Checklist requires structured outputs of STEP-02/03/04 and audit-log entries; forbids all raw source documents.
- **What should happen:**
  - `required_structured_fields=["step_02_output", "step_03_output", "step_04_output", "audit_log_entries"]` (names to match actual bundle keys — verify in `BundleAssembler.assemble_step05`).
  - `forbidden_source_ids=["VQ-OC-001", "ISP-001", "DPA-TM-001", "PAM-001", "SLK-001"]` — the Assembler sees no raw sources.
- **Acceptance criteria:** Smuggling any raw chunk into the STEP-05 bundle causes FAIL.

### [ ] 3.4 Add real STEP-06 Checkoff invariants

- **Location:** Same file, STEP-06 invariants.
- **What is wrong:** Both required lists are empty. Checklist requires finalized checklist, stakeholder map, approver list, required security actions, escalation reasons (if any), and domain determination summaries. Forbids all raw source documents and all index queries.
- **What should happen:**
  - `required_structured_fields=["finalized_checklist", "stakeholder_map", "required_approvers", "required_security_actions"]`.
  - `forbidden_source_ids=["VQ-OC-001", "ISP-001", "DPA-TM-001", "PAM-001", "SLK-001"]`.
  - Add a separate invariant that the Checkoff Agent emits **zero** retrieval audit entries (see 4.2).
- **Acceptance criteria:** A test that injects a raw source chunk or an index query for STEP-06 causes FAIL.

### [ ] 3.5 Add a `forbidden_source_ids` check to `assert_bundles`

- **Location:** `test_harness/result_assertions.py`, function `assert_bundles`.
- **What is wrong:** The `BundleInvariant` dataclass already has (or should have — verify in `scenario_fixtures.py`) a `forbidden_source_ids` field, but `assert_bundles` doesn't read it.
- **What should happen:** After the Slack-primary / Thread-4 loops, iterate `invariant.forbidden_source_ids` and raise if any admitted chunk's `source_id` matches.
- **Acceptance criteria:** Fixture 3.1–3.4 forbidden lists are actually enforced.

---

## Priority 4 — Retrieval-lane conformance is not asserted

### [ ] 4.1 Add a lane-per-source assertion

- **Location:** `test_harness/result_assertions.py`, new function `assert_retrieval_lanes` (called from `run_all_assertions`).
- **What is wrong:** The harness already emits a `RETRIEVE` event with a `lane` field (`run_test_scenario.py:284-288`), and the checklist declares the lane for each source:
  - `VQ-OC-001` → `DIRECT_STRUCTURED`
  - `ISP-001` → `INDEXED_HYBRID`
  - `DPA-TM-001` → `INDEXED_HYBRID` (row-targeted)
  - `PAM-001` → `INDEXED_HYBRID` (row-targeted)
  - `SLK-001` → `INDEXED_HYBRID`
  - checklist / pipeline state / audit log → `NON_RETRIEVAL`
  But nothing consumes these events for assertion purposes.
- **What should happen:** In `assert_retrieval_lanes`, walk the audit log entries where `event_type == "RETRIEVAL"` and confirm `(source_queried, details["lane"])` matches the expected mapping. Fail on mismatch.
- **Acceptance criteria:** Temporarily swapping the lane for `ISP-001` in the retrieval layer causes a harness FAIL.

### [ ] 4.2 Assert STEP-06 emits zero retrieval events

- **Location:** Same file, extend `assert_retrieval_lanes` or add `assert_checkoff_no_retrieval`.
- **What is wrong:** The checklist is explicit: "If the Checkoff Agent issues any index query, fail closed and log it." No assertion enforces this.
- **What should happen:** Count audit entries with `event_type == "RETRIEVAL"` and `step_id == "STEP-06"` — if > 0, FAIL. Same for STEP-05 if the Assembler is expected to do no raw retrieval.
- **Acceptance criteria:** If a future regression causes STEP-06 to call the retrieval layer, the harness FAILs.

---

## Priority 5 — Supervisor does not halt on ESCALATED on its own

### [ ] 5.1 Halt on ESCALATED inside `Supervisor.execute_next_step()`

- **Location:** `src/orchestration/supervisor.py`, end of `execute_next_step` — returns `self.state.overall_status is not RunStatus.BLOCKED and bool(self.state.next_step_queue)`.
- **What is wrong:** Only `BLOCKED` halts the supervisor's own loop. `ESCALATED` halting depends entirely on the harness wrapper (`run_test_scenario.py:258-260`). Any production caller using `execute_next_step()` directly would not halt on escalation.
- **What should happen:** Change the final return to:
  ```python
  return (
      self.state.overall_status not in (RunStatus.BLOCKED, RunStatus.ESCALATED)
      and bool(self.state.next_step_queue)
  )
  ```
  Verify this matches the orchestration plan (it does — ESCALATED is a terminal halt per §gate behavior).
- **Why it matters:** Defense in depth. The harness wrapper guard should remain, but the supervisor must be self-terminating on both halt statuses.
- **Acceptance criteria:** A unit test that drives the supervisor to ESCALATED and then calls `execute_next_step()` sees it return `False` without the wrapper.

---

## Priority 6 — Status-signal coverage is incomplete

For each item below, add a new `HarnessFixture` in `test_harness/scenario_fixtures.py`, register it in `run_test_scenario.py`'s `--scenario` choices, and drive it with the appropriate adapter override.

### [ ] 6.1 Add `scenario_step02_escalated_ambiguous_integration`

- **Trigger:** Questionnaire fields produce AMBIGUOUS integration tier classification in `MockLLMAdapter._run_it_security`. Use questionnaire override rather than agent override so the real bundle-aware adapter path is exercised.
- **Expected terminal:** STEP-02, overall=ESCALATED. STEP-03/04/05/06 stay PENDING.
- **Why:** Proves STEP-02's escalation path works and that downstream steps do not run.

### [ ] 6.2 Add `scenario_step04_escalated_no_pam_row`

- **Trigger:** Questionnaire `vendor_class` / `deal_size` combination yields no matching `PAM-001` row.
- **Expected terminal:** STEP-04, overall=ESCALATED. STEP-05/06 stay PENDING.
- **Why:** Checklist allows an ESCALATED status here; currently untested.

### [ ] 6.3 Add `scenario_step03_blocked_prohibited_source`

- **Trigger:** Force a prohibited source into the STEP-03 bundle (e.g., via a bundle-assembler test hook or a questionnaire that trips the prohibition logic in `MockLLMAdapter._run_legal`, which returns `{"status": "blocked"}` when `meta["prohibited_sources"]` is present — see `llm_agent_runner.py:~line 165`).
- **Expected terminal:** STEP-03, overall=BLOCKED. STEP-04/05/06 stay PENDING.
- **Why:** The only BLOCKED scenario today is STEP-01 (missing questionnaire). The adapter's other BLOCKED paths are dead until tested.

### [ ] 6.4 Add `scenario_step05_propagates_escalation`

- **Trigger:** STEP-03 returns ESCALATED (reuse scenario 2's override), but instead of halting the harness early, verify the Assembler would treat this correctly if it ever ran. If the plan says STEP-05 never runs after an ESCALATED upstream, then the existing scenario 2 already covers this — document that and add an explicit assertion in `assert_global` that STEP-05 and STEP-06 are PENDING on scenario 2.
- **Why:** Makes the "STEP-06 never runs after ESCALATED" invariant explicit rather than implicit.

### [ ] 6.5 Verify COMPLETE path exercises real agent logic

- **Location:** `run_test_scenario.py`, `_build_agent_overrides`.
- **What is wrong:** Scenario 1 hard-codes outputs for `legal_agent`, `procurement_agent`, `checklist_assembler`, and `checkoff_agent` — four of five agents never see their bundle. This was originally added to work around a type mismatch (`dpa_trigger_rows` being a `{"rows": [...]}` dict vs a list — see `_build_agent_overrides` docstring).
- **What should happen:**
  1. Fix the underlying type mismatch in `MockLLMAdapter._run_legal` (accept both shapes, or have `BundleAssembler` emit the shape the adapter expects).
  2. Remove the scenario-1 overrides for `legal_agent`, `procurement_agent`, `checklist_assembler`, `checkoff_agent`. Keep the scenario-2 `legal_agent` override (that one is load-bearing — it forces ESCALATED).
- **Why it matters:** Right now the COMPLETE path only proves state-machine sequencing. The adapter's real logic is barely exercised.
- **Acceptance criteria:** Scenario 1 passes with zero agent overrides (only questionnaire path is needed).

---

## Priority 7 — Documentation and traceability

### [ ] 7.1 Add a `master_log.md` entry for this audit and each fix batch

- **Location:** `master_log.md` at repo root.
- **What:** One session entry per fix batch, using the format in `CLAUDE.md`. Reference this file by name in each entry's **Plan** line.

### [ ] 7.2 Update the test-harness prompt doc if invariants change

- **Location:** `deterministic_orchestration_test_harness_prompt.md`.
- **What:** If any fix changes the expected shape of fixtures or the assertion set, update the prompt doc so the harness spec and the harness stay in lock-step.

---

## Verification Plan (run after all fixes)

A future agent should be able to answer **yes** to every line below before closing out this file.

- [ ] `uv run python test_harness/run_test_scenario.py --scenario scenario_1_complete` PASSes with no agent overrides beyond scenario 2's legal override.
- [ ] `uv run python test_harness/run_test_scenario.py --scenario scenario_2_escalated` PASSes and STEP-04/05/06 are PENDING.
- [ ] `uv run python test_harness/run_test_scenario.py --scenario scenario_blocked_missing_questionnaire` PASSes and all steps except STEP-01 are PENDING.
- [ ] Each new status-signal scenario (6.1–6.4) PASSes.
- [ ] For each of the following tampering injections, the harness **FAILs** (confirming assertions have teeth):
  - Inject a `DPA-TM-001` chunk into the STEP-02 bundle.
  - Inject a `PAM-001` chunk into the STEP-03 bundle.
  - Inject a `SLK-001` chunk marked `is_primary_citable=True` into the STEP-04 bundle.
  - Inject a Thread-4 Slack chunk into the STEP-04 bundle.
  - Inject any raw source chunk into the STEP-05 or STEP-06 bundle.
  - Swap the retrieval lane for `ISP-001` from `INDEXED_HYBRID` to `DIRECT_STRUCTURED`.
  - Make STEP-06 emit a retrieval event.
- [ ] `bundle_trace.json` shows real, non-empty `admitted_chunks` for STEP-02/03/04 on scenario 1.
- [ ] `ruff check .` and `pytest` pass.

---

## Quick reference — file locations

| Area | Path |
|------|------|
| Harness entry | `test_harness/run_test_scenario.py` |
| Fixtures | `test_harness/scenario_fixtures.py` |
| Assertions | `test_harness/result_assertions.py` |
| Dead mock agents | `test_harness/mock_agents/mock_step_0[1-6]_*.py` |
| Real adapter | `src/orchestration/agents/llm_agent_runner.py` (`MockLLMAdapter`) |
| Bundle assembly | `src/orchestration/retrieval/bundle_assembler.py` |
| Supervisor | `src/orchestration/supervisor.py` |
| Governing docs | `agent_bundle_integrity_checklist.md`, `core_documents/*.md` |

---

**End of checklist.** Future agents: do not mark a section complete without running the verification plan line for that section.
