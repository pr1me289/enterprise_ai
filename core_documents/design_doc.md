+-------------------------------------------------------------------------------+------------------------------------------+--------------------+
| **Enterprise Software Vendor Onboarding**                                     |                                          |                    |
|                                                                               |                                          |                    |
| AI-Assisted Intake Pipeline --- System Architecture & Technical Specification |                                          |                    |
|                                                                               |                                          |                    |
| *Illustrated with OptiChain as the Onboarding Candidate*                      |                                          |                    |
+-------------------------------------------------------------------------------+------------------------------------------+--------------------+
| **STATUS**                                                                    | **OWNER**                                | **LAST UPDATED**   |
|                                                                               |                                          |                    |
| **Draft v4.0**                                                                | **Engineering / IT Architecture**        | **April 10, 2026** |
+-------------------------------------------------------------------------------+------------------------------------------+--------------------+
| Pipeline: PRD → **Design Doc** → Context Contract → Agent Spec                |                                          |                    |
+-------------------------------------------------------------------------------+------------------------------------------+--------------------+

*This Design Document translates the business requirements from the PRD into a technical architecture for the AI-assisted software vendor onboarding pipeline. It specifies system topology, agent orchestration, retrieval strategy, security model, and output contracts. Owned by Engineering / IT Architecture. Not intended for non-technical stakeholders.*

*Target Audience: Engineers tasked with a project developer role or oversight.*

**1. Purpose & Scope**

This document defines the engineering architecture for a governed AI-assisted enterprise software vendor onboarding pipeline. It translates the PRD into a system design that engineers can implement, review, and evolve. The system is designed for a mid-size manufacturing enterprise onboarding a new software vendor. The immediate example is OptiChain, a supply-chain forecasting and inventory optimization platform under evaluation.

The design goal is not merely to answer vendor-onboarding questions with an LLM. The goal is to create an enterprise environment in which AI agents can operate safely by using scoped context, source-aware retrieval, auditable reasoning inputs, strict access controls, and human escalation points. This supports the PRD's core business objective: reduce onboarding cycle time while preserving compliance, auditability, and role-based access controls.

**Document Boundaries**

✓ System architecture and agent wiring

✓ Retrieval strategy and pipeline architecture

✓ Security and data access control model

✓ Output schemas and audit log structure

✓ Non-functional requirements (latency, auditability)

**2. Architecture Overview**

The pipeline is a sequential, gated orchestration system. Inputs enter through a single intake interface; a supervisor orchestrator routes them through domain-specific agents in dependency order; outputs are assembled into a structured approval checklist with a complete audit log. No domain agent may run until its upstream dependency has cleared --- this constraint is derived directly from the PRD requirement chain (R-01 → R-02 → R-03 → R-04 → R-05).

**System Topology**

  --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
  **LAYER**                **COMPONENT**         **FUNCTION**
  ------------------------ --------------------- ---------------------------------------------------------------------------------------------------------------------------------------------------------------
  Orchestration            Supervisor Agent      Completes proper intake of vendor questionnaire; enforces the execution graph; gates downstream agents; aggregates outputs; triggers escalation

  Domain --- Security      IT Security Agent     Classifies regulated data exposure; determines fast-track eligibility; cites policy sources

  Domain --- Legal         Legal Agent           Determines DPA requirement and NDA execution status; cites legal trigger matrix and ISP-001 NDA clause; flags DPA or NDA as blocker if required

  Domain --- Procurement   Procurement Agent     Determines approval path using upstream fast-track eligibility from IT Security Agent; validates against procurement matrix; routes to STANDARD or FAST_TRACK

  Output                   Checklist Assembler   Composes structured approval checklist; compiles all audit log entries; emits final status signal

  Output                   Checkoff Agent        Facilitates checkoff procedure; compiles guidance documents for stakeholders to proceed with onboarding process
  --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

**Execution Graph**

The pipeline enforces a strict dependency chain. The Supervisor Agent manages this graph; no domain agent receives a context bundle until its upstream gate has resolved.

+------------------------------------------------------------------------------------------------------------------+
| **EXECUTION ORDER**                                                                                              |
+------------------------------------------------------------------------------------------------------------------+
| Step 1 → Intake validation (R-01): questionnaire completeness check. BLOCKED if not submitted.                   |
|                                                                                                                  |
| Step 2 → Onboarding path classification (R-02): gates Step 3                                                     |
|                                                                                                                  |
| Step 3 → Legal and Compliance trigger determination (R-03): runs after R-02 resolves.                            |
|                                                                                                                  |
| Step 4 → Approval path determination (R-04): runs after R-03 reaches a terminal state                            |
|                                                                                                                  |
| Step 5 → Approval checklist generation (R-05): runs when R-01 through R-04 have all reached terminal step states |
|                                                                                                                  |
| Step 6 → Stakeholder guidance and checkoff support (R-06): runs when R-05 has reached a COMPLETE terminal state  |
+------------------------------------------------------------------------------------------------------------------+

