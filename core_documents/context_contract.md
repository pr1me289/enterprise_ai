+----------------------------------------------------------+------------------------------------------------------------------------------------------------------------+
| **LICHEN MANUFACTURING**                                 |                                                                                                            |
|                                                          |                                                                                                            |
| AI-Assisted Vendor Onboarding Pipeline                   |                                                                                                            |
|                                                          |                                                                                                            |
| **Context Contract**                                     |                                                                                                            |
|                                                          |                                                                                                            |
| *Illustrated with OptiChain as the Onboarding Candidate* |                                                                                                            |
+==========================================================+============================================================================================================+
| **DOCUMENT ID**                                          | **DOCUMENT HIERARCHY**                                                                                     |
|                                                          |                                                                                                            |
| **CC-001**                                               | PRD                                                                                                        |
|                                                          |                                                                                                            |
| **STATUS**                                               | Design Doc                                                                                                 |
|                                                          |                                                                                                            |
| **DRAFT v1.4**                                           | **► Context Contract ◄**                                                                                   |
|                                                          |                                                                                                            |
| **OWNER**                                                | Agent Spec                                                                                                 |
|                                                          |                                                                                                            |
| IT Architecture / Legal / Procurement                    | **CONTRACT APPLIES TO**                                                                                    |
|                                                          |                                                                                                            |
| **LAST UPDATED**                                         | OptiChain vendor onboarding pipeline --- all agents and retrieval operations within a single pipeline run. |
|                                                          |                                                                                                            |
| April 7, 2026                                            |                                                                                                            |
+----------------------------------------------------------+------------------------------------------------------------------------------------------------------------+

*This Context Contract governs source authority, retrieval method, provenance requirements, evidence admissibility, conflict resolution, and audit triggers for the OptiChain vendor onboarding pipeline at Lichen Manufacturing. It governs retrieval, not agent reasoning or pipeline step-control. Pipeline gate logic lives in the Design Doc. Behavioral rules live in the Agent Spec.*

# 1. Purpose & Scope

