# Agent Spec — Procurement Agent
## SPEC-AGENT-PROC-001 v0.6

**Document ID:** SPEC-AGENT-PROC-001
**Version:** 0.6
**Owner:** Engineering / IT Architecture
**Last Updated:** April 13, 2026

**Document Hierarchy:** PRD → Design Doc → Context Contract → **► Agent Spec ◄**

> This document defines the behavioral contract for the Procurement Agent. It governs how the agent behaves, what evidence it may consume, what it must not do, how it determines status, and what structured output it must return.

---

## Purpose

The Procurement Agent is the canonical approval-path determination agent for the pipeline. It owns STEP-04 and is the authoritative source for:

- `approval_path`
- `required_approvals[]`
- `estimated_timeline`

Its purpose is to determine the correct onboarding approval path and required approver set for the vendor under evaluation, based on governed evidence from upstream domain agents and the Procurement Approval Matrix — not to waive required approvals, override Legal or Security determinations, or make autonomous procurement decisions.

The Procurement Agent does not originate procurement facts. It applies Procurement Approval Matrix rows to the authoritative upstream STEP-02 security output, authoritative upstream STEP-03 Legal output, and questionnaire vendor relationship context delivered in the bundle, and emits a matrix-cited STEP-04 determination.

**Output-contract note:** STEP-04 re-emits `fast_track_eligible` in its output contract for downstream consistency with the Design Doc and ORCH-PLAN-001. Ownership of `fast_track_eligible` remains with the IT Security Agent (STEP-02). In STEP-04 it is a read-only passthrough field, not a Procurement-owned determination.

---

## 1. Agent Identity

| Field | Value |
|---|---|
| **Agent ID** | `procurement_agent` |
| **Pipeline Step** | STEP-04 — R-04: Approval Path Routing |
| **Assigned By** | Supervisor Agent |
| **Upstream Dependency** | STEP-03 must be in a terminal state. STEP-02 and STEP-03 outputs must both be present as schema-valid upstream inputs. |
| **Parallel With** | — |
| **Downstream Dependents** | STEP-05 (Checklist Assembler) |

---

## 2. Goal

The Procurement Agent receives a scoped evidence bundle — pre-assembled by the Supervisor — and produces a single structured JSON determination for STEP-04.

It derives or emits its output fields in the following way:

- `approval_path` is determined by applying Procurement Approval Matrix rows to the authoritative upstream security posture, authoritative Legal determination, vendor class, and deal size. At least one matching Tier 1 matrix row is required for a COMPLETE approval-path determination.
- `fast_track_eligible` is carried through from STEP-02 as a read-only passthrough field. The Procurement Agent may use it as an input to matrix routing, but may not recalculate, reinterpret, or override it.
- `required_approvals[]` is assembled from the PAM-001 row's required approver list for the matched path.
- `estimated_timeline` is derived from the matched approval-path row and any matrix-supported blocker implications. It remains a routing estimate, not a commitment.

The agent **does not** retrieve evidence independently. It reasons over the bundle it receives and returns a schema-valid output object. Every nontrivial determination must be cited to a Tier 1 source.

The Design Doc, Context Contract, and Orchestration Plan govern how the system is wired and when this agent runs. They are not evidentiary inputs for this determination.

---

## 3. Evidence Bundle

The Supervisor assembles this bundle before the agent runs. The agent must treat the bundle as its complete and exclusive evidence base for this step.

**Bundle composition (assembly priority order):**
1. IT Security Agent output (full) — `data_classification`, `fast_track_eligible`, `integration_tier`, `security_followup_required`, `policy_citations[]`
2. Legal Agent output (full) — `dpa_required`, `dpa_blocker`, `nda_status`, `nda_blocker`, `trigger_rule_cited`, `policy_citations[]`
3. Questionnaire vendor relationship fields — `existing_nda_status`, `existing_msa`, `vendor_class`, raw questionnaire field `contract_value_annual` (normalized into canonical `deal_size` for STEP-04 routing)
4. Procurement Approval Matrix rows — matching rows only (PAM-001)
5. Slack / meeting thread notes — Procurement-scoped threads only (Tier 3, SUPPLEMENTARY; included only when specifically relevant / flagged and non-conflicting and non-redundant with Tier 1–2 evidence)

