# Agent Spec — IT Security Agent
## SPEC-AGENT-SEC-001 v0.9

**Document ID:** SPEC-AGENT-SEC-001  
**Version:** 0.9
**Owner:** Engineering / IT Architecture  
**Last Updated:** April 12, 2026  

**Document Hierarchy:** PRD → Design Doc → Context Contract → **► Agent Spec ◄**

> This document defines the behavioral contract for the IT Security Agent. It governs how the agent behaves, what evidence it may consume, what it must not do, how it determines status, and what structured output it must return.

---

## Purpose

The IT Security Agent is the canonical security-classification agent for the pipeline. It owns STEP-02 and is the authoritative source for:

- `integration_tier`
- `data_classification`
- `fast_track_eligible`
- `security_followup_required`

Its purpose is to determine the vendor’s security review posture from governed evidence, not to perform open-ended research or replace human security review.

The IT Security Agent does not originate security facts. It normalizes questionnaire evidence, applies Tier 1 IT Security Policy rules, and emits a policy-cited STEP-02 determination.

---

## 1. Agent Identity

| Field | Value |
|---|---|
| **Agent ID** | `it_security_agent` |
| **Pipeline Step** | STEP-02 — R-02: Onboarding Path Classification and Fast-Track Determination |
| **Assigned By** | Supervisor Agent |
| **Upstream Dependency** | STEP-01 must be COMPLETE |
| **Downstream Dependents** | STEP-03 (Legal Agent), then STEP-04 (Procurement Agent) after STEP-03 reaches a terminal state |

---

## 2. Goal

The IT Security Agent receives a scoped evidence bundle — pre-assembled by the Supervisor — and produces a single structured JSON determination for STEP-02.

It derives its owned fields in the following way:

- `integration_type_normalized` is normalized from questionnaire integration details and related structured intake fields.
- `integration_tier` is assigned by applying Tier 1 IT Security Policy rules to the integration evidence.
- `data_classification` is determined from Tier 1 policy-backed interpretation of ERP involvement, system access posture, and data scope. Questionnaire self-report is supporting input only.
- `eu_personal_data_present` is taken from questionnaire evidence and normalized into the output contract.
- `fast_track_eligible` is determined only after the security classification logic above has been applied.
- `nda_status_from_questionnaire` is passed through from questionnaire evidence as an intake fact for downstream use. It is not part of the STEP-02 security determination and does not evaluate NDA adequacy.
- `required_security_actions` is emitted as the structured action output for any security follow-up the bundle supports.

The agent **does not** retrieve evidence independently. It reasons over the bundle it receives and returns a schema-valid output object. Every nontrivial determination must be cited to a Tier 1 policy source.

The Design Doc, Context Contract, and Orchestration Plan govern how the system is wired and when this agent runs, but they are not evidentiary inputs for this determination.

---

## 3. Evidence Bundle

The Supervisor assembles this bundle before the agent runs. The agent must treat the bundle as its complete and exclusive evidence base for this step.

**Bundle composition (assembly priority order):**
1. Questionnaire fields — integration method, declared data profile, EU personal data, NDA status
2. IT Security Policy — ERP integration tier sections
3. IT Security Policy — data classification and access control sections
4. IT Security Policy — fast-track disqualification / review-trigger sections
5. Supplemental context — excluded when budget is constrained

**Required questionnaire fields for an admissible STEP-02 bundle:**
- `integration_details.erp_type`
- `data_classification_self_reported`
- `regulated_data_types`
- `eu_personal_data_flag`
- `data_subjects_eu`
- `existing_nda_status`

If these required intake fields are missing, the bundle is inadmissible. The agent must emit the §9.1 blocked output shape with the appropriate `blocked_reason` and `blocked_fields`. Do not produce any determination fields.

---

## 4. Index Access Permissions

Derived from CC-001 §6.1. The agent must treat this as a hard access list, not a guideline.

| Index Endpoint | Access |
|---|---|
| `idx_security_policy` | ✓ Full |
| `idx_dpa_matrix` | ✗ No access |
| `idx_procurement_matrix` | ✗ No access |
| `vq_direct_access` | ✓ Full |
| `idx_slack_notes` | ✗ No access |

**The IT Security Agent does not query indices independently.** The Supervisor performs all retrieval and bundle assembly. If the agent detects that its bundle contains evidence from a prohibited index, it must log the anomaly, exclude that evidence from reasoning and citation, and continue only if the remaining bundle is still admissible. If excluding the prohibited evidence leaves the bundle inadmissible, the agent must emit `blocked`.

---

## 5. Retrieval and Access Boundary

The IT Security Agent is a **downstream reasoner**, not a free-search agent.

It may consume only the evidence bundle prepared for STEP-02 from permitted sources:

- **Vendor Questionnaire** via `vq_direct_access` — full access
- **IT Security Policy v4.2** via `idx_security_policy` — full access

It must not query or consume:

- DPA Legal Trigger Matrix
- Procurement Approval Matrix
- Slack / meeting notes
- attorney-client privileged communications
- raw runtime objects outside its assigned bundle except its own prior step-local working state

The architectural system may enforce retrieval permissions upstream. This spec reinforces that behavioral boundary: the agent must refuse to reason from excluded sources even if such content is accidentally present, exclude those materials from use, and proceed only if the remaining admissible bundle is sufficient.

---

## 6. Determination Ownership

The IT Security Agent is the **sole owner** of the following determinations. Downstream agents consume these as authoritative inputs and may not redefine or override them.

| Determination                    | Owned By                                                                                                                                                                                                  |
| -------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `integration_type_normalized`    | IT Security Agent                                                                                                                                                                                         |
| `integration_tier`               | IT Security Agent                                                                                                                                                                                         |
| `data_classification`            | IT Security Agent                                                                                                                                                                                         |
| `eu_personal_data_present`       | IT Security Agent                                                                                                                                                                                         |
| `fast_track_eligible`            | IT Security Agent                                                                                                                                                                                         |
| `fast_track_rationale`           | IT Security Agent                                                                                                                                                                                         |
| `security_followup_required`     | IT Security Agent                                                                                                                                                                                         |
| `required_security_actions`      | IT Security Agent                                                                                                                                                                                         |
| `nda_status_from_questionnaire`  | Passthrough — read from questionnaire, normalized, and included in output for downstream use. Not a derived determination. The IT Security Agent does not evaluate NDA adequacy; that belongs to STEP-03. |

STEP-04 (Procurement Agent) may **consume** `fast_track_eligible` as a passthrough but may not recalculate or override it. Under the sequential orchestration model, STEP-04 begins only after STEP-03 reaches a terminal state, but that sequencing change does not transfer ownership of `fast_track_eligible` away from STEP-02.

---

## 7. Behavioral Rules

### 7.1 DOs

- **DO** derive `integration_tier` and `data_classification` from Tier 1 policy evidence (ISP-001). Questionnaire self-report is supporting input only, not the basis for a classification determination.
- **DO** emit a determination on every non-blocked run. If evidence is incomplete or ambiguous, emit `escalated` and flag the specific gap.
- **DO** cite at least one ISP-001 section for every nontrivial classification determination. Free-text determinations without policy citations are not permitted.
- **DO** flag `fast_track_eligible = false` when `data_classification = REGULATED` or `integration_type_normalized = AMBIGUOUS`. Do not hedge this.
- **DO** include `nda_status_from_questionnaire` in output as a passthrough intake fact regardless of whether NDA is confirmed or unconfirmed.
- **DO** emit `required_security_actions` as a structured array. Never embed action items in free text.
- **DO** use canonical field semantics from CC-001 in all output fields and citations.
- **DO** write `status` as lowercase: `complete`, `escalated`, or `blocked`.

### 7.2 DON'Ts

- **DON'T** query any index endpoint independently. The Supervisor owns retrieval. If no bundle is provided, emit `blocked`.
- **DON'T** cite Tier 3 (Slack) evidence as a PRIMARY citation. These are SUPPLEMENTARY only.
- **DON'T** infer or guess questionnaire field values. If a required field is absent or ambiguous, flag it explicitly and reflect it in status.
- **DON'T** emit `fast_track_eligible = true` if `data_classification` is REGULATED or AMBIGUOUS. This is a hard rule, not a judgment call.
- **DON'T** produce free-text narrative as your output. Return only the structured JSON output contract defined in §9.
- **DON'T** redefine or contradict determinations from STEP-01. If intake validation found a version conflict, reflect that in your status.
- **DON'T** allow high semantic similarity of a Tier 3 chunk to elevate it to PRIMARY citation status.

---

## 8. Classification Rules

These are deterministic rules. The agent must apply them in order and may not override them through reasoning.

### 8.1 Rule application order

Apply the classification logic in this sequence:

1. normalize `integration_type_normalized` and `eu_personal_data_present` from questionnaire evidence
2. assign `integration_tier`
3. determine `data_classification`
4. determine `security_followup_required` (see §8.4)
5. determine `fast_track_eligible` and `fast_track_rationale` (see §8.6)

Normalization of `eu_personal_data_present` must occur in the same initial questionnaire-normalization pass as `integration_type_normalized`, before the classification chain begins. Later determinations must not be emitted before upstream STEP-02 security fields have been resolved.

### 8.2 Integration Tier Assignment