**3. Agent Orchestration Model**

This section defines the orchestration contract for each agent: what it receives as input, what it returns, and what downstream components depend on its output. Behavioral rules (what the agent should and should not do) are deferred to the Agent Spec. This section defines the wiring, not the rules.

**Agent Input / Output Contracts**

+---------------------+--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| **AGENT**           | **INPUT BUNDLE / OUTPUT CONTRACT**                                                                                                                                                                                                                                                                                                                                                                                                         |
+=====================+============================================================================================================================================================================================================================================================================================================================================================================================================================================+
| Supervisor Agent    | Input: raw questionnaire submission + pipeline state after each step + status signals from domain agents + outputs from domain agents                                                                                                                                                                                                                                                                                                      |
|                     |                                                                                                                                                                                                                                                                                                                                                                                                                                            |
|                     | Output: execution graph updates with gate status per step; escalation signal if any step is BLOCKED or ESCALATED; context bundles assembled for domain agents                                                                                                                                                                                                                                                                              |
+---------------------+--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| IT Security Agent   | Input: vendor questionnaire (data classification fields) + IT Security Policy                                                                                                                                                                                                                                                                                                                                                              |
|                     |                                                                                                                                                                                                                                                                                                                                                                                                                                            |
|                     | Output: {data_classification, fast_track_eligible, policy_citations\[\], status}                                                                                                                                                                                                                                                                                                                                                           |
+---------------------+--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| Legal Agent         | Input: IT Security Agent output (data_classification) + DPA legal trigger matrix + questionnaire NDA field (existing_nda_status) + questionnaire EU personal data fields + ISP-001 §12.1.4 NDA clause                                                                                                                                                                                                                                      |
|                     |                                                                                                                                                                                                                                                                                                                                                                                                                                            |
|                     | Output: {dpa_required, dpa_blocker, nda_status, nda_blocker, trigger_rule_cited, status}                                                                                                                                                                                                                                                                                                                                                   |
+---------------------+--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| Procurement Agent   | Input: IT Security Agent full output (fast_track_eligible, data_classification, policy_citations\[\]) + Legal Agent full output (dpa_required, dpa_blocker, nda_status, nda_blocker) + questionnaire vendor relationship fields (vendor_class, deal_size, existing_nda_status) + procurement approval matrix Output: {approval_path, fast_track_eligible, executive_approval_required, required_approvals\[\], estimated_timeline, status} |
+---------------------+--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| Checklist Assembler | Input: previous domain agent outputs + audit log                                                                                                                                                                                                                                                                                                                                                                                           |
|                     |                                                                                                                                                                                                                                                                                                                                                                                                                                            |
|                     | Output: structured approval checklist + complete audit log + status signal (COMPLETE / ESCALATED / BLOCKED)                                                                                                                                                                                                                                                                                                                                |
+---------------------+--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| Checkoff Agent      | Input: all domain agent outputs + stakeholder map                                                                                                                                                                                                                                                                                                                                                                                          |
|                     |                                                                                                                                                                                                                                                                                                                                                                                                                                            |
|                     | Output: guidance documents                                                                                                                                                                                                                                                                                                                                                                                                                 |
+---------------------+--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+

**Routing Logic**

The Supervisor Agent evaluates each step against a simple gate model. A step is COMPLETE when it returns a valid output object with status: complete. A step is BLOCKED when a required input is entirely absent --- the step cannot proceed because there is nothing to reason over. A step is ESCALATED when evidence is present but conflicting or outside the defined rule set, and a human decision is required before proceeding.

  -----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
  **CONDITION**                                                                                                    **SYSTEM BEHAVIOR**
  ---------------------------------------------------------------------------------------------------------------- ------------------------------------------------------------------------------------------------------------------------------
  **WHEN** any Document is not yet submitted or is missing                                                         **→ THE SYSTEM SHALL** return BLOCKED status; domain agent must halt; halt all downstream steps

  **WHEN** multiple Document versions exist                                                                        **→ THE SYSTEM SHALL** return status signal ESCALATED; notify relevant department (owner of document); halt downstream steps

  **WHEN** Data classification is ambiguous                                                                        **→ THE SYSTEM SHALL** return status signal ESCALATED; notify relevant department (owner of document); halt downstream steps

  **WHEN** output contract of relevant domain agent is fulfilled according to Design Doc specifications            **→ THE SYSTEM SHALL** return status signal COMPLETE; Supervisor Agent assessment begins

  **WHEN** Supervisor Agent assesses a step in the execution graph to be resolved properly, with COMPLETE status   **→ THE SYSTEM SHALL** trigger the domain agent of the next step in the execution graph order

  **WHEN** R-01 through R-04 have all reached terminal states with status COMPLETE                                 **→ THE SYSTEM SHALL** trigger Checklist Assembler

  **WHEN** Any domain agent returns status: ESCALATED                                                              **→ THE SYSTEM SHALL** include escalation reason in audit log entry and suspend execution

  **WHEN** R-05 reaches a terminal state with signal status COMPLETE                                               **→ THE SYSTEM SHALL** trigger Checkoff Agent
  -----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

