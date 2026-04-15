r# Agent Bundle Integrity Checklist for Coding Agent

## Purpose

Use this checklist to verify that the supervisor is assembling the correct context bundle for each step and each assigned agent.

This checklist is derived from the locked governing documents in this precedence order:

1. Supervisor Orchestration Plan — runtime sequencing, subqueries, bundle assembly priority, and gate behavior
2. Context Contract — retrieval lanes, endpoint permissions, authority hierarchy, and minimum bundle composition
3. Design Doc — agent input/output contracts, role-to-source access, and per-agent composition rules

This checklist is intended to validate bundle integrity in the deterministic test harness before live LLM-backed agents are introduced.

---

## Global Rules That Apply to Every Bundle

The supervisor must enforce the following for every bundle:

- Only sources on the locked source manifest may be used.
- Each source must be retrieved through its designated retrieval lane.
- Endpoint permissions must be enforced per agent.
- Higher-authority evidence overrides lower-authority evidence.
- Slack / meeting notes are low-authority supplemental context and may never be primary evidence.
- The questionnaire is direct structured access, not semantic retrieval.
- Matrix rows are retrieved through the indexed hybrid lane as row-preserved chunks, not through a separate structured-lookup backend.
- Checklist / pipeline state / audit log are runtime state objects, not indexed evidence sources. fileciteturn18file1 fileciteturn18file0 fileciteturn18file2

---

## Canonical Source List

The coding agent should expect only these run-scoped source documents as primary evidence inputs:

- `VQ-OC-001` — OptiChain Vendor Questionnaire
- `ISP-001` — IT Security Policy v4.2
- `DPA-TM-001` — DPA Legal Trigger Matrix v2.1
- `PAM-001` — Procurement Approval Matrix v3.0
- `SLK-001` — Slack / Meeting Thread Notes

The following are not primary indexed evidence sources:

- checklist output
- pipeline state
- audit log
- assembled prior agent outputs

These are runtime state objects used downstream, not raw retrieval sources. fileciteturn18file1

---

## Retrieval Lane Expectations by Source

The coding agent should verify:

- `VQ-OC-001` → `DIRECT_STRUCTURED`
- `ISP-001` → `INDEXED_HYBRID`
- `DPA-TM-001` → `INDEXED_HYBRID` row-targeted
- `PAM-001` → `INDEXED_HYBRID` row-targeted
- `SLK-001` → `INDEXED_HYBRID`
- checklist / pipeline state / audit log → `NON_RETRIEVAL` / pipeline state read

If any step retrieves these through the wrong lane, fail the test. fileciteturn18file1 fileciteturn18file2

---

## Endpoint Permission Expectations

The coding agent should verify the following source-access boundaries:

### IT Security Agent
Allowed:
- `vq_direct_access` — full
- `idx_security_policy` — full

Not allowed:
- `idx_dpa_matrix`
- `idx_procurement_matrix`
- `idx_slack_notes`

### Legal Agent
Allowed:
- `vq_direct_access` — full
- `idx_dpa_matrix` — full
- `idx_security_policy` — read-only reference use

Not allowed:
- `idx_procurement_matrix`
- `idx_slack_notes`

### Procurement Agent
Allowed:
- `vq_direct_access` — full
- `idx_procurement_matrix` — full
- `idx_security_policy` — read-only reference use
- `idx_slack_notes` — procurement-scoped only

Not allowed:
- `idx_dpa_matrix`

### Checklist Assembler
Allowed:
- no raw index access
- may read prior structured outputs and audit log only

### Checkoff Agent
Allowed:
- no raw index access
- downstream-only consumption of finalized checklist, stakeholder routing metadata, required approver list, escalation reasons, and domain summaries

If the Checkoff Agent issues any index query, fail closed and log it. fileciteturn18file1 fileciteturn18file0 fileciteturn18file2

---

## STEP-01 — Intake Validation

## Assigned component
Supervisor only

## Expected bundle / evidence inputs
This is not a domain-agent bundle. It is a supervisor-controlled intake check.

The supervisor should read only:

- `VQ-OC-001` via direct structured access

It should check:

- questionnaire exists
- questionnaire is complete
- no version conflict detected

## Documents expected
- OptiChain Vendor Questionnaire (`VQ-OC-001`) only

## Documents not expected
- IT Security Policy
- DPA Matrix
- Procurement Matrix
- Slack threads
- prior agent outputs
- audit log
- stakeholder map

If any of those appear in STEP-01 intake validation, fail the test. fileciteturn18file2

---

## STEP-02 — IT Security Agent Bundle

