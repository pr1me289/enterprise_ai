# LLM Domain Agent Output Evaluation Checklist
## OptiChain Vendor Onboarding Pipeline — Pre-Live-Test Reference

**Purpose:** This checklist defines what a valid, passing output looks like for each domain agent before live API testing begins. Because LLM outputs are nondeterministic, every test run must be evaluated against the explicit input/output contracts established in the Design Doc, Context Contract, and Agent Specs — not just against whether the call succeeded. A passing run is one where every field below is present, non-null, correctly typed, semantically valid, and paired with an appropriate status signal.

**How to use this document:** After each agent test call, work through the agent's section top to bottom. Mark each item. A single failed required field is a test failure regardless of whether `status` looks correct. Record the raw response alongside the evaluation result for traceability.

---

## General Rules Applying to All Agents

These conditions must pass on every agent output before agent-specific checks begin.

- [ ] Response is a valid JSON object — no prose, no markdown code fences wrapping the output
- [ ] All required fields are present at the top level (no missing keys)
- [ ] No required field is `null`, an empty string, or an empty array where content is expected
- [ ] `status` field is present and is exactly one of: `complete`, `escalated`, `blocked` (lowercase; no other values permitted)
- [ ] No fields are hallucinated beyond the defined output contract (extra fields should be flagged and reviewed)
- [ ] If `status` is `escalated` or `blocked`, the output must still contain all required fields at their correct types — partial outputs do not excuse missing fields

---

## STEP-02 — IT Security Agent

**Input contract:** Vendor questionnaire (data classification fields: `integration_details.erp_type`, `data_classification_self_reported`, `regulated_data_types`) + relevant IT Security Policy sections (ISP-001).

### Required Output Fields

- [ ] **`data_classification`** — must be exactly one of: `REGULATED`, `UNREGULATED`, `AMBIGUOUS` (uppercase). No other values permitted. This field drives every downstream determination and must be present even when `status` is `escalated`.
- [ ] **`fast_track_eligible`** — must be a boolean (`true` or `false`). Must be `false` when `data_classification` is `REGULATED` or `AMBIGUOUS`. If `data_classification` is `UNREGULATED` and the agent returns `fast_track_eligible: true`, verify a policy citation supports this.
- [ ] **`policy_citations`** — must be a non-empty array. Each entry must include at minimum: `source_id` (`ISP-001`), `version`, `section_id`, `citation_class`. `section_id` and `citation_class` are the machine-to-machine provenance fields defined by the Agent Spec, ORCH-PLAN STEP-02 output contract, and CC-001 §7; do not confuse `section_id` with the Checklist Assembler's human-facing `section` label (Design Doc §10). `chunk_id` is expected per the same contracts and should be verified when present, but its absence is logged as a warning rather than a hard failure — this keeps the hard-fail set stable as chunking identifiers evolve. An empty array is a test failure — the agent must cite the specific ISP-001 clause(s) that support its classification determination.
- [ ] **`status`** — see general rules. Expected values by scenario:
  - Scenario 1 (clean vendor, export-only): `complete`
  - Scenario 2 (ERP ambiguity): `escalated`

### Semantic Validity Checks

- [ ] `data_classification` is consistent with the questionnaire inputs provided in the bundle — if `erp_type` is ambiguous, `AMBIGUOUS` is the only valid output; `REGULATED` or `UNREGULATED` would be a hallucination
- [ ] `fast_track_eligible: true` never co-occurs with `data_classification: REGULATED` or `data_classification: AMBIGUOUS`
- [ ] `policy_citations` reference ISP-001 — citations to any other source are a contract violation for this agent
- [ ] If `status: escalated`, verify the output includes enough signal (in `data_classification: AMBIGUOUS` or in a structured escalation note) for the Supervisor to construct the escalation payload

### Red Flags to Log

- `data_classification` value outside the three permitted strings
- `fast_track_eligible` as a string instead of a boolean
- `policy_citations` is an empty array or omitted entirely
- Agent cites DPA matrix or procurement matrix (outside its retrieval permissions)
- `status: complete` returned despite `data_classification: AMBIGUOUS`

---

## STEP-03 — Legal Agent

**Input contract:** IT Security Agent output (`data_classification`) + DPA Legal Trigger Matrix (DPA-TM-001) relevant rows + questionnaire EU personal data fields (`eu_personal_data_flag`, `data_subjects_eu`) + questionnaire NDA field (`existing_nda_status`) + ISP-001 §12.1.4 NDA clause.

### Required Output Fields