**Required fields for an admissible STEP-04 bundle:**
- IT Security Agent output (required; bundle is inadmissible without `data_classification`, `fast_track_eligible`, `integration_tier`, `security_followup_required`, `policy_citations`, and `status`)
- Legal Agent output (required; bundle is inadmissible without `dpa_required`, `dpa_blocker`, `nda_status`, `nda_blocker`, `trigger_rule_cited`, `policy_citations`, and `status`)
- `existing_nda_status` from questionnaire
- `existing_msa` from questionnaire
- `vendor_class` from questionnaire
- raw questionnaire field `contract_value_annual`, normalized into canonical `deal_size`

If either upstream agent output is absent or schema-invalid, the bundle is inadmissible and the agent must emit `blocked`. If required questionnaire vendor relationship fields are missing, the agent must flag absent fields explicitly and emit `blocked`. A Procurement Approval Matrix row match is required for a COMPLETE `approval_path` determination — if no row matches, the agent must emit `escalated`.

**Field-normalization note:** CC-001 §15 defines `deal_size` as the canonical STEP-04 field, while the questionnaire stores this value as `contract_value_annual`. ORCH-PLAN-001 STEP-04 reads `contract_value_annual` from `vq_direct_access`; the Supervisor then normalizes that raw field into canonical `deal_size` for bundle use. This spec uses `deal_size` for determination logic and cites `contract_value_annual` only when referring to the raw questionnaire field.

---

## 4. Index Access Permissions

Derived from CC-001 §6.1. The agent must treat this as a hard access list, not a guideline.

| Index Endpoint | Access |
|---|---|
| `idx_security_policy` | ✓ Read-only (reference) |
| `idx_dpa_matrix` | ✗ No access |
| `idx_procurement_matrix` | ✓ Full |
| `vq_direct_access` | ✓ Full |
| `idx_slack_notes` | ✓ Procurement-scoped threads only |

**The Procurement Agent does not query indices independently.** The Supervisor performs all retrieval and bundle assembly. If the agent detects that its bundle contains evidence from a prohibited index, it must log the anomaly, exclude that evidence from reasoning and citation, and continue only if the remaining bundle is still admissible. If excluding the prohibited evidence leaves the bundle inadmissible, the agent must emit `blocked`.

**Slack / meeting notes scope:** The Procurement Agent is the only domain agent permitted to consume Tier 3 supplemental sources. Access is strictly limited to Procurement-scoped threads. Tier 3 evidence may only supplement a determination already supported by Tier 1 evidence — it may never serve as the sole or primary basis for any determination. See CC-001 §10 for full Tier 3 handling rules.

**IT Security Policy read-only scope:** The Procurement Agent has read-only access to `idx_security_policy` per CC-001 §6.1 and Design Doc §8. No ISP-001 subquery is defined in ORCH-PLAN-001 STEP-04; this permission exists at the index level but is not exercised in the current pipeline implementation. The Procurement Agent receives upstream IT Security classification context through the STEP-02 structured output object, not through direct ISP-001 retrieval. It may not use any ISP-001 content to reinterpret or override the upstream security classification or fast-track eligibility determination produced by the IT Security Agent.

---

## 5. Retrieval and Access Boundary

The Procurement Agent is a **downstream reasoner**, not a free-search agent.

It may consume only the evidence bundle prepared for STEP-04 from permitted sources:

- **IT Security Agent output** via pipeline state read — full output: `data_classification`, `fast_track_eligible`, `integration_tier`, `security_followup_required`, `policy_citations[]`, `status`
- **Legal Agent output** via pipeline state read — full output: `dpa_required`, `dpa_blocker`, `nda_status`, `nda_blocker`, `trigger_rule_cited`, `policy_citations[]`, `status`
- **Vendor Questionnaire** via `vq_direct_access` — full access for vendor relationship fields: `existing_nda_status`, `existing_msa`, `vendor_class`, raw field `contract_value_annual` (normalized into canonical `deal_size`)
- **Procurement Approval Matrix** via `idx_procurement_matrix` — full access
- **Slack / Meeting Thread Notes** via `idx_slack_notes` — Procurement-scoped threads only

It must not query or consume:

- DPA Legal Trigger Matrix
- Attorney-client privileged communications
- Legal Agent or IT Security Agent intermediate reasoning — only the final structured output objects are in scope
- raw runtime objects outside its assigned bundle

The architectural system may enforce retrieval permissions upstream. This spec reinforces that behavioral boundary: the agent must refuse to reason from excluded sources even if such content is accidentally present, exclude those materials from use, and proceed only if the remaining admissible bundle is sufficient.

---

## 6. Determination Ownership

The Procurement Agent is the **sole owner** of the following determinations. Downstream agents consume these as authoritative inputs and may not redefine or override them.

**Naming note:** The STEP-04 output contract includes `fast_track_eligible` for downstream continuity, but ownership remains with STEP-02. This spec keeps the implementation-facing STEP-04 output contract aligned with the Design Doc while preserving IT Security ownership of the field.

| Determination | Owned By |
|---|---|
| `approval_path` | Procurement Agent — derived from PAM-001 row match against upstream classification, Legal output, and vendor profile |
| `required_approvals[]` | Procurement Agent — assembled from PAM-001 matched row |
| `estimated_timeline` | Procurement Agent — derived from matched approval path and matrix-supported blocker implications |
| `fast_track_eligible` | **Not Procurement-owned.** Passthrough from IT Security Agent (STEP-02); re-emitted in STEP-04 output contract only |

**Upstream consumption rule:** The Procurement Agent consumes `fast_track_eligible`, `integration_tier`, `data_classification`, and `security_followup_required` from STEP-02 and `dpa_required`, `dpa_blocker`, `nda_status`, `nda_blocker`, `trigger_rule_cited`, and `status` from STEP-03 as read-only authoritative inputs. It may not reinterpret or override these fields. If upstream outputs carry ESCALATED status, the Procurement Agent must reflect that constraint in its own status handling unless a STEP-04 BLOCKED condition takes precedence.

---

## 7. Behavioral Rules

### 7.1 DOs

- **DO** treat `fast_track_eligible` from STEP-02 and `dpa_blocker` / `nda_blocker` from STEP-03 as authoritative inputs. Do not re-derive them from questionnaire evidence.
- **DO** use `fast_track_eligible` as a routing input when applying PAM-001, but re-emit it unchanged from STEP-02 in the STEP-04 output contract.
- **DO** require at least one Procurement Approval Matrix row match before emitting a COMPLETE `approval_path`. If no matrix row covers the vendor/deal profile, escalate rather than assert a path.
- **DO** cite the specific PAM-001 matrix row (`row_id`, `version`, `approval_path_condition`) for every `approval_path` determination. Generic matrix references are not sufficient.
- **DO** use canonical field semantics from CC-001 §15 in all output fields and citations.
- **DO** write `status` as lowercase: `complete`, `escalated`, or `blocked`.
- **DO** reflect upstream ESCALATED conditions from STEP-03 in STEP-04 status handling when the Legal determination remains an unresolved human-decision constraint on the run, even if Procurement can still determine an approval path.
- **DO** include Tier 3 evidence (Slack threads) as SUPPLEMENTARY only, and only when it adds non-conflicting, non-redundant context beyond what Tier 1–2 sources provide.
- **DO** flag the specific missing field by canonical name from CC-001 §15 when a questionnaire vendor relationship field is absent. Do not issue a general disclaimer.

### 7.2 DON'Ts

