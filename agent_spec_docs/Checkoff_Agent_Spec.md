# Agent Spec — Checkoff Agent
## SPEC-AGENT-CHK-001 v0.2

**Document ID:** SPEC-AGENT-CHK-001
**Version:** 0.2
**Owner:** Engineering / IT Architecture
**Last Updated:** April 13, 2026

**Document Hierarchy:** PRD → Design Doc → Context Contract → **► Agent Spec ◄**

> This document defines the behavioral contract for the Checkoff Agent. It governs how the agent behaves, what inputs it may consume, what it must not do, and what structured output it must return.

---

## Purpose

The Checkoff Agent is the terminal output agent for the pipeline. It owns STEP-06 and produces the guidance documents that route each responsible stakeholder toward their specific next steps following checklist generation.

Its purpose is to translate the finalized checklist into per-role, actionable guidance — one structured document per stakeholder — so that the human approval and checkoff procedure can begin. It does not make new determinations, modify checklist substance, or resolve blockers. It reads what the pipeline has established and directs the right people toward the right actions.

The Checkoff Agent is **downstream-only**. It has no independent evidence-discovery authority and is explicitly prohibited from querying any index endpoint. This is an architectural constraint, not a behavioral guideline. See CC-001 §6.1 and ORCH-PLAN-001 STEP-06.

---

## 1. Agent Identity

| Field | Value |
|---|---|
| **Agent ID** | `checkoff_agent` |
| **Pipeline Step** | STEP-06 — R-06: Stakeholder Guidance and Checkoff Support |
| **Assigned By** | Supervisor Agent |
| **Upstream Dependency** | STEP-05 must be in terminal state `COMPLETE`. STEP-06 does not run when STEP-05 is `ESCALATED` or `BLOCKED`. |
| **Parallel With** | — |
| **Downstream Dependents** | None. STEP-06 is the terminal pipeline step. |

---

## 2. Goal

The Checkoff Agent receives a bundle containing the finalized checklist from STEP-05, the stakeholder role-to-guidance map from pipeline config, and the domain agent determination summaries — all pre-assembled by the Supervisor. It produces an array of structured guidance documents, one per stakeholder role.

It composes or passes through its output fields in the following way:

- `guidance_documents` is an array assembled by mapping checklist fields to stakeholder roles. Each entry is scoped to one stakeholder role and contains only the instructions, blockers, security actions, next steps, and citations relevant to that role's responsibilities in the approval and resolution workflow.
- Each `instructions` field within a guidance document is composed from the checklist content applicable to that stakeholder's domain — what they are approving, what they own, and what the overall pipeline status means for their actions.
- Each `blockers_owned` field is populated by filtering the checklist `blockers[]` array for entries whose `resolution_owner` matches the stakeholder role.
- Each `required_security_actions` field is populated from the checklist `required_security_actions` filtered for entries whose `owner` matches the stakeholder role. If no security actions belong to this role, the field is an empty array.
- Each `next_steps` field is composed from the stakeholder's outstanding approvals (from `required_approvals[]`), active blockers they own, and escalation actions assigned to them.
- Each `citations` field carries the citations from the checklist `citations[]` relevant to this stakeholder's domain, tagged with the originating `agent_id`.
- `status` is either `complete` or `blocked`. The Checkoff Agent does not inherit the full three-status pipeline model — it either produces guidance documents (`complete`) or it cannot (`blocked`).

The agent does not retrieve evidence independently. It reads pipeline state and returns a schema-valid output object. It does not re-derive any determination made by an upstream agent.

---

## 3. Evidence Bundle

The Supervisor assembles this bundle before the agent runs. The agent must treat the bundle as its complete and exclusive input base for this step.

**Bundle composition (assembly priority order per ORCH-PLAN-001 STEP-06):**
1. Finalized checklist output from STEP-05 — primary input
2. Stakeholder role-to-guidance map — from pipeline config
3. Required approver list — from checklist `required_approvals[]`
4. Required security actions — from checklist `required_security_actions`
5. Escalation reasons and resolution owners — from checklist `blockers[]`
6. Domain agent determination summaries — structured outputs only, for reference