**Pipeline Status Signals**

Every domain agent and the Supervisor emits one of three terminal status signals. No other status values are defined in this pipeline.

**COMPLETE** The step has fulfilled its output contract. All required fields are present and schema-valid. The Supervisor may advance to the next step in the execution graph.

**BLOCKED** A required source document or upstream agent output is entirely absent. The step has nothing to reason over and cannot proceed. All downstream steps halt. The Supervisor emits a BLOCKED signal and notifies the responsible owner.

**ESCALATED** Evidence is present but contains a conflict, ambiguity, or condition that requires human judgment before the pipeline can proceed. The Supervisor records the escalation reason in the audit log and suspends execution of the affected step and all downstream steps pending human resolution.

**4. Design Goals & Non-Goals**

This section defines the engineering objectives the architecture is intended to satisfy, along with the boundaries it intentionally does not cross. It translates the PRD's scope into technical priorities such as governed automation, role-based access, auditability, and safe human escalation, while explicitly excluding responsibilities that belong outside this pipeline, such as autonomous approval authority, contract negotiation, or post-approval implementation ownership.

+---------------------------------------------------------------------------------------------------------------------------------------------------------------+-----------------------------------------------------------------------------------------------------------------------------------------+
|   ----------------------------------------------------------------------------------------------------------------------------------------------------------- |   ------------------------------------------------------------------------------------------------------------------------------------- |
|   **Goals**                                                                                                                                                   |   **Non-Goals**                                                                                                                         |
|                                                                                                                                                               |                                                                                                                                         |
|   Create a governed AI-assisted environment in which domain agents operate with scoped context, auditable retrieval, and clear escalation boundaries.         |   Autonomously approve vendors, waive required approvals, or replace legal, security, or procurement judgment.                          |
|                                                                                                                                                               |                                                                                                                                         |
|   Reduce onboarding coordination overhead by transforming intake materials and enterprise policy into a structured approval package for human stakeholders.   |   Perform contract negotiation, post-approval implementation management, or broader vendor lifecycle administration.                    |
|                                                                                                                                                               |                                                                                                                                         |
|   Preserve role-based access controls and prevent unauthorized exposure of privileged or domain-restricted materials at retrieval time.                       |   Serve as a universal enterprise context platform for every organizational workflow in its first implementation.                       |
|                                                                                                                                                               |                                                                                                                                         |
|   Produce citation-complete, schema-compliant outputs that engineers and business reviewers can trace back to authoritative sources.                          |   Resolve source-authority policy, freshness SLAs, or agent behavioral rules within this document; those remain downstream artifacts.   |
|                                                                                                                                                               |   ------------------------------------------------------------------------------------------------------------------------------------- |
|   Support modular orchestration so that Security, Legal, and Procurement logic can evolve independently without redesigning the full pipeline.                |                                                                                                                                         |
|   ----------------------------------------------------------------------------------------------------------------------------------------------------------- |                                                                                                                                         |
+---------------------------------------------------------------------------------------------------------------------------------------------------------------+-----------------------------------------------------------------------------------------------------------------------------------------+

**5. Governing Engineering Principles**

This section defines the core architectural principles that govern how the system should be designed and how AI-assisted behavior should be constrained. These principles establish the non-negotiable engineering posture of the pipeline --- including source authority, permissions-aware retrieval, escalation over silent inference, and auditability by default --- and serve as the bridge between system architecture in this document and behavioral rules later formalized in the Agent Spec.

  --------- -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
  **---**   **Authoritative sources over convenience sources.** Formal policies, approval matrices, and structured intake records outrank Slack threads, meeting notes, and informal precedent.

  **---**   **Escalation over silent inference.** When facts are missing, ambiguous, conflicting, or privilege-sensitive, the pipeline escalates rather than guessing.

  **---**   **Least-context necessary.** Each agent receives only the scoped evidence bundle required for its determination; no agent receives unrestricted enterprise context.

  **---**   **Permissions-aware retrieval.** Access control is enforced before or during retrieval, not after generation.

  **---**   **Recommendations, not autonomous waivers.** The system may classify, summarize, recommend, and route, but may not waive required approvals or finalize protected decisions.

  **---**   **Citation-complete outputs.** Every nontrivial determination must be traceable to the source material that supported it.

  **---**   **Auditability by default.** Retrieval actions, determinations, escalations, and status changes are append-only and reconstructable.
  --------- -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

