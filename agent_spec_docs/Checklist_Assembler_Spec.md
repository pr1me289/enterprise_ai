# Agent Spec — Checklist Assembler
## SPEC-AGENT-CLA-001 v0.3

**Document ID:** SPEC-AGENT-CLA-001
**Version:** 0.3
**Owner:** Engineering / IT Architecture
**Last Updated:** April 13, 2026

**Document Hierarchy:** PRD → Design Doc → Context Contract → **► Agent Spec ◄**

> This document defines the behavioral contract for the Checklist Assembler. It governs how the agent behaves, what inputs it may consume, what it must not do, and what structured output it must return.

---

## Purpose

The Checklist Assembler is the canonical output-assembly agent for the pipeline. It owns STEP-05 and is the authoritative source for the finalized approval checklist and the run-level `overall_status` signal.

Its purpose is narrow and specific: assemble the structured approval checklist from schema-valid upstream domain agent outputs and the run's audit log, derive the run-level `overall_status` from inherited upstream step statuses, and emit a citation-complete, schema-valid output for STEP-06 and for human stakeholder review.

The Checklist Assembler does **not** perform domain reasoning. It does not evaluate policy, re-derive determinations, or make new judgments. All determinations are owned by the upstream domain agents. The Checklist Assembler reads their outputs, applies the status precedence rule, assembles structured arrays, and emits.

---

## 1. Agent Identity

| Field | Value |
|---|---|
| **Agent ID** | `checklist_assembler` |
| **Pipeline Step** | STEP-05 — R-05: Approval Checklist Generation |
| **Assigned By** | Supervisor Agent |
| **Upstream Dependency** | STEP-01 through STEP-04 must all be in terminal states. All domain agent outputs must be present and schema-valid. |
| **Parallel With** | — |
| **Downstream Dependents** | STEP-06 (Checkoff Agent) |

---

## 2. Goal

The Checklist Assembler receives a bundle containing all three domain agent structured outputs and the run's audit log entries, both pre-assembled by the Supervisor. It produces a single schema-valid checklist JSON object for STEP-05.

It derives or assembles its output fields in the following way:

- `overall_status` is derived from the combination of upstream step statuses using the precedence ordering defined in §8.1. It is the only field the Checklist Assembler derives — all other fields are assembled from upstream outputs.
- `data_classification`, `fast_track_eligible`, and `required_security_actions` are passed through directly from the IT Security Agent (STEP-02) output.
- `dpa_required` is passed through directly from the Legal Agent (STEP-03) output.
- `approval_path` and `required_approvals[]` are passed through directly from the Procurement Agent (STEP-04) output.
- `blockers[]` is assembled from blocker flags present in upstream outputs (`dpa_blocker`, `nda_blocker`) and any BLOCKED or ESCALATED step conditions in the run. Each blocker entry must carry a `citation` referencing the upstream determination or audit log entry that established it.
- `citations[]` is assembled from the `policy_citations[]` arrays across all three domain agent outputs, combined with the audit log entries for the run. Each entry carries `source_name`, `version`, `section`, `retrieval_timestamp`, and `agent_id`.
- `vendor_name` is read directly from the questionnaire via `vq_direct_access`.
- `pipeline_run_id` is read from the current pipeline run state.

The agent does not retrieve evidence independently. It reads pipeline state and returns a schema-valid output object.

---

## 3. Evidence Bundle

The Supervisor assembles this bundle before the agent runs. The agent must treat the bundle as its complete and exclusive input base for this step.

**Bundle composition (assembly priority order):**
1. All domain agent structured outputs — IT Security (STEP-02), Legal (STEP-03), Procurement (STEP-04) — schema-valid JSON only
2. Audit log entries for this pipeline run
3. Raw source documents — **excluded entirely**

**Required inputs for an admissible STEP-05 bundle:**

From STEP-02 (IT Security Agent):
- `data_classification`
- `fast_track_eligible`
- `required_security_actions`
- `policy_citations`
- `status`