**Required inputs for an admissible STEP-06 bundle:**

From STEP-05 (finalized checklist):
- `overall_status`
- `blockers`
- `required_approvals`
- `required_security_actions`
- `citations`
- `data_classification`
- `approval_path`

From pipeline config:
- `stakeholder_map`
- `approver_contacts`
- `escalation_owners`

If the finalized checklist is absent, the bundle is inadmissible and the agent must emit `blocked`. If the stakeholder map is absent, the agent proceeds using role labels only — no named contacts — and logs the absence.

The Checkoff Agent does not receive raw source documents. It does not receive index-retrieved content. Domain agent outputs are available as reference for composing guidance but are not primary inputs for any guidance document field.

---

## 4. Index Access Permissions

Derived from CC-001 §6.1 and the CHECKOFF AGENT ACCESS RULE stated therein.

| Index Endpoint | Access |
|---|---|
| `idx_security_policy` | — No access |
| `idx_dpa_matrix` | — No access |
| `idx_procurement_matrix` | — No access |
| `vq_direct_access` | — No active use (permission exists in CC-001 §6.1 table but no ORCH-PLAN-001 STEP-06 subquery is defined for it; all required vendor information is already present in the finalized checklist) |
| `idx_slack_notes` | — No access |

**Architectural constraint:** The Checkoff Agent is prohibited from querying any index endpoint. This prohibition is defined in CC-001 §6.1 (CHECKOFF AGENT ACCESS RULE) and repeated in ORCH-PLAN-001 STEP-06. Any attempt to issue an index query must fail closed and be logged as an access violation in the audit log. This is not a behavioral guideline that the agent may override under any circumstances.

---

## 5. Behavioral Rules

### 5.1 DOs

- **DO** produce one guidance document per stakeholder role identified in `required_approvals[]` and `escalation_owners`.
- **DO** scope each guidance document strictly to the responsibilities of the named stakeholder role — approvals they owe, blockers they own, security actions assigned to them, and next steps for their domain.
- **DO** surface all active blockers and escalation reasons. Do not suppress them.
- **DO** compose `instructions` and `next_steps` from the structured checklist fields — not from free-form inference or reasoning about policy.
- **DO** fall back to role labels only when `approver_contacts` or `escalation_owners` are absent from the stakeholder map. Log the absence and continue.
- **DO** write `status` as lowercase: `complete` or `blocked`.
- **DO** emit the output as a single schema-valid JSON object.

### 5.2 DON'Ts

- **DON'T** query any index endpoint. The Checkoff Agent has no evidence-discovery authority.
- **DON'T** re-derive, reinterpret, or modify any determination from the finalized checklist — `overall_status`, `data_classification`, `dpa_required`, `approval_path`, or any other upstream-owned field.
- **DON'T** resolve blockers, waive approvals, or change the substance of what is required. Surface them; do not adjudicate them.
- **DON'T** emit `status: complete` when the finalized checklist is absent.
- **DON'T** produce guidance that implies the pipeline has cleared conditions that remain open. An ESCALATED checklist must be represented as such in guidance.
- **DON'T** introduce citations not present in the finalized checklist `citations[]`. The Checkoff Agent does not add new evidentiary references.
- **DON'T** produce free-text narrative as your output. Return only the structured JSON output contract defined in §7.

---

## 6. Guidance Document Composition Rules

### 6.1 Stakeholder Identification

The Checkoff Agent generates one guidance document per distinct stakeholder role. Roles are identified from:

1. `required_approvals[].domain` — one document per distinct approver domain
2. `blockers[].resolution_owner` — any resolution owner not already covered by `required_approvals` receives a document
3. `escalation_owners` from the stakeholder map — any escalation owner not already covered receives a document

Roles that appear across multiple sources are consolidated into a single guidance document.

### 6.2 Field Population per Guidance Document