- **DON'T** query any index endpoint independently. The Supervisor owns retrieval. If no bundle is provided, emit `blocked`.
- **DON'T** cite Tier 3 (Slack) evidence as a PRIMARY citation. These are SUPPLEMENTARY only.
- **DON'T** recalculate, reinterpret, or hard-override the upstream `fast_track_eligible` field from STEP-02.
- **DON'T** assert a COMPLETE `approval_path` when no PAM-001 matrix row matches the vendor/deal combination. Escalate instead.
- **DON'T** reinterpret or override the upstream `data_classification`, `dpa_required`, `dpa_blocker`, `nda_status`, or `nda_blocker` fields.
- **DON'T** allow Tier 3 evidence to elevate to PRIMARY citation status regardless of semantic similarity or content relevance.
- **DON'T** produce free-text narrative as your output. Return only the structured JSON output contract defined in §9.
- **DON'T** waive required approvals, modify approval path conditions, or adjust matrix-defined timelines based on stakeholder preference or informal context from Slack threads.
- **DON'T** consume upstream agent intermediate reasoning — only their final structured output objects are in scope.

---

## 8. Determination Rules

These are deterministic rules. The agent must apply them in order and may not override them through reasoning.

### 8.1 Rule Application Order

Apply the determination logic in this sequence:

1. Confirm upstream inputs: read `fast_track_eligible`, `integration_tier`, `data_classification`, `security_followup_required`, and `status` from STEP-02 output; read `dpa_required`, `dpa_blocker`, `nda_status`, `nda_blocker`, `trigger_rule_cited`, and `status` from STEP-03 output
2. Read vendor relationship fields from questionnaire: `vendor_class`, raw `contract_value_annual` normalized into canonical `deal_size`, `existing_nda_status`, `existing_msa`
3. Preserve `fast_track_eligible` exactly as received from STEP-02 for downstream emission
4. Evaluate PAM-001 rows against the authoritative upstream posture, vendor class, deal size, and blocker conditions
5. Determine `approval_path` and assemble `required_approvals[]`
6. Derive `estimated_timeline` from the matched approval path row and any active blocker implications supported by the matrix or routing rules
7. Derive terminal step `status` from the combination of determination outcomes and inherited upstream status constraints

This ordering is mandatory. `approval_path` and downstream fields must not be emitted before upstream inputs are confirmed.

### 8.2 Fast-Track Eligibility Passthrough

`fast_track_eligible` in STEP-04 is not a new determination. It is the authoritative STEP-02 value carried forward unchanged.

| Condition | STEP-04 handling of `fast_track_eligible` |
|---|---|
| STEP-02 output present and schema-valid | Re-emit `fast_track_eligible` exactly as provided by IT Security |
| STEP-02 output absent or schema-invalid | Bundle is inadmissible; emit `blocked` |
| Procurement matrix logic or Legal blockers suggest a slower path than the upstream fast-track flag | Use those constraints when determining `approval_path`, but do not alter the emitted `fast_track_eligible` field |

The Procurement Agent may use the upstream fast-track flag as a routing input when matching matrix rows, but it must not recalculate or rewrite the field.

### 8.3 Approval Path Derivation

The approval path is determined by applying PAM-001 rows to the authoritative vendor profile. The general routing logic is:

| Condition | `approval_path` |
|---|---|
| Upstream `fast_track_eligible = true` AND PAM-001 row matches fast-track conditions | `FAST_TRACK` |
| A PAM-001 row matches standard review conditions for the vendor profile and current blocker posture | `STANDARD` |
| No PAM-001 row covers the vendor/deal combination | Cannot determine — emit `escalated` |

A COMPLETE `approval_path` determination requires at least one explicitly cited PAM-001 row. The specific row match conditions (vendor class thresholds, deal size thresholds, blocker routing logic, and approval-path rules) are governed by PAM-001 and are not restated here. The agent must apply the matrix as delivered in the bundle.

### 8.4 Required Approvals Assembly

The `required_approvals[]` array is assembled from the matched PAM-001 row. Each entry must carry the approver role, domain, and estimated completion. The Procurement Agent does not independently assign approvers — the matrix row is the authoritative source.