**6. Retrieval Strategy [\-\-- UPDATE REQUIRED]{.mark}**

Retrieval is the most architecturally differentiated component of this pipeline. The retrieval decision shapes context quality, hallucination risk, audit compliance, and access control enforcement. This section documents the chosen approach and its rationale.

**Approach Comparison**

  ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
  **APPROACH**                              **STRENGTHS**                                                                                                                                                                          **WEAKNESSES FOR THIS PIPELINE**
  ----------------------------------------- -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
  Naive RAG (vector similarity, top-k)      Simple to implement; works well for general-purpose Q&A                                                                                                                                Silent failure risk; no source authority enforcement; retrieval lottery on policy documents; cannot enforce access control at retrieval time

  Raw long-context dump                     No chunking required; preserves document structure                                                                                                                                     Context rot degrades performance beyond \~32k tokens; \"lost in the middle\" effect buries critical policy clauses; no citation discipline; cannot scale to enterprise data volumes

  **Hybrid Agentic Retrieval (selected)**   Query decomposition into source-specific subqueries; authority hierarchy applied at retrieval; role-aware access enforcement; structured context bundle per agent; citation-complete   Higher implementation complexity; requires explicit source inventory and authority configuration per retrieval run
  ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

  ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
  **DECISION: HYBRID AGENTIC RETRIEVAL**

  The Supervisor Agent decomposes each domain task into source-specific subqueries rather than issuing a single broad similarity search. Each subquery targets a specific indexed source (e.g., IT Security Policy v4.2, procurement approval matrix) using the retrieval method appropriate to that source type. Results are re-ranked by source authority (defined in the Context Contract) before being assembled into the domain agent\'s context bundle. This approach eliminates the retrieval lottery, enforces source hierarchy, and produces citation-complete outputs required by the PRD audit constraint.
  ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

**Chunking Strategy**

Chunking is document-type aware. Policy documents are chunked by section boundary (preserving numbered clause structure). The procurement approval matrix is treated as a structured table --- rows are not split across chunks. Slack threads and meeting notes are chunked by conversation thread, not by token count. Vendor questionnaire responses are ingested as a single structured object and are not chunked.

**Source Priority Application**

Source priority is applied at the re-ranking stage, after initial retrieval. Retrieved chunks are scored by semantic relevance first, then re-weighted by source authority rank (defined in the Context Contract). Chunks from informal sources (Slack threads, meeting notes) are capped in score regardless of semantic similarity, and are never surfaced as a primary citation --- only as supplementary context flagged as low-authority.

**Embedding & Search [\-\-- UPDATE REQUIRED]{.mark}**

  ---------------------------------------------------------------------------------------------------------------------------------------------------------------------
  **COMPONENT**           **DECISION**
  ----------------------- ---------------------------------------------------------------------------------------------------------------------------------------------
  Embedding model         To be confirmed in Technology Decisions Log (§10); placeholder: OpenAI text-embedding-3-small or equivalent

  Search method           Hybrid: semantic (vector) + lexical (BM25) combined; BM25 handles policy clause identifiers and section numbers that semantic search misses

  Re-ranker               Cross-encoder re-ranker applied after hybrid retrieval; source authority weighting applied on top of relevance score

  Index scope             Per-source indices (not a single shared index); allows source-specific chunking strategy and access control enforcement at index query time
  ---------------------------------------------------------------------------------------------------------------------------------------------------------------------

**7. Data Source Integration**

This section defines the integration architecture for each data source in the pipeline. Source authority rules (which source overrides which) and freshness requirements are specified in the Context Contract. This section defines the plumbing --- how each source is accessed, indexed, and surfaced.

  --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
  **SOURCE**                       **TYPE**                         **INTEGRATION METHOD / NOTES**
  -------------------------------- -------------------------------- --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
  IT Security Policy v4.2          Static versioned document        Ingested at pipeline initialization; version-pinned; not refreshed during a pipeline run. If a newer version exists, IT Security must confirm before re-indexing (see PRD Q3).

  DPA Legal Trigger Matrix         Static structured document       Ingested at initialization; Legal must confirm version before pipeline runs. Treated as authoritative for all DPA determinations.

  Procurement Approval Matrix      Static structured table          Ingested at initialization; row-level chunking preserves approval path logic. Procurement confirms version before run.

  OptiChain Vendor Questionnaire   Dynamic --- intake form          Ingested as a single structured JSON object at intake time. The Supervisor Agent validates completeness before any retrieval begins.

  Slack / meeting thread notes     Unstructured --- low authority   Ingested from a governed export; flagged as low-authority at index time. Never surfaced as primary citation. Access restricted by role.
  --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