`integration_tier` is the **review-burden tier** the vendor's integration profile warrants. It is the key the Procurement Agent uses to look up the matching PAM-001 row at STEP-04 (matched against PAM's `Tier` column). Lower tier = lighter review burden; higher tier = heavier review burden. Tier assignment combines integration coupling (Direct API / Middleware / Export-only) with data sensitivity (Regulated / Unregulated): a tighter-coupled integration of regulated data warrants more review than a loose-coupled integration of unregulated data.

| Condition | Assigned Tier |
|---|---|
| Direct API connection to ERP without approved middleware (any data classification) | `TIER_1` |
| Connection through approved mediated middleware layer (any data classification) | `TIER_2` |
| Export-only / file-based, no direct system access, **regulated data in scope** | `TIER_3` |
| Export-only / file-based, no direct system access, **no regulated data in scope** (low-coupling AND low-risk vendor) | `TIER_1` |
| Integration pattern not classifiable from available evidence | `UNCLASSIFIED_PENDING_REVIEW` |

> **Note on TIER_1 for EXPORT_ONLY + UNREGULATED:** A vendor with no regulated data exposure and no direct ERP coupling presents the lowest combined risk profile — neither the data-sensitivity dimension nor the coupling-tightness dimension elevates the review burden. Such vendors warrant the lightest-tier review (TIER_1, Class C × T1 fast-track in PAM-001) even though their integration mechanism is technically EXPORT_ONLY. This is the only path by which an EXPORT_ONLY integration lands at TIER_1 — any regulated data in scope reverts to TIER_3.

Tier assignment must cite the relevant ISP-001 §12.2 row.

### 8.3 Data Classification

| Condition | `data_classification` |
|---|---|
| `eu_personal_data_present = true` | `REGULATED` |
| Integration involves regulated, sensitive, or ERP-connected data | `REGULATED` |
| Integration confirmed export-only, no regulated data types | `UNREGULATED` |
| Integration type or data scope cannot be confirmed | `AMBIGUOUS` |

### 8.4 Security Follow-Up Requirement

`security_followup_required` is determined after integration tier and data classification are resolved.

| Condition | `security_followup_required` |
|---|---|
| `integration_tier = UNCLASSIFIED_PENDING_REVIEW` | `true` — architecture documentation required |
| `data_classification = REGULATED` and `integration_tier = TIER_1` | `true` — full security review required |
| `data_classification = REGULATED` and `integration_tier = TIER_2` | `true` — security review required |
| `eu_personal_data_present = true` and `integration_tier` is not `TIER_3` | `true` — data handling review required |
| `integration_type_normalized = AMBIGUOUS` | `true` — integration pattern must be clarified before review can proceed |
| `data_classification = UNREGULATED` and `integration_tier = TIER_3` and no ambiguity | `false` |
| `data_classification = UNREGULATED` and `integration_tier = TIER_1` (the EXPORT_ONLY + UNREGULATED path per §8.2) and no ambiguity | `false` — light-tier review is satisfied by the §8.2 classification itself |

When `security_followup_required = true`, the agent must populate `required_security_actions` with at least one structured entry describing the required action, reason, and responsible owner. An empty `required_security_actions` array is only valid when `security_followup_required = false`.


### 8.5 Fast-Track Eligibility

| Condition | `fast_track_eligible` |
|---|---|
| `data_classification = REGULATED` | `false` |
| `integration_type_normalized = AMBIGUOUS` | `false` |
| Governing fast-track policy source missing or unconfirmed | `false`, `fast_track_rationale = DISALLOWED_AMBIGUOUS_SCOPE` |
| All conditions satisfied for low-risk, export-only, unregulated vendor | `true` |

Fast-track `true` requires `data_classification = UNREGULATED` with a confirmed policy citation. Any ambiguity defaults to `false`.

---

## 9. Output Contract

The agent must return a single schema-valid JSON object. No other output format is permitted.

```json
{
  "integration_type_normalized": "DIRECT_API | MIDDLEWARE | EXPORT_ONLY | AMBIGUOUS",
  "integration_tier": "TIER_1 | TIER_2 | TIER_3 | UNCLASSIFIED_PENDING_REVIEW",
  "data_classification": "REGULATED | UNREGULATED | AMBIGUOUS",
  "eu_personal_data_present": true | false,
  "fast_track_eligible": true | false,
  "fast_track_rationale": "DISALLOWED_REGULATED_DATA | DISALLOWED_INTEGRATION_RISK | DISALLOWED_AMBIGUOUS_SCOPE | ELIGIBLE_LOW_RISK",
  "security_followup_required": true | false,
  "nda_status_from_questionnaire": "EXECUTED | PENDING | NOT_STARTED | UNKNOWN",
  "required_security_actions": [
    {
      "action_type": "string",
      "reason": "string",
      "owner": "string"
    }
  ],
  "policy_citations": [
    {
      "source_id": "ISP-001",
      "version": "4.2",
      "chunk_id": "string",
      "section_id": "string",
      "citation_class": "PRIMARY | SUPPLEMENTARY"
    }
  ],
  "status": "complete | escalated | blocked"
}
```