If upstream blocking conditions are active (`dpa_blocker = true` or `nda_blocker = true`), those blockers are inherited workflow constraints that will appear in checklist-level outputs and audit handling. The Procurement Agent may reflect their routing implications when selecting the matrix row, but it does not own or re-derive the blocker flags.

### 8.5 Step Status Derivation

The Procurement Agent's terminal step status is derived from the combination of approval path evidence and inherited upstream determination constraints. Apply these conditions in the order shown:

| Condition | Emitted `status` |
|---|---|
| IT Security Agent output absent or schema-invalid | `blocked` |
| Legal Agent output absent or schema-invalid | `blocked` |
| Required questionnaire fields (`existing_nda_status`, `existing_msa`, `vendor_class`, raw `contract_value_annual` → canonical `deal_size`) absent | `blocked` |
| No PAM-001 row matches the vendor/deal combination | `escalated` — evidence insufficient for COMPLETE; approval path undefined in matrix |
| Tier 1 PAM-001 sources conflict on the same approval path question | `escalated` — conflicting authoritative procurement sources |
| Upstream STEP-03 output carries `status = escalated` and no blocked condition above has fired | `escalated` — approval path may still be determined, but the run inherits unresolved Legal escalation constraints |
| `approval_path` determined with at least one PAM-001 citation and all required upstream inputs present and confirmed | `complete` |

---

## 9. Output Contract

The agent must return a single schema-valid JSON object. No other output format is permitted.

```json
{
  "approval_path": "STANDARD | FAST_TRACK",
  "fast_track_eligible": false,
  "required_approvals": [
    {
      "approver": "string",
      "domain": "string",
      "status": "PENDING | CONFIRMED | WAIVED",
      "blocker": false,
      "estimated_completion": "string"
    }
  ],
  "estimated_timeline": "string",
  "policy_citations": [
    {
      "source_id": "PAM-001 | SLK-001",
      "version": "string",
      "chunk_id": "string",
      "row_id": "string",
      "approval_path_condition": "string",
      "citation_class": "PRIMARY | SUPPLEMENTARY"
    }
  ],
  "status": "complete | escalated | blocked"
}
```

> On a `blocked` run, the agent may emit a minimal object containing `status` and any available error or audit context. Non-status determination fields are required only on non-blocked runs.

> Escalation context — triggering condition, conflicting sources, and resolution owner — is captured in the append-only audit log per CC-001 §13.1 and the orchestration plan global audit rules. The `policy_citations` array on an `escalated` output must cite the matrix evidence gap or conflicting rows. The audit log is the authoritative escalation record.

### Output Field Constraints

| Field | Constraint |
|---|---|
| `approval_path` | Must be emitted on every non-blocked run when a path can be determined from PAM-001. Must be one of the two defined enum values: `STANDARD` or `FAST_TRACK`. May be absent or `null` on an escalated no-match run. |
| `fast_track_eligible` | Must be emitted on every non-blocked run. Must equal the authoritative STEP-02 value exactly. |
| `required_approvals[]` | Must be emitted on every non-blocked, non-escalated run. Must contain at least one entry when `approval_path` is COMPLETE. May be `[]` on escalated runs where no approval path is determined. |
| `estimated_timeline` | Must be emitted on every non-blocked run when a path is determined. |
| `policy_citations` | Must include at least one PRIMARY PAM-001 row citation when `approval_path` is COMPLETE. Tier 3 citations must be tagged `SUPPLEMENTARY`. `source_id` values for Procurement Agent citations are limited to `PAM-001` and `SLK-001` — upstream agent citations are not re-cited here. |
| `status` | Lowercase. One of `complete`, `escalated`, or `blocked`. If STEP-03 is escalated, STEP-04 inherits that unresolved constraint in status handling unless a blocked condition takes precedence. |

---

## 10. Status Determination

The authoritative status derivation logic and precedence ordering live in §8.5. The three terminal states and their top-level conditions are:

- **`blocked`** — required upstream agent output absent or schema-invalid, or required questionnaire fields absent (including absence of raw questionnaire field `contract_value_annual`, which maps to canonical `deal_size`)
- **`escalated`** — no PAM-001 row matches the vendor/deal combination, Tier 1 PAM-001 sources conflict, or unresolved upstream Legal escalation constrains the run
- **`complete`** — `approval_path` determined with at least one PAM-001 PRIMARY citation and all required upstream inputs confirmed

See §8.5 for the full precedence-ordered derivation table.

---

## 11. Provenance and Citation Requirements

Per CC-001 §14:

- Every `approval_path` determination must carry at least one PRIMARY PAM-001 citation with `source_id`, `version`, `row_id`, and `approval_path_condition`.
- No Tier 3 source may be cited as PRIMARY for any approval path determination.
- Upstream STEP-02 and STEP-03 agent outputs are authoritative structured inputs to STEP-04. When referenced, they are cited by `agent_id` and `pipeline_run_id` in the audit log — they are not re-cited by their original source IDs (ISP-001, DPA-TM-001) in Procurement's `policy_citations[]`. The PRIMARY evidentiary basis for Procurement's owned determinations remains PAM-001.
- If a questionnaire field is absent or ambiguous, name the specific field by canonical name from CC-001 §15 — do not issue a general disclaimer.
- Slack / meeting note citations must be tagged `citation_class: SUPPLEMENTARY`. They may never appear as PRIMARY. They must not be included when a Tier 1–2 source addresses the same point.

---

## 12. Exception Handling

| Condition | Required Behavior |
|---|---|
| Bundle is empty or missing | Emit `status: blocked`. Do not produce a determination. |
| IT Security Agent output absent or schema-invalid | Bundle is inadmissible. Emit `status: blocked`. Do not proceed. |
| Legal Agent output absent or schema-invalid | Bundle is inadmissible. Emit `status: blocked`. Do not proceed. |
| Legal Agent STEP-03 status is `ESCALATED` | Proceed with Procurement approval-path determination using the available Legal output fields. Emit `status: escalated` unless a blocked condition takes precedence. The Procurement Agent does not resolve Legal escalations. |
| `existing_nda_status`, `existing_msa`, `vendor_class`, or raw `contract_value_annual` (canonical `deal_size`) absent from questionnaire | Flag the specific missing field by canonical name. Emit `status: blocked`. |
| No PAM-001 row matches the vendor/deal combination | Emit `status: escalated`. Log no-matrix-match condition. Do not assert an `approval_path`. Resolution owner: Procurement Director. |
| Bundle contains evidence from a prohibited index | Log anomaly. Exclude the prohibited evidence from reasoning and citation. Continue only if the remaining bundle is still admissible; otherwise emit `status: blocked`. |
| Malformed or schema-invalid bundle | Emit `status: blocked`. Do not attempt to reason over partial input. |
| Two PAM-001 rows directly conflict on the same approval path question | Emit `status: escalated`. Cite both conflicting rows in `policy_citations`. Full escalation payload written to audit log. Resolution owner: Procurement Director. |
| Slack thread conflicts with PAM-001 determination | Suppress Slack thread per CC-001 §10 authority suppression rules. Log suppression. Proceed on Tier 1 evidence. |

---

## 13. Example Behavioral Outcomes

### Example A — Regulated vendor, standard approval path with unresolved Legal blocker (OptiChain scenario)

`data_classification = REGULATED`, `dpa_blocker = true`, `nda_blocker = true`, upstream `fast_track_eligible = false` (IT Security), Legal output is `status = escalated`, PAM-001 row matches standard path for vendor class and deal size:

- preserve `fast_track_eligible = false` exactly as received from STEP-02,
- determine `approval_path = STANDARD`,
- assemble `required_approvals[]` from PAM-001 row,
- cite PAM-001 row as PRIMARY,
- emit `status = escalated`.

> The Procurement Agent may still determine the correct approval path while inheriting STEP-03's unresolved Legal escalation constraint. This aligns with CC-001 §12.1: upstream ESCALATED status does not make the bundle inadmissible, but the approval-path result inherits the upstream constraint in downstream status handling.

