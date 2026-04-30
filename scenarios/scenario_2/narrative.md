# Demo Scenario 2 — Governed Escalation on First Escalated Status

## Purpose of this scenario
Show a governed onboarding run where the questionnaire is present and intake succeeds, the pipeline makes the determinations it can support from authoritative evidence, and then **halts at the first `ESCALATED` status** rather than continuing through unresolved legal and contractual blockers.

This scenario is built to match the current OptiChain mock corpus.

## Narrative
Lichen Manufacturing is evaluating OptiChain for an enterprise demand forecasting deployment. The formal questionnaire has already been submitted, so the pipeline is able to begin normal review. The evidence confirms that OptiChain will process EU employee scheduling data and that SAP-related operational data is in scope. It also shows that the ERP integration pattern cannot yet be confidently classified from questionnaire evidence alone.

The pipeline therefore does three things in sequence:

1. clears intake,
2. classifies the onboarding path as regulated and denies fast-track,
3. reaches Legal, where the first true `ESCALATED` status is emitted because a GDPR Art. 28 DPA is required but not yet executed, and NDA execution is still unconfirmed.

Per this demo version, the pipeline **returns and ends immediately at that first escalated status**.

---

## What this scenario proves
- the pipeline can read a complete formal intake artifact and begin normally
- the supervisor can retrieve from formal policy, matrix, questionnaire, and low-authority supplemental context
- the pipeline can preserve the difference between:
  - resolved determinations,
  - provisional technical ambiguity,
  - and escalated human-owned blockers
- the system does not continue blindly once a hard escalated condition is reached
- the first `ESCALATED` status can terminate the run safely with auditable reasoning

---

## Source-aligned input facts

### Questionnaire-backed facts
Use the current mock source values:
- `vendor_name = OptiChain`
- `procurement_reference = PRQ-2024-0047`
- `integration_details.erp_system = SAP S/4HANA`
- `integration_details.erp_type = ambiguous`
- `deployment_model = multi-tenant SaaS`
- `regulated_data_types` includes EU employee scheduling / shift data
- `eu_personal_data_flag = YES`
- `data_subjects_eu = EMPLOYEES`
- `existing_nda_status = IN_PROGRESS / PROVISIONAL`
- `existing_msa = NO`
- `vendor_class = Class A — Enterprise Platform`
- `contract_value_tcv = 675000`
- `contract_value_tier = T3`

### Key authoritative interpretations supported by the mock corpus
- The ERP integration description is **not** clear enough to assign a final tier from questionnaire evidence alone.
- EU employee personal data is in scope.
- A GDPR Art. 28 DPA is required.
- NDA execution is not yet confirmed.
- Fast-track is not allowed.
- Procurement classification is `STANDARD — ENHANCED` for a Class A / T3 vendor.

---

## Step-by-step pipeline chain

### STEP-01 — Intake Validation

#### What the Supervisor checks
- questionnaire existence
- questionnaire completeness
- questionnaire version validity
- procurement reference presence

#### Retrieved / inspected evidence
- OptiChain Vendor Questionnaire submission record

#### What the pipeline can support
The questionnaire is present, formally submitted, and sufficiently complete for downstream review to begin.

#### Determination
- questionnaire exists
- questionnaire complete
- no version conflict blocking review
- `vendor_name = OptiChain`
- `procurement_reference = PRQ-2024-0047`

#### Status
- `COMPLETE`

#### Audit events
- questionnaire existence check logged
- completeness check logged
- intake acceptance logged
- STEP-01 status transition logged

---

### STEP-02 — Onboarding Path Classification and IT Security Determination

#### What the Supervisor retrieves
- questionnaire integration architecture fields
- questionnaire data access / data classification fields
- IT Security Policy sections for:
  - data classification
  - ERP integration tier assignment
  - third-party security review
  - NDA / information-exchange constraint references as relevant context
- relevant Slack threads as **supplementary only**

#### How the governed pipeline interprets the evidence
The questionnaire confirms that OptiChain will access SAP-derived operational data and process EU employee scheduling data. That is sufficient to support a **regulated-path classification** and deny fast-track.

However, the ERP integration description remains ambiguous. The questionnaire says there is no persistent SAP session, but also says a lightweight extraction agent may operate with service account credentials depending on configuration. That is not enough to confidently assign the ERP integration tier.

The Slack thread mentioning a “nightly export” is not allowed to override this ambiguity because Slack is low-authority supplemental context only.

