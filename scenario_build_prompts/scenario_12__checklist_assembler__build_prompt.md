# Scenario 12 — Checklist Assembler Fixture Build: Clean Upstream Pass → COMPLETE

## What this tests

A happy-path Checklist Assembler run where all three upstream domain agents are `complete`, every required upstream field is present and schema-valid, the audit log is non-empty, and there are no blocker flags or upstream escalations to propagate.

The correct behavior is: the Checklist Assembler assembles the checklist, passes through upstream-owned fields unchanged, aggregates citations across the three domain agents, and emits:

- `overall_status: "COMPLETE"`
- all required checklist fields present and non-null
- `blockers: []` (empty array, not absent)
- `blocked_reason` and `blocked_fields` absent

This scenario is intentionally minimal. It is the reference "clean pass" path and serves as the baseline against which Scenario 11's escalated path and any future blocked-path scenarios can be compared. It also catches two specific failure modes that only surface on the happy path: over-conservative escalation (the agent emits ESCALATED despite every upstream step being clean) and phantom blocker fabrication (the agent invents a blocker entry from upstream data that doesn't actually contain a blocker flag).

**Expected Checklist Assembler output per SPEC-AGENT-CLA-001 v0.3:**
- `overall_status: "COMPLETE"`
- All assembly fields present and non-null — §7.2 null passthrough does not apply because no upstream agent returned null
- `data_classification: "UNREGULATED"`, `fast_track_eligible: true`, `required_security_actions: []` — passthrough from STEP-02
- `dpa_required: false` — passthrough from STEP-03
- `approval_path: "FAST_TRACK"`, `required_approvals[]` populated — passthrough from STEP-04
- `blockers: []`
- `citations[]` aggregated from all three domain agents, each entry tagged with its originating `agent_id`
- `vendor_name: "OptiChain"`, `pipeline_run_id: "run_scenario_12"`
- `blocked_reason` and `blocked_fields` absent

---

## Critical rule: isolated scenario data only

**Do not edit any production source documents.** All artifacts live under `scenario_data/scenario_12/`.

The Checklist Assembler has no index access per SPEC-AGENT-CLA-001 §4. This scenario requires **no chunking and no index builds** — the bundle is composed entirely of upstream domain agent outputs, audit log entries, and the minimal questionnaire stub needed for `vq_direct_access` header lookup.

---

## What you need to build

### 1. Bundle fixture

Create `tests/fixtures/bundles/step_05_scenario_12.json`. The bundle must contain full (not trimmed) domain agent outputs, a non-empty audit log with retrieval + determination + status-change entries, and the minimal questionnaire stub.

**IT Security Agent output (STEP-02) — `status: complete`**, full STEP-02 contract per ORCH-PLAN-001:
- `integration_type_normalized: "EXPORT_ONLY"`
- `integration_tier: "TIER_3"`
- `data_classification: "UNREGULATED"`
- `eu_personal_data_present: "NO"`
- `fast_track_eligible: true`
- `fast_track_rationale: "ELIGIBLE_LOW_RISK"`
- `security_followup_required: false`
- `nda_status_from_questionnaire: "EXECUTED"`
- `required_security_actions: []`
- `policy_citations`: at least one ISP-001 PRIMARY entry (e.g., §12.2 ERP integration tier chunk), with `source_id`, `version`, `chunk_id`, `section_id`, `citation_class: "PRIMARY"`, `retrieval_timestamp`
- `status: "complete"`

**Legal Agent output (STEP-03) — `status: complete`**, all fields resolved:
- `dpa_required: false`
- `dpa_blocker: false`
- `nda_status: "EXECUTED"`
- `nda_blocker: false`
- `trigger_rule_cited: []` (empty is correct when `dpa_required: false`)
- `policy_citations`: at least one ISP-001 §12.1.4 NDA clause PRIMARY entry
- `status: "complete"`