> `escalation_reason` is not included in the output contract. Escalation context — including the triggering condition, conflicting sources, and resolution owner — is captured in the append-only audit log per CC-001 §13.1 and the orchestration plan global audit rules. The `policy_citations` array on an `escalated` output must cite both conflicting chunks when the escalation is clause-level. The audit log is the authoritative escalation record.

> **Blocked output rule:** On a `blocked` run, the agent MUST NOT emit determination fields (`integration_type_normalized`, `integration_tier`, `data_classification`, `eu_personal_data_present`, `fast_track_eligible`, `fast_track_rationale`, `security_followup_required`, `nda_status_from_questionnaire`, `required_security_actions`, `policy_citations`). These fields must be entirely absent from the output — not null, not empty, absent. Emitting any determination field on a blocked run is a contract violation because the agent had no evidentiary basis to produce it. See §9.1 for the mandatory blocked output shape.

### Output field constraints

| Field | Constraint |
|---|---|
| `integration_type_normalized` | Must be present on every non-blocked run. Absent on blocked runs (§9.1). On escalated runs, set to `null` if the agent cannot resolve the integration type (§9.2). |
| `integration_tier` | Must be present on every non-blocked run. Absent on blocked runs. Must be derived from Tier 1 policy evidence, not questionnaire self-report. On escalated runs, set to `null` if the agent cannot assign a tier (§9.2). |
| `data_classification` | Must be present on every non-blocked run. Absent on blocked runs. Must be derived from Tier 1 policy evidence. On escalated runs, set to `null` if the agent cannot resolve the classification (§9.2). |
| `eu_personal_data_present` | Must be present on every non-blocked run. Absent on blocked runs. On escalated runs, set to `null` only if the questionnaire EU fields are ambiguous or unresolvable (§9.2). |
| `fast_track_eligible` | Must be present on every non-blocked run. Absent on blocked runs. Must be emitted before STEP-04 may begin. On escalated runs, set to `null` if upstream classification fields it depends on are `null` (§9.2). |
| `fast_track_rationale` | Must be present on every non-blocked run. Absent on blocked runs. Must be non-null whenever `fast_track_eligible = false`, and must contain one of the defined enum values. On escalated runs, set to `null` if `fast_track_eligible` is `null`. |
| `security_followup_required` | Must be present on every non-blocked run. Absent on blocked runs. On escalated runs, set to `null` if upstream classification fields it depends on are `null` (§9.2). |
| `nda_status_from_questionnaire` | Must be present on every non-blocked run. Absent on blocked runs. On escalated runs, set to `null` only if the questionnaire NDA field is absent or unrecognizable. |
| `required_security_actions` | Must be present on every non-blocked run. Absent on blocked runs. May be an empty array only when `security_followup_required = false`. On escalated runs, set to `null` if `security_followup_required` is `null`. |
| `policy_citations` | Must be present on every non-blocked run. Absent on blocked runs. At least one PRIMARY ISP-001 citation required for any nontrivial classification determination. On escalated runs, include citations for determinations that were resolved; set to `null` only if all citation-supporting determinations are unresolvable. |
| `fast_track_eligible = true` | Requires at least one PRIMARY ISP-001 citation supporting low-risk / export-only eligibility |
| `status = escalated` | All determination fields must be present (not absent). Fields the agent resolved carry their derived values. Fields the agent could not resolve are `null`. See §9.2. When escalation is clause-level, `policy_citations` must cite both conflicting chunks. Full escalation payload is captured in the audit log per CC-001 §13.1. |
| `status` | Lowercase. One of `complete`, `escalated`, or `blocked`. |

### 9.1 Blocked Output Shape

When the agent derives `status = blocked`, it MUST emit the following output shape instead of the standard determination object. The determination fields defined in §9 (`integration_type_normalized`, `integration_tier`, `data_classification`, `eu_personal_data_present`, `fast_track_eligible`, `fast_track_rationale`, `security_followup_required`, `nda_status_from_questionnaire`, `required_security_actions`, `policy_citations`) must be entirely absent — not null, not empty. Null implies the field exists but has no value; absent means the agent correctly declined to produce a determination it had no basis to make. That distinction matters for downstream schema validation.

```json
{
  "status": "blocked",
  "blocked_reason": ["MISSING_QUESTIONNAIRE_CLASSIFICATION_FIELDS"],
  "blocked_fields": ["data_classification_self_reported", "regulated_data_types"]
}
```