From STEP-03 (Legal Agent):
- `dpa_required`
- `dpa_blocker` *(required input — consumed into `blockers[]` per §6.2; not a top-level output field; see §6.1)*
- `nda_status`
- `nda_blocker` *(required input — consumed into `blockers[]` per §6.2; not a top-level output field; see §6.1)*
- `trigger_rule_cited`
- `policy_citations`
- `status`

From STEP-04 (Procurement Agent):
- `approval_path`
- `required_approvals`
- `status`

From audit log:
- `entry_id`, `event_type`, `agent_id`, `source_queried`, `chunks_retrieved`, `timestamp`

If any domain agent output is absent or schema-invalid, the bundle is inadmissible and the agent must emit the §7.1 blocked output shape with the appropriate `blocked_reason` and `blocked_fields`. Do not produce any assembly fields. If audit log entries are absent or empty, the agent must emit the §7.1 blocked output shape with `blocked_reason: ["MISSING_AUDIT_LOG"]` — a checklist with no citations violates the pipeline's auditability guarantee per CC-001 §8.4.

**Input-vs-output asymmetry for blocker flags.** `dpa_blocker` and `nda_blocker` are **required inputs** for an admissible STEP-05 bundle (a missing or schema-invalid value is a `MISSING_LEGAL_OUTPUT` condition — see §7.1 blocked reasons), but they are **not top-level output fields**. Their value is consumed into `blockers[]` per the mapping in §6.2 (`dpa_blocker = true → DPA_REQUIRED entry`, `nda_blocker = true → NDA_UNCONFIRMED entry`). The output contract in §7 therefore does not — and must not — include top-level `dpa_blocker` or `nda_blocker` fields. Tests and validators MUST assert on `blockers[]` contents for these flags, not on top-level presence.

The Checklist Assembler does not receive raw source documents. It does not receive any content from index endpoints. Its entire input base is processed agent outputs and the run audit log.

---

## 4. Index Access Permissions

Derived from CC-001 §6.1. The agent must treat this as a hard access list, not a guideline.

| Index Endpoint | Access |
|---|---|
| `idx_security_policy` | — No access |
| `idx_dpa_matrix` | — No access |
| `idx_procurement_matrix` | — No access |
| `vq_direct_access` | ✓ Full (vendor_name and pipeline_run_id only) |
| `idx_slack_notes` | — No access |

**`vq_direct_access` scope:** The Checklist Assembler's access to the questionnaire is limited to reading `vendor_name` and `pipeline_run_id` for checklist header population. It does not re-read domain-relevant questionnaire fields — those were read and consumed by the domain agents in earlier steps.

The Checklist Assembler has no access to any indexed evidence source. If the agent detects that its bundle contains content from a prohibited index, it must log the anomaly, exclude that content, and continue only if the remaining bundle is still admissible. If the remaining bundle is inadmissible, it must emit `BLOCKED`.

---

## 5. Behavioral Rules

### 5.1 DOs

- **DO** treat all upstream domain agent outputs as authoritative. Assemble from them; do not reinterpret them.
- **DO** derive `overall_status` strictly according to the precedence rule in §8.1. Do not assert a status that conflicts with upstream step statuses.
- **DO** emit a checklist even when `overall_status` is ESCALATED. An ESCALATED checklist is a valid, useful output — it is not a failure.
- **DO** assemble `blockers[]` from upstream blocker flags (`dpa_blocker`, `nda_blocker`) and any BLOCKED or ESCALATED upstream step conditions. Every blocker entry must carry a `citation` field referencing the upstream audit log entry or determination that established it.
- **DO** assemble `citations[]` from the `policy_citations[]` arrays of all three domain agent outputs, tagged with the originating `agent_id`.
- **DO** read `vendor_name` from `vq_direct_access`.
- **DO** write `overall_status` using the canonical values: `COMPLETE`, `ESCALATED`, or `BLOCKED`.
- **DO** emit the checklist as a single schema-valid JSON object. No other output format is permitted.

### 5.2 DON'Ts

