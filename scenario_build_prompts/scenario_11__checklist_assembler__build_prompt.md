# Scenario 11 — Checklist Assembler Fixture Build: Cross-Agent Escalation Cascade → ESCALATED

## What this tests

The Checklist Assembler receives a bundle where STEP-02 is complete, STEP-03 is escalated (workflow-consequence escalation with `dpa_blocker: true`, all Legal fields fully resolved — the Scenario 8 upstream shape), and STEP-04 is escalated (downstream propagation from Legal — the Scenario 8 output shape, with `approval_path` populated from a clean PAM-001 match). Every upstream domain output is present and schema-valid; the audit log is non-empty.

The correct behavior is: the agent derives `overall_status = ESCALATED` from §8.1 precedence (NOT complete, despite every step reaching a terminal state and STEP-04 producing a valid approval path), assembles `blockers[]` from the upstream flags and statuses per §6.2, passes every other assembly field through from its upstream owner unchanged, and aggregates `citations[]` across all three domain agents.

This scenario targets the single field the Checklist Assembler actually derives (`overall_status`) and the cross-agent behaviors (blocker assembly from multiple sources, citation aggregation across agents) that structurally cannot be tested at any individual domain agent. It is the Scenario 8 "silent swallow of upstream escalation" pattern recurring at the pipeline endpoint — the highest-stakes manifestation of that failure mode because a false COMPLETE here sends the run forward to STEP-06 with stakeholder guidance for a vendor that hasn't actually cleared.

**Expected Checklist Assembler output per SPEC-AGENT-CLA-001 v0.3:**
- `overall_status: "ESCALATED"`
- All assembly fields **present and non-null** (no nulls — every upstream agent resolved its determinations even while escalated; §7.2 null-passthrough does not apply here)
- `data_classification`, `fast_track_eligible`, `required_security_actions` — passthrough from STEP-02
- `dpa_required: true` — passthrough from STEP-03
- `approval_path: "STANDARD"`, `required_approvals[]` — passthrough from STEP-04
- `blockers[]` containing three entries:
  - `DPA_REQUIRED` with `resolution_owner` naming Legal / General Counsel and a `citation` referencing Legal's DPA determination audit log entry
  - `ESCALATION_PENDING` referencing STEP-03's escalation audit entry
  - `ESCALATION_PENDING` referencing STEP-04's escalation audit entry
- `citations[]` aggregated from all three agents' `policy_citations[]`, each entry tagged with its originating `agent_id`
- `vendor_name` and `pipeline_run_id` populated from the questionnaire / pipeline state
- `blocked_reason` and `blocked_fields` **absent** from the output (escalated shape, not blocked shape)

---

## Critical rule: isolated scenario data only

**Do not edit any production source documents.** All artifacts live under `scenario_data/scenario_11/`. The Checklist Assembler has no index access per SPEC-AGENT-CLA-001 §4 — `idx_security_policy`, `idx_dpa_matrix`, `idx_procurement_matrix`, `idx_slack_notes` are all prohibited. CLA reads pipeline state and only queries `vq_direct_access` for `vendor_name`. This scenario therefore requires **no chunks and no index builds** — the bundle is constructed entirely from domain agent outputs and synthetic audit log entries.

---

## What you need to build

### 1. Bundle fixture

Create `tests/fixtures/bundles/step_05_scenario_11.json`. The bundle must contain all three domain agent outputs, audit log entries, and the minimal questionnaire stub needed for `vq_direct_access` header lookup.

**IT Security Agent output (STEP-02) — `status: complete`**, all fields fully resolved per the STEP-02 output contract in ORCH-PLAN-001:
- `integration_type_normalized: "DIRECT_API"`
- `integration_tier: "TIER_2_SAAS"`
- `data_classification: "REGULATED"`
- `eu_personal_data_present: "YES"`
- `fast_track_eligible: false` (consistent with REGULATED)
- `fast_track_rationale: "DISALLOWED_REGULATED_DATA"`
- `security_followup_required: false`
- `nda_status_from_questionnaire: "EXECUTED"`
- `required_security_actions: []`
- `policy_citations`: at least two ISP-001 PRIMARY entries (e.g., §12.2 ERP tier chunk and §4 data classification chunk), each with `source_id`, `version`, `chunk_id`, `section_id`, `citation_class: "PRIMARY"`, `retrieval_timestamp`
- `status: "complete"`