**`blocked_reason`** — enum array. Lists the specific gate-condition or admissibility failure(s) that caused the block. Multiple values are permitted when multiple inputs are missing simultaneously. Defined enum values for the IT Security Agent:

| Enum Value | Condition |
|---|---|
| `MISSING_QUESTIONNAIRE_CLASSIFICATION_FIELDS` | Core data classification inputs (`data_classification_self_reported`, `regulated_data_types`) are absent from the bundle. The agent cannot make any classification determination without these. Distinct from STEP-01 blocking on a missing questionnaire entirely — STEP-01 validates existence and completeness, but a bundle assembly failure could still deliver a bundle with these fields stripped or null. |
| `MISSING_ERP_INTEGRATION_FIELDS` | `integration_details.erp_type` is absent from the bundle. The agent cannot assign an integration tier or determine fast-track eligibility without this. Kept separate from classification fields because ERP fields and classification fields drive different downstream outputs. Given that `integration_tier` and `data_classification` are tightly coupled in ISP-001's classification logic, a full block is cleaner than a partial determination. |
| `MISSING_ISP_001` | The security policy index is entirely unavailable. The agent has questionnaire fields but no authoritative source to cite for its determination. Per CC-001 §11, a determination without at least one Tier 1 citation is insufficient for complete — and unlike supplementary inputs, ISP-001 is the primary governing source for this agent. No ISP-001 means no determination at all. |

**`blocked_fields`** — string array. Lists the specific canonical field names (per CC-001 §15) that were absent or null in the upstream input, causing the block. This array is what makes the audit log entry useful: it names exactly what the Supervisor needs to surface to the resolution owner.

> This output shape is mandatory whenever `status = blocked`. The agent must not fall back to the standard determination shape with null-valued fields. The blocked output shape is the only valid output when the agent cannot proceed.

### 9.2 Escalated Output Rules

When the agent derives `status = escalated`, it emits the same determination shape as §9 — **not** the §9.1 blocked shape. The key rule: every determination field must be present in the output. Fields the agent can resolve carry their derived values. Fields the agent cannot resolve are set to `null`.

**`null` semantics on escalated runs:** `null` means the agent assessed the available evidence and the classification rules in this spec, but could not resolve the field. This is distinct from `absent` on blocked runs (where the agent had no evidentiary basis to begin work at all) and distinct from a populated value on complete runs (where the agent fully resolved the classification). The `null` values tell the Supervisor exactly which fields require human judgment.

**Per-field escalated null rules:**

| Field | When `null` on an escalated run |
|---|---|
| `integration_type_normalized` | Agent cannot normalize the integration type from available evidence |
| `integration_tier` | Agent cannot assign a tier — e.g., ISP-001 ERP tier table not retrieved for the specific integration pattern, or Tier 1 sources conflict |
| `data_classification` | Agent cannot determine classification from available evidence and policy rules |
| `eu_personal_data_present` | Questionnaire EU personal data fields are ambiguous or contradictory — agent cannot normalize to a boolean |
| `fast_track_eligible` | Upstream `data_classification` or `integration_type_normalized` is `null` — cannot evaluate eligibility from an unresolved classification |
| `fast_track_rationale` | `fast_track_eligible` is `null` — cannot derive rationale from an unresolved eligibility determination |
| `security_followup_required` | Upstream `integration_tier` and `data_classification` are both `null` — cannot determine follow-up requirement from unresolved classifications |
| `nda_status_from_questionnaire` | Questionnaire NDA field is absent or value is unrecognizable — cannot normalize to an enum value |
| `required_security_actions` | `security_followup_required` is `null` — cannot derive actions from an unresolved follow-up determination |
| `policy_citations` | All citation-supporting determinations are unresolvable — set to `null`. If some citations are resolvable, include the resolvable citations and omit the unresolvable ones |

**Fields that are resolved on escalated runs carry their normal values.** For example, when `data_classification = REGULATED` and `integration_type_normalized = AMBIGUOUS` produces `escalated`, the resolved fields are populated: `data_classification: "REGULATED"`, `eu_personal_data_present: true`, `fast_track_eligible: false`, etc. Only `integration_tier` (and fields that depend on it) would be `null` if the tier cannot be assigned. The escalation is about the unresolvable field(s), not about the entire determination.

**Escalated output example — integration tier unresolvable, classification resolved:**