## Assigned agent
IT Security Agent

## Minimum documents expected in the bundle
The IT Security Agent should receive:

1. OptiChain Vendor Questionnaire (`VQ-OC-001`)
   - specifically the questionnaire data classification and integration fields required for the security determination

2. IT Security Policy (`ISP-001`)
   - relevant policy sections only
   - full document should not be passed wholesale if the system is subquery-based

3. Risk classification / ERP integration tier policy evidence from `ISP-001`
   - delivered as relevant section chunks from the policy index

## Documents allowed but not required
- none beyond the two above under the locked architecture

## Documents not expected
- DPA Legal Trigger Matrix
- Procurement Approval Matrix
- Slack threads
- Legal output
- Procurement output
- audit log
- stakeholder map

## Notes for the coding agent
The Design Doc says the IT Security Agent input is the vendor questionnaire plus IT Security Policy. The per-agent budget rule further narrows this to questionnaire data fields plus relevant IT Security Policy sections, excluding supplementary context when constrained. The role-to-source matrix also denies IT Security access to Slack, DPA, and procurement matrix endpoints. fileciteturn18file0

## Pass criteria
The STEP-02 bundle passes only if it contains:
- required questionnaire fields
- relevant `ISP-001` chunks
- no forbidden sources

---

## STEP-03 — Legal Agent Bundle

## Assigned agent
Legal Agent

## Minimum documents expected in the bundle
The Legal Agent should receive:

1. IT Security Agent output
   - specifically at minimum `data_classification`
   - the orchestration plan later also expects legal structured output to include policy citations downstream, so preserve provenance

2. DPA Legal Trigger Matrix (`DPA-TM-001`)
   - relevant row-targeted chunks only

3. OptiChain Vendor Questionnaire (`VQ-OC-001`)
   - `eu_personal_data_flag`
   - `data_subjects_eu`
   - `existing_nda_status`

4. IT Security Policy (`ISP-001`)
   - specifically the NDA clause chunk at `§12.1.4`

## Documents allowed but not required
- only the above under the current governing docs

## Documents not expected
- Procurement Approval Matrix
- Slack threads
- Procurement output
- audit log
- stakeholder map

## Notes for the coding agent
The Design Doc explicitly defines the Legal Agent input as IT Security output (`data_classification`) + DPA trigger matrix + questionnaire NDA field + questionnaire EU personal data fields + `ISP-001 §12.1.4` NDA clause. The per-agent budget rule says the same, and the orchestration-plan revision history explicitly notes that the legal bundle was expanded to include NDA inputs and policy citations. fileciteturn18file0 fileciteturn17file6 fileciteturn17file19

## Pass criteria
The STEP-03 bundle passes only if it contains:
- upstream STEP-02 security output
- relevant `DPA-TM-001` row chunks
- required questionnaire legal fields
- `ISP-001 §12.1.4` NDA clause chunk
- no procurement matrix
- no Slack threads

---

## STEP-04 — Procurement Agent Bundle

## Assigned agent
Procurement Agent

## Minimum documents expected in the bundle
The Procurement Agent should receive:

1. IT Security Agent full output
   - `fast_track_eligible`
   - `data_classification`
   - `policy_citations[]`

2. Legal Agent full output
   - `dpa_required`
   - `dpa_blocker`
   - `nda_status`
   - `nda_blocker`

3. OptiChain Vendor Questionnaire (`VQ-OC-001`)
   - vendor relationship and procurement fields, including:
     - `vendor_class`
     - `deal_size`
     - `existing_nda_status`

4. Procurement Approval Matrix (`PAM-001`)
   - relevant row-targeted chunks only

## Documents allowed conditionally
5. Procurement-scoped Slack / meeting notes (`SLK-001`)
   - only if specifically flagged or conditionally included by the orchestration plan
   - only if non-conflicting with Tier 1–2 evidence
   - supplementary only
   - never primary evidence

## Documents not expected
- DPA Matrix
- raw IT Security Policy chunks unless narrowly included as reference support
- audit log
- stakeholder map

## Notes for the coding agent
The Design Doc defines the Procurement Agent input as IT Security full output + Legal full output + questionnaire vendor relationship fields + procurement approval matrix. The per-agent budget rule says the same and allows procurement-scoped prior relationship context, with Slack excluded unless specifically flagged. The orchestration plan also defines a conditional procurement Slack subquery with authority suppression if it conflicts with higher-tier evidence. fileciteturn18file0 fileciteturn17file6 fileciteturn17file12