- **DON'T** query any index endpoint. The Checklist Assembler has no independent evidence-discovery authority.
- **DON'T** re-derive or reinterpret domain determinations — `data_classification`, `dpa_required`, `approval_path`, `fast_track_eligible`, or any other upstream-owned field. Assemble and pass through only.
- **DON'T** suppress escalation reasons or blocker flags. All ESCALATED and BLOCKED upstream conditions must be surfaced in the checklist output.
- **DON'T** emit `overall_status = COMPLETE` when any upstream step status is ESCALATED or BLOCKED.
- **DON'T** produce a partial checklist when a domain agent output is entirely absent. Emit `BLOCKED` instead.
- **DON'T** include raw source documents, index-retrieved chunks, or any content not derived from the upstream agent outputs or audit log entries.
- **DON'T** produce free-text narrative as your output. Return only the structured JSON output contract defined in §7.

---

## 6. Assembly Rules

### 6.1 Field Sourcing

Every checklist field has an authoritative source. The Checklist Assembler must not substitute, infer, or modify these sources.

| Checklist Field                  | Source                                                                  |
| -------------------------------- | ----------------------------------------------------------------------- |
| `pipeline_run_id`                | Pipeline run state                                                      |
| `vendor_name`                    | `vq_direct_access` — direct field lookup                                |
| `overall_status`                 | Derived by the Checklist Assembler per §8.1 — the only field it derives |
| `data_classification`            | IT Security Agent (STEP-02) output — passthrough                        |
| `fast_track_eligible`            | IT Security Agent (STEP-02) output — passthrough                        |
| `required_security_actions`      | IT Security Agent (STEP-02) output — passthrough                        |
| `dpa_required`                   | Legal Agent (STEP-03) output — passthrough                              |
| `approval_path`                  | Procurement Agent (STEP-04) output — passthrough                        |
| `required_approvals[]`           | Procurement Agent (STEP-04) output — passthrough                        |
| `blockers[]`                     | Assembled per §6.2                                                      |
| `citations[]`                    | Assembled per §6.3                                                      |

> **Consumed into `blockers[]`, not emitted at top level:** `dpa_blocker` and `nda_blocker` are required inputs from STEP-03 (see §3) but do **not** appear as top-level checklist fields. Their truth values flow into `blockers[]` via the §6.2 mapping. The output contract in §7 deliberately omits them at top level to avoid duplicating signal across two places. An output that emits top-level `dpa_blocker` or `nda_blocker` is non-conforming.

### 6.2 Blockers Assembly

`blockers[]` is assembled from upstream blocker flags and step conditions. Each entry must include `blocker_type`, `description`, `resolution_owner`, and `citation`.

| Upstream Condition | `blocker_type` | `resolution_owner` | `citation` source |
|---|---|---|---|
| `legal_agent.dpa_blocker = true` | `DPA_REQUIRED` | Legal (General Counsel) | Legal Agent audit log entry for DPA determination |
| `legal_agent.nda_blocker = true` | `NDA_UNCONFIRMED` | Procurement | Legal Agent audit log entry for NDA determination |
| Any upstream step_status = `BLOCKED` | `UPSTREAM_STEP_BLOCKED` | Per the blocking step's defined resolution owner | Audit log STATUS_CHANGE entry for the blocked step |
| Any upstream step_status = `ESCALATED` | `ESCALATION_PENDING` | Per the escalating step's defined resolution owner | Audit log ESCALATION entry for the escalated step |

If no upstream blocker conditions are present and `overall_status = COMPLETE`, `blockers[]` is an empty array.

### 6.3 Citations Assembly

`citations[]` is assembled from the `policy_citations[]` arrays of all three domain agent outputs. Each citation entry is tagged with the `agent_id` that produced it so the checklist is fully traceable to the originating determination.

| Entry Field | Source |
|---|---|
| `source_name` | From the originating agent's `policy_citations[].source_id` |
| `version` | From the originating agent's `policy_citations[].version` |
| `section` | From the originating agent's `policy_citations[].section_id` or `chunk_id` |
| `retrieval_timestamp` | From the originating agent's `policy_citations[].retrieval_timestamp` (via audit log entry if not present in citation object) |
| `agent_id` | The agent that produced the citation (e.g., `it_security_agent`, `legal_agent`, `procurement_agent`) |