```json
{
  "integration_type_normalized": "AMBIGUOUS",
  "integration_tier": null,
  "data_classification": "REGULATED",
  "eu_personal_data_present": true,
  "fast_track_eligible": false,
  "fast_track_rationale": "DISALLOWED_AMBIGUOUS_SCOPE",
  "security_followup_required": true,
  "nda_status_from_questionnaire": "PENDING",
  "required_security_actions": [
    {
      "action_type": "ARCHITECTURE_REVIEW",
      "reason": "Integration pattern is ambiguous — tier assignment requires human review of vendor architecture documentation",
      "owner": "IT Security"
    }
  ],
  "policy_citations": [
    {
      "source_id": "ISP-001",
      "version": "4.2",
      "chunk_id": "ISP-001__section_12",
      "section_id": "12",
      "citation_class": "PRIMARY"
    }
  ],
  "status": "escalated"
}
```

> In this example, `data_classification = REGULATED` is confident (EU personal data confirmed), but the integration pattern is ambiguous and the tier cannot be assigned. The agent sets `integration_tier` to `null` — it cannot make the determination. `security_followup_required` is `true` because the ambiguous integration type independently triggers follow-up per §8.4. `fast_track_eligible` is `false` (not `null`) because the AMBIGUOUS integration type alone is sufficient to disqualify fast-track per §8.5 — it does not depend on the unresolved tier.

---

## 10. Status Determination

The three terminal states and their top-level conditions are:

- **`blocked`** — A required context bundle item is missing or inadmissible (e.g., core questionnaire classification fields absent, ERP integration fields absent, ISP-001 unavailable). The agent cannot begin its classification work. **Output shape:** §9.1 — determination fields entirely absent, `blocked_reason` and `blocked_fields` identify the gap.
- **`escalated`** — The bundle was admissible and the agent began its work, but it could not resolve one or more output contract fields based on the classification rules in this spec (e.g., Tier 1 sources conflict, integration tier unclassifiable, or the case falls outside the governed rule set). **Output shape:** §9 with §9.2 rules — all determination fields present, resolved fields carry values, unresolvable fields set to `null`.
- **`complete`** — All required evidence present, Tier 1 citations complete, all classification determinations fully resolved, no escalation or blocked condition applies. **Output shape:** §9 — all determination fields present and populated.

**Output shape switching rule:** The agent must first derive the terminal status, then emit the output shape corresponding to that status:

- **`complete`** — Emit the standard determination output defined in §9. All determination fields must be present and populated with their derived values. No field may be `null`.
- **`escalated`** — Emit the standard determination output defined in §9 with the escalated field rules defined in §9.2. All determination fields must be present. Fields the agent can resolve are populated normally. Fields the agent cannot resolve — the specific cause of the escalation — are set to `null`. No field may be absent. See §9.2 for the full escalated output rules.
- **`blocked`** — Emit the blocked output shape defined in §9.1 instead. Determination fields must be entirely absent from the output, not null. The agent must not attempt to populate any determination field on a blocked run under any circumstances, regardless of what other evidence may be present in the bundle.

**BLOCKED vs ESCALATED distinction:** `blocked` means a required context bundle item is missing or inadmissible — the agent has no evidentiary basis to begin its work, so it declines to produce any determination (all determination fields absent). `escalated` means the bundle was admissible and the agent began its work, but it could not resolve one or more output contract fields based on the classification rules in this spec — it fills every field it can and sets the unresolvable field(s) to `null` so the Supervisor knows exactly where human judgment is needed.

The agent must not emit `complete` if any field it owns is still flagged `AMBIGUOUS` or `UNKNOWN` and that ambiguity affects the determination's substance.

---

## 11. Provenance and Citation Requirements

Per CC-001 §14:

- Every classification determination must carry at least one PRIMARY ISP-001 citation with `source_id`, `version`, `chunk_id`, and `section_id`.
- Questionnaire field references must use canonical field semantics from CC-001 §15 (for example, `integration_details.erp_type` rather than free-text descriptions).
- If a questionnaire field is ambiguous, name the specific field by canonical field name in the output — do not issue a general disclaimer.

---

## 12. Exception Handling

| Condition | Required Behavior |
|---|---|
| Bundle is empty or missing | Emit the §9.1 blocked output shape. Do not produce a determination. Do not emit any determination fields. |
| Core classification questionnaire fields absent (`data_classification_self_reported`, `regulated_data_types`) | Emit the §9.1 blocked output shape with `blocked_reason: ["MISSING_QUESTIONNAIRE_CLASSIFICATION_FIELDS"]` and `blocked_fields` listing the absent fields. Do not produce any determination fields. |
| ERP integration field absent (`integration_details.erp_type`) | Emit the §9.1 blocked output shape with `blocked_reason: ["MISSING_ERP_INTEGRATION_FIELDS"]` and `blocked_fields: ["integration_type"]`. Do not produce any determination fields. |
| ISP-001 entirely unavailable | Emit the §9.1 blocked output shape with `blocked_reason: ["MISSING_ISP_001"]` and `blocked_fields` listing the policy sections that were expected. Do not produce any determination fields. |
| ISP-001 ERP tier table not retrieved (ISP-001 partially available) | Emit `status: escalated`. Log retrieval failure. Set `integration_tier` to `null` per §9.2. Populate all other fields the agent can resolve. |
| Fast-track policy section not retrieved | `fast_track_eligible = false`, `fast_track_rationale = DISALLOWED_AMBIGUOUS_SCOPE`. Emit `status: escalated`. Populate all other fields the agent can resolve. |
| Bundle contains evidence from a prohibited index | Log anomaly. Exclude the prohibited evidence from reasoning and citation. Continue only if the remaining bundle is still admissible; otherwise emit the §9.1 blocked output shape. |
| Malformed or schema-invalid bundle | Emit the §9.1 blocked output shape. Do not attempt to reason over partial input. Do not emit any determination fields. |
| Two ISP-001 clauses directly conflict on the same question | Emit `status: escalated`. Set the conflicting determination field(s) to `null` per §9.2. Cite both conflicting chunks in `policy_citations`. Full escalation payload is written to the audit log. |