**8. Security & Access Control Architecture**

Access control is enforced at the retrieval layer, not only at the application layer. It is insufficient to instruct an agent not to surface privileged content --- privileged documents must be excluded from the index queries that agent runs against. This section defines the technical model.

**Role-to-Source Access Matrix**

  --------------------------------------------------------------------------------------------------------
  **SOURCE**                    **IT SECURITY AGENT**   **LEGAL AGENT**         **PROCUREMENT AGENT**
  ----------------------------- ----------------------- ----------------------- --------------------------
  IT Security Policy v4.2       Full access             Read-only (reference)   Read-only (reference)

  DPA Legal Trigger Matrix      No access               Full access             No access

  Procurement Approval Matrix   No access               No access               Full access

  Vendor Questionnaire          Full access             Full access             Full access

  Slack / meeting notes         No access               No access               Procurement threads only
  --------------------------------------------------------------------------------------------------------

  ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
  **PRIVILEGED DOCUMENT EXCLUSION**

  Attorney-client privileged communications are excluded from retrieval at the index level --- they are not indexed, and no agent can retrieve them regardless of query content or instruction. This is a hard infrastructure constraint, not an agent behavioral rule. The Agent Spec may reinforce this exclusion in behavioral guidelines, but the architectural guarantee lives here. This satisfies the PRD non-negotiable constraint on privileged communication access.
  ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

**Identity Model**

The pipeline enforces a strong identity model: the Supervisor Agent must know, at runtime, which human reviewer is initiating or receiving results from the pipeline. This identity determines which sources are included in each domain agent\'s context bundle. The system refuses to escalate-of-privilege --- if a requesting reviewer does not have access to a source, that source is silently excluded from their view. It is not surfaced with a permission error that would reveal its existence.

**9. Context Budget & Window Management**

Context rot is an empirically documented failure mode: LLM performance degrades non-linearly as input length grows, and models disproportionately lose track of information in the middle of long prompts. Per-agent context budgets are an engineering constraint, not an optimization --- they must be enforced in the pipeline orchestration layer, not left to the agent\'s discretion.

**Per-Agent Token Budgets**

  -----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
  **AGENT**             **BUDGET & COMPOSITION RULES**
  --------------------- -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
  IT Security Agent     \~8,000 tokens. Questionnaire data fields + relevant IT Security Policy sections (subquery; full doc excluded) + risk classification matrix rows. Supplementary context excluded when budget is constrained.

  Legal Agent           \~6,000 tokens. IT Security Agent output (data_classification only) + relevant DPA trigger matrix rows + questionnaire EU personal data fields (eu_personal_data_flag, data_subjects_eu) + questionnaire NDA field (existing_nda_status) + ISP-001 §12.1.4 NDA clause chunk + any prior DPA precedents for this vendor class.

  Procurement Agent     \~7,000 tokens. IT Security output + Legal output + relevant approval matrix rows + prior vendor relationship context (Procurement-scoped only). Slack threads excluded unless specifically flagged.

  Checklist Assembler   \~10,000 tokens. All domain agent outputs (structured JSON) + audit log entries + final status signals. Does not receive raw source documents.

  Checkoff Agent        \~8,000 tokens. Finalized checklist output + stakeholder map + required approver list + escalation reasons (if any) + relevant domain agent determination summaries. No raw source retrieval.
  -----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

**Budget Enforcement & Priority Ordering**

When assembled context for a domain agent approaches the token budget, the pipeline applies the following priority ordering for inclusion --- highest priority first:

> **1.** Mandatory structured data: vendor questionnaire fields required for this agent\'s determination.
>
> **2.** Primary policy source: the highest-authority policy document relevant to this determination (e.g., IT Security Policy for the Security Agent).
>
> **3.** Secondary structured sources: approval matrices, trigger matrices.
>
> **4.** Supplementary context: Slack threads, meeting notes (where access-permitted). Excluded first when budget is constrained.

**10. Output Contract**

Every output the pipeline produces must conform to a defined schema. Engineers and downstream consumers (Legal, Security, Procurement reviewers) need to know the exact shape of outputs before the pipeline is built. Schemas defined here are the contract --- the Agent Spec may constrain agent behavior to produce schema-compliant outputs, but schema ownership lives in this document.