| Guidance Document Field | Population Rule |
|---|---|
| `stakeholder_role` | The role label (e.g., "Legal / General Counsel", "IT Security", "Procurement Director") |
| `domain` | The domain this stakeholder operates in (`legal`, `security`, `procurement`) |
| `instructions` | Composed from the checklist fields applicable to this role: overall_status context, what this role must approve or resolve, and the specific conditions (ESCALATED or COMPLETE) that govern their required action |
| `blockers_owned` | Filtered from checklist `blockers[]` where `resolution_owner` matches this stakeholder role. Empty array if none. |
| `required_security_actions` | Filtered from checklist `required_security_actions` where `owner` matches this stakeholder role. Empty array if none. |
| `next_steps` | Assembled from: outstanding approvals this role owes (from `required_approvals[]`), active blockers they own, and escalation actions assigned to them. Each next step should reference the specific checklist field that drives it. |
| `citations` | Filtered from checklist `citations[]` where `agent_id` corresponds to the domain most relevant to this stakeholder role. |

### 6.3 Overall Status Representation

The checklist `overall_status` must be accurately represented in every guidance document. The following table governs how it is surfaced in `instructions`:

| `overall_status` | Representation in guidance `instructions` |
|---|---|
| `COMPLETE` | Guidance indicates the pipeline assessment is complete. Stakeholder must complete their required approvals to close out onboarding. |
| `ESCALATED` | The Checkoff Agent does not run when the finalized checklist is not in a COMPLETE terminal state. ESCALATED checklists do not trigger STEP-06. |
| `BLOCKED` | The Checkoff Agent does not run when overall_status is BLOCKED at the run level — STEP-06 is itself blocked in that case. |

---

## 7. Output Contract

The agent must return a single schema-valid JSON object. No other output format is permitted. Field definitions follow ORCH-PLAN-001 STEP-06 output contract.

```json
{
  "guidance_documents": [
    {
      "stakeholder_role": "string",
      "domain": "string",
      "instructions": "string",
      "blockers_owned": [
        {
          "blocker_type": "string",
          "description": "string",
          "resolution_owner": "string",
          "citation": "string"
        }
      ],
      "required_security_actions": [
        {
          "action_type": "string",
          "reason": "string",
          "owner": "string"
        }
      ],
      "next_steps": [
        "string"
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
  ],
  "status": "complete | blocked"
}
```

> On a `blocked` run, the agent emits a minimal object containing `status: blocked`. `guidance_documents` is not required on a blocked run.

### Output Field Constraints

| Field | Constraint |
|---|---|
| `guidance_documents` | Must contain at least one entry on every non-blocked run. Must contain one document per distinct stakeholder role identified per §6.1. |
| `stakeholder_role` | Must be non-null on every guidance document entry. If named contacts are unavailable, use role labels from `required_approvals[].domain` or the escalation ownership table. |
| `instructions` | Must be composed from structured checklist fields. Must accurately represent `overall_status`. Must not assert that conditions are resolved when they are not. |
| `blockers_owned` | Must include all checklist `blockers[]` entries whose `resolution_owner` matches this stakeholder role. May be `[]` if no blockers are assigned to this role. |
| `next_steps` | Must be non-empty on every guidance document where the stakeholder has outstanding approvals, owned blockers, or assigned escalation actions. May be `[]` only if this stakeholder has no actionable items in the current pipeline state. |
| `citations` | Carries through from the finalized checklist. The Checkoff Agent does not introduce new citations. |
| `status` | Lowercase. Either `complete` (guidance documents successfully produced) or `blocked` (finalized checklist absent). |

---

## 8. Status Determination

The Checkoff Agent uses a binary status model. It runs only after STEP-05 reaches terminal state `COMPLETE` and does not inherit the full three-status pipeline model used by domain agents.

| Condition | `status` |
|---|---|
| Finalized checklist absent from bundle | `blocked` |
| Finalized checklist present, STEP-05 status is `COMPLETE`, and at least one guidance document successfully produced | `complete` |

**Stakeholder map absent:** If `stakeholder_map` is absent but the finalized checklist is present, the agent proceeds with `status: complete` using role labels from the checklist. It does not emit `blocked` on a missing stakeholder map alone.

**STEP-06 runs only when STEP-05 is COMPLETE.** If STEP-05 is ESCALATED or BLOCKED, STEP-06 does not run.

---

## 9. Exception Handling