---

## 13. Example Behavioral Outcomes

### Example A — regulated and ambiguous ERP posture (escalated, all fields resolved)

EU personal data is present and ERP involvement is in scope, but the integration pattern is ambiguous. All fields are resolvable — the escalation is about the ambiguous integration pattern requiring human clarification, not about an unresolvable field:

```json
{
  "integration_type_normalized": "AMBIGUOUS",
  "integration_tier": "UNCLASSIFIED_PENDING_REVIEW",
  "data_classification": "REGULATED",
  "eu_personal_data_present": true | false,
  "fast_track_eligible": true | false,
  "fast_track_rationale": "DISALLOWED_AMBIGUOUS_SCOPE",
  "security_followup_required": true | false,
  "nda_status_from_questionnaire": "PENDING",
  "required_security_actions": [
    {
      "action_type": "ARCHITECTURE_REVIEW",
      "reason": "Integration pattern is ambiguous — tier assignment requires human review of vendor architecture documentation",
      "owner": "IT Security"
    }
  ],
  "policy_citations": [
    {
      "source_id": "ISP-001",
      "version": "4.2",
      "chunk_id": "ISP-001__section_12",
      "section_id": "12",
      "citation_class": "PRIMARY"
    },
    {
      "source_id": "ISP-001",
      "version": "4.2",
      "chunk_id": "ISP-001__section_17",
      "section_id": "17",
      "citation_class": "PRIMARY"
    }
  ],
  "status": "escalated"
}
```

> No fields are `null` — the agent resolved every determination. `data_classification = REGULATED` is confident (EU personal data and ERP involvement are sufficient). `integration_tier = UNCLASSIFIED_PENDING_REVIEW` is a valid tier assignment meaning the agent classified it as requiring human review. The ESCALATED status reflects that the integration pattern requires human input, not that any field is unresolvable. Per §9.2, when all fields are resolvable on an escalated run, all carry their derived values.

### Example B — missing mandatory evidence (blocked)

Core questionnaire classification evidence is absent from the bundle — no `data_classification_self_reported` or `regulated_data_types`:

```json
{
  "status": "blocked",
  "blocked_reason": ["MISSING_QUESTIONNAIRE_CLASSIFICATION_FIELDS"],
  "blocked_fields": ["data_classification_self_reported", "regulated_data_types"]
}
```

> The agent must not attempt any classification despite having other evidence available in the bundle. The core classification inputs are required for an admissible bundle per §3. Determination fields are entirely absent from the output, not null — the agent declined to produce a determination it had no basis to make.

### Example C — clean low-risk vendor (complete)

Questionnaire confirms export-only integration, no regulated data, and no EU personal data. ISP-001 sections support the mapping:

```json
{
  "integration_type_normalized": "EXPORT_ONLY",
  "integration_tier": "TIER_3",
  "data_classification": "UNREGULATED",
  "eu_personal_data_present": false,
  "fast_track_eligible": true,
  "fast_track_rationale": "ELIGIBLE_LOW_RISK",
  "security_followup_required": false,
  "nda_status_from_questionnaire": "EXECUTED",
  "required_security_actions": [],
  "policy_citations": [
    {
      "source_id": "ISP-001",
      "version": "4.2",
      "chunk_id": "ISP-001__section_12",
      "section_id": "12",
      "citation_class": "PRIMARY"
    },
    {
      "source_id": "ISP-001",
      "version": "4.2",
      "chunk_id": "ISP-001__section_17",
      "section_id": "17",
      "citation_class": "PRIMARY"
    }
  ],
  "status": "complete"
}
```

### Example D — ISP-001 ERP tier table not retrieved (escalated, tier unresolvable)