**Legal Agent output (STEP-03) — `status: escalated`** with `dpa_blocker: true`. This is the Scenario 8 upstream shape: every determination field present and resolved — the escalation is a workflow consequence, not an evidence gap. All nullable fields have concrete values (no nulls):
- `dpa_required: true`
- `dpa_blocker: true`
- `nda_status: "EXECUTED"`
- `nda_blocker: false`
- `trigger_rule_cited`: non-empty array with at least one DPA-TM-001 entry (`source_id`, `version`, `row_id`, `trigger_condition`)
- `policy_citations`: at least two PRIMARY entries — one DPA-TM-001 row citation and one ISP-001 §12.1.4 NDA clause citation
- `status: "escalated"`

**Procurement Agent output (STEP-04) — `status: escalated`**. The Scenario 8 output shape: matrix lookup succeeded cleanly, but the agent emitted `escalated` because upstream carried a terminal blocker. Every determination field is present and populated — this is NOT the blocked shape:
- `approval_path: "STANDARD"`
- `fast_track_eligible: false` (passthrough from IT Security)
- `required_approvals[]`: at least two entries (named approvers per the matched PAM-001 row); at least one entry should carry `blocker: true` with a description referencing the upstream DPA gap (this is one of the three channels by which Procurement can surface upstream blockers per the Scenario 8 contract)
- `estimated_timeline`: non-empty string (e.g., `"5-7 business days once DPA is executed"`)
- `policy_citations`: at least one PAM-001 PRIMARY citation for the matched row
- `status: "escalated"`

**Audit log entries** — `audit_log_entries` array in the bundle. At minimum, the following events must be present with well-formed `entry_id`, `event_type`, `agent_id`, `timestamp`, plus `source_queried` and `chunks_retrieved` where applicable:

- `RETRIEVAL` entries for STEP-02 (ISP-001 queries)
- `DETERMINATION` entry for STEP-02 by `it_security_agent`
- `STATUS_CHANGE` entry marking STEP-02 complete
- `RETRIEVAL` entries for STEP-03 (DPA-TM-001 row query; ISP-001 §12.1.4 NDA clause query)
- `DETERMINATION` entry for STEP-03 by `legal_agent` — **this is the entry the DPA_REQUIRED blocker in the final checklist will cite**
- `ESCALATION` entry for STEP-03 with full payload per CC-001 §13.1: `evidence_condition` naming `dpa_blocker: true`, `triggering_agent_id: "legal_agent"`, `resolution_owner: "Legal / General Counsel"`, `minimum_evidence_to_resolve` describing the executed DPA
- `STATUS_CHANGE` entry marking STEP-03 escalated
- `RETRIEVAL` entries for STEP-04 (PAM-001 row query)
- `DETERMINATION` entry for STEP-04 by `procurement_agent`
- `ESCALATION` entry for STEP-04 naming upstream `dpa_blocker` propagation, `triggering_agent_id: "procurement_agent"`, `resolution_owner: "Legal / General Counsel"` (distinct from any Procurement-owned escalation)
- `STATUS_CHANGE` entry marking STEP-04 escalated

The Checklist Assembler uses these entries as citation sources for `blockers[].citation` (referencing the escalation payloads) and for `citations[].retrieval_timestamp` (where not already on the `policy_citations` object).

**Questionnaire stub for `vq_direct_access`**. Minimal — only what CLA needs for header population:
- `vendor_name: "OptiChain"`
- `pipeline_run_id: "run_scenario_11"`

No other questionnaire fields should be present in the CLA bundle. Per SPEC-AGENT-CLA-001 §4, CLA's `vq_direct_access` scope is limited to `vendor_name` and `pipeline_run_id` — domain-relevant questionnaire fields were consumed upstream and arrive only via the domain agent outputs.

The bundle is **admissible** per SPEC-AGENT-CLA-001 §3: all three domain outputs are present and schema-valid, and the audit log is non-empty. The upstream escalations are workflow conditions, not admissibility failures — the assembler must proceed with assembly, not block.

### 2. Isolated test environment configuration

The test harness must:

- load `scenario_data/scenario_11/` fixtures and route the Checklist Assembler run to the scenario-11 bundle
- provide a scenario-scoped `vq_direct_access` stub that returns only `vendor_name` and `pipeline_run_id` for this run
- assert that no index endpoint is queried during the run — CLA should produce zero `RETRIEVAL` entries against any `idx_*` endpoint under `agent_id: "checklist_assembler"`
- leave scenarios 1–10 untouched (existing fixtures, indices, and evaluators continue as-is)
- not mutate production artifacts under any failure path

