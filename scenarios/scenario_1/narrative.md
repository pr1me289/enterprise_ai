# Demo Scenario 1 — Clean Governed Completion

## Purpose of this scenario
Show that when the intake is complete and the evidence is sufficient, the pipeline moves step by step through governed retrieval, produces domain determinations, assembles a checklist, and ends in a clean `COMPLETE` state.

This is the “the system works as intended under normal conditions” path.

## Narrative
Lichen Manufacturing is evaluating OptiChain for supply-chain forecasting support. In this version of the case, OptiChain only consumes **exported, non-regulated operational data** and does **not** connect directly to ERP through a risky integration pattern. No EU personal data is involved. Legal finds no DPA trigger. Procurement finds a valid fast-track matrix row. The system completes the workflow and generates the final approval checklist plus stakeholder guidance.

## What this scenario proves
- sequential orchestration works
- supervisor-controlled retrieval works
- domain agents can reason over scoped bundles
- audit logging captures the run
- the system reaches `COMPLETE` without human intervention
- the final checklist and stakeholder guidance are useful outputs

## Recommended input facts

### Questionnaire facts
Use values like:
- `vendor_name = OptiChain`
- `integration_details.erp_type = EXPORT_ONLY`
- `integration_details.erp_system = SAP`
- `data_classification_self_reported = NON_REGULATED`
- `regulated_data_types = []`
- `eu_personal_data_flag = NO`
- `data_subjects_eu = NONE`
- `existing_nda_status = EXECUTED`
- `existing_msa = YES`
- `vendor_class = TIER_3`
- `contract_value_annual = 45000`

### Intended policy / matrix interpretation
- Security policy maps `EXPORT_ONLY` to low-risk integration tier
- No regulated data means `UNREGULATED`
- Fast-track is allowed for low-risk export-only vendor
- DPA matrix returns no applicable row requiring DPA
- Procurement matrix has a valid `FAST_TRACK` row for this vendor class / deal size

## Expected step-by-step results

### STEP-01 — Intake Validation
Result:
- questionnaire exists
- questionnaire complete
- no version conflict

Status:
- `COMPLETE`

Audit events:
- questionnaire existence checked
- completeness checked
- version conflict check logged
- STEP-01 status change logged

### STEP-02 — IT Security
Supervisor retrieves:
- questionnaire fields
- IT Security Policy ERP tier sections
- IT Security Policy classification sections
- IT Security Policy fast-track sections

Agent determines:
- `integration_type_normalized = EXPORT_ONLY`
- `integration_tier = TIER_3`
- `data_classification = UNREGULATED`
- `eu_personal_data_present = NO`
- `fast_track_eligible = true`
- `fast_track_rationale = ELIGIBLE_LOW_RISK`
- `security_followup_required = false`
- `required_security_actions = []`

Status:
- `complete`

Audit events:
- retrieval attempts
- admitted policy chunks
- security determination
- STEP-02 status change

### STEP-03 — Legal
Supervisor retrieves:
- STEP-02 `data_classification`
- questionnaire EU fields
- questionnaire NDA status
- DPA trigger matrix rows
- NDA clause from ISP-001

Agent determines:
- `dpa_required = false`
- `dpa_blocker = false`
- `nda_status = EXECUTED`
- `nda_blocker = false`

Status:
- `complete`

Audit events:
- matrix retrieval
- clause retrieval
- legal determination
- STEP-03 status change

### STEP-04 — Procurement
Supervisor retrieves:
- STEP-02 structured output
- STEP-03 structured output
- questionnaire vendor relationship fields
- procurement approval matrix rows

Agent determines:
- `approval_path = FAST_TRACK`
- `fast_track_eligible = true` passthrough
- `required_approvals = [...]` minimal fast-track set
- `estimated_timeline = short / fast-track timeline`

Status:
- `complete`

Audit events:
- procurement matrix retrieval
- matrix row match logged
- procurement determination
- STEP-04 status change

### STEP-05 — Checklist Assembler
Assembler produces:
- `overall_status = COMPLETE`
- checklist with no blockers
- citations rolled up from prior steps
- required approvals populated

Status:
- `COMPLETE`

Audit events:
- checklist assembly
- checklist status emission

### STEP-06 — Checkoff
Checkoff Agent runs because STEP-05 is `COMPLETE`.

Produces:
- stakeholder guidance documents
- one per relevant role
- mostly “complete your approvals” guidance, little or no blocker handling

Status:
- `complete`

Audit events:
- guidance generation
- terminal run completion

## Final UI outcome
Show:
- all steps green / complete
- final checklist
- approval path = `FAST_TRACK`
- no blockers
- stakeholder guidance documents generated

## Demo takeaway line
“When the intake is complete and the evidence is sufficient, the supervisor deterministically routes governed context to the right agents, collects auditable determinations, and completes onboarding assessment without open-ended searching or manual policy interpretation.”