**Approval Checklist Schema**

+-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| **CHECKLIST OUTPUT FIELDS**                                                                                                                                                                                 |
+-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| **pipeline_run_id** --- Unique identifier for this pipeline run                                                                                                                                             |
|                                                                                                                                                                                                             |
| **vendor_name** --- OptiChain (or the onboarding candidate name)                                                                                                                                            |
|                                                                                                                                                                                                             |
| **overall_status** --- COMPLETE \| ESCALATED \| BLOCKED                                                                                                                                                     |
|                                                                                                                                                                                                             |
| **data_classification** --- REGULATED \| UNREGULATED \| AMBIGUOUS                                                                                                                                           |
|                                                                                                                                                                                                             |
| **dpa_required** --- boolean; dpa_blocker = true when dpa_required = true and no executed DPA is on record. dpa_blocker may be false even when dpa_required = true if an executed DPA is already confirmed. |
|                                                                                                                                                                                                             |
| **fast_track_eligible** --- boolean; always false if data_classification = REGULATED                                                                                                                        |
|                                                                                                                                                                                                             |
| **approval_path** --- STANDARD \| FAST_TRACK \| EXECUTIVE_APPROVAL                                                                                                                                          |
|                                                                                                                                                                                                             |
| **required_approvals\[\]** --- Array: {approver, domain, status, blocker, estimated_completion}                                                                                                             |
|                                                                                                                                                                                                             |
| **blockers\[\]** --- Array: {blocker_type, description, resolution_owner}                                                                                                                                   |
|                                                                                                                                                                                                             |
| **citations\[\]** --- Array: {source_name, version, section, retrieval_timestamp, agent_id}                                                                                                                 |
+-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+

**Audit Log Entry Schema**

Every retrieval operation, determination, and escalation event produces an audit log entry. The log is append-only; no entry may be modified or deleted once written.

+------------------------------------------------------------------------------+
| **AUDIT LOG ENTRY FIELDS**                                                   |
+------------------------------------------------------------------------------+
| **entry_id** --- Unique entry identifier                                     |
|                                                                              |
| **pipeline_run_id** --- Links entry to its pipeline run                      |
|                                                                              |
| **agent_id** --- Which agent produced this entry                             |
|                                                                              |
| **event_type** --- RETRIEVAL \| DETERMINATION \| ESCALATION \| STATUS_CHANGE |
|                                                                              |
| **source_queried** --- Source name and version (for RETRIEVAL events)        |
|                                                                              |
| **chunks_retrieved** --- IDs and relevance scores of retrieved chunks        |
|                                                                              |
| **timestamp** --- ISO 8601; all timestamps in UTC                            |
+------------------------------------------------------------------------------+

**Status Signal Model**

  --------------------------------------------------------------------------------------------------------------------------------------------------------------------
  **CONDITION**                                        **SYSTEM BEHAVIOR**
  ---------------------------------------------------- ---------------------------------------------------------------------------------------------------------------
  **WHEN** all domain agents return status: complete   **→ THE SYSTEM SHALL** emit COMPLETE; generate approval checklist

  **WHEN** any agent returns status: escalated         **→ THE SYSTEM SHALL** emit ESCALATED; include escalation reason; mark affected items as PENDING HUMAN REVIEW

  **WHEN** questionnaire is missing or incomplete      **→ THE SYSTEM SHALL** emit BLOCKED; halt pipeline; notify Procurement
  --------------------------------------------------------------------------------------------------------------------------------------------------------------------

**11. Failure Modes & Recovery Behavior**

The pipeline must fail safely. Failure handling is treated as part of the system architecture, not as an afterthought delegated to agent prompting. When the system cannot retrieve, validate, or interpret required inputs with sufficient confidence, it halts the affected step, emits a structured status signal, and records the event for audit.

**Failure Handling Matrix**

  -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
  **FAILURE MODE**                                   **SYSTEM RESPONSE**                                                                                                                                                 **RESOLUTION OWNER**
  -------------------------------------------------- ------------------------------------------------------------------------------------------------------------------------------------------------------------------- --------------------------------
  Missing or incomplete questionnaire submission     Emit BLOCKED; halt all downstream steps; notify Procurement; do not create a partial checklist.                                                                     Procurement

  Conflicting questionnaire versions                 Emit ESCALATED; require authoritative version selection before path classification proceeds.                                                                        Procurement

  Ambiguous ERP integration or data-handling facts   Pause onboarding path classification; surface missing fields in the audit log and route for manual Security review.                                                 IT Security

  Conflicting authoritative policy sources           Emit ESCALATED on the affected determination; halt downstream steps; require the relevant domain owners to resolve the conflict before the pipeline may continue.   IT Security + Legal

  Unauthorized or out-of-scope retrieval attempt     Fail closed; exclude the source from the context bundle; log the attempt without revealing restricted content.                                                      Platform / Security

  Malformed or schema-invalid agent output           Reject the output object; do not advance downstream; require rerun in a new pipeline run or human intervention.                                                     Engineering / Supervisor Agent

  Index unavailable or source retrieval timeout      Emit ESCALATED; preserve completed upstream outputs; log the retrieval failure; do not silently fall back to low-authority context.                                 Engineering
  -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