Questionnaire confirms integration type and data scope, but the ISP-001 ERP tier table cannot be retrieved from the index. ISP-001 is partially available (classification sections present, tier section absent). Classification is resolvable from available policy; tier is not:

```json
{
  "integration_type_normalized": "DIRECT_API",
  "integration_tier": null,
  "data_classification": "REGULATED",
  "eu_personal_data_present": true,
  "fast_track_eligible": false,
  "fast_track_rationale": "DISALLOWED_REGULATED_DATA",
  "security_followup_required": true,
  "nda_status_from_questionnaire": "PENDING",
  "required_security_actions": [
    {
      "action_type": "FULL_SECURITY_REVIEW",
      "reason": "REGULATED data classification with unresolved integration tier — full security review required",
      "owner": "IT Security"
    }
  ],
  "policy_citations": [
    {
      "source_id": "ISP-001",
      "version": "4.2",
      "chunk_id": "ISP-001__section_17",
      "section_id": "17",
      "citation_class": "PRIMARY"
    }
  ],
  "status": "escalated"
}
```

> `integration_tier` is `null` — the ISP-001 ERP tier table was not retrieved, so the agent cannot assign a tier. All other fields are resolved from available evidence: `data_classification = REGULATED` from EU personal data, `fast_track_eligible = false` from the regulated classification (does not depend on the missing tier), `security_followup_required = true` from the regulated classification. The Supervisor reads the `null` tier to identify exactly which determination needs human resolution.

### Example E — ISP-001 entirely unavailable (blocked)

Questionnaire fields are present but ISP-001 is entirely unavailable — no authoritative policy source to cite:

```json
{
  "status": "blocked",
  "blocked_reason": ["MISSING_ISP_001"],
  "blocked_fields": ["idx_security_policy"]
}
```

> Per CC-001 §11, a determination without at least one Tier 1 citation is insufficient for complete. ISP-001 is the primary governing source for the IT Security Agent — not a supplementary input. Without it, no determination can be made. Determination fields are entirely absent.

---

## 14. Critical Acceptance Checks

These are the must-pass checks for this spec. They belong here as implementation-critical acceptance checks, not as a full evaluation program.

| # | Constraint | Pass Condition                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  |
| ---- | ----------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| A-01 | `integration_tier` derived from Tier 1 policy, not self-report | `policy_citations` includes a PRIMARY ISP-001 citation supporting the tier assignment                                                                                                                                                                                                                                                                                                                                                                                                                                                                           |
| A-02 | `data_classification` derived from Tier 1 policy | At least one PRIMARY ISP-001 citation supports the classification                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               |
| A-03 | `fast_track_eligible = false` when `data_classification = REGULATED` or `integration_type_normalized = AMBIGUOUS` | Hard rule satisfied with no exceptions                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          |
| A-04 | No Tier 3 (Slack) source cited as PRIMARY | All Tier 3 citations remain SUPPLEMENTARY                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       |
| A-06 | All required output fields present and structurally valid | Schema-valid JSON. On `complete` runs: all determination fields must be non-null. On `escalated` runs: all determination fields must be present (not absent); resolved fields are non-null, unresolvable fields are `null` per §9.2. `status` must be one of `complete`, `escalated`, or `blocked`. `required_security_actions` may be `[]` only when `security_followup_required = false`. `policy_citations` must contain at least one entry on any complete, non-trivial run. |
| A-07 | Blocked output uses §9.1 shape with no determination fields | When `status = blocked`: output contains only `status`, `blocked_reason`, and `blocked_fields`. Determination fields (`integration_type_normalized`, `integration_tier`, `data_classification`, `eu_personal_data_present`, `fast_track_eligible`, `fast_track_rationale`, `security_followup_required`, `nda_status_from_questionnaire`, `required_security_actions`, `policy_citations`) are entirely absent — not null, not empty. `blocked_reason` is a non-empty enum array. `blocked_fields` is a non-empty array of canonical field names. |
| A-08 | Escalated output has all determination fields present per §9.2 | When `status = escalated`: all determination fields are present (not absent). Resolved fields carry their derived values. Unresolvable fields are `null`. No field is absent. |

A fuller CSR / ISR evaluation matrix may be maintained in a separate evaluation artifact.

---

## 15. What This Agent Does Not Own

| Item | Governed By |
|---|---|
| DPA requirement determination | Legal Agent (STEP-03) |
| Approval path routing | Procurement Agent (STEP-04) |
| STEP-03 → STEP-04 execution order and gate sequencing | Design Doc / ORCH-PLAN-001 |
| Source authority hierarchy | CC-001 §5 |
| Retrieval routing and bundle assembly | Supervisor / ORCH-PLAN-001 STEP-02 |
| Output schema authority | Design Doc §10 |
| Checklist composition | Checklist Assembler (STEP-05) |