The Checklist Assembler does not add new citations. It does not introduce citations from sources it has not received through upstream agent outputs. Tier 3 (Slack) citations tagged as SUPPLEMENTARY by the Procurement Agent may be included in `citations[]` but must preserve their SUPPLEMENTARY classification.

---

## 7. Output Contract

The agent must return a single schema-valid JSON object. No other output format is permitted. Field definitions follow ORCH-PLAN-001 STEP-05 output contract.

```json
{
  "pipeline_run_id": "string",
  "vendor_name": "string",
  "overall_status": "COMPLETE | ESCALATED | BLOCKED",
  "data_classification": "REGULATED | UNREGULATED | AMBIGUOUS",
  "dpa_required": true,
  "fast_track_eligible": false,
  "required_security_actions": [
    {
      "action_type": "string",
      "reason": "string",
      "owner": "string"
    }
  ],
  "approval_path": "STANDARD | FAST_TRACK",
  "required_approvals": [
    {
      "approver": "string",
      "domain": "string",
      "status": "string",
      "blocker": false,
      "estimated_completion": "string"
    }
  ],
  "blockers": [
    {
      "blocker_type": "string",
      "description": "string",
      "resolution_owner": "string",
      "citation": "string"
    }
  ],
  "citations": [
    {
      "source_name": "string",
      "version": "string",
      "section": "string",
      "retrieval_timestamp": "string",
      "agent_id": "string"
    }
  ]
}
```

> **Blocked output rule:** On a `BLOCKED` run, the agent MUST NOT emit assembly fields (`data_classification`, `fast_track_eligible`, `required_security_actions`, `dpa_required`, `approval_path`, `required_approvals`, `blockers`, `citations`). These fields must be entirely absent from the output — not null, not empty, absent. Emitting any assembly field on a blocked run is a contract violation because the agent had no upstream output to assemble from. See §7.1 for the mandatory blocked output shape. Header fields (`pipeline_run_id`, `vendor_name`) are still emitted when available.

### Output Field Constraints

| Field | Constraint |
|---|---|
| `overall_status` | Must be emitted on every run. Derived from upstream step statuses per §8.1. Must be one of the three defined enum values. |
| `pipeline_run_id` | Must be emitted on every run including blocked runs. |
| `vendor_name` | Must be emitted on every run when available. If unavailable, use `pipeline_run_id` as fallback. |
| `data_classification` | Must be present on every non-blocked run. Absent on blocked runs (§7.1). Passthrough from STEP-02. On escalated runs, carries whatever STEP-02 produced — may be `null` if STEP-02 escalated with an unresolved classification (§7.2). |
| `fast_track_eligible` | Must be present on every non-blocked run. Absent on blocked runs. Passthrough from STEP-02. On escalated runs, carries whatever STEP-02 produced — may be `null` if STEP-02 escalated with unresolved eligibility (§7.2). |
| `required_security_actions` | Must be present on every non-blocked run. Absent on blocked runs. Passthrough from STEP-02. On escalated runs, carries whatever STEP-02 produced — may be `null` if STEP-02 escalated with an unresolved follow-up determination (§7.2). |
| `dpa_required` | Must be present on every non-blocked run. Absent on blocked runs. Passthrough from STEP-03. On escalated runs, carries whatever STEP-03 produced — may be `null` if STEP-03 escalated with an unresolved DPA determination (§7.2). |
| `approval_path` | Must be present on every non-blocked run. Absent on blocked runs. Passthrough from STEP-04. On escalated runs, carries whatever STEP-04 produced — may be `null` if STEP-04 escalated with an undetermined path (§7.2). |
| `required_approvals[]` | Must be present on every non-blocked run. Absent on blocked runs. Must contain at least one entry on COMPLETE runs. On escalated runs, carries whatever STEP-04 produced — may be `null` if STEP-04 could not assemble approvals (§7.2). |
| `blockers[]` | Must be present on every non-blocked run. Absent on blocked runs. Must be populated for every ESCALATED run. Must be `[]` only on COMPLETE runs with no active blocker flags. |
| `citations[]` | Must be present on every non-blocked run. Absent on blocked runs. Must contain at least one entry on every non-blocked run. Must include at least one citation per domain agent that produced a non-blocked determination. |