#### Determination
- `integration_type_normalized = AMBIGUOUS`
- `integration_tier = UNCLASSIFIED_PENDING_REVIEW`
- `data_classification = REGULATED`
- `eu_personal_data_present = YES`
- `fast_track_eligible = false`
- `fast_track_rationale = NOT_ELIGIBLE`
- `security_followup_required = true`
- `required_security_actions = [request architecture diagram, confirm credential model, assign ERP integration tier]`

#### Status
- `COMPLETE` for the step’s supported classification outputs

#### Important note on semantics
This step does **not** produce the first `ESCALATED` status in this scenario file. It produces a valid governed output object while preserving the ERP tier as provisional / unclassified pending IT Security review. The technical ambiguity is recorded, but the pipeline continues because the first explicit escalated condition in the current source set is emitted at Legal.

#### Audit events
- retrieval attempts logged
- admitted questionnaire sections logged
- admitted policy sections logged
- low-authority Slack use logged as supplementary
- irrelevant Slack thread excluded
- security determination logged
- provisional ERP tier status logged
- STEP-02 status transition logged

---

### STEP-03 — Legal and Compliance Trigger Determination

#### What the Supervisor retrieves
- STEP-02 structured output
- questionnaire EU personal data fields
- questionnaire NDA status fields
- DPA Legal Trigger Matrix rows relevant to EU personal data processing
- IT Security Policy clause governing NDA execution before information exchange
- supplementary Slack thread confirming no executed NDA is on file

#### How the governed pipeline interprets the evidence
At this point, the evidence is sufficient for Legal to make two formal determinations:

1. **A GDPR Art. 28 DPA is required** because OptiChain will process personal data of EU-based Lichen employees.
2. **NDA execution is still unconfirmed** because the questionnaire states the NDA is still in progress and internal review confirms there is no countersigned NDA on file.

Unlike the ERP tier issue, the DPA issue is not merely unresolved technical classification. It is a human-owned legal blocker. The current source set explicitly treats the unexecuted DPA as a hard blocker and the unconfirmed NDA as an open blocking condition for information exchange.

#### Determination
- `dpa_required = true`
- `dpa_blocker = true`
- `nda_status = PROVISIONAL / UNCONFIRMED`
- `nda_blocker = true`
- `legal_owner = General Counsel / Privacy Team`
- `procurement_legal_owner_for_nda = Procurement / Legal`

#### Status
- `ESCALATED`

#### Why this is the first escalated status
This is the first step in the chain where the current authoritative source set emits a true escalated condition rather than a resolved determination or provisional technical ambiguity. Legal cannot clear the run because:
- the DPA is mandatory and not yet executed,
- NDA execution is not yet confirmed,
- information exchange may not proceed.

#### Audit events
- DPA matrix retrieval logged
- NDA clause retrieval logged
- legal determination logged
- escalation payload logged with:
  - triggering step = STEP-03
  - reason = DPA required but not executed; NDA unconfirmed
  - owner = General Counsel / Privacy Team; Procurement / Legal
  - minimum evidence / action required to resolve = execute GDPR Art. 28 DPA and confirm fully executed NDA
- STEP-03 status transition logged

---

## Scenario termination point
This demo scenario **ends here**.

Because STEP-03 is the **first instance of `ESCALATED`**, the pipeline returns immediately and does not continue to:
- STEP-04 Procurement Approval Path Routing
- STEP-05 Approval Checklist Generation
- STEP-06 Stakeholder Guidance and Checkoff Support

Those downstream stages may still exist in the broader architecture, but they are intentionally out of scope for this scenario file because this version is designed to stop on the first escalated status.

---

## Final UI outcome
Show:
- STEP-01 complete
- STEP-02 complete
- STEP-03 escalated
- STEP-04 to STEP-06 not executed due to early return on escalation
- escalation panel containing:
  - **Status:** ESCALATED
  - **Step:** STEP-03 Legal and Compliance Trigger Determination
  - **Reason:** GDPR Art. 28 DPA is required but not yet executed; NDA execution remains unconfirmed
  - **What was successfully determined before halt:** regulated-path classification, EU personal data present, fast-track ineligible, ERP tier still pending IT Security classification
  - **Resolution owners:** General Counsel / Privacy Team; Procurement / Legal
  - **Required human action:** execute DPA and confirm fully executed NDA before the run may proceed further

---

## Demo takeaway line
“When formal intake exists, the governed pipeline can still make scoped, auditable determinations before halting at the first true escalated condition. It preserves the distinction between provisional technical ambiguity and human-owned legal blockers, then stops safely instead of continuing through unresolved compliance requirements.”