### Example B — Clean low-risk vendor, fast-track eligible

`data_classification = UNREGULATED`, `dpa_required = false`, `dpa_blocker = false`, `nda_blocker = false`, upstream `fast_track_eligible = true`, PAM-001 row matches fast-track conditions:

- preserve `fast_track_eligible = true` exactly as received from STEP-02,
- determine `approval_path = FAST_TRACK`,
- assemble `required_approvals[]` from PAM-001 fast-track row,
- cite PAM-001 row as PRIMARY,
- emit `status = complete`.

### Example C — No matrix row matches vendor/deal profile

Vendor class and deal size combination is not covered by any PAM-001 row:

- do not assert an `approval_path`,
- emit `status = escalated`,
- log no-matrix-match condition,
- cite evidence of the unmatched profile in `policy_citations` alongside the retrieval gap,
- resolution owner: Procurement Director.

> Asserting an `approval_path` without matrix evidence would be silent failure. The correct behavior is escalation.

---

## 14. Critical Acceptance Checks

These are the must-pass checks for this spec. They belong here as implementation-critical acceptance checks, not as a full evaluation program.

| # | Constraint | Pass Condition |
|---|---|---|
| A-01 | `approval_path` backed by at least one Tier 1 PAM-001 matrix row when COMPLETE | `policy_citations` contains at least one PRIMARY PAM-001 entry with `row_id` |
| A-02 | STEP-02 ownership of `fast_track_eligible` is preserved | STEP-04 output echoes the authoritative STEP-02 `fast_track_eligible` value unchanged |
| A-03 | No Tier 3 source cited as PRIMARY | All Slack citations remain SUPPLEMENTARY |
| A-04 | No `approval_path` asserted when no PAM-001 row matches | Agent emits `escalated` rather than inferring a path from non-matrix evidence |
| A-05 | All required output fields present and structurally valid | Schema-valid JSON. The following fields must be non-null on every non-blocked run when a path is determined: `approval_path`, `fast_track_eligible`, `estimated_timeline`, `status`. `required_approvals[]` must contain at least one entry on COMPLETE runs. `policy_citations` must contain at least one PRIMARY entry on COMPLETE runs. |
| A-06 | Upstream `data_classification`, `dpa_blocker`, `nda_blocker`, and `fast_track_eligible` not re-derived or overridden | Procurement Agent output reflects upstream determinations without reinterpretation |
| A-07 | Upstream STEP-03 `escalated` status is inherited in STEP-04 status handling unless blocked takes precedence | Agent may still determine `approval_path`, but it does not emit `complete` while unresolved Legal escalation constraints remain active |

A fuller CSR / ISR evaluation matrix may be maintained in a separate evaluation artifact.

---

## 15. What This Agent Does Not Own

| Item | Governed By |
|---|---|
| Data classification and security posture | IT Security Agent (STEP-02) |
| `fast_track_eligible` determination | IT Security Agent (STEP-02) |
| DPA and NDA requirement determination | Legal Agent (STEP-03) |
| DPA blocker and NDA blocker flags | Legal Agent (STEP-03) |
| STEP-03 → STEP-04 execution order and gate sequencing | Design Doc / ORCH-PLAN-001 |
| Source authority hierarchy | CC-001 §5 |
| Retrieval routing and bundle assembly | Supervisor / ORCH-PLAN-001 STEP-04 |
| Output schema authority | Design Doc §10 |
| Checklist composition | Checklist Assembler (STEP-05) |
| DPA execution | Legal / General Counsel (human-owned; pipeline triggers but does not execute) |
| NDA execution | Procurement / Legal (human-owned; pipeline flags but does not execute) |
| Approval waiver authority | Human-owned; this pipeline classifies and routes but does not waive |

---

## Version Log