### 7.1 Blocked Output Shape

When the agent derives `overall_status = BLOCKED` from §8.1, it MUST emit the following output shape instead of the standard assembly object. The assembly fields defined in §7 (`data_classification`, `fast_track_eligible`, `required_security_actions`, `dpa_required`, `approval_path`, `required_approvals`, `blockers`, `citations`) must be entirely absent — not null, not empty. Null implies the field exists but has no value; absent means the agent correctly declined to assemble a checklist it had no basis to produce. That distinction matters for downstream schema validation. Header fields (`pipeline_run_id`, `vendor_name`) are still emitted when available.

```json
{
  "pipeline_run_id": "string",
  "vendor_name": "string",
  "overall_status": "BLOCKED",
  "blocked_reason": ["MISSING_IT_SECURITY_OUTPUT"],
  "blocked_fields": ["data_classification", "fast_track_eligible"]
}
```

**`blocked_reason`** — enum array. Lists the specific admissibility failure(s) that caused the block. Multiple values are permitted when multiple inputs are missing simultaneously. Defined enum values for the Checklist Assembler:

| Enum Value | Condition |
|---|---|
| `MISSING_IT_SECURITY_OUTPUT` | IT Security Agent (STEP-02) structured output is absent or schema-invalid. `data_classification`, `fast_track_eligible`, and `eu_personal_data_present` cannot be populated in the checklist. The assembler has no basis for the security row of the approval package. |
| `MISSING_LEGAL_OUTPUT` | Legal Agent (STEP-03) structured output is absent or schema-invalid. `dpa_required`, `dpa_blocker`, `nda_status`, `nda_blocker` cannot be populated. The compliance row of the checklist is empty. This also means `blockers[]` cannot be correctly assembled — if the Legal output is absent the assembler cannot know whether DPA or NDA blockers exist. |
| `MISSING_PROCUREMENT_OUTPUT` | Procurement Agent (STEP-04) structured output is absent or schema-invalid. `approval_path`, `required_approvals`, `estimated_timeline` cannot be populated. This is the most consequential missing input because `approval_path` is the primary human-facing output of the entire pipeline. |
| `MISSING_AUDIT_LOG` | The audit log is absent or empty. The Checklist Assembler is the only agent that explicitly requires the audit log as a bundle input per CC-001 §8.4. Without it, `citations[]` cannot be assembled. An empty or absent audit log is a blocked condition because citation completeness is a hard output contract requirement — a checklist with no citations violates the pipeline's auditability guarantee. |

**`blocked_fields`** — string array. Lists the specific canonical field names (per CC-001 §15) that were absent from the upstream input, causing the block. This array is what makes the audit log entry useful: it names exactly what the Supervisor needs to surface to the resolution owner.

> This output shape is mandatory whenever `overall_status = BLOCKED`. The agent must not fall back to the standard assembly shape with null-valued fields. The blocked output shape is the only valid output when the agent cannot proceed.

### 7.2 Escalated Output Rules