## Pass criteria
The STEP-04 bundle passes only if it contains:
- full STEP-02 output
- full STEP-03 output
- relevant `PAM-001` rows
- required procurement questionnaire fields
- optional Slack only when conditionally included and properly marked supplementary

---

## STEP-05 — Checklist Assembler Bundle

## Assigned agent
Checklist Assembler

## Minimum documents expected in the bundle
The Checklist Assembler should receive only runtime-assembled downstream inputs:

1. STEP-02 IT Security structured output
2. STEP-03 Legal structured output
3. STEP-04 Procurement structured output
4. audit log entries for the current pipeline run
5. final status signals from upstream steps

## Documents explicitly not expected
- Vendor Questionnaire raw document
- IT Security Policy raw chunks
- DPA Matrix raw chunks
- Procurement Matrix raw chunks
- Slack raw chunks
- Stakeholder Map

## Notes for the coding agent
The Design Doc says the Checklist Assembler input is previous domain agent outputs plus audit log. The orchestration plan is even stricter: bundle assembly priority is all domain agent structured outputs first, audit log entries second, and raw source documents are excluded entirely. fileciteturn18file0 fileciteturn17file12

## Pass criteria
The STEP-05 bundle passes only if it contains:
- no raw evidence documents
- only structured upstream outputs
- audit log entries
- status signals needed to generate the final checklist

---

## STEP-06 — Checkoff Agent Bundle

## Assigned agent
Checkoff Agent

## Minimum documents expected in the bundle
The Checkoff Agent should receive only downstream assembled materials:

1. finalized checklist output from STEP-05
2. stakeholder map / stakeholder role-to-guidance map
3. required approver list
4. required security actions from STEP-02
5. escalation reasons and resolution owners, if any
6. domain agent determination summaries
   - structured summaries only

## Documents explicitly not expected
- Vendor Questionnaire raw document
- IT Security Policy raw chunks
- DPA Matrix raw chunks
- Procurement Matrix raw chunks
- Slack raw chunks
- any raw index retrieval results

## Notes for the coding agent
The Design Doc says the Checkoff Agent input is all domain agent outputs plus stakeholder map. The per-agent budget section sharpens this to finalized checklist output + stakeholder map + required approver list + escalation reasons + relevant domain summaries, with no raw source retrieval. The orchestration plan explicitly prohibits any index query by the Checkoff Agent and defines the STEP-06 bundle assembly priority accordingly. fileciteturn18file0 fileciteturn17file6 fileciteturn17file16 fileciteturn18file1

## Pass criteria
The STEP-06 bundle passes only if it contains:
- finalized checklist
- stakeholder routing metadata
- approver list
- downstream structured summaries
- no raw retrieved evidence

---

## Compact Step-by-Step Checklist

Use this as the quick test checklist.

### STEP-01
Expected:
- `VQ-OC-001` only

Forbidden:
- `ISP-001`
- `DPA-TM-001`
- `PAM-001`
- `SLK-001`

### STEP-02 — IT Security
Expected:
- `VQ-OC-001`
- relevant `ISP-001` chunks

Forbidden:
- `DPA-TM-001`
- `PAM-001`
- `SLK-001`

### STEP-03 — Legal
Expected:
- STEP-02 output
- relevant `DPA-TM-001` rows
- required `VQ-OC-001` legal fields
- `ISP-001 §12.1.4` NDA clause chunk

Forbidden:
- `PAM-001`
- `SLK-001`

### STEP-04 — Procurement
Expected:
- STEP-02 full output
- STEP-03 full output
- required `VQ-OC-001` procurement fields
- relevant `PAM-001` rows
- optional procurement-scoped `SLK-001` supplementary chunks only when explicitly flagged

Forbidden:
- `DPA-TM-001`

### STEP-05 — Checklist Assembler
Expected:
- STEP-02 output
- STEP-03 output
- STEP-04 output
- audit log

Forbidden:
- all raw source documents

### STEP-06 — Checkoff
Expected:
- finalized STEP-05 checklist
- stakeholder map
- required approver list
- required security actions
- escalation reasons if any
- domain determination summaries

Forbidden:
- all raw source documents
- all index queries

---

## Final Instruction to Coding Agent

For each test run, validate each step bundle against this checklist before the mock step handler executes.

If any forbidden document appears in a bundle, fail the test.

If any required document is missing from a bundle, fail the test.

If a downstream-only step attempts raw retrieval, fail the test.

The point of this checklist is not just to check whether the pipeline runs. It is to verify that the supervisor is enforcing the governed context design exactly as specified in the Design Doc, Context Contract, and Orchestration Plan.
