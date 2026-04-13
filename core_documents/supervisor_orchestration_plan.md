# Supervisor Orchestration Plan — ORCH-PLAN-001 v0.8

**Document ID:** ORCH-PLAN-001  
**Version:** 0.10
**Owner:** Engineering / IT Architecture  
**Last Updated:** April 13, 2026

> Deterministic orchestration plan for the Supervisor Agent state machine. Defines execution steps, gate conditions, subqueries, retrieval routing, downstream handoff contracts, and runtime state mutation rules. The Supervisor loads this document at pipeline initialization and drives the execution graph against it.

---

## Document Authority and Dependency Notes

This orchestration plan is the runtime contract for execution sequencing, gate evaluation, state mutation, and step-to-step handoff behavior. It is authoritative for how the Supervisor walks the pipeline.

It does **not** redefine source authority, evidence admissibility, provenance minimums, or escalation ownership. Those remain governed by the Context Contract. It also does **not** redefine system architecture, component topology, or output schema ownership, which remain governed by the Design Doc. Agent behavioral rules, output-writing discipline, and DO / DON'T implementation guidance remain governed by the Agent Spec.

When document boundaries appear to overlap, the precedence for implementation is:

1. **This orchestration plan** for execution order, gate logic, step-to-step handoff behavior, and `PipelineState` mutation
2. **Context Contract** for source authority, retrieval permissions, admissibility, provenance, freshness, conflict handling, and escalation ownership
3. **Design Doc** for architecture, component responsibilities, and system-level output contracts
4. **Agent Spec** for behavioral rules and implementation discipline

---

## Quick Navigation