### 3. Scenario 11 evaluator

Add a scenario 11 path to the Checklist Assembler evaluator.

**Hard checks:**

- **`overall_status == "ESCALATED"`** — the linchpin check. The primary failure mode this scenario catches is emitting COMPLETE despite two upstream steps being escalated. §8.1 precedence is unambiguous: any upstream `escalated` → ESCALATED, and the rule is first-match, not best-match.

- **All assembly fields are present and non-null.** Required present: `data_classification`, `fast_track_eligible`, `required_security_actions`, `dpa_required`, `approval_path`, `required_approvals`, `blockers`, `citations`, `vendor_name`, `pipeline_run_id`. None may be absent (the §7.1 blocked shape) and none may be null (which would imply §7.2 upstream-null passthrough — but no upstream agent returned null in this bundle).

- **Passthrough integrity — field-by-field exact match against upstream:**
  - `data_classification == "REGULATED"` (from STEP-02 exactly)
  - `fast_track_eligible == false` (from STEP-02 exactly)
  - `required_security_actions == []` (from STEP-02 exactly)
  - `dpa_required == true` (from STEP-03 exactly)
  - `approval_path == "STANDARD"` (from STEP-04 exactly)
  - `required_approvals` deep-equals STEP-04's `required_approvals` output

- **`blockers[]` contains a `DPA_REQUIRED` entry:**
  - exactly one entry with `blocker_type == "DPA_REQUIRED"`
  - `resolution_owner` contains the substring `"Legal"` (exact-string match is too brittle; accept `"Legal (General Counsel)"`, `"Legal / General Counsel"`, etc.)
  - `citation` is a non-empty string referencing the Legal `DETERMINATION` audit log entry — match on `entry_id` or a recognizable substring of the audit entry identifier
  - `description` is non-empty

- **`blockers[]` contains `ESCALATION_PENDING` entries for STEP-03 and STEP-04:**
  - at least two entries with `blocker_type == "ESCALATION_PENDING"`
  - one references the STEP-03 `ESCALATION` audit entry; one references the STEP-04 `ESCALATION` audit entry
  - each carries a non-empty `citation` pointing to the corresponding audit entry

- **`citations[]` per-agent coverage:**
  - at least one entry with `agent_id == "it_security_agent"`
  - at least one entry with `agent_id == "legal_agent"`
  - at least one entry with `agent_id == "procurement_agent"`
  - **no hallucinated citations**: every citation's `source_name` and `section` correspond to an entry actually present in the originating agent's upstream `policy_citations[]` array. Build a lookup from the bundle's `policy_citations` entries and assert every output citation matches one of them.

- **No domain-owned fields re-surfaced at the checklist level.** The output must NOT contain top-level `dpa_blocker`, `nda_status`, `nda_blocker`, `trigger_rule_cited`, `integration_tier`, `integration_type_normalized`, `fast_track_rationale`, or `security_followup_required`. Those live in the upstream agent outputs; the checklist contract does not include them. Emitting them is a schema violation and a subtle passthrough-discipline failure (A-02).

- **`blocked_reason` and `blocked_fields` are absent.** This run is not blocked; the blocked-shape-only fields must not appear.

- **No index endpoint queried.** Scan the run's post-execution audit log for any entries where `agent_id == "checklist_assembler"` and `event_type == "RETRIEVAL"` against an `idx_*` endpoint. Any such entry is a §4 violation — fail.

**Soft checks:**

- STEP-03 and STEP-04 `ESCALATION` audit entries have distinct `entry_id`s, and the two `ESCALATION_PENDING` blocker entries cite them correctly (not pointing to the same entry).
- `vendor_name == "OptiChain"` and `pipeline_run_id == "run_scenario_11"` — populated via `vq_direct_access`, not inferred from other bundle contents.
- If Procurement's upstream output included any SUPPLEMENTARY (Tier 3 / Slack) citations, those entries in the final `citations[]` preserve their SUPPLEMENTARY classification.

**The critical failure modes to catch:**

