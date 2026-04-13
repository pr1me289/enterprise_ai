# Demo Scenario 2 — Two-Run Governed Failure Story: BLOCKED Intake, Then Safe Escalation

## Purpose of this scenario
Show two different governed failure behaviors in sequence:

1. The pipeline **blocks immediately** when required intake is absent.
2. After the intake is submitted and a new run begins, the pipeline proceeds until it encounters an ambiguity it cannot safely resolve, then **escalates** rather than guessing.

This is the strongest “safe failure” demo path because it shows both:
- hard intake gating
- governed escalation over silent inference

---

## Narrative

Lichen Manufacturing is evaluating OptiChain for a richer deployment. On the first attempt, Procurement has **not yet submitted the vendor questionnaire**, so the pipeline cannot even begin domain review. The Supervisor blocks the run at STEP-01 and records the missing intake requirement.

Procurement then submits the questionnaire and a **new run** begins. This time intake succeeds, but the questionnaire still describes the ERP integration pattern ambiguously while also indicating EU employee scheduling data. Security can confidently determine that EU personal data is involved and that fast-track is not allowed, but it cannot confidently assign the integration tier. The pipeline therefore escalates at STEP-02 and stops safely before downstream completion.

---

## What this scenario proves
- the system blocks immediately when required intake is absent
- blocked runs are preserved rather than silently bypassed
- a corrected or newly submitted intake should trigger a **new run**, not mutate the old one
- the system does not silently infer through ambiguity
- escalation is governed, not ad hoc
- audit logs preserve reason, ownership, and what evidence would be needed to proceed
- the supervisor halts the pipeline safely
- the architecture respects “escalation over silent inference”

---

# Run 1 — STEP-01 BLOCKED Because Questionnaire Is Missing

## Purpose of Run 1
Show that the pipeline refuses to proceed when the formal intake artifact is absent.

## Input condition
No questionnaire is present for the run.

### Questionnaire facts
There is **no submitted questionnaire** available to the Supervisor in this run.

---

## Expected step-by-step results

### STEP-01 — Intake Validation
Supervisor checks:
- questionnaire existence
- questionnaire completeness
- version conflict

Result:
- questionnaire does not exist
- completeness check cannot proceed
- version conflict check cannot proceed

Status:
- `BLOCKED`

Why blocked:
- the required intake artifact is absent
- there is nothing to reason over
- downstream steps must not begin

Audit events:
- questionnaire existence check logged
- blocked condition logged
- resolution owner logged as Procurement
- run halt logged

### Downstream behavior
The Supervisor halts the run after STEP-01.

STEP-02 through STEP-06 do **not** execute in Run 1.

---

## Final UI outcome for Run 1
Show:
- STEP-01 blocked
- STEP-02 to STEP-06 not executed
- blocked panel containing:
  - reason
  - owner
  - required next action

Suggested panel language:
- **Status:** BLOCKED
- **Step:** STEP-01 Intake Validation
- **Reason:** Vendor questionnaire not submitted
- **Resolution owner:** Procurement
- **Required human action:** Submit formal vendor questionnaire before pipeline may proceed

## Demo takeaway line for Run 1
“The pipeline does not begin domain reasoning until required intake exists. Missing intake is a governed stop condition, not an invitation for the system to improvise.”

---

# Run 2 — Questionnaire Submitted, Then STEP-02 Safely ESCALATES

## Purpose of Run 2
Show that after Procurement submits the questionnaire and a new run begins, the pipeline can proceed through intake and still halt safely later when a governed ambiguity appears.

## Input condition
A questionnaire is now present, but the ERP integration description is ambiguous.

### Questionnaire facts
Use values like:
- `vendor_name = OptiChain`
- `integration_details.erp_type = unclear / mixed description`
- `integration_details.erp_system = SAP`
- `data_classification_self_reported = LIMITED_OPERATIONAL_DATA`
- `regulated_data_types = ["employee scheduling data"]`
- `eu_personal_data_flag = YES`
- `data_subjects_eu = EMPLOYEES`
- `existing_nda_status = PENDING`
- `existing_msa = NO`
- `vendor_class = TIER_2`
- `contract_value_annual = 180000`

The key is that the questionnaire should support:
- confident EU personal data presence
- ambiguous integration pattern

---

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
- ERP tier table
- security classification sections
- fast-track disqualification sections

Agent determines:
- `integration_type_normalized = AMBIGUOUS`
- `integration_tier = UNCLASSIFIED_PENDING_REVIEW`
- `eu_personal_data_present = YES`
- `data_classification = REGULATED`
- `fast_track_eligible = false`
- `fast_track_rationale = DISALLOWED_AMBIGUOUS_SCOPE`
- `security_followup_required = true`
- `required_security_actions = [...]`

Status:
- `escalated`

Why escalated:
- evidence is sufficient to classify as `REGULATED`
- evidence is not sufficient to confidently assign integration tier
- human IT Security review is required

Audit events:
- all retrievals logged
- ambiguity in integration type logged
- security determination logged
- escalation payload logged with:
  - evidence condition
  - triggering step
  - relevant evidence references
  - resolution owner = IT Security
  - minimum evidence to resolve = clarified integration pattern / architecture confirmation

### Downstream behavior
The Supervisor halts the run after STEP-02.

STEP-03 through STEP-06 do **not** proceed in Run 2.

This is cleaner than trying to continue downstream while carrying unresolved security ambiguity.

---

## Final UI outcome for Run 2
Show:
- STEP-01 complete
- STEP-02 escalated
- STEP-03 to STEP-06 halted / not executed
- escalation panel containing:
  - reason
  - owner
  - required next action
  - evidence references

Suggested panel language:
- **Status:** ESCALATED
- **Step:** STEP-02 IT Security
- **Reason:** Integration pattern cannot be confidently classified from available intake evidence
- **What was still determined:** EU personal data present; data classification = REGULATED; fast-track not allowed
- **Resolution owner:** IT Security
- **Required human action:** Confirm architecture/integration method for ERP interaction before pipeline may proceed

## Demo takeaway line for Run 2
“The system does not guess through ambiguity. It makes the determinations it can support, records the escalation with ownership and evidence, and halts safely rather than producing a misleading downstream result.”

---

# Overall demo takeaway for Scenario 2

Scenario 2 should be presented as a **two-attempt governed failure story**:

1. **Attempt 1 / Run 1:** blocked immediately because required intake is missing
2. **Attempt 2 / Run 2:** intake is supplied, but the system later escalates because the security evidence is ambiguous

This gives the audience two clear enterprise messages:

- the pipeline is governed from the very first intake gate
- later ambiguity is surfaced explicitly instead of being hidden behind model guesswork

It also reinforces an important architectural principle for the demo:

> A corrected or newly submitted intake should produce a **new run**.  
> The original blocked run remains preserved for auditability.