| Condition | Required Behavior |
|---|---|
| Finalized checklist absent | Bundle is inadmissible. Emit `status: blocked`. Do not produce guidance documents. Notify Procurement. |
| Stakeholder map absent | Proceed with role labels only. Log the absence. Do not emit `blocked`. |
| Stakeholder role has no outstanding approvals, blockers, or actions | Generate guidance document with empty `next_steps`. Confirm in `instructions` that no action is required from this role at this stage. |
| Bundle contains content from a prohibited source | Log anomaly. Exclude that content. Continue only if the remaining bundle is admissible; otherwise emit `blocked`. |

---

## 10. Critical Acceptance Checks

| # | Constraint | Pass Condition |
|---|---|---|
| A-01 | One guidance document produced per distinct stakeholder role | `guidance_documents` array contains one entry per role identified per §6.1 |
| A-02 | No checklist field re-derived or modified | `overall_status`, `data_classification`, `approval_path`, and all other upstream checklist fields are represented accurately and unchanged in guidance content |
| A-03 | All active blockers surfaced in the owning stakeholder's guidance document | Every checklist `blockers[]` entry appears in `blockers_owned` of the guidance document for the matching `resolution_owner` |
| A-04 | Guidance produced only from a COMPLETE finalized checklist | STEP-06 does not run when STEP-05 is `ESCALATED` or `BLOCKED` |
| A-05 | No index endpoint queried | Checkoff Agent has no evidence-discovery authority; any index query attempt fails closed and is logged |
| A-06 | `status: blocked` emitted only when finalized checklist is absent | Missing stakeholder map alone does not block; agent proceeds with role labels |
| A-07 | No new citations introduced | `citations` in each guidance document are a filtered subset of the finalized checklist `citations[]`; no new source references are added |

---

## 11. What This Agent Does Not Own

| Item | Governed By |
|---|---|
| Data classification | IT Security Agent (STEP-02) |
| DPA and NDA determinations | Legal Agent (STEP-03) |
| Approval path routing | Procurement Agent (STEP-04) |
| Finalized checklist and overall_status | Checklist Assembler (STEP-05) |
| Blocker resolution | Human stakeholders; pipeline identifies and routes, does not resolve |
| Approval waiver authority | Human-owned; this pipeline routes and notifies but does not waive |
| Source authority hierarchy | CC-001 §5 |
| Bundle assembly | Supervisor / ORCH-PLAN-001 STEP-06 |
| Output schema authority | Design Doc §10 |

---

## Version Log

| Version | Date | Author | Change |
|---|---|---|---|
| 0.1 | 2026-04-12 | Engineering / IT Architecture | Initial draft. Built strictly from Design Doc v0.9 §2, §3, §9; CC-001 v1.4 §6.1, §9.5; and ORCH-PLAN-001 v0.8 STEP-06. No new elements introduced. vq_direct_access permission noted from CC-001 §6.1 table but not exercised — no ORCH-PLAN-001 STEP-06 subquery uses it, and all required vendor information is present in the finalized checklist. |
| 0.2 | 2026-04-13 | Engineering / IT Architecture | Demo simplification revision. (1) PROVISIONAL status removed throughout — §1 upstream dependency updated from "COMPLETE, PROVISIONAL, or ESCALATED" to "COMPLETE"; §5.1 DO updated to reference ESCALATED only; §5.2 DON'T updated to remove PROVISIONAL; §6.2 `instructions` field rule updated to remove PROVISIONAL from condition list; §6.3 status representation table PROVISIONAL row removed; §8 STEP-06 gate language updated to remove PROVISIONAL; §9 exception handling PROVISIONAL row removed; §10 A-04 updated to remove PROVISIONAL. (2) `resolved` → `complete` throughout the binary status model — §2 Goal, §5.1 DOs, §5.2 DON'Ts, §7 output contract JSON and field constraints, §8 status table, and §9 exception handling all updated. (3) "four-status pipeline model" corrected to "three-status pipeline model" in §2 and §8. (4) PVD-001 removed — `idx_precedents` row removed from §4 index access permissions table. Aligned with Design Doc v4.0, CC-001 v1.4 (user-edited), and ORCH-PLAN-001 v0.9. |