- [ ] **`dpa_required`** — must be a boolean. Determined by DPA trigger matrix row match against the vendor's EU data footprint. Must be present even if `false`.
- [ ] **`dpa_blocker`** — must be a boolean. Must be `true` only when `dpa_required: true` AND no executed DPA is confirmed on record. Must be `false` when `dpa_required: false` OR when `dpa_required: true` but an executed DPA is already confirmed.
- [ ] **`nda_status`** — must be exactly one of: `EXECUTED`, `PENDING`, `NOT_STARTED`, `UNKNOWN` (uppercase). This is the Legal Agent's normalized determination, not a raw passthrough of the questionnaire field.
- [ ] **`nda_blocker`** — must be a boolean. Must be `true` when `nda_status` is anything other than `EXECUTED`.
- [ ] **`trigger_rule_cited`** — must be a non-empty array when `dpa_required: true`. Each entry must include: `source_id` (`DPA-TM-001`), `version`, `row_id`, `trigger_condition`. If `dpa_required: false`, this may be an empty array — but the agent should still cite the absence determination.
- [ ] **`policy_citations`** — each entry must include at minimum: `source_id`, `version`, `citation_class`, plus the per-source-id primary identifier keys defined in Legal Agent Spec §11. ISP-001 is section-indexed and requires `chunk_id` + `section_id`. DPA-TM-001 is row-indexed and requires `row_id` + `trigger_condition`. A uniform required-keys tuple does not fit because the two sources have different primary identifiers — do not flatten them together. Do not confuse `section_id` with the Checklist Assembler's human-facing `section` label (Design Doc §10). Required to carry an ISP-001 §12.1.4 NDA clause entry when `nda_blocker: true` and at least one PRIMARY DPA-TM-001 entry when `dpa_required: true` (see semantic checks below).
- [ ] **`status`** — see general rules. Expected values by scenario:
  - Scenario 1 (no EU data, NDA executed): `complete`
  - Scenario 2 (EU data present, DPA required but not executed, NDA unconfirmed): `escalated` — per Agent Spec §14 A-07 (`dpa_blocker = true` → `status = escalated`; the agent must not emit `complete` when a DPA blocker is confirmed) and demo_scenario_02_escalated.md (STEP-03 is the first step in the scenario chain to emit `ESCALATED`)

### Semantic Validity Checks

- [ ] `dpa_required` is consistent with upstream `data_classification` — if IT Security returned `REGULATED`, the Legal Agent's DPA determination must reflect that data exposure
- [ ] `dpa_blocker` logic is internally consistent with `dpa_required` (see field definition above — these must not contradict each other)
- [ ] `nda_status` is a normalized output, not a raw copy of `existing_nda_status` from the questionnaire
- [ ] `trigger_rule_cited` entries reference DPA-TM-001 only — citations to ISP-001 for DPA trigger purposes are a contract violation (ISP-001 §12.1.4 is cited for NDA, not DPA)
- [ ] If `nda_blocker: true`, confirm the NDA clause (ISP-001 §12.1.4) is cited in `trigger_rule_cited` or in a separate `policy_citations` field per the agent spec

### Red Flags to Log

- `dpa_blocker: true` when `dpa_required: false`
- `nda_status` containing a value outside the four permitted strings
- `trigger_rule_cited` empty when `dpa_required: true`
- Agent cites procurement matrix or security policy for DPA trigger determination (outside its retrieval permissions for that purpose)
- `status: escalated` returned for an NDA blocker alone — the blocker is a workflow consequence of a resolved determination, not an evidence gap

---

## STEP-04 — Procurement Agent

**Input contract:** IT Security Agent full output (`fast_track_eligible`, `data_classification`, `policy_citations[]`) + Legal Agent full output (`dpa_required`, `dpa_blocker`, `nda_status`, `nda_blocker`) + questionnaire vendor relationship fields (`vendor_class`, `deal_size`, `existing_nda_status`) + Procurement Approval Matrix (PAM-001) relevant rows. Slack threads permitted only if specifically flagged as relevant.

### Required Output Fields