This Context Contract governs all retrieval operations, source access, evidence handling, provenance requirements, and conflict resolution for the AI-assisted vendor onboarding pipeline at Lichen Manufacturing. It is the authoritative reference for which sources agents are permitted to access, how evidence must be structured before downstream use, and what triggers escalation or provisional status at the evidence layer. This document must be finalized and locked before orchestration is built. Pipeline step-control behavior (execution graph, gate logic, routing decisions) is governed by the Design Doc. Agent behavioral rules (DOs, DON'Ts, output format enforcement) are governed by the Agent Spec.

  ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
  **GOVERNANCE BOUNDARY:** This document governs source admissibility, evidence sufficiency, provenance, retrieval permissions, freshness, conflict handling, and audit triggers. It does not govern pipeline step sequencing, agent behavioral rules, or output schema definitions. Those belong in the Design Doc and Agent Spec respectively.
  ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

  ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

## 1.1 Executive Navigation

Readers who need a quick orientation should read these sections first:

  --------------------------------------------------------------------------------------------------------------------------------------------------
  **§**   **SECTION**                                        **WHY IT MATTERS**
  ------- -------------------------------------------------- ---------------------------------------------------------------------------------------
  §2      Document Boundaries                                What this contract does and does not govern.

  §3      Source Initialization Manifest                     Exactly which sources and versions are in scope for this run.

  §4      Authority Hierarchy & Conflict Resolution          Which sources override which. How conflicts are resolved.

  §5      Retrieval Method & Endpoint Permissions            How each source is retrieved and which agents are permitted at which index.

  §6      Freshness & Versioning Policy                      Source-class-specific staleness and version-pinning rules.

  §8      Bundle Composition Requirements                    Minimum evidence each agent needs before its bundle is admissible.

  §11     Evidence Sufficiency Thresholds                    When retrieved evidence is sufficient to support a determination status.

  §12     Escalation Ownership                               Which escalation types are triggered by retrieval conditions and who owns resolution.

  §13     Citation Requirements                              What every determination and audit log entry must cite.

  §14     Source Normalization and Canonical Field Mapping   Defines the authoritative names for key concepts across all source types.

  §15     Contract Lock and Source Protocol                  Governs the pipeline run through completion and verifies source version.
  --------------------------------------------------------------------------------------------------------------------------------------------------

# 2. Document Boundaries

The table below is authoritative for scope disputes. When a rule touches both retrieval governance and agent behavior, the retrieval governance portion belongs here; the behavioral enforcement portion belongs in the Agent Spec.

  -------------------------------------------------------------------------------------------------------------------------------------
  **THIS DOCUMENT ANSWERS**                                  **THIS DOCUMENT DEFERS TO**
  ---------------------------------------------------------- --------------------------------------------------------------------------
  Which sources are authoritative                            Pipeline step-control behavior, gate logic, execution graph → Design Doc

  Source authority hierarchy and override rules              Agent behavioral rules and DOs / DON'Ts → Agent Spec

  Freshness and staleness requirements by source class       Output format enforcement and exception handling → Agent Spec

  Retrieval endpoint permissions per agent                   Approval checklist schema and audit log entry schema → Design Doc §10

  Evidence provenance minimum requirements                   Evaluation criteria and CSR benchmarks → Agent Spec

  Minimum bundle composition before a bundle is admissible   How agents respond to inadmissible bundles (behavioral) → Agent Spec

  Evidence sufficiency thresholds for determination status   Status emission and routing logic → Design Doc §3 / Agent Spec

  Conflict resolution protocol

  Escalation ownership (retrieval-triggered conditions)

  Audit log trigger rules for retrieval events

  Canonical field mapping across source types

  Contract lock and change protocol
  -------------------------------------------------------------------------------------------------------------------------------------

# 3. Source Initialization Manifest

The Supervisor Agent locks a source manifest at pipeline initialization. This manifest records exactly which sources, at which versions, are in scope for this run. Any source not on the manifest is out-of-scope for the duration of the run. Mid-run manifest changes are not permitted. See §16 for the contract lock and change protocol.

  ----------------------------------------------------------------------------------------------------------------------------------------------------------
  **SOURCE ID**   **SOURCE NAME**                    **VERSION**         **CONFIRMED BY (ROLE)**      **CONFIRMATION TIMESTAMP**   **STATUS**
  --------------- ---------------------------------- ------------------- ---------------------------- ---------------------------- -------------------------
  ISP-001         IT Security Policy v4.2            4.2                 IT Security (K. Whitfield)   \[to be confirmed\]          **CONFIRMED / PENDING**

  DPA-TM-001      DPA Legal Trigger Matrix v2.1      2.1                 Legal (General Counsel)      \[to be confirmed\]          **CONFIRMED / PENDING**

  PAM-001         Procurement Approval Matrix v3.0   3.0                 Procurement (Director)       \[to be confirmed\]          **CONFIRMED / PENDING**

  VQ-OC-001       OptiChain Vendor Questionnaire     Submission rev. 1   Procurement (Intake)         \[on submission\]            **CONFIRMED / PENDING**

  SLK-001         Slack / Meeting Thread Notes       Export at init.     Procurement                  \[at initialization\]        **CONFIRMED / PENDING**
  ----------------------------------------------------------------------------------------------------------------------------------------------------------

# 4. Source Authority Hierarchy

Sources are ranked into four authority tiers. When a retrieval bundle includes evidence from multiple tiers, higher-tier evidence takes precedence over lower-tier evidence for all determinations. Agents may not cite a lower-tier source as a primary citation when a higher-tier source addresses the same question.

  ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
  **AUTHORITY TIER**                                                                                          **SOURCES INCLUDED**
  ----------------------------------------------------------------------------------------------------------- ---------------------------------------------------------------------------------------------------------------
  Tier 1 --- Formal Governing Sources (Override all lower tiers)                                              IT Security Policy v4.2 (ISP-001) DPA Legal Trigger Matrix (DPA-TM-001) Procurement Approval Matrix (PAM-001)

  Tier 2 --- Structured Intake (Factual record; does not override Tier 1)                                     OptiChain Vendor Questionnaire (VQ-OC-001)

  Tier 3 --- Low-Authority Supplemental (Never primary citation; suppressed on any conflict with Tier 1--2)   Slack / Meeting Thread Notes (SLK-001)
  ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

## 4.1 Conflict Resolution Protocol

The table below governs how evidence conflicts are resolved. Note that BLOCKED and ESCALATED are used per the convention in §3.2.

  --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
  **CONFLICT TYPE**                                                                     **RESOLUTION RULE**                                                                                                                              **ESCALATION / BLOCKED CONVENTION**
  ------------------------------------------------------------------------------------- ------------------------------------------------------------------------------------------------------------------------------------------------ -----------------------------------------------------------------------------------------------
  Tier 3 conflicts with Tier 1 or 2                                                     Suppress Tier 3 source from bundle; log suppression in retrieval manifest with reason: AUTHORITY_SUPPRESSED; proceed with higher-tier evidence   No escalation --- automatic suppression. No workflow impact.

  Tier 3 thread A conflicts with Tier 3 thread B                                        Suppress both conflicting threads from bundle; log both suppressions                                                                             No escalation unless Tier 3 is the only available evidence on the point.

  Tier 1 source A conflicts with Tier 1 source B (e.g., policy clause vs. matrix row)   Neither source is suppressed. Both must be cited in the evidence payload.                                                                        workflow_state = ESCALATED (affected determination cannot resolve without human intervention)

  Multiple questionnaire versions detected                                              No version may be used until authoritative version is selected.                                                                                  workflow_state = BLOCKED (all downstream steps)
  --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

# 5. Retrieval Method per Source

Each source has a designated retrieval lane and chunking strategy. Agents may not retrieve a source through a different lane than the one defined here.

  ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
  **SOURCE**                               **RETRIEVAL LANE**                                      **CHUNKING STRATEGY**                                                                    **NOTES**
  ---------------------------------------- ------------------------------------------------------- ---------------------------------------------------------------------------------------- ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
  IT Security Policy v4.2 (ISP-001)        Indexed: hybrid dense vector + BM25                     Section-boundary chunking on numbered headings; preserves clause identifiers             BM25 handles exact clause IDs (e.g., §12.2.1); dense search handles semantic variants. Cross-encoder re-rank applied post-fusion.

  DPA Legal Trigger Matrix (DPA-TM-001)    Indexed: hybrid dense vector + BM25, row-targeted       Row-level chunking; each row = one atomic chunk; column headers embedded in each chunk   Row structure is preserved during chunking so rows remain interpretable as complete decision units. \"Row-targeted\" means queries are issued to retrieve specific rows by trigger condition, using the same hybrid index.

  Procurement Approval Matrix (PAM-001)    Indexed: hybrid dense vector + BM25, row-targeted       Row-level chunking; same as DPA matrix                                                   Same row-preservation approach. Row structure must survive chunking. Eligible for structured lookup upgrade in a future version.

  Vendor Questionnaire (VQ-OC-001)         Direct structured access --- JSON field lookup by key   No chunking. Ingested as a single structured JSON object at intake.                      Fields are read by canonical key name (see §14), not by similarity search. Never embedded or indexed.

  Slack / Meeting Notes (SLK-001)          Indexed: hybrid dense vector + BM25                     Thread-level chunking; one thread = one chunk                                            Authority cap applied at re-rank stage regardless of similarity score. Procurement-scoped threads only. Never primary citation.

  Checklist / pipeline state / audit log   Non-retrieval: assembled runtime state                  Not chunked; not indexed                                                                 These are outputs and state objects, not knowledge sources. Never embedded, indexed, or retrieved.
  ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

  ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
  **MATRIX RETRIEVAL NOTE:** Matrices are retrieved through the hybrid index using row-targeted queries --- not through a separate structured-lookup backend. \"Structured\" in this context means that row integrity is preserved during chunking so that each retrieved chunk represents a complete, interpretable row. The retrieval mechanism remains hybrid dense + BM25.
  ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

  ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

## 5.1 Retrieval Endpoint Permissions

Retrieval endpoint permissions define which index endpoints each agent is authorized to query at the infrastructure level. This is an architectural constraint (Design Doc §8), not a behavioral guideline. An agent that attempts to query an index it is not authorized to access must fail closed; the attempt is logged per §12.2.

  -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
  **INDEX ENDPOINT**                     **IT SECURITY AGENT**   **LEGAL AGENT**   **PROCUREMENT AGENT**        **CHECKLIST ASSEMBLER**   **CHECKOFF AGENT**
  -------------------------------------- ----------------------- ----------------- ---------------------------- ------------------------- ---------------------------------------------------
  idx_security_policy                    **✓ Full**              ✓ Read-only       ✓ Read-only                  --- No access             --- No access

  idx_dpa_matrix                         --- No access           **✓ Full**        --- No access                --- No access             --- No access

  idx_procurement_matrix                 --- No access           --- No access     **✓ Full**                   --- No access             --- No access

  vq_direct_access (structured)          **✓ Full**              **✓ Full**        **✓ Full**                   **✓ Full**                **✓ Full**

  idx_slack_notes (Procurement-scoped)   --- No access           --- No access     ✓ Procurement threads only   --- No access             *--- Downstream-only; no index queries permitted*
  -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

  ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
  **CHECKOFF AGENT ACCESS RULE:** The Checkoff Agent is downstream-only and may consume only assembled outputs, stakeholder-routing metadata, and audit-visible determination summaries. It has no independent evidence-discovery authority. It is explicitly prohibited from querying any index endpoint. This is an architectural constraint, not a behavioral guideline.
  ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

  ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

# 6. Freshness & Versioning Policy by Source Class

Freshness rules differ by source class. A single blanket staleness rule is insufficient because static policy documents, dynamic intake records, and informal notes have fundamentally different update characteristics and risk profiles.

  -----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
  **SOURCE CLASS**                                         **VERSION PINNING**                                                                                 **RUN-TIME REFRESH**                                                      **STALE-BUT-USABLE**                                                                                                          **PROVISIONAL USE**                                                                  **HUMAN RECONFIRMATION**
  -------------------------------------------------------- --------------------------------------------------------------------------------------------------- ------------------------------------------------------------------------- ----------------------------------------------------------------------------------------------------------------------------- ------------------------------------------------------------------------------------ -------------------------------------------------------------------------
  Static versioned policy (ISP-001, DPA-TM-001, PAM-001)   Pinned at initialization. Version ID locked to manifest entry.                                      Not eligible for refresh during run.                                      Not permitted. Unverified version triggers PENDING evidence flag.                                                             Permitted only when manifest_status = PENDING and owning domain has been notified.   Required before overall_status = COMPLETE when source is PENDING.

  Structured intake (VQ-OC-001)                            Pinned at submission. If multiple versions exist: workflow_state = BLOCKED                          Not eligible. Questionnaire is immutable once intake validation passes.   Not applicable.                                                                                                               Not applicable.                                                                      Required if version conflict detected.

  Governed precedent (PVD-001)                             Pinned to state at initialization. New precedents added after init are out of scope for this run.   Not eligible during run.                                                  Permitted. Precedents are supplementary; a dated record is usable as context with a recency note in the retrieval manifest.   Permitted without triggering run-level PENDING.                                      Not required unless precedent is the only evidence for a determination.

  Low-authority supplemental (SLK-001)                     Captured as export at initialization. No run-time update.                                           Not eligible.                                                             Permitted. Recency noted in retrieval manifest but not blocking.                                                              Not applicable --- Tier 3 sources never drive determinations.                        Not required.
  -----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

# 7. Evidence Provenance Minimum Requirements

Every piece of retrieved evidence must carry a complete provenance record before it is eligible for inclusion in an agent context bundle or for citation in a determination. Evidence without a complete provenance record is ineligible for downstream use regardless of retrieval score.

  --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
  **PROVENANCE FIELD**   **DEFINITION AND REQUIREMENTS**
  ---------------------- ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
  source_id              Matches the source ID in the initialization manifest (e.g., ISP-001). Required for all source types.

  source_name            Human-readable display name. Required for all source types.

  source_type            One of: POLICY \| MATRIX \| QUESTIONNAIRE \| SUPPLEMENTAL_NOTE. Required for all source types.

  version                Version string from the initialization manifest. Must match manifest exactly. Required for all source types.

  chunk_identifier       For indexed sources: section number, row ID, record ID, or thread ID. For direct-access sources: JSON field path (e.g., integration_details.erp_type). Required for all source types.

  retrieval_timestamp    ISO 8601 UTC timestamp of the retrieval operation. Required for all source types.

  authority_tier         Integer 1--3, matching the tier in §4. Required for all source types.

  citation_class         One of: PRIMARY \| SUPPLEMENTARY. Tier 3 sources are always SUPPLEMENTARY. See §12 for citation rules. Required for all source types.

  retrieval_score        Fused hybrid score (dense + BM25 via RRF) before re-ranking. Optional for direct-access sources.

  rerank_score           Score after cross-encoder re-ranking and authority weight application. Optional for direct-access sources.

  manifest_status        Status of the source in the initialization manifest: CONFIRMED \| PENDING
  --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

  ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
  **INELIGIBILITY RULE:** Any retrieved chunk missing source_id, version, chunk_identifier, retrieval_timestamp, authority_tier, citation_class, or manifest_status is excluded from the context bundle. The exclusion must be logged in the retrieval manifest with reason: INCOMPLETE_PROVENANCE.
  ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

  ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

# 8. Retrieval Bundle Admissibility Requirements

These requirements define the minimum evidence composition a bundle must satisfy before it is considered admissible for agent use. A bundle that does not meet its admissibility requirements is inadmissible. How agents respond to an inadmissible bundle is governed by the Agent Spec and Design Doc §11. This section governs the evidence threshold, not the response behavior.

## 8.1 IT Security Agent Bundle

  --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
  **REQUIRED ELEMENT**                            **ADMISSIBILITY CONDITION**
  ----------------------------------------------- --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
  Vendor questionnaire --- data handling fields   integration_details.erp_type, data_classification_self_reported, regulated_data_types must be present. Bundle is inadmissible without these fields.

  IT Security Policy citation                     At least one section-level citation required for any nontrivial classification determination. If no policy section is retrieved, classification evidence is insufficient for a RESOLVED determination.
  --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

## 8.2 Legal Agent Bundle

  --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
  **REQUIRED ELEMENT**                                     **ADMISSIBILITY CONDITION**
  -------------------------------------------------------- -----------------------------------------------------------------------------------------------------------------------------------------------------
  IT Security Agent output --- data_classification field   Required. Bundle is inadmissible without upstream classification. If Security Agent output is AMBIGUOUS, Legal bundle must include that explicitly.

  DPA Legal Trigger Matrix --- at least one matching row   Required for a DPA determination to be admissible as RESOLVED. If no trigger-matrix row matches, the determination lacks sufficient evidence.

  Questionnaire --- EU personal data fields                Required for DPA scoping: eu_personal_data_flag, data_subjects_eu.

  Questionnaire --- NDA status field                       Required: existing_nda_status. Consumed by the Legal Agent to normalize nda_status and derive nda_blocker.

  Questionnaire --- DPA execution status field             Optional: existing_dpa_status. Consumed by the Legal Agent to derive dpa_blocker. Absence is treated as equivalent to a non-EXECUTED status (dpa_blocker defaults to true when dpa_required = true); absence does not make the bundle inadmissible.
  --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

## 8.3 Procurement Agent Bundle

  ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
  **REQUIRED ELEMENT**                                                      **ADMISSIBILITY CONDITION**
  ------------------------------------------------------------------------- -------------------------------------------------------------------------------------------------------------------------------------
  IT Security Agent output (full)                                           Required: fast_track_eligible, data_classification, policy_citations.

  Legal Agent output (full)                                                 Required: dpa_required, dpa_blocker, trigger_rule_cited. Bundle is inadmissible if either upstream agent output is absent.

  Procurement Approval Matrix --- at least one matching approval path row   Required for an approval_path determination. If no matching row is found, the determination lacks sufficient evidence for RESOLVED.

  Questionnaire --- vendor relationship fields                              Required: existing_nda_status, existing_msa, vendor_class, deal_size.

  Slack / meeting notes                                                     Permitted (Procurement-scoped threads only) when specifically relevant. Otherwise excluded.
  ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

## 8.4 Checklist Assembler Bundle

  ---------------------------------------------------------------------------------------------------------------------------------------------------
  **REQUIRED ELEMENT**                         **ADMISSIBILITY CONDITION**
  -------------------------------------------- ------------------------------------------------------------------------------------------------------
  All domain agent structured outputs (JSON)   IT Security, Legal, and Procurement outputs must all be present and schema-valid per Design Doc §10.

  Audit log entries for the current run        Required. Used to compose citations\[\] and blockers\[\] arrays.
  ---------------------------------------------------------------------------------------------------------------------------------------------------

## 8.5 Checkoff Agent Bundle

  --------------------------------------------------------------------------------------------------------------------------------------
  **REQUIRED ELEMENT**                           **ADMISSIBILITY CONDITION**
  ---------------------------------------------- ---------------------------------------------------------------------------------------
  Finalized checklist output (structured JSON)   Required. Primary input.

  Stakeholder guidance context                   Required: role-to-stakeholder map, required approver list, escalation reasons if any.

  Domain agent outputs                           Available for reference when composing guidance documents (structured outputs only).
  --------------------------------------------------------------------------------------------------------------------------------------

# 9. Token Budget per Agent

Per-agent token budgets are defined in Design Doc §9 and extended here with the Checkoff Agent. These are architectural constraints enforced in the pipeline orchestration layer.

  ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
  **AGENT**             **BUDGET & COMPOSITION RULES**
  --------------------- --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
  IT Security Agent     \~8,000 tokens. Questionnaire data fields + relevant IT Security Policy sections (subquery; full doc excluded) + risk classification matrix rows. Supplementary context excluded when budget is constrained.

  Legal Agent           \~6,000 tokens. IT Security Agent output (data_classification only) + relevant DPA trigger matrix rows + any prior DPA precedents for this vendor class.

  Procurement Agent     \~7,000 tokens. IT Security output + Legal output + relevant approval matrix rows + prior vendor relationship context (Procurement-scoped only). Slack threads excluded unless specifically flagged.

  Checklist Assembler   \~10,000 tokens. All domain agent outputs (structured JSON) + audit log entries + final status signals. Does not receive raw source documents.

  Checkoff Agent        \~8,000 tokens. Finalized checklist output + stakeholder map + required approver list + escalation reasons (if any) + relevant domain agent determination summaries. No raw source retrieval.
  ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

## 9.1 Priority Ordering Under Budget Constraint

When assembled context approaches the token budget, the pipeline retains evidence in the following priority order:

> 1\. Mandatory structured intake data (questionnaire fields required for this determination)
>
> 2\. Primary policy source (highest-authority Tier 1 source relevant to this determination)
>
> 3\. Secondary structured sources (matrices, trigger tables)
>
> 4\. Precedent context (Tier 3)
>
> 5\. Supplementary context (Tier 3 --- Slack / notes). Excluded first when budget is constrained.

# 10. Low-Authority Source Handling Rules

Slack threads and meeting notes (SLK-001) are governed by the following rules in addition to the authority hierarchy in §5.

  --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
  **RULE**                           **SPECIFICATION**
  ---------------------------------- ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
  Authority score cap                Tier 3 sources receive a fixed authority weight cap at re-ranking, regardless of semantic similarity score. A Tier 3 chunk with a higher similarity score than a Tier 1 chunk is still weighted below the Tier 1 chunk in the final bundle.

  Citation class restriction         Tier 3 sources may only appear as citation_class: SUPPLEMENTARY. They may never appear as citation_class: PRIMARY.

  Conflict suppression               When a Tier 3 source conflicts with any Tier 1 or 2 source, the Tier 3 source is suppressed from the bundle. Logged in the retrieval manifest with reason: AUTHORITY_SUPPRESSED.

  Intra-Tier 3 conflict              When two Tier 3 threads conflict with each other, both are suppressed. If Tier 3 is the only available evidence on a point, the evidence is insufficient for a RESOLVED determination.

  Access scope                       Only Procurement-scoped threads are eligible. No other agent may access Tier 3 sources.

  Inclusion gate                     Tier 3 evidence is included only when it adds non-conflicting, non-redundant context beyond what Tier 1-2 sources provide.

  Determination driver prohibition   Tier 3 evidence is never the sole or primary basis for a RESOLVED determination. It may supplement a RESOLVED determination but may not constitute it.
  --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

# 11. Determination Evidence Sufficiency Thresholds

These thresholds define when retrieved evidence is sufficient to support a given determination status. This is a retrieval governance rule about evidence adequacy. How the pipeline emits and routes statuses in response to these evidence conditions is governed by the Design Doc (§10) and Agent Spec.

  ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
  **DETERMINATION STATUS**                                       **EVIDENCE REQUIREMENTS**
  -------------------------------------------------------------- ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
  RESOLVED (evidence sufficient)                                 At least one Tier 1 source citation supporting the determination. Questionnaire fields relevant to the determination are present and unambiguous. No unresolved conflicting Tier 1 evidence exists.

  ESCALATED (evidence present but conflicting or out-of-scope)   Required evidence is present but conflicts between two or more Tier 1 sources, OR the evidence pattern falls outside the defined rule set of the governing matrix, OR human judgment is explicitly required by policy.

  BLOCKED (required evidence absent entirely)                    Required source is entirely unavailable, OR required upstream evidence is absent (upstream agent unresolved). The determination cannot proceed. See §3.2.
  ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

## 11.1 Specific Thresholds by Determination Type

  ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
  **DETERMINATION TYPE**                       **MINIMUM EVIDENCE THRESHOLD**
  -------------------------------------------- -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
  Data classification (IT Security Agent)      At least one IT Security Policy section citation plus questionnaire ERP integration type confirmed. If ERP type is ambiguous: evidence is insufficient for RESOLVED

  DPA requirement (Legal Agent)                At least one DPA trigger matrix row match plus upstream data_classification field confirmed. If no matrix row matches: evidence is insufficient; determination requires escalation.

  Fast-track eligibility (IT Security Agent)   Requires RESOLVED data_classification = UNREGULATED. If classification is REGULATED or AMBIGUOUS, evidence is insufficient for fast_track_eligible = true.

  Approval path routing (Procurement Agent)    Both IT Security and Legal outputs must be present (RESOLVED). At least one procurement matrix row match required. If no row matches: evidence is insufficient for RESOLVED.

  Checklist completion (Checklist Assembler)   All three domain agent outputs present and schema-valid. Evidence sufficiency is inherited from upstream determinations.
  ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

# 12. Escalation Ownership

This section governs escalation conditions that are triggered by retrieval or evidence quality issues --- specifically, conditions where the evidence layer cannot provide sufficient or unambiguous context for a determination. Workflow routing in response to escalation is governed by the Design Doc (§3).

  ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
  **EVIDENCE CONDITION**                                        **BLOCKED/ESCALATED CONVENTION**                                                                                                             **RESOLUTION OWNER**
  ------------------------------------------------------------- -------------------------------------------------------------------------------------------------------------------------------------------- -------------------------------------------
  Questionnaire not submitted or incomplete                     workflow_state = BLOCKED (no evidence base for any determination)                                                                            Procurement

  Multiple questionnaire versions detected                      workflow_state = BLOCKED resolution_mode = ESCALATED_TO_PROCUREMENT                                                                          Procurement

  Data classification ambiguous (ERP type field unclear)        Evidence insufficient for RESOLVED classification                                                                                            IT Security (K. Whitfield or delegate)

  Tier 1 source conflict (policy clause vs. matrix row)         Evidence conflicting; determination cannot be RESOLVED resolution_mode = ESCALATED_TO\_\[both domain owners\]                                Both domain owners of conflicting sources

  DPA required but no executed DPA on record                    Evidence supports dpa_required = true, dpa_blocker = true; determination is RESOLVED on the trigger; the blocker is a workflow consequence   Legal (General Counsel)

  ERP integration tier unclassified (ISP-001 §12.2 amber row)   Evidence insufficient for RESOLVED classification                                                                                            IT Security

  NDA status unconfirmed (ISP-001 §12.1.4)                      Evidence insufficient to confirm NDA requirement satisfied                                                                                   Procurement

  No approval matrix row matches vendor/deal combination        Evidence insufficient for RESOLVED approval path resolution_mode = ESCALATED_TO_PROCUREMENT_DIRECTOR                                         Procurement Director
  ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

## 12.1 Minimum Escalation Evidence Payload

Every escalation triggered by a retrieval or evidence condition must include these fields in its audit log entry:

-   evidence_condition --- description of the retrieval or evidence gap that triggered the escalation

-   triggering_agent_id --- which agent detected the condition

-   triggering_source --- source ID, version, and chunk_identifier of the evidence that is conflicting or absent

-   conflicting_evidence --- structured summary of both (or all) conflicting chunks (if applicable)

-   resolution_owner --- role per the table above

-   minimum_evidence_to_resolve --- what the resolution owner must provide for the evidence condition to clear

# 13. Citation Requirements

Every nontrivial determination must be traceable to the source evidence that supported it. Citations are embedded in agent outputs, audit log entries, and the final checklist.

  ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
  **DETERMINATION TYPE**          **CITATION REQUIREMENTS**
  ------------------------------- -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
  Data classification             PRIMARY: at least one IT Security Policy section (ISP-001, section number, version). If questionnaire field is ambiguous: note the ambiguous field by canonical name. If risk matrix row cited: include row ID and version.

  DPA requirement determination   PRIMARY: at least one DPA trigger matrix row (DPA-TM-001, row ID, version, trigger condition). SUPPLEMENTARY: upstream classification output reference (agent_id, pipeline_run_id). No Tier 3 source may be cited as PRIMARY.

  Fast-track eligibility          PRIMARY: IT Security Policy section governing fast-track conditions. Must reference the specific clause.

  Approval path routing           PRIMARY: procurement approval matrix row (PAM-001, row ID, approval path condition). SUPPLEMENTARY: both upstream domain agent outputs cited by agent_id. Tier 3 note permitted as SUPPLEMENTARY only if non-conflicting.

  Blocker identification          PRIMARY: the authoritative source that creates the blocker condition (e.g., ISP-001 §12.1.4 for NDA confirmation). Free-text blockers without source citations are not permitted.

  ESCALATED finding               Both (or all) conflicting sources must be cited with their chunk_identifiers. The escalation payload must describe the specific conflict, not a general description.
  ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

## 13.1 Audit Log Citation Requirements by Event Type

Every audit log entry must include citations per Design Doc §10 schema. The following requirements augment that schema by event type:

  ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
  **AUDIT LOG event_type**   **CITATION REQUIREMENT**
  -------------------------- ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
  RETRIEVAL                  List all sources queried, method used (hybrid / direct / row-targeted), chunks returned (chunk_identifier, retrieval_score), chunks admitted to bundle, chunks excluded (with reason: INCOMPLETE_PROVENANCE / AUTHORITY_SUPPRESSED / BUDGET_CONSTRAINED / ACCESS_DENIED).

  DETERMINATION              Full citation per the determination-type rules in §14 above. Each cited piece of evidence must carry all provenance fields from §8.

  STATUS_CHANGE              Reference to the triggering determination or retrieval event. For ESCALATED: both conflicting sources with chunk_identifiers. For BLOCKED: the missing required evidence type. For COMPLETE, objective complete with proper citations

  ESCALATION                 Full escalation payload per §12.1 including triggering_source and conflicting_evidence with chunk_identifiers.
  ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

## 13.2 Audit Log Event Triggers

The following events are audit-worthy and must produce an audit log entry:

-   Every retrieval query attempt against any index endpoint

-   Every chunk admitted to a final context bundle

-   Every chunk excluded due to access control, authority suppression, provenance incompleteness, or budget constraint

-   Every evidence-layer status change: ESCALATED condition identified, BLOCKED condition identified, COMPLETE

-   Every determination emitted by a domain agent

# 14. Source Normalization and Canonical Field Mapping

The pipeline operates across sources with different schemas, naming conventions, and formats. The canonical field map below defines the authoritative names for key concepts across all source types. Agents and the orchestration layer use canonical names in outputs and audit log entries, not source-native names.

  ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
  **CANONICAL FIELD**     **DEFINITION**                                                                                                                **PRIMARY SOURCE**         **SOURCE-NATIVE EQUIVALENTS**
  ----------------------- ----------------------------------------------------------------------------------------------------------------------------- -------------------------- -------------------------------------------------------------------------------------------------
  vendor_name             Legal name of the software vendor                                                                                             VQ-OC-001                  vendor_name (JSON); \"Vendor\" (matrix rows); \"third party\" (ISP-001 §12)

  integration_type        How OptiChain connects to Lichen systems (direct ERP vs. export-only)                                                         VQ-OC-001                  integration_details.erp_type (JSON); \"Integration Method\" (ISP-001 §12.2 table)

  regulated_data_flag     Boolean: does the integration involve regulated or sensitive data?                                                            IT Security Agent output   data_classification_self_reported (VQ); ERP tier classification (ISP-001 §12.2)

  eu_personal_data_flag   Boolean: does the integration involve EU personal data subject to GDPR?                                                       VQ-OC-001                  data_subjects_eu (JSON); \"EU Data Subjects\" (DPA-TM-001 trigger column)

  nda_status              NDA status normalized from questionnaire evidence and ISP-001 §12.1.4 clause: EXECUTED \| PENDING \| NOT_STARTED \| UNKNOWN   Legal Agent output         existing_nda_status (JSON, raw input from VQ-OC-001); NDA confirmation clause (ISP-001 §12.1.4)

  existing_dpa_status     Vendor-reported DPA execution status: EXECUTED \| PENDING \| NOT_STARTED \| UNKNOWN. Legal Agent normalizes into dpa_blocker (dpa_blocker = false when dpa_required = true AND existing_dpa_status = EXECUTED; dpa_blocker = true when dpa_required = true AND existing_dpa_status != EXECUTED or the field is absent).   VQ-OC-001                  existing_dpa_status (JSON, raw input from VQ-OC-001)

  dpa_required            Boolean: does a Data Processing Agreement need to be executed?                                                                Legal Agent output         dpa_required (DPA-TM-001 trigger column)

  approval_path           Routing outcome: STANDARD \| FAST_TRACK                                                                                       Procurement Agent output   approval_path (PAM-001 rows); \"Approval Route\" (Procurement matrix)

  vendor_class            Procurement classification: TIER_1 \| TIER_2 \| TIER_3                                                                        VQ-OC-001 / PAM-001        vendor_class (JSON); \"Vendor Tier\" (PAM-001)

  deal_size               Annualized contract value in USD                                                                                              VQ-OC-001                  contract_value_annual (JSON); \"Deal Value\" (PAM-001)

  data_classification     IT Security Agent output: REGULATED \| UNREGULATED \| AMBIGUOUS                                                               IT Security Agent output   data_classification_self_reported (VQ); ERP integration tier (ISP-001 §12.2)

  fast_track_eligible     Boolean: eligible for expedited onboarding?                                                                                   IT Security Agent output   fast_track flag (VQ); expedited route conditions (PAM-001)
  ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

# 15. Contract Lock and Change Protocol

The Context Contract is locked at pipeline initialization. Once a run has begun, this contract version governs that run through completion. Mid-run changes are not permitted.

  -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
  **SCENARIO**                                          **PROTOCOL**
  ----------------------------------------------------- -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
  Contract change between runs                          New contract version issued (CC-001 vN+1). Version Log updated. In-flight runs complete against the version on which they were initialized.

  Source authority ruling changes                       Requires contract version increment. New version reviewed by all owning roles before taking effect.

  New source added to pipeline                          Requires contract version increment. New source must receive source ID, retrieval lane assignment, freshness policy entry, and endpoint permission mapping.

  Source removed from pipeline                          Requires contract version increment. Existing runs complete under prior version.

  Emergency mid-run correction (source version error)   Pipeline is halted. The run is invalidated. A corrected run is initiated under a new or re-confirmed manifest entry. The invalidated run is retained in the audit log with status: INVALIDATED.
  -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

# 16. Version Log

  ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
  **VERSION**        **DATE**         **AUTHOR**                              **CHANGE**
  ------------------ ---------------- --------------------------------------- --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
  v1.0 (Draft)       April 6, 2026    IT Architecture / Legal / Procurement   Initial draft. All governance sections established.

  v1.1 (Draft)       April 7, 2026    IT Architecture                         Revised: (1) orchestration behavior removed to Design Doc / Agent Spec boundary; (2) PROVISIONAL established as first-class pipeline status; (3) BLOCKED vs. ESCALATED unified convention introduced in §3.2 and applied consistently; (4) Tier 1 label updated to \"Formal Governing Sources\"; (5) matrix retrieval phrasing standardized to row-targeted hybrid; (6) Checkoff Agent downstream-only access rule made explicit; (7) executive navigation section added; (8) bundle composition reframed as admissibility (evidence threshold) not orchestration behavior.

  v1.2 (Draft)       April 10, 2026   IT Architecture                         Added onboarding_path_classification to §15 canonical field map. Field sourced from ORCH-PLAN-001 STEP-02 output contract; previously omitted from CC-001.

  v1.3 (Draft)       April 10, 2026   IT Architecture                         Aligned bundle admissibility and canonical field map with Legal Agent Spec v0.4 and sequential pipeline model. Changes: (1) §9.2 Legal Agent bundle --- added questionnaire NDA field (existing_nda_status) and ISP-001 §12.1.4 NDA clause chunk as required admissibility elements; (2) §9.3 Procurement Agent bundle --- updated to require full Legal Agent output including nda_status, nda_blocker, trigger_rule_cited, and policy_citations under the sequential STEP-03 → STEP-04 model; (3) §12.1 Procurement approval path threshold --- updated to reflect that both IT Security and Legal outputs must be present as schema-valid terminal upstream outputs; upstream PROVISIONAL or ESCALATED does not make the bundle inadmissible; (4) §15 canonical field map --- added dpa_blocker and nda_blocker as Legal Agent output fields.

  **v1.4 (Draft)**   April 10, 2026   IT Architecture                         Three integrity fixes. (1) §3.1 PROVISIONAL status section --- added status precedence note: ESCALATED takes precedence over PROVISIONAL when both are present in the same run; cross-reference to Design Doc §10 added. (2) §15 canonical field map --- corrected nda_status primary source from VQ-OC-001 to Legal Agent output, reflecting that nda_status is a normalized determination owned by the Legal Agent; existing_nda_status (VQ-OC-001) moved to source-native equivalents as the raw input. (3) Version header and log updated from v1.2 to v1.4 to reflect accumulated changes since last log entry.
  ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------