**Procurement Agent output (STEP-04) — `status: complete`**, all fields resolved:
- `approval_path: "FAST_TRACK"`
- `fast_track_eligible: true` (passthrough from IT Security — must match STEP-02's value)
- `required_approvals[]`: at least one named approver entry with `approver`, `domain`, `status`, `blocker: false`, `estimated_completion`
- `estimated_timeline`: non-empty string (e.g., `"2-3 business days"`)
- `policy_citations`: at least one PAM-001 PRIMARY entry for the matched fast-track row
- `status: "complete"`

**Audit log entries** — `audit_log_entries` array. Include the realistic minimum that a clean run would produce. Each entry must have `entry_id`, `event_type`, `agent_id`, `timestamp`, plus `source_queried` and `chunks_retrieved` where applicable:

- `RETRIEVAL` entry for STEP-02 (ISP-001 query by `it_security_agent`)
- `DETERMINATION` entry for STEP-02 by `it_security_agent`
- `STATUS_CHANGE` entry marking STEP-02 complete
- `RETRIEVAL` entries for STEP-03 (ISP-001 §12.1.4 NDA clause query by `legal_agent`; DPA-TM-001 may or may not be queried depending on implementation)
- `DETERMINATION` entry for STEP-03 by `legal_agent`
- `STATUS_CHANGE` entry marking STEP-03 complete
- `RETRIEVAL` entry for STEP-04 (PAM-001 query by `procurement_agent`)
- `DETERMINATION` entry for STEP-04 by `procurement_agent`
- `STATUS_CHANGE` entry marking STEP-04 complete

**No `ESCALATION` entries should appear** — their absence is part of what makes this scenario the clean-pass reference.

**Questionnaire stub for `vq_direct_access`**. Minimal:
- `vendor_name: "OptiChain"`
- `pipeline_run_id: "run_scenario_12"`

No other questionnaire fields present — CLA's `vq_direct_access` scope is limited to these two fields per §4.

The bundle is **admissible** per SPEC-AGENT-CLA-001 §3: three schema-valid domain outputs, non-empty audit log, every admissibility-required field present.

### 2. Isolated test environment configuration

The test harness must:

- load `scenario_data/scenario_12/` fixtures and route the Checklist Assembler run to the scenario-12 bundle
- provide a scenario-scoped `vq_direct_access` stub that returns only `vendor_name` and `pipeline_run_id`
- assert that the Checklist Assembler issues zero queries against any `idx_*` endpoint (queries against `vq_direct_access` for `vendor_name` are permitted)
- leave scenarios 1–11 untouched
- not mutate production artifacts under any failure path

### 3. Scenario 12 evaluator

Add a scenario 12 path to the Checklist Assembler evaluator.

**Hard checks:**

- **`overall_status == "COMPLETE"`** — the linchpin check. Catches over-conservative escalation (emitting ESCALATED despite every upstream step being clean) and establishes the baseline behavior.

- **All required checklist fields are present and non-null:** `data_classification`, `fast_track_eligible`, `required_security_actions`, `dpa_required`, `approval_path`, `required_approvals`, `blockers`, `citations`, `vendor_name`, `pipeline_run_id`. On a COMPLETE run no field may be null per §7 output field constraints.

- **`blockers` is present and deep-equals `[]`.** The field must exist as an empty array, not be absent (absent is §7.1 blocked-shape semantics) and not be populated with phantom entries.

- **Passthrough integrity — field-by-field exact match:**
  - `data_classification == "UNREGULATED"` (from STEP-02)
  - `fast_track_eligible == true` (from STEP-02; also matches STEP-04's passthrough value)
  - `required_security_actions == []` (from STEP-02)
  - `dpa_required == false` (from STEP-03)
  - `approval_path == "FAST_TRACK"` (from STEP-04)
  - `required_approvals` deep-equals STEP-04's `required_approvals`

- **`citations[]` per-agent coverage:**
  - at least one entry with `agent_id == "it_security_agent"`
  - at least one entry with `agent_id == "legal_agent"`
  - at least one entry with `agent_id == "procurement_agent"`

- **No hallucinated citations.** Every citation in the output traces back to an entry actually present in the originating agent's upstream `policy_citations[]`. Build a lookup from the bundle and assert every output citation's `source_name` + `section` matches an upstream entry. This is a hard check, not soft — hallucination is a silent failure regardless of scenario difficulty, and the temptation to "clean up" citations exists even on the happy path.

- **No top-level domain-owned fields surfaced in the checklist.** The output must NOT contain top-level `dpa_blocker`, `nda_status`, `nda_blocker`, `trigger_rule_cited`, `integration_type_normalized`, `integration_tier`, `eu_personal_data_present`, `fast_track_rationale`, `security_followup_required`, `nda_status_from_questionnaire`, or `estimated_timeline`. These fields live in their originating agent outputs; the checklist contract does not include them.

- **`blocked_reason` and `blocked_fields` are absent from the output.**

- **Header fields populated from `vq_direct_access`:** `vendor_name == "OptiChain"`, `pipeline_run_id == "run_scenario_12"`.

- **No index endpoint queried during the CLA run.** Scan the run's post-execution audit log for entries where `agent_id == "checklist_assembler"` and `event_type == "RETRIEVAL"` against any `idx_*` endpoint. Any such entry is a §4 violation — fail. Queries against `vq_direct_access` are permitted and should be ignored by this check.

**Soft checks:**

- `blocker: false` on every entry in `required_approvals[]` — no approval entry should carry an active blocker flag on a clean pass.
- Citations include the ISP-001, DPA-TM-001 (if queried), and PAM-001 sources in the aggregate — a full `citations[]` array should span all three Tier 1 formal governing sources.
- Audit log has three `STATUS_CHANGE` entries marking each upstream step complete, and no `ESCALATION` entries.

**The critical failure modes to catch:**

1. **Over-conservative escalation.** The agent sees three upstream outputs, notices the bundle is richer than strictly required, and emits `overall_status: "ESCALATED"` with a constructed blocker entry because it feels like something must need escalating. The `overall_status == "COMPLETE"` and `blockers == []` hard checks catch this. This failure mode is specific to the happy path — Scenarios 11 and 8 test the opposite (silent-swallow) failure, and a model that over-corrects after those scenarios may fail here.

2. **Phantom blocker fabrication.** The agent emits `overall_status: "COMPLETE"` correctly but populates `blockers[]` with entries derived from upstream fields that are NOT flagged as blockers — for example, creating a `NDA_UNCONFIRMED` entry because it saw `nda_status: "EXECUTED"` and misread "status" as an escalation signal. Per §6.2, `blockers[]` entries are generated only from explicit upstream blocker flags (`dpa_blocker: true`, `nda_blocker: true`) or from BLOCKED / ESCALATED step statuses. None of those conditions hold here. The `blockers == []` deep-equality check catches this.

3. **Null assembly fields on a COMPLETE run.** The agent emits `overall_status: "COMPLETE"` but leaves one or more assembly fields null — for instance, `required_approvals: null` because the agent treats the happy path like an escalated path with nothing to escalate. Per §7 and A-05, on COMPLETE runs all assembly fields must be non-null. The non-null hard check catches this.

4. **Citation under-aggregation.** The agent pulls citations from only one or two upstream agents — for example, favoring Procurement's citation because "the approval path is the headline output." The per-agent coverage check catches this.

5. **Citation hallucination.** The agent invents plausible-looking citations to "pad" the citations array — e.g., emitting `"ISP-001 §6.2"` when no such section was actually cited upstream. The no-hallucinated-citations hard check catches this.

6. **Index query attempt.** The agent tries to verify or enrich a citation by querying `idx_security_policy` or similar. The audit log scan catches this.

### 4. Verify fixture integrity before the API call

Validate before the API call is issued:

- All three domain agent outputs are schema-valid per their respective output contracts (full shape, not just CLA's admissibility minimum).
- Audit log is non-empty and contains at least one `DETERMINATION` entry per upstream agent.
- No `ESCALATION` entries are present — their absence is part of the scenario's correctness.
- Every `policy_citations[]` entry in each domain output has a corresponding `RETRIEVAL` audit log entry with matching `source_queried` and a `retrieval_timestamp` consistent within tolerance.
- `vendor_name` and `pipeline_run_id` resolve correctly via the scenario-scoped `vq_direct_access` stub.
- `fast_track_eligible` in STEP-04's output matches STEP-02's value (both `true`) — a mismatch here would be a bundle inconsistency that could produce confusing downstream failures.

If any fixture check fails, fix the fixture before the API call — the fixture-vs-model failure lesson from Scenario 9 applies here too.

---

## Before running

State the fixture path (`tests/fixtures/bundles/step_05_scenario_12.json`), the spec version being tested (SPEC-AGENT-CLA-001 v0.3), and confirm:

1. no production artifacts were touched
2. no new indices were built
3. the test harness is routing CLA only to the scenario-12 bundle
4. fixture integrity checks passed

Wait for confirmation before the API call.