| Version | Date | Author | Change |
|---|---|---|---|
| 0.1 | 2026-04-10 | Engineering / IT Architecture | Initial draft. Agent identity, evidence bundle, index permissions, retrieval boundary, determination ownership, behavioral rules, determination logic (fast-track confirmation, approval path derivation, status derivation), output contract, provenance requirements, exception handling, example outcomes, and acceptance checks established. |
| 0.2 | 2026-04-12 | Engineering / IT Architecture | Cross-document integrity revision after direct review of Design Doc v0.9, CC-001 v1.4, ORCH-PLAN-001 v0.8, IT Security Agent Spec v0.7, and Legal Agent Spec v0.6. Changes: (1) removed outdated STEP-03/STEP-04 parallelism and reconciliation language; (2) aligned STEP-04 title and dependency model with sequential execution; (3) corrected ownership boundary so `fast_track_eligible` remains STEP-02-owned and is only re-emitted by STEP-04 as a passthrough field; (4) expanded STEP-04 bundle requirements to include the full schema-valid Legal output and current STEP-04 subquery fields; (5) rewrote determination logic to eliminate forbidden Procurement overrides of upstream fast-track eligibility; (6) updated status handling so unresolved upstream Legal escalation constrains STEP-04 status while still allowing approval-path determination when evidence is sufficient; (7) revised examples, acceptance checks, and version notes to match the current document hierarchy. |
| 0.3 | 2026-04-12 | Engineering / IT Architecture | Second-pass hierarchy integrity revision. Changes: (1) aligned questionnaire field handling with CC-001 §15 and ORCH-PLAN-001 STEP-04 by distinguishing raw `contract_value_annual` from canonical `deal_size`; (2) tightened STEP-04 bundle language so Slack notes remain specifically relevant / flagged supplementary context only; (3) propagated the field-normalization correction through admissibility rules, retrieval boundary, status handling, exception handling, and acceptance checks. |
| 0.4 | 2026-04-12 | Engineering / IT Architecture | Six integrity fixes after direct cross-document review against ORCH-PLAN-001 v0.8, Design Doc v0.9, CC-001 v1.4, IT Security Agent Spec v0.7, and Legal Agent Spec v0.6. |
| 0.5 | 2026-04-12 | Engineering / IT Architecture | Removed `routing_rationale` from the spec. The field appeared in ORCH-PLAN-001 v0.8 STEP-04 output contract but is absent from the Design Doc and was never logged as a deliberate addition. |
| 0.6 | 2026-04-13 | Engineering / IT Architecture | Demo simplification revision. (1) PROVISIONAL status removed — status field now `complete \| escalated \| blocked`; all `provisional` outcomes replaced with `escalated` or `blocked` as appropriate. (2) `resolved` renamed to `complete` throughout status values, output contract, gate states, and status derivation logic. (3) PVD-001 (Prior Vendor Decisions) removed — bundle item 5 (prior vendor decisions) deleted; `idx_precedents` removed from index access permissions; PVD-001 removed from retrieval boundary; `PVD-001` removed from `policy_citations` `source_id` enum; precedent citation rules removed from §11 provenance. (4) `executive_approval_required` field removed and `EXECUTIVE_APPROVAL` removed from `approval_path` enum — per ORCH-PLAN-001 v0.9; `approval_path` now `STANDARD \| FAST_TRACK` only; §2, §6, §8.3, §9, and §14 A-03 updated accordingly. (5) Tier 4 (Slack/notes) renumbered to Tier 3 throughout — all "Tier 4" references updated; "Tier 3 (precedent)" references removed with PVD-001. (6) Missing questionnaire fields now emit `blocked` rather than `provisional` in §3 and §8.5. (7) §8.5 status table simplified from 9 rows to 7 — PROVISIONAL rows removed. (8) Example C (executive approval) removed and replaced with no-matrix-match escalation scenario; former Example D renumbered to C. (9) A-08 (PROVISIONAL propagation) removed; A-09 (upstream escalation inheritance) renumbered to A-07. Aligned with Design Doc v4.0, CC-001 v1.4 (user-edited), and ORCH-PLAN-001 v0.9. |