**12. Technology Decisions Log [\-\-- UPDATE REQUIRED]{.mark}**

Every architectural technology choice is documented here with explicit rationale tied to a requirement or constraint. When a decision changes, the old entry is superseded in the Version Log --- never deleted.

  -----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
  **DECISION**                                    **RATIONALE**                                                                                                                                                                                                                                                                                                                                                                           **REQ. SATISFIED**                                                                                    **ALTERNATIVES REJECTED**
  ----------------------------------------------- --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- ----------------------------------------------------------------------------------------------------- -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
  Sequential gate orchestration model             The PRD requirement chain (R-01 → R-02 → R-03 → R-04 → R-05) creates hard sequential dependencies. Each step must reach a terminal state before the next begins. A parallel or event-driven dispatch model would allow downstream agents to run on unresolved inputs, producing incorrect determinations. Sequential gating is the only model that respects the dependency structure.   R-01 through R-05; PRD §7 non-negotiables                                                             Parallel STEP-03/STEP-04 execution (rejected: Procurement requires Legal output to determine approval path; parallelism added implementation complexity without proportionate benefit); Event-driven pipeline (rejected: adds complexity without benefit for this dependency graph)

  Hybrid agentic retrieval (semantic + lexical)   Policy document clause retrieval requires both semantic understanding and exact-match on clause identifiers. Pure vector search misses clause IDs; pure keyword search misses semantic variants. Hybrid search with cross-encoder re-ranking addresses both failure modes.                                                                                                              Retrieval quality; citation completeness; PRD success criterion \'accepted without major revision\'   Naive top-k RAG (rejected: silent failure, no authority enforcement); Long-context dump (rejected: context rot at enterprise data volumes)

  Per-source indices (not a unified index)        Role-based access control is enforced at index query time. A unified index would require post-retrieval filtering, which creates risk of accidental inclusion. Per-source indices allow access control to be applied before retrieval begins.                                                                                                                                           PRD §7 non-negotiable: attorney-client privilege exclusion; role-based access                         Single unified vector store (rejected: access control at post-retrieval stage is insufficient); Application-layer filtering only (rejected: insufficient for privileged content)

  Append-only audit log                           The PRD requires a complete, auditable approval record. An immutable log ensures that no retrieval operation or determination can be suppressed after the fact. Required for post-process audit compliance.                                                                                                                                                                             PRD success criterion \'zero compliance gaps\'; PRD §7 auditability constraint                        Mutable event log (rejected: does not satisfy audit requirement); No log (rejected: non-starter for compliance)

  Structured JSON output per agent                Downstream agents (Checklist Assembler) consume outputs programmatically. Free-text outputs would require parsing and introduce extraction errors. Structured JSON ensures deterministic handoff between agents.                                                                                                                                                                        R-05: complete approval checklist generation; output contract reliability                             Free-text agent outputs (rejected: parsing errors; no schema enforcement); YAML (rejected: no meaningful advantage; less common for API contracts)
  -----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

**13. Non-Functional Requirements**

These requirements translate the PRD\'s R-06 cycle time target and success criteria into engineering targets. They are minimum thresholds, not optimization goals.

  ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
  **REQUIREMENT**              **METRIC**                                                **TARGET**                                                                                              **SOURCE**
  ---------------------------- --------------------------------------------------------- ------------------------------------------------------------------------------------------------------- ----------------------------------------------------------
  Latency --- AI assessment    End-to-end pipeline runtime (all inputs available)        \< 1 business day (PRD R-06); target: \< 4 hours for standard path                                      PRD R-06

  Latency --- human review     Total elapsed time including human review steps           ≤ 10 business days                                                                                      PRD R-06 / Success Criteria

  Auditability                 Coverage of audit log                                     100% of retrieval operations, determinations, and status changes logged; zero silent failures           PRD §7; PRD Success Criteria

  Citation completeness        Proportion of determinations with source citation         100%; every determination cites an authoritative source                                                 PRD Success Criteria \'accepted without major revision\'

  Checklist accuracy           Required approvals omitted from AI-generated checklist    Zero omissions, verified by post-process audit                                                          PRD Success Criteria \'zero omissions\'

  Access control enforcement   Privileged documents surfaced to unauthorized reviewers   Zero incidents                                                                                          PRD §7 non-negotiable

  Compliance gap rate          Compliance gaps attributable to this pipeline             Zero, per internal audit                                                                                PRD Success Criteria \'zero compliance gaps\'

  Availability                 Pipeline availability during business hours               \> 99% (target); graceful degradation if a source is unavailable (log, flag as provisional, continue)   Engineering baseline
  ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