1. **Silent swallow of upstream escalation (status precedence error).** The agent sees every step reached a terminal state, every upstream output is populated, and `approval_path` is a clean `"STANDARD"`, and emits `overall_status: "COMPLETE"` — reasoning "the pipeline completed." This is the Scenario 8 failure mode recurring at the pipeline's final boundary. The `overall_status` hard check catches it directly. A false COMPLETE here is the single most consequential failure the Checklist Assembler can produce because it sends the run forward to STEP-06 (Checkoff Agent) and causes stakeholder onboarding guidance to be generated for a vendor that hasn't actually cleared the compliance step.

2. **Shape collapse (treating ESCALATED as BLOCKED).** The agent sees upstream escalations and emits the §7.1 blocked output shape, stripping every assembly field. This is the over-conservative failure, distinct from (1). The "all assembly fields present and non-null" check catches it. Watch for this specifically if the agent has been trained to associate "escalation" with "failure" — the spec's ESCALATED shape is a valid, useful output, not a failure.

3. **Blocker assembly incomplete — missing the DPA_REQUIRED entry.** The agent emits `blockers[]` with only the two `ESCALATION_PENDING` entries (derived from step statuses) and forgets to also derive an entry from `legal_agent.dpa_blocker == true`. §6.2 makes the flag-derived and status-derived sources independent — both generate entries. Catching this matters because the DPA_REQUIRED blocker is the ONLY signal in the final checklist that tells a downstream human what specifically needs to be resolved for the vendor to clear.

4. **Citation aggregation gap.** The agent pulls citations from only one or two of the three agents — for example, favoring STEP-04's citations because that was the final step, or omitting Legal's citations because the Legal output was escalated and the agent treated escalation as partial-completion. This is a quiet failure: the checklist schema-validates and passes eyeball review, but audit traceability for a domain is missing. The per-agent citation-coverage hard check is the only defense.

5. **Hallucinated citations.** The agent invents plausible-looking `source_name` + `section` combinations (e.g., `"ISP-001 §6.2"` when no such section was actually cited upstream) because the aggregation prompt is interpreted as "describe the authoritative sources" rather than "copy what upstream already cited." The no-hallucinated-citations cross-check catches this.

6. **Re-derivation of upstream fields.** The agent emits top-level `dpa_blocker: true` or `nda_status: "EXECUTED"` at the checklist level, duplicating Legal's fields. The Checklist Assembler's output contract does not include these fields; they remain in Legal's output and are referenced via `blockers[]` and `citations[]`. The no-domain-fields-at-checklist-level check catches this.

7. **Index query attempt.** The agent tries to enrich the checklist by querying `idx_security_policy` or similar — for example, to "verify" a citation or pull additional context. §4 prohibits this categorically. The audit log scan catches this.

### 4. Verify fixture integrity before the API call

Run a fixture-validation pass before the API call is issued. The Scenario 9 lesson — that fixture defects can masquerade as model failures — applies with particular force here because CLA's bundle is composed entirely of upstream agent outputs and audit log entries, and internal inconsistency between them would produce confusing failure signals.

Validate:

- Every `policy_citations[]` entry in each domain agent output has a corresponding `RETRIEVAL` audit log entry with matching `source_queried` and a `retrieval_timestamp` that matches within tolerance.
- Every `ESCALATION` audit log entry has `triggering_agent_id`, `resolution_owner`, and a non-empty `evidence_condition` populated per CC-001 §13.1.
- STEP-03's `ESCALATION` entry and Legal's `DETERMINATION` entry have distinct `entry_id`s — the DPA_REQUIRED blocker in the checklist must be able to cite them independently.
- The questionnaire stub resolves via the scenario-scoped `vq_direct_access` for `vendor_name` without error.
- The three domain agent outputs collectively satisfy SPEC-AGENT-CLA-001 §3 admissibility exactly — no missing required fields.
- Every `required_approvals[]` entry in STEP-04's output has the expected shape (`approver`, `domain`, `status`, `blocker`, `estimated_completion`) so that passthrough deep-equality does not fail on a schema mismatch.

If any fixture check fails, adjust the fixture and re-run validation before the API call.

---

## Before running

State the fixture path (`tests/fixtures/bundles/step_05_scenario_11.json`), the spec version being tested (SPEC-AGENT-CLA-001 v0.3), and confirm: (1) no production artifacts were touched, (2) no new indices were built, (3) the test harness is routing CLA to the scenario-11 bundle only, and (4) fixture integrity checks passed. Wait for confirmation before the API call.