| Step | Requirement | Label | Agent | Parallel With |
|------|-------------|-------|-------|---------------|
| [STEP-01](#step-01--r-01-intake-validation) | R-01 | Intake Validation | Supervisor | — |
| [STEP-02](#step-02--r-02-onboarding-path-classification-and-fast-track-determination) | R-02 | Onboarding Path Classification and Fast-Track Determination | IT Security Agent | — |
| [STEP-03](#step-03--r-03-legal-and-compliance-trigger-determination) | R-03 | Legal & Compliance Trigger Determination | Legal Agent | — |
| [STEP-04](#step-04--r-04-approval-path-routing) | R-04 | Approval Path Routing | Procurement Agent | — |
| [STEP-05](#step-05--r-05-approval-checklist-generation) | R-05 | Approval Checklist Generation | Checklist Assembler | — |
| [STEP-06](#step-06--r-06-stakeholder-guidance-and-checkoff-support) | R-06 | Stakeholder Guidance & Checkoff Support | Checkoff Agent | — |

---

## Pipeline Run Schema

Every pipeline run is initialized with the following fields:

| Field | Type |
|-------|------|
| `pipeline_run_id` | Unique string — generated at init |
| `vendor_name` | String — populated only after STEP-01 confirms a valid questionnaire |
| `manifest_version` | String — CC-001 version locked at init |
| `initialized_at` | ISO 8601 UTC |

---

## PipelineState Initialization

At pipeline initialization, before any retrieval or questionnaire inspection occurs, the Supervisor shall create a mutable `PipelineState` object for the run. This object is the runtime source of truth for orchestration progress, step results, escalations, audit references, and next-step selection. Questionnaire presence, completeness, and version checks remain exclusively in STEP-01 and must not be inferred during initialization.

### Canonical `PipelineState` object

```json
{
  "pipeline_run_id": "run_001",
  "vendor_name": null,
  "manifest_version": "CC-001-v1.4",
  "initialized_at": "2026-04-10T16:00:00Z",
  "overall_status": "IN_PROGRESS",
  "current_step": "STEP-01",
  "active_steps": [],
  "step_statuses": {
    "STEP-01": "PENDING",
    "STEP-02": "PENDING",
    "STEP-03": "PENDING",
    "STEP-04": "PENDING",
    "STEP-05": "PENDING",
    "STEP-06": "PENDING"
  },
  "determinations": {
    "step_01_intake": null,
    "step_02_security_classification": null,
    "step_03_legal": null,
    "step_04_procurement": null,
    "step_05_checklist": null,
    "step_06_guidance": null
  },
  "escalations": [],
  "audit_refs": [],
  "next_step_queue": ["STEP-01"]
}
```

### PipelineState field meanings

| Field | Meaning |
|---|---|
| `overall_status` | Run-level status derived from terminal step results. May be `IN_PROGRESS`, `COMPLETE`, `ESCALATED`, or `BLOCKED`. |
| `current_step` | The step currently being evaluated by the Supervisor. In this sequential plan, only one step is actively processed at a time. |
| `active_steps` | Array of steps currently in progress. In this sequential plan, it contains at most one step at a time. |
| `step_statuses` | Canonical state map for each step. Valid values: `PENDING`, `IN_PROGRESS`, `COMPLETE`, `ESCALATED`, `BLOCKED`. |
| `determinations` | Stores the schema-valid output object returned for each completed step. |
| `escalations` | Array of escalation payloads emitted during the run. |
| `audit_refs` | References to append-only audit log entries written during the run. |
| `next_step_queue` | Ordered list of steps eligible for evaluation after current transition logic completes. |

### Initialization rules

1. The Supervisor generates `pipeline_run_id`.
2. The Supervisor locks `manifest_version` and records `initialized_at`.
3. The Supervisor sets `current_step = STEP-01`.
4. All step statuses initialize to `PENDING`.
5. No questionnaire-derived values are populated during initialization.
6. `next_step_queue` initializes with `STEP-01` only.
7. The first mutation of `vendor_name` occurs only after STEP-01 confirms a valid questionnaire.
8. `determinations` entries remain `null` until the corresponding step returns a schema-valid output object.
9. `overall_status` remains `IN_PROGRESS` until a terminal run-level state is derived.

### PipelineState mutation rules

1. A step must transition `PENDING -> IN_PROGRESS -> TERMINAL_STATE`.
2. Terminal states are `COMPLETE`, `ESCALATED`, and `BLOCKED`.
3. A step may not revert from any terminal state back to `IN_PROGRESS` within the same run.
4. `current_step` must always reflect the step whose transition logic is being applied.
5. `active_steps` may contain at most one in-progress step at a time under this sequential plan.
6. `next_step_queue` is populated only by satisfied gate conditions; downstream steps may not be enqueued speculatively.
7. `overall_status` is derived by the Supervisor after every terminal step transition:
   - if any required active step is `BLOCKED`, run status becomes `BLOCKED`
   - else if any required active step is `ESCALATED`, run status becomes `ESCALATED`
   - else if all required steps for the run stage are `COMPLETE`, run status remains `IN_PROGRESS` until STEP-05 or `COMPLETE` after STEP-05
8. When a step is both BLOCKED and ESCALATED under the combined expression model, `overall_status` is emitted as `BLOCKED` and the escalation payload must still be preserved in `escalations[]` and the audit log.
9. STEP-06 does not change checklist substance; it produces downstream guidance only.

---

## Control Flow Rules

How the Supervisor walks this document at runtime:

1. Steps execute in `step_order` sequentially.
2. Before executing a step, the Supervisor evaluates `gate_condition` against current `pipeline_state`. If not satisfied, emit the step's `blocked_status` and halt all dependent downstream steps.
3. A step is **COMPLETE** when its agent returns a schema-valid output object fulfilling its output contract.
4. A step is **BLOCKED** when a required upstream step has not reached a terminal state or required evidence is entirely absent.
5. A step is **ESCALATED** when evidence is present but conflicting, or a human decision is explicitly required.
7. For each step, the Supervisor issues subqueries in the order listed, unless `subquery_condition` evaluates to false — in that case, skip and log the skip reason.
8. After all subqueries for a step complete, the Supervisor assembles the context bundle per `bundle_assembly_priority` and passes it to the assigned agent.
9. The Supervisor writes an audit log entry for every retrieval attempt, every chunk admitted or excluded, every determination, and every status change.

---

## Per-Step Execution Loop

For every executable step in this document, the Supervisor shall process the step through the same deterministic execution loop. This loop is the runtime procedure by which a step moves from `PENDING` to a terminal step state.

1. Read the current step definition from this plan.
2. Evaluate the step’s `gate_condition` against `PipelineState`.
3. If the gate fails, emit the configured blocked or escalation behavior, update `step_statuses`, and halt dependent downstream steps as defined.
4. Mark the step `IN_PROGRESS` in `PipelineState`.
5. Issue listed subqueries in order, skipping only when a documented condition evaluates to false.
6. Route each subquery to the correct retrieval lane and endpoint.
7. Collect returned evidence, log retrieval outcomes, and assemble the context bundle according to `bundle_assembly_priority`.
8. Pass the bundle to the assigned agent or, where explicitly stated, evaluate directly in Supervisor logic.
9. Validate the returned output against the step’s output contract.
10. Write the resulting determination, citations, and status into `PipelineState`.
11. Update `current_step`, `active_steps`, and `next_step_queue`, then advance to the next permitted step.
12. Append all retrieval, determination, suppression, escalation, and status-change events to the audit log.

### Terminal step states

A step is terminal when it reaches one of the following:

- `COMPLETE`
- `BLOCKED`
- `ESCALATED`

Downstream advancement rules must key off these terminal states, not off partial retrieval completion or partial agent output.

### `PipelineState` mutation rules

The Supervisor shall mutate `PipelineState` only through deterministic state transitions tied to step execution, escalation creation, and checklist emission.

1. On step dispatch, the Supervisor sets `step_statuses[STEP-X] = IN_PROGRESS`.
2. On terminal step completion, the Supervisor writes the step output into `determinations` and updates `step_statuses[STEP-X]` to the returned terminal state.
3. On every escalation, the Supervisor appends a structured escalation payload to `escalations[]`.
4. On every auditable event, the Supervisor appends a reference or pointer to `audit_refs[]`.
5. `current_step` advances only when the next step's gate condition is satisfied.
6. `next_step_queue` may contain only the next sequentially eligible step(s) whose gate conditions are satisfied.
7. When a step is both BLOCKED and ESCALATED under the combined expression model, `overall_status` is emitted as `BLOCKED` while the escalation payload is preserved in `escalations[]`; the escalation must not be collapsed or discarded.


---

## Canonical Gate States

Each step must resolve to one of the following:

- **COMPLETE** — the step returned a schema-valid output object fulfilling its output contract
- **BLOCKED** — a required source or upstream agent output is entirely absent; the step cannot proceed
- **ESCALATED** — evidence is present but conflicting, ambiguous, or outside the defined rule set; human judgment is required

BLOCKED and ESCALATED are distinct and must not be conflated. BLOCKED means there is nothing to reason over. ESCALATED means there is evidence but it cannot be resolved without human input.

---

## Lane Routing Rules

Each subquery must be routed according to the locked retrieval architecture.

| Source Type | Retrieval Lane | Retrieval Method |
|---|---|---|
| Questionnaire facts | direct structured lane | direct field lookup |
| Policy sections | indexed hybrid lane | BM25 + dense vector |
| Matrix rows | indexed hybrid lane | BM25 + dense vector |
| Slack / notes | indexed hybrid lane | BM25 + semantic, low-authority supplemental |
| Runtime outputs | non_retrieval | pipeline state read / prior step output read |

The questionnaire remains outside Chroma and BM25 and should be directly addressable as structured data. Indexed sources use one Chroma backend plus one BM25 backend with metadata filtering.

## Supervisor Retrieval Permissions and Boundaries

The Supervisor is an orchestration authority, not a free-form evidentiary retriever.

It **may**:
- read direct structured questionnaire fields required for STEP-01 intake validation
- read `PipelineState`, prior step outputs, and audit references
- dispatch retrieval requests defined in this plan to the correct lane and endpoint on behalf of downstream domain steps
- assemble bundle inputs strictly according to this plan and the Context Contract

It **may not**:
- independently query indexed-hybrid evidence sources as a domain reasoner outside explicitly defined orchestration checks
- introduce new retrieval logic, evidence reuse policies, or citation-passthrough behavior not already defined in the governing documents
- reinterpret domain evidence in place of the assigned domain agent
- override source authority, admissibility rules, or determination ownership defined elsewhere

This keeps the Supervisor aligned with the project architecture: it manages execution, routing, sequential handoff, and auditability, while domain agents remain responsible for evidence interpretation and domain determinations.

---

## STEP-01 — R-01: Intake Validation

**Assigned Agent:** Supervisor  
**Gates Downstream:** STEP-02  
**Parallel With:** —  
**Gate Condition:** Always executes first. No upstream dependency.

**If BLOCKED:** emit `BLOCKED`, notify Procurement, halt STEP-02 through STEP-06.

**Resolution Condition:** `questionnaire_exists == true AND questionnaire_complete == true AND version_conflict_detected == false`

**Audit Triggers:** `RETRIEVAL`, `STATUS_CHANGE`

---

### Subqueries


#### R01-SQ-01 — Questionnaire Existence Check

> Has a valid vendor questionnaire been submitted for this pipeline run?

| Field | Value |
|-------|-------|
| Retrieval Lane | `direct_structured` |
| Source | VQ-OC-001 |
| Endpoint | `vq_direct_access` |
| Method | `direct_field_lookup` |
| Condition | Always runs |
| Output Field | `questionnaire_exists` |

**Fields Required:** `submission_id`, `submission_timestamp`, `vendor_name`

**If fails:** Emit BLOCKED, halt all downstream steps, notify Procurement. Do not proceed to R01-SQ-02.

---

#### R01-SQ-02 — Questionnaire Completeness Check

> Are all required intake fields present and non-null in the submitted questionnaire?

| Field | Value |
|-------|-------|
| Retrieval Lane | `direct_structured` |
| Source | VQ-OC-001 |
| Endpoint | `vq_direct_access` |
| Method | `direct_field_lookup` |
| Condition | `questionnaire_exists == true` |
| Output Field | `questionnaire_complete` |

**Fields Required:**
- `vendor_name`
- `integration_details.erp_type`
- `data_classification_self_reported`
- `regulated_data_types`
- `eu_personal_data_flag`
- `data_subjects_eu`
- `existing_nda_status`
- `existing_msa`
- `vendor_class`
- `contract_value_annual`

**If fails:** Emit BLOCKED with field list, notify Procurement. Log each missing field individually in audit log.

---

#### R01-SQ-03 — Multiple Version Detection

> Does more than one questionnaire submission exist for this vendor and pipeline run?

| Field | Value |
|-------|-------|
| Retrieval Lane | `direct_structured` |
| Source | VQ-OC-001 |
| Endpoint | `vq_direct_access` |
| Method | `direct_field_lookup` |
| Condition | `questionnaire_exists == true` |
| Output Field | `version_conflict_detected` |

**Fields Required:** `submission_id`, `submission_version`

**If fails:** `workflow_state = BLOCKED`, `resolution_mode = ESCALATED_TO_PROCUREMENT`. No version may be used until authoritative version is selected.

---

### STEP-01 Output Fields

`questionnaire_exists` · `questionnaire_complete` · `version_conflict_detected`

---

## STEP-02 — R-02: Onboarding Path Classification and Fast-Track Determination

**Assigned Agent:** IT Security Agent  
**Gates Downstream:** STEP-03  
**Parallel With:** —  
**Gate Condition:** STEP-01 must be COMPLETE.

**If BLOCKED:** emit `BLOCKED`, notify IT Security, halt STEP-03 through STEP-06.

**Bundle Assembly Priority:**
1. Questionnaire fields — integration method, declared data profile, EU personal data, NDA status
2. IT Security Policy — ERP integration tier sections
3. IT Security Policy — data classification and access control sections
4. IT Security Policy — fast-track disqualification / review-trigger sections
5. Supplemental context — excluded when budget is constrained

**Resolution Condition:** `classification_policy_chunks` is non-empty AND `erp_tier_policy_chunks` is non-empty AND `integration_type_raw` is present


**Audit Triggers:** `RETRIEVAL`, `DETERMINATION`, `STATUS_CHANGE`

### STEP-02 Determination Logic

STEP-02 is the canonical security classification step. It owns:
- integration tier assignment
- data classification
- fast-track eligibility
- security follow-up requirement

Downstream agents must consume STEP-02 output as the authoritative security determination. STEP-04 may route approval path using this output, but it may not redefine fast-track eligibility or security classification.

### Subqueries

#### R02-SQ-01 — Read ERP Integration Type from Questionnaire

> What ERP integration method does OptiChain use — direct API, mediated middleware, or export-only file-based?

| Field | Value |
|-------|-------|
| Retrieval Lane | `direct_structured` |
| Source | VQ-OC-001 |
| Endpoint | `vq_direct_access` |
| Method | `direct_field_lookup` |
| Condition | Always runs |
| Output Field | `integration_type_raw` |

**Fields Required:** `integration_details.erp_type`, `integration_details.erp_system`

**If fails:** Flag as AMBIGUOUS. Do not halt — proceed to policy lookup to attempt classification from policy rules alone. Log ambiguity.

---

#### R02-SQ-02 — Read Self-Reported Data Classification from Questionnaire

> What data classification does OptiChain self-report for the data it will process?

| Field | Value |
|-------|-------|
| Retrieval Lane | `direct_structured` |
| Source | VQ-OC-001 |
| Endpoint | `vq_direct_access` |
| Method | `direct_field_lookup` |
| Condition | Always runs |
| Output Field | `self_reported_classification` |

**Fields Required:** `data_classification_self_reported`, `regulated_data_types`

**If fails:** Note as absent. Do not halt — policy retrieval will govern the classification determination.

---

#### R02-SQ-03 — Read EU Personal Data Flags from Questionnaire

> Does OptiChain process EU personal data? Who are the data subjects?

| Field | Value |
|-------|-------|
| Retrieval Lane | `direct_structured` |
| Source | VQ-OC-001 |
| Endpoint | `vq_direct_access` |
| Method | `direct_field_lookup` |
| Condition | Always runs |
| Output Field | `eu_personal_data_raw` |

**Fields Required:** `eu_personal_data_flag`, `data_subjects_eu`

**If fails:** Log as absent. Treat as unconfirmed — Legal Agent must be informed this field is absent.

---

#### R02-SQ-04 — Retrieve ERP Integration Tier Table from IT Security Policy

> What are the ERP integration tier classifications and their associated security requirements under ISP-001?

| Field | Value |
|-------|-------|
| Retrieval Lane | `indexed_hybrid` |
| Source | ISP-001 |
| Endpoint | `idx_security_policy` |
| Method | `hybrid_dense_bm25` |
| Rerank | Yes |
| Authority Weight | Tier 1 |
| Citation Class | PRIMARY |
| Condition | Always runs |
| Output Field | `erp_tier_policy_chunks` |

**Search Terms:** `ERP integration tier`, `§12.2`, `integration classification`, `Tier 1`, `Tier 2`, `Tier 3`, `Unclassified`

**If fails:** Classification evidence is insufficient. Emit ESCALATED on security determination. Log retrieval failure.

---

#### R02-SQ-05 — Retrieve Data Classification Sections from IT Security Policy

> What criteria determine whether a vendor integration is classified as regulated vs. unregulated under ISP-001?

| Field | Value |
|-------|-------|
| Retrieval Lane | `indexed_hybrid` |
| Source | ISP-001 |
| Endpoint | `idx_security_policy` |
| Method | `hybrid_dense_bm25` |
| Rerank | Yes |
| Authority Weight | Tier 1 |
| Citation Class | PRIMARY |
| Condition | Always runs |
| Output Field | `classification_policy_chunks` |

**Search Terms:** `regulated data`, `sensitive data`, `data classification`, `third-party access`, `§12`, `§4`, `access control`

**If fails:** Note in retrieval manifest. Proceed with ERP tier evidence alone if available.

---

#### R02-SQ-06 — Retrieve Fast-Track Disqualification and Review Conditions from IT Security Policy

> Under what security conditions is fast-track disallowed or forced into manual review?

| Field | Value |
|-------|-------|
| Retrieval Lane | `indexed_hybrid` |
| Source | ISP-001 |
| Endpoint | `idx_security_policy` |
| Method | `hybrid_dense_bm25` |
| Rerank | Yes |
| Authority Weight | Tier 1 |
| Citation Class | PRIMARY |
| Condition | Always runs |
| Output Field | `fast_track_policy_chunks` |

**Search Terms:** `fast track`, `manual review`, `regulated data`, `ERP integration`, `architecture review`, `third-party risk`

**If fails:** Fast-track determination cannot be made. Emit ESCALATED. Log retrieval failure.

---

#### R02-SQ-07 — Retrieve NDA Confirmation Requirement from IT Security Policy

> What does ISP-001 require regarding NDA execution before information exchange with a third party?

| Field | Value |
|-------|-------|
| Retrieval Lane | `indexed_hybrid` |
| Source | ISP-001 |
| Endpoint | `idx_security_policy` |
| Method | `hybrid_dense_bm25` |
| Rerank | Yes |
| Authority Weight | Tier 1 |
| Citation Class | PRIMARY |
| Condition | Always runs |
| Output Field | `nda_policy_chunks` |

**Search Terms:** `NDA`, `non-disclosure agreement`, `§12.1.4`, `information exchange`, `third-party`

**If fails:** NDA clause retrieval failed. Log retrieval failure. NDA determination deferred to Legal Agent.

---


### STEP-02 Output Contract

| Field | Values |
|-------|--------|
| `integration_type_normalized` | `DIRECT_API \| MIDDLEWARE \| EXPORT_ONLY \| AMBIGUOUS` |
| `integration_tier` | `TIER_1 \| TIER_2 \| TIER_3 \| UNCLASSIFIED_PENDING_REVIEW` |
| `data_classification` | `REGULATED \| UNREGULATED \| AMBIGUOUS` |
| `eu_personal_data_present` | `YES \| NO \| UNKNOWN` |
| `fast_track_eligible` | boolean |
| `fast_track_rationale` | `DISALLOWED_REGULATED_DATA \| DISALLOWED_INTEGRATION_RISK \| DISALLOWED_AMBIGUOUS_SCOPE \| ELIGIBLE_LOW_RISK` |
| `security_followup_required` | boolean |
| `nda_status_from_questionnaire` | `EXECUTED \| PENDING \| NOT_STARTED \| UNKNOWN` |
| `required_security_actions` | array of `{action_type, reason, owner}` |
| `policy_citations` | array of `{source_id, version, chunk_id, section_id, citation_class}` |
| `status` | `complete \| escalated \| blocked` |

### STEP-02 Classification rules

1. `integration_type_normalized` must be emitted on every non-blocked run of STEP-02.
2. `integration_tier` must be derived from Tier 1 policy evidence, not questionnaire self-report.
3. `data_classification` must be derived from Tier 1 policy evidence, with questionnaire fields treated as supporting input only.
4. `fast_track_eligible` is owned by STEP-02 and must be emitted before STEP-04 begins.
5. If `data_classification = REGULATED` or `integration_type_normalized = AMBIGUOUS`, then `fast_track_eligible = false`.
6. If fast-track cannot be confidently determined because a governing source is missing or unconfirmed, then `fast_track_eligible = false` and `fast_track_rationale = DISALLOWED_AMBIGUOUS_SCOPE`.
7. STEP-04 may consume `fast_track_eligible`, but may not override it.

---

## STEP-03 — R-03: Legal and Compliance Trigger Determination

**Assigned Agent:** Legal Agent  
**Gates Downstream:** STEP-04  
**Parallel With:** —  
**Gate Condition:** STEP-02 must be COMPLETE. Legal Agent requires `data_classification` from IT Security output.

**If BLOCKED:** emit `BLOCKED`, notify Legal, halt STEP-04 through STEP-06.

**Bundle Assembly Priority:**
1. IT Security Agent output — `data_classification` field only
2. Questionnaire EU personal data fields
3. Questionnaire NDA field — `existing_nda_status`
4. DPA legal trigger matrix rows — matching rows only
5. ISP-001 §12.1.4 NDA clause chunk
6. Supplemental context — excluded when budget is constrained

**Resolution Condition:** `upstream_data_classification` is present AND at least one applicable DPA trigger row match exists AND `nda_clause_chunks` is non-empty


**Audit Triggers:** `RETRIEVAL`, `DETERMINATION`, `STATUS_CHANGE`

---

### Subqueries

#### R03-SQ-01 — Read Upstream Data Classification from IT Security Output

> What data classification did the IT Security Agent determine for this vendor?

| Field | Value |
|-------|-------|
| Retrieval Lane | `non_retrieval` |
| Source | STEP-02 output |
| Method | `pipeline_state_read` |
| Condition | Always runs |
| Output Field | `upstream_data_classification` |

**Fields Required:** `data_classification`, `status`, `policy_citations`

**If fails:** Bundle is inadmissible. Emit BLOCKED. Do not proceed.

---

#### R03-SQ-02 — Read EU Personal Data Fields from Questionnaire

> Do questionnaire fields confirm that OptiChain processes EU personal data, and who are the data subjects?

| Field | Value |
|-------|-------|
| Retrieval Lane | `direct_structured` |
| Source | VQ-OC-001 |
| Endpoint | `vq_direct_access` |
| Method | `direct_field_lookup` |
| Condition | Always runs |
| Output Field | `eu_personal_data_questionnaire_fields` |

**Fields Required:** `eu_personal_data_flag`, `data_subjects_eu`

**If fails:** Flag as unconfirmed. DPA determination may still proceed using upstream `data_classification` and matrix evidence if sufficient. Log absence.

---

#### R03-SQ-03 — Read NDA Status from Questionnaire

> What is the current NDA execution status between OptiChain and Lichen Manufacturing?

| Field | Value |
|-------|-------|
| Retrieval Lane | `direct_structured` |
| Source | VQ-OC-001 |
| Endpoint | `vq_direct_access` |
| Method | `direct_field_lookup` |
| Condition | Always runs |
| Output Field | `nda_status_raw` |

**Fields Required:** `existing_nda_status`

**If fails:** Treat as UNKNOWN. Log as absent. NDA determination carries ESCALATED flag if NDA clause cannot be resolved.

---

#### R03-SQ-04 — Retrieve DPA Trigger Matrix Rows for EU Personal Data

> Which DPA trigger matrix rows apply when a vendor processes EU personal data, including employee scheduling and shift data?

| Field | Value |
|-------|-------|
| Retrieval Lane | `indexed_hybrid` |
| Source | DPA-TM-001 |
| Endpoint | `idx_dpa_matrix` |
| Method | `hybrid_dense_bm25_row_targeted` |
| Rerank | Yes |
| Authority Weight | Tier 1 |
| Citation Class | PRIMARY |
| Condition | `eu_personal_data_confirmed == YES OR upstream_data_classification == REGULATED` |
| Output Field | `dpa_eu_trigger_rows` |

**Search Terms:** `EU personal data`, `GDPR`, `Art. 28`, `employee data`, `data subjects`, `A-01`, `A-02`

**If fails:** Evidence is insufficient for RESOLVED DPA determination. Emit ESCALATED — no matrix row match for this data profile.

---

#### R03-SQ-06 — Retrieve NDA Confirmation Clause from IT Security Policy

> What does ISP-001 §12.1.4 require regarding NDA confirmation before information exchange may proceed?

> **Retrieval independence note:** For v1, Legal retrieves this clause independently even if a similar ISP-001 citation was already gathered in STEP-02. This keeps bundle assembly rules simple and avoids introducing undefined citation passthrough behavior into the orchestration contract.


| Field | Value |
|-------|-------|
| Retrieval Lane | `indexed_hybrid` |
| Source | ISP-001 |
| Endpoint | `idx_security_policy` |
| Method | `hybrid_dense_bm25` |
| Rerank | Yes |
| Authority Weight | Tier 1 |
| Citation Class | PRIMARY |
| Condition | Always runs |
| Output Field | `nda_clause_chunks` |

**Search Terms:** `NDA`, `§12.1.4`, `information exchange`, `non-disclosure`, `confirmation`

**If fails:** NDA clause absent. Log retrieval failure. NDA determination is insufficient for COMPLETE — emit ESCALATED.

---


### STEP-03 Output Contract

| Field | Values |
|-------|--------|
| `dpa_required` | boolean |
| `dpa_blocker` | boolean — true if `dpa_required` and no executed DPA on record |
| `nda_status` | `EXECUTED \| PENDING \| NOT_STARTED \| UNKNOWN` |
| `nda_blocker` | boolean — true if `nda_status != EXECUTED` |
| `trigger_rule_cited` | array of `{source_id, version, row_id, trigger_condition}` |
| `policy_citations` | array of `{source_id, version, chunk_id, section_id, citation_class}` |
| `status` | `complete \| escalated \| blocked` |

---

## STEP-04 — R-04: Approval Path Routing

**Assigned Agent:** Procurement Agent  
**Gates Downstream:** STEP-05  
**Parallel With:** —  
**Gate Condition:** STEP-03 must be in a terminal state and Legal output (STEP-03) must be present as a schema-valid upstream input.

> **Sequential execution note:** STEP-04 begins only after STEP-03 reaches a terminal state. Procurement routes the vendor through the correct approval path using authoritative STEP-02 security output, authoritative STEP-03 legal output, and questionnaire deal data. Procurement does not own security classification and does not determine fast-track eligibility.

**If BLOCKED:** emit `BLOCKED`, notify Procurement, halt STEP-05 and STEP-06.

**Bundle Assembly Priority:**
1. IT Security Agent full output
2. Legal Agent full output
3. Questionnaire vendor relationship fields
4. Procurement approval matrix — matching rows
5. Slack / meeting notes — procurement-scoped threads only, if non-conflicting and non-redundant
7. Supplemental context — excluded when budget is constrained

**Resolution Condition:** `it_security_output` is present AND `legal_output` is present AND `approval_path_matrix_rows` is non-empty AND `vendor_relationship_raw` fields are present


**Audit Triggers:** `RETRIEVAL`, `DETERMINATION`, `STATUS_CHANGE`

### STEP-04 ownership rule

STEP-04 owns only:
- approval path selection
- required approvals list
- estimated timeline
- procurement-specific routing notes

STEP-04 must treat the following STEP-02 fields as read-only authoritative inputs:
- `integration_tier`
- `data_classification`
- `fast_track_eligible`
- `security_followup_required`

### Subqueries

#### R04-SQ-01 — Read IT Security Agent Full Output from Pipeline State

> What did the IT Security Agent determine — data classification, fast-track eligibility, integration tier, and policy citations?

| Field | Value |
|-------|-------|
| Retrieval Lane | `non_retrieval` |
| Source | STEP-02 output |
| Method | `pipeline_state_read` |
| Condition | Always runs |
| Output Field | `it_security_output` |

**Fields Required:** `data_classification`, `fast_track_eligible`, `integration_tier`, `security_followup_required`, `policy_citations`, `status`

**If fails:** Bundle is inadmissible. Emit BLOCKED.

---
#### R04-SQ-02 — Read Legal Agent Full Output from Pipeline State

> What did the Legal Agent determine regarding DPA and NDA status for this vendor?

| Field | Value |
|-------|-------|
| Retrieval Lane | `non_retrieval` |
| Source | STEP-03 output |
| Method | `pipeline_state_read` |
| Condition | Always runs |
| Output Field | `legal_output` |

**Fields Required:** `dpa_required`, `dpa_blocker`, `nda_status`, `nda_blocker`, `trigger_rule_cited`, `policy_citations`, `status`

**If fails:** Bundle is inadmissible. Emit BLOCKED.

---


#### R04-SQ-03 — Read Vendor Relationship and Deal Fields from Questionnaire

> What is OptiChain's vendor class, deal size, existing NDA status, and existing MSA status?

| Field | Value |
|-------|-------|
| Retrieval Lane | `direct_structured` |
| Source | VQ-OC-001 |
| Endpoint | `vq_direct_access` |
| Method | `direct_field_lookup` |
| Condition | Always runs |
| Output Field | `vendor_relationship_raw` |

**Fields Required:** `vendor_class`, `contract_value_annual`, `existing_nda_status`, `existing_msa`

**If fails:** If `vendor_class` or `contract_value_annual` is absent — approval path matching is insufficient. Emit BLOCKED. Log missing fields.

---

#### R04-SQ-04 — Retrieve Approval Path Matrix Rows

> Which procurement approval path applies to OptiChain's vendor class, contract value, and security classification profile?

| Field | Value |
|-------|-------|
| Retrieval Lane | `indexed_hybrid` |
| Source | PAM-001 |
| Endpoint | `idx_procurement_matrix` |
| Method | `hybrid_dense_bm25_row_targeted` |
| Rerank | Yes |
| Authority Weight | Tier 1 |
| Citation Class | PRIMARY |
| Condition | Always runs |
| Output Field | `approval_path_matrix_rows` |

**Search Terms:** `vendor class`, `deal size`, `approval path`, `standard`, `fast track`, `executive approval`, `contract value`, `regulated`, `security review`

**If fails:** Evidence insufficient for RESOLVED approval path. Emit `ESCALATED_TO_PROCUREMENT_DIRECTOR`. Log as no-matrix-match.

---

#### R04-SQ-05 — Retrieve Fast-Track Routing Conditions from Procurement Matrix

> If STEP-02 has already marked the vendor fast-track eligible, what procurement routing path applies?

| Field | Value |
|-------|-------|
| Retrieval Lane | `indexed_hybrid` |
| Source | PAM-001 |
| Endpoint | `idx_procurement_matrix` |
| Method | `hybrid_dense_bm25_row_targeted` |
| Rerank | Yes |
| Authority Weight | Tier 1 |
| Citation Class | PRIMARY |
| Condition | `it_security_output.fast_track_eligible == true` |
| Output Field | `fast_track_routing_rows` |

**Search Terms:** `fast track`, `expedited`, `routing`, `eligible`, `low risk`

**If skipped:** Log skip reason: `upstream fast_track_eligible = false`.

**Important:** This subquery routes already-eligible vendors; it does not determine eligibility.

---


#### R04-SQ-07 — Retrieve Slack / Meeting Notes for Procurement Context

> Are there Procurement-scoped discussion threads containing relevant context not captured in formal sources?

| Field | Value |
|-------|-------|
| Retrieval Lane | `indexed_hybrid` |
| Source | SLK-001 |
| Endpoint | `idx_slack_notes` |
| Method | `hybrid_dense_bm25` |
| Metadata Filter | `scope: procurement` |
| Rerank | Yes |
| Authority Weight | Tier 4 (capped) |
| Citation Class | SUPPLEMENTARY |
| Condition | `approval_path_matrix_rows` is non-empty |
| Inclusion Gate | Include only if non-conflicting with Tier 1–3 evidence and adds non-redundant context |
| Output Field | `slack_procurement_chunks` |

**Search Terms:** `OptiChain`, `vendor approval`, `procurement`, `onboarding`

**If conflicts with Tier 1–3:** Suppress and log `AUTHORITY_SUPPRESSED`. Never primary citation.

---

### STEP-04 Output Contract

| Field                         | Values                                                                                                            |
| ----------------------------- | ----------------------------------------------------------------------------------------------------------------- |
| `approval_path`               | `STANDARD \| FAST_TRACK \| EXECUTIVE_APPROVAL`                                                                     |
| `fast_track_eligible`         | boolean — passthrough only; copied through from authoritative STEP-02 output and not re-determined by Procurement |
| `required_approvals`          | array of `{approver, domain, status, blocker, estimated_completion}`                                              |
| `estimated_timeline`          | string                                                                                                            |
| `status`                      | `complete \| escalated \| blocked`                                                                                |

---

## STEP-05 — R-05: Approval Checklist Generation

**Assigned Agent:** Checklist Assembler  
**Gates Downstream:** STEP-06  
**Parallel With:** —  
**Gate Condition:** STEP-01 through STEP-04 must all be in terminal states, and all required domain agent outputs must be present and schema-valid. No domain agent output may be absent or schema-invalid.

**If BLOCKED:** emit `BLOCKED`, notify Procurement, halt STEP-06.

**Bundle Assembly Priority:**
1. All domain agent structured outputs — IT Security, Legal, Procurement (schema-valid JSON only)
2. Audit log entries for this pipeline run
3. Raw source documents — **excluded entirely**

**Resolution Condition:** `all_agent_outputs` are schema-valid AND `audit_log_entries` is non-empty

**Audit Triggers:** `DETERMINATION`, `STATUS_CHANGE`

---

### Subqueries

#### R05-SQ-00 — Read All Domain Agent Outputs from Pipeline State

> Are all three domain agent outputs present and schema-valid?

| Field | Value |
|-------|-------|
| Retrieval Lane | `non_retrieval` |
| Sources | STEP-02 output, STEP-03 output, STEP-04 output |
| Method | `pipeline_state_read` |
| Condition | Always runs |
| Output Field | `all_agent_outputs` |

**Fields Required:**
- `it_security_agent.data_classification`
- `it_security_agent.fast_track_eligible`
- `it_security_agent.required_security_actions`
- `it_security_agent.policy_citations`
- `it_security_agent.status`
- `legal_agent.dpa_required`
- `legal_agent.dpa_blocker`
- `legal_agent.nda_status`
- `legal_agent.nda_blocker`
- `legal_agent.trigger_rule_cited`
- `legal_agent.policy_citations`
- `legal_agent.status`
- `procurement_agent.approval_path`
- `procurement_agent.required_approvals`
- `procurement_agent.status`

**If fails:** Emit BLOCKED. Identify which agent output is missing. Halt STEP-06.

---

#### R05-SQ-01 — Read Audit Log Entries for This Run

> What retrieval operations, determinations, status changes, and escalations have been logged for this pipeline run?

| Field | Value |
|-------|-------|
| Retrieval Lane | `non_retrieval` |
| Source | `audit_log` |
| Method | `pipeline_state_read` |
| Condition | Always runs |
| Output Field | `audit_log_entries` |

**Fields Required:** `entry_id`, `event_type`, `agent_id`, `source_queried`, `chunks_retrieved`, `timestamp`

**If fails:** Emit audit log gap warning. Checklist is still generated but flagged as incomplete for audit purposes.

---

### STEP-05 Output Contract

| Field | Values |
|-------|--------|
| `pipeline_run_id` | string |
| `vendor_name` | string |
| `overall_status` | `COMPLETE \| ESCALATED \| BLOCKED` |
| `data_classification` | `REGULATED \| UNREGULATED \| AMBIGUOUS` |
| `dpa_required` | boolean |
| `fast_track_eligible` | boolean |
| `required_security_actions` | array of `{action_type, reason, owner}` |
| `approval_path` | `STANDARD \| FAST_TRACK \| EXECUTIVE_APPROVAL` |
| `required_approvals` | array of `{approver, domain, status, blocker, estimated_completion}` |
| `blockers` | array of `{blocker_type, description, resolution_owner, citation}` |
| `citations` | array of `{source_name, version, section, retrieval_timestamp, agent_id}` |

---

## STEP-06 — R-06: Stakeholder Guidance and Checkoff Support

**Assigned Agent:** Checkoff Agent  
**Gates Downstream:** —  
**Parallel With:** —  
**Gate Condition:** STEP-05 must be COMPLETE. STEP-06 does not run from an ESCALATED or BLOCKED STEP-05 result.

> **Index Access Rule: PROHIBITED.** The Checkoff Agent may not query any index endpoint. It is downstream-only. Any attempt to issue an index query must fail closed and be logged.

**If BLOCKED:** emit `BLOCKED`, notify Procurement.

**Bundle Assembly Priority:**
1. Finalized checklist output from STEP-05
2. Stakeholder role-to-guidance map
3. Required approver list
4. Required security actions from STEP-02
5. Escalation reasons and resolution owners
6. Domain agent determination summaries — structured outputs only

**Resolution Condition:** `finalized_checklist` is present AND `stakeholder_map` is present

**Audit Triggers:** `DETERMINATION`, `STATUS_CHANGE`

---

### Subqueries

#### R06-SQ-01 — Read Finalized Checklist from Pipeline State

> What is the finalized approval checklist produced by the Checklist Assembler?

| Field | Value |
|-------|-------|
| Retrieval Lane | `non_retrieval` |
| Source | STEP-05 output |
| Method | `pipeline_state_read` |
| Condition | Always runs |
| Output Field | `finalized_checklist` |

**Fields Required:** `overall_status`, `blockers`, `required_approvals`, `required_security_actions`, `citations`, `data_classification`, `approval_path`

**If fails:** Emit BLOCKED. Checkoff Agent cannot operate without the finalized checklist.

---

#### R06-SQ-02 — Read Stakeholder Role Map from Pipeline Config

> Who are the responsible stakeholders for each domain, and what is their role in resolving blockers or approving next steps?

| Field | Value |
|-------|-------|
| Retrieval Lane | `non_retrieval` |
| Source | `pipeline_config` |
| Method | `pipeline_state_read` |
| Condition | Always runs |
| Output Field | `stakeholder_map` |

**Fields Required:** `stakeholder_map`, `approver_contacts`, `escalation_owners`

**If fails:** Generate guidance documents with role labels only (no named contacts). Log as missing.

---

### STEP-06 Output Contract

| Field | Values |
|-------|--------|
| `guidance_documents` | array of `{stakeholder_role, domain, instructions, blockers_owned, required_security_actions, next_steps, citations}` |
| `status` | `complete \| blocked` |

---


## Implementation Note — Condition Evaluation

`subquery_condition` and related gate expressions in this document are intentionally written as human-readable expressions for specification clarity. In implementation, `supervisor.py` should include a small deterministic condition evaluator that parses and evaluates these expressions against `PipelineState` and prior step outputs. This document defines the logic to be evaluated; it does not prescribe the parser implementation.

## Global Audit Rules

These rules apply across all steps regardless of which agent is running. The audit log is **append-only** — no entry may be modified or deleted once written.

| Event | Audit Log Entry Required |
|-------|--------------------------|
| Every retrieval query attempt against any index endpoint | `RETRIEVAL` entry |
| Every chunk admitted to a final context bundle | Log `chunk_id`, `retrieval_score`, `rerank_score`, `citation_class` |
| Every chunk excluded from a context bundle | Log `chunk_id` and reason: `INCOMPLETE_PROVENANCE \| AUTHORITY_SUPPRESSED \| BUDGET_CONSTRAINED \| ACCESS_DENIED` |
| Every determination emitted by a domain agent | `DETERMINATION` entry |
| Every pipeline status change | `STATUS_CHANGE` entry |
| Every escalation | `ESCALATION` entry with full payload per CC-001 §13.1 |

---

## Version Log

| Version | Date | Author | Change |
|---------|------|--------|--------|
| 0.1 | 2026-04-10 | Engineering / IT Architecture | Initial draft. Six steps derived from Design Doc execution graph. Subqueries, retrieval routing, gate conditions, and output contracts defined per CC-001 v1.1 and chunking/retrieval strategy. |
| 0.4 | 2026-04-10 | Engineering / IT Architecture | Aligned document versioning with title metadata. Added canonical `supervisor_reconciliation` state to `PipelineState` and tied STEP-05 gating to that object. Clarified document-boundary authority, Supervisor retrieval permissions, STEP-04 ownership limits, and combined BLOCKED/ESCALATED handling. Removed undefined citation-passthrough reuse behavior from Legal retrieval. |
| 0.6 | 2026-04-12 | Engineering / IT Architecture | Aligned orchestration plan with sequential STEP-03 → STEP-04 execution and current Legal/Design Doc contracts. Changes: (1) removed STEP-03/STEP-04 parallel markers, reconciliation logic, and related `PipelineState` reconciliation state; (2) updated control-flow and mutation rules to a fully sequential execution model; (3) changed STEP-03 to gate STEP-04 and STEP-04 to require schema-valid STEP-03 output; (4) removed forbidden STEP-02 EU-personal-data read from Legal subqueries and replaced it with questionnaire-field read; (5) removed unsupported system-access / hosted-processing DPA trigger retrieval path; (6) expanded STEP-03 bundle and output to include NDA inputs and `policy_citations`; (7) updated STEP-04 bundle to include full Legal output; (8) removed STEP-05 reconciliation dependency and simplified checklist gating to terminal upstream outputs plus schema-valid agent outputs. |
| 0.7 | 2026-04-12 | Engineering / IT Architecture | Logged version capture. State of document after v0.6 sequential changes were applied; no additional content changes beyond what is described in the v0.6 entry. |
| 0.8 | 2026-04-12 | Engineering / IT Architecture | Four integrity fixes. (1) STEP-06 gate condition corrected. (2) STEP-02 "Gates Downstream" corrected to STEP-03 only. (3) STEP-04 output contract expanded. (4) Subquery renumbering to match execution order. |
| 0.9 | 2026-04-12 | Engineering / IT Architecture | Demo simplification revision. (1) Status model reduced to three signals: COMPLETE, BLOCKED, ESCALATED — PROVISIONAL removed throughout. (2) RESOLVED renamed to COMPLETE in all step statuses, output contracts, gate states, and status derivation logic. (3) PVD-001 (Prior Vendor Decisions) removed — R02-SQ-08, R03-SQ-07, and R04-SQ-06 precedent subqueries deleted; Precedents lane removed from routing rules; precedent bundle entries removed from STEP-02, STEP-03, STEP-04. (4) EXECUTIVE_APPROVAL removed from approval_path enum; executive_approval_required field removed from STEP-04 output contract. (5) PROVISIONAL Conditions removed from STEP-02, STEP-03, STEP-04. (6) provisional_flags removed from PipelineState. (7) All "if fails → emit PROVISIONAL" language replaced with ESCALATED or BLOCKED as appropriate. (8) STEP-06 gate updated to COMPLETE or ESCALATED only. Aligned with Design Doc v4.0 and CC-001 v2.0. |
| 0.10 | 2026-04-13 | Engineering / IT Architecture | Integrity alignment revision. (1) Removed `onboarding_path_classification` from STEP-02, STEP-04, and STEP-05 contracts and requirements. (2) Corrected STEP-06 gate so it runs only when STEP-05 is COMPLETE. (3) Re-aligned `approval_path` enum with the Design Doc by restoring `EXECUTIVE_APPROVAL` in orchestration output contracts. |