**14. Handoff Map --- What This Document Does Not Answer**

This Design Document defines how the system is built. It does not specify which sources are authoritative, how agents should behave, or how agents are evaluated. Those questions are answered in downstream documents.

+-------------------------------------------------+----------------------------------------+
| **Context Contract**                            | **Agent Spec**                         |
+=================================================+========================================+
| -   Which sources are authoritative             | -   Agent roster & behavioral rules    |
|                                                 |                                        |
| -   Source authority hierarchy & override rules | -   DOs and DON\'Ts per agent          |
|                                                 |                                        |
| -   Freshness & staleness requirements          | -   Output format enforcement          |
|                                                 |                                        |
| -   Context budget & prioritization             | -   Exception handling rules           |
|                                                 |                                        |
| -   Conflict resolution protocol                | -   Evaluation criteria                |
|                                                 |                                        |
| -   Retrieval endpoint permissions              | -   Constraint Success Rate benchmarks |
+-------------------------------------------------+----------------------------------------+

**15. Open Technical Questions**

  -----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
  **Q1: ERP Integration Type --- Direct or Export-Only? (Maps to PRD Q1)**

  Determines the data classification ruling in R-02 and the access control scope in §6. If OptiChain pulls directly from ERP, the data classification is REGULATED, which affects the Security Agent context bundle composition and the upstream classification that the Legal Agent consumes as an authoritative input for STEP-03. (The Legal Agent does not directly evaluate ERP integration posture --- that determination belongs to STEP-02.) If export-only, classification may be lower, narrowing the retrieval scope. Owner: Operations, to confirm with OptiChain before retrieval indices are built.
  -----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

  --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
  **Q2: Existing Vendor Relationship? (Maps to PRD Q2)**

  An existing NDA or MSA may modify the approval path routing in the Procurement Agent. If confirmed, the Technology Decisions Log entry for \'Sequential gate orchestration model\' may need to be revisited for the approval path step. Owner: Procurement, to confirm before pipeline configuration is finalized.
  --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

  -----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
  **Q3: IT Security Policy Version --- Is v4.2 Current? (Maps to PRD Q3)**

  The retrieval index for IT Security Policy will be pinned to v4.2 at initialization. If a newer version exists or is in draft, the index must be rebuilt against the confirmed authoritative version before the pipeline runs. Owner: IT Security, to confirm before pipeline initialization.
  -----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

  -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
  **Q4: Embedding Model Selection (Engineering --- new)**

  The embedding model choice affects retrieval quality for policy documents. The Technology Decisions Log entry currently carries a placeholder. A side-by-side retrieval quality test on a sample of IT Security Policy clauses is recommended before the index is built. Owner: Engineering, to resolve before retrieval layer implementation begins.
  -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

**Version Log**

  ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
  **VERSION**   **DATE**     **AUTHOR**                      **CHANGE**
  ------------- ------------ ------------------------------- ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
  v0.1          2026-03-31   Engineering / IT Architecture   Initial draft. Architecture overview, agent orchestration model, retrieval strategy, security model, output contracts, and technology decisions established.

  **v0.8**      2026-04-10   Engineering / IT Architecture   Removed STEP-03/STEP-04 parallelism; pipeline is now fully sequential end to end. Execution graph, routing logic, and technology decisions log updated accordingly. Aligned with PRD v0.3.

  **v0.9**      2026-04-10   Engineering / IT Architecture   Integrity and alignment fixes: Procurement I/O contracts expanded; routing trigger corrected; status model precedence note added; failure modes aligned with no-same-run-revert principle.

  **v4.0**      2026-04-10   Engineering / IT Architecture   Demo simplification revision. Changes: (1) cover updated to v4.0; (2) Document Boundaries converted from table to checklist; (3) agent responsibilities scoped to demo implementation; (4) status model simplified to COMPLETE / ESCALATED / BLOCKED only --- PROVISIONAL removed throughout; (5) routing logic updated to reflect simplified signals; (6) failure modes updated to remove PROVISIONAL cases; (7) version log trimmed to first and last two entries.
  ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------