- [ ] **`approval_path`** — must be exactly one of: `STANDARD`, `FAST_TRACK`, `EXECUTIVE_APPROVAL` (uppercase). This is the primary determination of this step. Must be present and non-null in all non-blocked runs.
- [ ] **`fast_track_eligible`** — must be a boolean. This is a passthrough of the IT Security Agent's determination — the Procurement Agent does not re-derive it. Must match the upstream value.
- [ ] **`executive_approval_required`** — must be a boolean. Must be `true` when `approval_path: EXECUTIVE_APPROVAL`.
- [ ] **`required_approvals`** — must be a non-empty array on `status: complete` runs. Each entry must include at minimum: `approver`, `domain`. An empty array is a test failure on resolved runs.
- [ ] **`estimated_timeline`** — must be a non-null string describing the expected approval timeline. Cannot be omitted or empty on complete runs.
- [ ] **`policy_citations`** — must be a non-empty array on `status: complete` runs. Each entry must include at minimum: `source_id` (`PAM-001` or `SLK-001`), `version`, `row_id`, `approval_path_condition`, `citation_class`. These are the machine-to-machine provenance fields defined by the Agent Spec §9 output contract and §11 provenance, and §14 A-01 acceptance check; PAM-001 is row-indexed (not section-indexed), so `section_id` is not part of the Procurement contract — do not confuse Procurement `policy_citations[]` with Checklist Assembler `citations[]`. `chunk_id` is expected per the Agent Spec but is a soft expectation — its absence is logged as a warning rather than a hard failure. On `status: complete`, at least one entry must be `source_id: PAM-001` with `citation_class: PRIMARY` and a non-empty `row_id` per §14 A-01. Citations to ISP-001 or DPA-TM-001 are a contract violation (outside Procurement's retrieval lane per spec §5 and §11).
- [ ] **`status`** — see general rules. Expected values by scenario:
  - Scenario 1 (clean path): `complete`
  - Scenario 2 (upstream escalation present or no matrix row match): `escalated`

### Semantic Validity Checks

- [ ] `approval_path` is internally consistent with `fast_track_eligible` — if `fast_track_eligible: false`, `approval_path` must not be `FAST_TRACK`
- [ ] `approval_path` is internally consistent with upstream Legal output — if `dpa_blocker: true` or `nda_blocker: true`, verify the approval path correctly reflects the blocker condition
- [ ] `fast_track_eligible` matches the value passed in from the IT Security Agent output — the Procurement Agent must not override this field
- [ ] `executive_approval_required` is consistent with `approval_path` (must be `true` if and only if `approval_path: EXECUTIVE_APPROVAL`)
- [ ] `required_approvals` entries are plausible for the determined approval path — a FAST_TRACK path should have fewer required approvers than a STANDARD or EXECUTIVE path
- [ ] Agent does not cite DPA matrix or IT Security Policy as primary sources — its retrieval lane is PAM-001 and the upstream agent outputs

### Red Flags to Log

- `approval_path: FAST_TRACK` when `fast_track_eligible: false`
- `fast_track_eligible` value differs from STEP-02 output (re-derivation by Procurement Agent)
- `required_approvals` is empty on a `status: complete` run
- `estimated_timeline` omitted or null
- `executive_approval_required: false` when `approval_path: EXECUTIVE_APPROVAL`
- Agent cites DPA-TM-001 or ISP-001 as a primary determination source (outside its lane)

---

## STEP-05 — Checklist Assembler

**Input contract:** All domain agent structured outputs (IT Security, Legal, Procurement — all must be present and schema-valid) + audit log entries for the current run. Does not receive raw source documents.

### Required Output Fields

- [ ] **`pipeline_run_id`** — must be present and match the run ID used throughout the pipeline
- [ ] **`vendor_name`** — must be present (OptiChain in the demo)
- [ ] **`overall_status`** — must be exactly one of: `COMPLETE`, `ESCALATED`, `BLOCKED` (uppercase). Reflects the aggregate status of the pipeline run.
- [ ] **`data_classification`** — must be present; inherited and restated from STEP-02 output
- [ ] **`dpa_required`** — must be present; inherited from STEP-03 output
- [ ] **`dpa_blocker`** — must be present; inherited from STEP-03 output
- [ ] **`fast_track_eligible`** — must be present; inherited from STEP-02 output
- [ ] **`approval_path`** — must be present; inherited from STEP-04 output
- [ ] **`required_approvals`** — must be a non-empty array on `overall_status: COMPLETE` runs. Each entry should include `approver`, `domain`, `status`, `blocker` (if applicable), `estimated_completion`
- [ ] **`blockers`** — must be an array. May be empty if no blockers exist. Each blocker entry must include `blocker_type`, `description`, `resolution_owner`. Must not be empty if any upstream agent returned a blocker flag.
- [ ] **`citations`** — must be a non-empty array. Each citation entry must include `source_name`, `version`, `section`, `retrieval_timestamp`, `agent_id`. An empty citations array is a test failure — the checklist must be traceable.

### Semantic Validity Checks

- [ ] `overall_status` is consistent with upstream step statuses — cannot be `COMPLETE` if any upstream agent returned `escalated` or `blocked`
- [ ] All inherited field values match their upstream source exactly (no re-derivation or reinterpretation by the Checklist Assembler)
- [ ] `blockers` array is consistent with `dpa_blocker` and `nda_blocker` from Legal Agent output — if either is `true`, a corresponding entry must appear in `blockers`
- [ ] `citations` covers all three domain agent steps — an omission of any upstream agent's citations is a test failure
- [ ] `required_approvals` entries are consistent with STEP-04's `required_approvals` output

### Red Flags to Log

- `overall_status: COMPLETE` when any upstream agent returned `escalated` or `blocked`
- Any inherited field value contradicts its upstream source
- `blockers` array is empty when `dpa_blocker: true` or `nda_blocker: true` from Legal output
- `citations` array is empty or covers only one or two agents
- Checklist Assembler re-derives or re-interprets any domain determination rather than passing it through

---

## STEP-06 — Checkoff Agent

**Input contract:** Finalized checklist output (structured JSON from STEP-05) + stakeholder map + required approver list + escalation reasons (if any) + relevant domain agent determination summaries. No independent index queries permitted.

**Gate condition:** STEP-06 runs only when STEP-05 has reached `overall_status: COMPLETE`. If STEP-05 is `ESCALATED` or `BLOCKED`, STEP-06 must not be triggered.

### Required Output Conditions

- [ ] **Guidance documents are present** — the agent must produce at least one stakeholder-facing guidance document. An empty or null output is a test failure.
- [ ] **No re-derivation of upstream determinations** — the Checkoff Agent must not alter, reinterpret, or re-evaluate any determination from STEP-02 through STEP-05. Its role is facilitation and routing only.
- [ ] **Stakeholder routing is present** — the output must include routing or guidance specific to the required approvers identified in STEP-04/STEP-05, not generic boilerplate
- [ ] **Escalation reasons are surfaced if present** — if any upstream blockers exist in the checklist, the Checkoff Agent's guidance must address them explicitly
- [ ] **No raw source retrieval evidence** — the Checkoff Agent must not reference raw policy sections, matrix rows, or Slack threads directly. Its inputs are assembled outputs only; any evidence references must be traceable to the checklist, not to a source document.

### Semantic Validity Checks

- [ ] Guidance documents reference the correct vendor name and pipeline run
- [ ] Approver list in guidance matches `required_approvals` from the checklist
- [ ] If `blockers` were present in the checklist, they are clearly surfaced and assigned to their `resolution_owner`
- [ ] No new determinations are introduced — anything stated as a finding must be traceable to a prior step's output

### Red Flags to Log

- STEP-06 triggered when STEP-05 did not reach `COMPLETE`
- Guidance documents are empty or purely generic
- Agent introduces a new determination not present in any upstream output
- Agent cites a raw source document (ISP-001, DPA-TM-001, PAM-001) as if it retrieved it independently

---

## Status Signal Summary Table

Use this as a quick reference during test evaluation.

| Agent | Expected `complete` conditions | Expected `escalated` conditions | Expected `blocked` conditions |
|---|---|---|---|
| IT Security (STEP-02) | Unambiguous ERP type, clean classification | ERP type ambiguous; no policy section resolves the tier | Required questionnaire fields absent |
| Legal (STEP-03) | `dpa_required = false` OR (`dpa_required = true` AND executed DPA confirmed); NDA status normalized | `dpa_blocker = true` (DPA required but not executed) per spec §14 A-07; NDA clause (ISP-001 §12.1.4) unretrievable; Tier 1 conflict | Upstream IT Security output absent |
| Procurement (STEP-04) | Approval path determined; matrix row matched | No matrix row matches vendor/deal combination | Upstream IT Security or Legal output absent |
| Checklist Assembler (STEP-05) | All three domain outputs present and schema-valid | Any upstream agent returned `escalated` | Any upstream agent returned `blocked` or output is absent |
| Checkoff Agent (STEP-06) | Guidance documents produced; approvers routed | N/A — does not make determinations | STEP-05 did not reach `COMPLETE` |

---

## Notes for Test Execution

**Record every raw response.** Before evaluating, save the full raw JSON output from each agent call to `tests/recorded_responses/`. Evaluation happens against the saved response, not against a re-run.

**Do not re-run an agent to fix a failed evaluation.** If a field is missing or invalid, log the failure, record the response, and report it. Re-runs happen only after a deliberate code or prompt change, with explicit approval.

**Evaluate agents in step order.** STEP-02 must pass before STEP-03 is tested. Downstream agents depend on upstream outputs being schema-valid — testing out of order produces meaningless results.

**Distinguish between a model failure and a prompt failure.** If a required field is consistently absent across multiple runs, the system prompt (agent spec) likely does not instruct the model clearly enough on that field. If the field is sometimes present and sometimes not, it is a nondeterminism issue to address in the output instruction block.