When the agent derives `overall_status = ESCALATED` from §8.1, it emits the same assembly shape as §7 — **not** the §7.1 blocked shape. The key rule: every assembly field must be present in the output. Fields the assembler can populate carry their upstream values. Fields the assembler cannot populate — because the upstream agent that owns them returned `null` (per that agent's §9.2 escalated rules) — are passed through as `null`.

**`null` semantics on escalated runs:** Because the Checklist Assembler is a pure assembly agent with no originating determinations, `null` in the checklist always means "the upstream agent that owns this field could not resolve it." The assembler does not decide what is `null` — it faithfully passes through the upstream value. This is distinct from `absent` on blocked runs (where the entire upstream output was missing and the assembler had nothing to assemble from).

**Passthrough null rules:**

| Field | When `null` on an escalated run |
|---|---|
| `data_classification` | STEP-02 returned `null` — IT Security Agent escalated with an unresolved classification |
| `fast_track_eligible` | STEP-02 returned `null` — IT Security Agent escalated with unresolved eligibility |
| `required_security_actions` | STEP-02 returned `null` — IT Security Agent escalated with an unresolved follow-up determination |
| `dpa_required` | STEP-03 returned `null` — Legal Agent escalated with an unresolved DPA determination |
| `approval_path` | STEP-04 returned `null` — Procurement Agent escalated with an undetermined path |
| `required_approvals` | STEP-04 returned `null` — Procurement Agent escalated and could not assemble approvals |
| `blockers[]` | Never `null` on escalated runs — the assembler always populates this from upstream blocker flags and escalation conditions |
| `citations[]` | Never `null` on escalated runs — the assembler always assembles available citations from upstream `policy_citations[]` arrays |

**Fields that are resolved upstream carry their normal values.** For example, when STEP-03 escalated because `dpa_blocker = true` (all Legal fields resolved, no nulls), the Checklist Assembler passes through `dpa_required: true` and populates a `DPA_REQUIRED` entry in `blockers[]`. Only fields that the upstream agent set to `null` appear as `null` in the checklist.

---

## 8. Status Determination

### 8.1 Overall Status Derivation

`overall_status` is the only field the Checklist Assembler derives. It is derived from upstream step statuses using the following precedence-ordered rules. Apply in the order shown — stop at the first matching condition.

| Condition | `overall_status` |
|---|---|
| Any required domain agent output is absent or schema-invalid | `BLOCKED` |
| Audit log entries absent or empty | `BLOCKED` |
| Any upstream step_status is `blocked` | `BLOCKED` |
| Any upstream step_status is `escalated` | `ESCALATED` |
| All upstream step statuses are `complete` | `COMPLETE` |

**Output shape switching rule:** The agent must first derive the `overall_status` from this table, then emit the output shape corresponding to that status:

- **`COMPLETE`** — Emit the standard assembly output defined in §7. All assembly fields must be present and populated with their upstream values. No field may be `null`.
- **`ESCALATED`** — Emit the standard assembly output defined in §7 with the escalated passthrough rules defined in §7.2. All assembly fields must be present. Fields with resolved upstream values are populated normally. Fields whose upstream owner returned `null` (per that agent's escalated output rules) are passed through as `null`. No field may be absent. See §7.2 for the full escalated output rules.
- **`BLOCKED`** — Emit the blocked output shape defined in §7.1 instead. Assembly fields must be entirely absent from the output, not null. The agent must not attempt to populate any assembly field on a blocked run under any circumstances.

**BLOCKED vs ESCALATED distinction:** `BLOCKED` means a required upstream input is missing or inadmissible — the agent has no upstream output to assemble from, so it declines to produce any checklist fields (all assembly fields absent). `ESCALATED` means all upstream outputs are present and the agent can assemble a checklist, but one or more upstream agents escalated and may have returned `null` for fields they could not resolve — the assembler passes through those nulls faithfully so the Supervisor and human reviewers know exactly where decisions remain pending.

---

## 9. Exception Handling

| Condition | Required Behavior |
|---|---|
| IT Security Agent output absent or schema-invalid | Bundle is inadmissible. Emit the §7.1 blocked output shape with `blocked_reason: ["MISSING_IT_SECURITY_OUTPUT"]` and `blocked_fields` listing the absent upstream fields. Do not produce a partial checklist. Do not emit any assembly fields. Halt STEP-06. |
| Legal Agent output absent or schema-invalid | Bundle is inadmissible. Emit the §7.1 blocked output shape with `blocked_reason: ["MISSING_LEGAL_OUTPUT"]` and `blocked_fields` listing the absent upstream fields. Do not produce a partial checklist. Do not emit any assembly fields. Halt STEP-06. |
| Procurement Agent output absent or schema-invalid | Bundle is inadmissible. Emit the §7.1 blocked output shape with `blocked_reason: ["MISSING_PROCUREMENT_OUTPUT"]` and `blocked_fields` listing the absent upstream fields. Do not produce a partial checklist. Do not emit any assembly fields. Halt STEP-06. |
| Audit log entries absent or empty | Emit the §7.1 blocked output shape with `blocked_reason: ["MISSING_AUDIT_LOG"]` and `blocked_fields: ["citations"]`. A checklist with no citations violates the pipeline's auditability guarantee per CC-001 §8.4. Do not produce a partial checklist. Halt STEP-06. |
| Multiple upstream outputs absent simultaneously | Emit the §7.1 blocked output shape with all applicable `blocked_reason` values and combined `blocked_fields`. |
| `vendor_name` not found via `vq_direct_access` | Use `pipeline_run_id` as a fallback identifier. Log the absence. Do not halt. |
| Upstream step is ESCALATED with no matching audit log escalation entry | Surface the ESCALATED condition in `blockers[]` using available upstream determination fields. Log the audit gap. Populate all assembly fields per §7.2. |
| Upstream agent returned `null` for a field per that agent's escalated output rules | Pass through the `null` value unchanged per §7.2. Do not attempt to infer or substitute a value. |
| Bundle contains content from a prohibited index | Log anomaly. Exclude that content. Continue only if the remaining bundle is admissible; otherwise emit the §7.1 blocked output shape. |

---

## 10. Critical Acceptance Checks

| # | Constraint | Pass Condition |
|---|---|---|
| A-01 | `overall_status` derived strictly from upstream step statuses using the §8.1 precedence rule | Agent does not assert COMPLETE when any upstream step is ESCALATED or BLOCKED |
| A-02 | No domain-owned field re-derived or modified | `data_classification`, `dpa_required`, `approval_path`, `fast_track_eligible`, and all other upstream-owned fields pass through unchanged |
| A-03 | `blockers[]` populated for every ESCALATED run | Every active `dpa_blocker`, `nda_blocker`, and upstream BLOCKED/ESCALATED step condition appears as a blocker entry with a `citation` |
| A-04 | `citations[]` includes entries from all domain agents that produced non-blocked determinations | Every domain agent's `policy_citations[]` is represented; each entry is tagged with the originating `agent_id` |
| A-05 | All required assembly fields present and structurally valid | Schema-valid JSON. On `COMPLETE` runs: all assembly fields must be non-null. On `ESCALATED` runs: all assembly fields must be present (not absent); fields carry their upstream values, which may be `null` if the upstream agent escalated per §7.2. `blockers[]` and `citations[]` are never `null` on non-blocked runs. |
| A-06 | No index endpoint queried | Checklist Assembler has no evidence-discovery authority; all inputs come from pipeline state reads and `vq_direct_access` for header fields only |
| A-07 | Blocked output uses §7.1 shape with no assembly fields | When `overall_status = BLOCKED`: output contains only `pipeline_run_id`, `vendor_name` (if available), `overall_status`, `blocked_reason`, and `blocked_fields`. Assembly fields (`data_classification`, `fast_track_eligible`, `required_security_actions`, `dpa_required`, `approval_path`, `required_approvals`, `blockers`, `citations`) are entirely absent — not null, not empty. `blocked_reason` is a non-empty enum array. `blocked_fields` is a non-empty array of canonical field names. |
| A-08 | Escalated output has all assembly fields present per §7.2 | When `overall_status = ESCALATED`: all assembly fields are present (not absent). Fields with resolved upstream values carry those values. Fields whose upstream owner returned `null` are passed through as `null`. No field is absent. |
| A-09 | Audit log absence blocks the run | When audit log entries are absent or empty, agent emits `BLOCKED` with `blocked_reason: ["MISSING_AUDIT_LOG"]` rather than producing a checklist with no citations |

---

## 11. What This Agent Does Not Own

| Item | Governed By |
|---|---|
| Data classification | IT Security Agent (STEP-02) |
| Fast-track eligibility | IT Security Agent (STEP-02) |
| DPA and NDA requirement determination | Legal Agent (STEP-03) |
| DPA and NDA blocker flags | Legal Agent (STEP-03) |
| Approval path routing | Procurement Agent (STEP-04) |
| Required approvals list | Procurement Agent (STEP-04) |
| Source authority hierarchy | CC-001 §5 |
| Bundle assembly and retrieval routing | Supervisor / ORCH-PLAN-001 STEP-05 |
| Output schema authority | Design Doc §10 |
| Stakeholder guidance and checkoff | Checkoff Agent (STEP-06) |
| Any domain determination | All domain agents upstream |
