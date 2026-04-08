# Design Document — OptiChain Vendor Onboarding Pipeline v0.2

**Status:** Draft v0.2
**Owner:** Engineering / IT Architecture
**Last Updated:** March 31, 2026 (v0.2 changes applied April 7, 2026)

**Document Hierarchy:** PRD → **► Design Doc ◄** → Context Contract → Agent Spec

> This Design Document translates the business requirements from the PRD into a technical architecture for the AI-assisted software vendor onboarding pipeline. It specifies system topology, agent orchestration, retrieval strategy, security model, and output contracts. Owned by Engineering / IT Architecture. Not intended for non-technical stakeholders.
>
> **Target Audience:** Engineers tasked with a project developer role or oversight.

---

## Document Boundaries

| THIS DOCUMENT ANSWERS | THIS DOCUMENT DEFERS TO |
|-----------------------|------------------------|
| System architecture and agent wiring | Which sources are authoritative → Context Contract |
| Retrieval strategy and pipeline architecture | Source priority and conflict resolution → Context Contract |
| Security and data access control model | Agent behavioral rules and DOs / DON'Ts → Agent Spec |
| Output schemas and audit log structure | Evaluation criteria and CSR benchmarks → Agent Spec |
| Non-functional requirements (latency, auditability) | Contract negotiation or post-approval steps → Out of scope |

---

## 1. Purpose & Scope

This document defines the engineering architecture for a governed AI-assisted enterprise software vendor onboarding pipeline. It translates the PRD into a system design that engineers can implement, review, and evolve. The system is designed for a mid-size manufacturing enterprise onboarding a new software vendor. The immediate example is OptiChain, a supply-chain forecasting and inventory optimization platform under evaluation.

The design goal is not merely to answer vendor-onboarding questions with an LLM. The goal is to create an enterprise environment in which AI agents can operate safely by using scoped context, source-aware retrieval, auditable reasoning inputs, strict access controls, and human escalation points. This supports the PRD's core business objective: reduce onboarding cycle time while preserving compliance, auditability, and role-based access controls.

---

## 2. Architecture Overview

The pipeline is a sequential, gated orchestration system. Inputs enter through a single intake interface; a supervisor orchestrator routes them through domain-specific agents in dependency order; outputs are assembled into a structured approval checklist with a complete audit log. No domain agent may run until its upstream dependency has resolved — this constraint is derived directly from the PRD requirement chain (R-01 → R-02 → R-03 / R-04 → R-05).

### System Topology

| LAYER | COMPONENT | FUNCTION |
|-------|-----------|----------|
| Intake | Vendor Questionnaire Interface | Receives the OptiChain questionnaire submission; validates completeness; writes to intake store |
| Orchestration | Supervisor Agent | Enforces the execution graph; gates downstream agents; aggregates outputs; triggers escalation |
| Domain — Security | IT Security Agent | Classifies regulated data exposure; determines fast-track eligibility; cites policy sources |
| Domain — Legal | Legal Agent | Determines DPA requirement; cites legal trigger matrix; flags DPA as blocker if required |
| Domain — Procurement | Procurement Agent | Determines approval path; validates against procurement matrix; routes standard vs. fast-track |
| Output | Checklist Assembler | Composes structured approval checklist; writes audit log entries; emits final status signal |
| Output | Checkoff Agent | Facilitates checkoff procedure, compiling guidance documents for stakeholders to proceed |

### Execution Graph

The pipeline enforces a strict dependency chain. The Supervisor Agent manages this graph; no domain agent receives a context bundle until its upstream gate has resolved.

```
Step 1 → Intake validation (R-01): questionnaire completeness check. BLOCKED if not submitted.

Step 2 → Onboarding path classification (R-02): gates both Step 3 and Step 4.

Step 3 → Legal and Compliance trigger determination (R-03): runs after R-02 resolves.

Step 4 → Fast-track eligibility (R-04): runs after R-02 resolves. Steps 3 and 4 may run in parallel.

Step 5 → Approval checklist generation (R-05): runs only when R-01 through R-04 are all resolved.

Step 6 → Stakeholder guidance and checkoff support (R-06): runs only when R-01 through R-05 are all resolved.
```

Steps 3 and 4 may execute in parallel once R-02 resolves. The Supervisor Agent is responsible for managing this concurrency and ensuring both results are present before triggering Step 5. The Checklist Assembler does not run until all upstream agents have returned a resolved state.

---

## 3. Agent Orchestration Model

This section defines the orchestration contract for each agent: what it receives as input, what it returns, and what downstream components depend on its output. Behavioral rules (what the agent should and should not do) are deferred to the Agent Spec. This section defines the wiring, not the rules.

### Agent Input / Output Contracts

| AGENT | INPUT BUNDLE / OUTPUT CONTRACT |
|-------|-------------------------------|
| Supervisor Agent | **Input:** raw questionnaire submission + pipeline state<br>**Output:** execution graph with gate status per step; escalation signal if any step is BLOCKED |
| IT Security Agent | **Input:** vendor questionnaire (data classification fields) + IT Security Policy + risk matrix<br>**Output:** `{data_classification, fast_track_eligible, policy_citations[], status}` |
| Legal Agent | **Input:** IT Security Agent output (`data_classification`) + DPA legal trigger matrix<br>**Output:** `{dpa_required, dpa_blocker, trigger_rule_cited, status}` |
| Procurement Agent | **Input:** IT Security output + Legal output + procurement approval matrix<br>**Output:** `{approval_path, required_approvals[], estimated_timeline, status}` |
| Checklist Assembler | **Input:** previous domain agent outputs + audit log<br>**Output:** structured approval checklist + complete audit log + status signal (`COMPLETE` / `PROVISIONAL` / `ESCALATED` / `BLOCKED`) |
| Checkoff Agent | **Input:** all domain agent outputs + stakeholder map<br>**Output:** guidance documents |

### Routing Logic

The Supervisor Agent evaluates each step against a simple gate model:

- **RESOLVED** — step returns a valid output object with `status: resolved`
- **BLOCKED** — a required input is entirely absent; the step cannot proceed because there is nothing to reason over
- **ESCALATED** — evidence is present but conflicting or outside the defined rule set; a human decision is required before proceeding
- **PROVISIONAL** — the governing source is queryable but version-unconfirmed, or a required field is ambiguous; the step may proceed with a PROVISIONAL flag attached to its output

PROVISIONAL is a first-class pipeline status co-equal with COMPLETE, ESCALATED, and BLOCKED; it is not a substate of ESCALATED. See Context Contract §3 for the authoritative BLOCKED vs. ESCALATED vs. PROVISIONAL convention.

| CONDITION | SYSTEM BEHAVIOR |
|-----------|----------------|
| **WHEN** Questionnaire is not yet submitted | **→ THE SYSTEM SHALL** return BLOCKED status; halt all downstream steps; notify Procurement |
| **WHEN** Multiple questionnaire versions exist | **→ THE SYSTEM SHALL** escalate to Procurement before selecting a version; halt downstream steps |
| **WHEN** Data classification is ambiguous | **→ THE SYSTEM SHALL** escalate to IT Security for manual determination; halt R-03 and R-04 |
| **WHEN** R-03 and R-04 are both resolved | **→ THE SYSTEM SHALL** trigger Checklist Assembler; do not wait for manual review steps to complete |
| **WHEN** Any domain agent returns `status: escalated` | **→ THE SYSTEM SHALL** include escalation reason in checklist output; do not suppress; mark item as PENDING HUMAN REVIEW |
| **WHEN** R-05 is resolved | **→ THE SYSTEM SHALL** trigger Checkoff Agent |
| **WHEN** a required source version is unconfirmed at initialization, or a required questionnaire field is ambiguous | **→ THE SYSTEM SHALL** emit PROVISIONAL on the affected determination; allow the step to proceed with the PROVISIONAL flag attached to its output; propagate the flag to all downstream determinations that depend on it; require human confirmation before `overall_status = COMPLETE` |

---

## 4. Design Goals & Non-Goals

| GOALS | NON-GOALS |
|-------|-----------|
| Create a governed AI-assisted environment in which domain agents operate with scoped context, auditable retrieval, and clear escalation boundaries. | Autonomously approve vendors, waive required approvals, or replace legal, security, or procurement judgment. |
| Reduce onboarding coordination overhead by transforming intake materials and enterprise policy into a structured approval package for human stakeholders. | Perform contract negotiation, post-approval implementation management, or broader vendor lifecycle administration. |
| Preserve role-based access controls and prevent unauthorized exposure of privileged or domain-restricted materials at retrieval time. | Serve as a universal enterprise context platform for every organizational workflow in its first implementation. |
| Produce citation-complete, schema-compliant outputs that engineers and business reviewers can trace back to authoritative sources. | Resolve source-authority policy, freshness SLAs, or agent behavioral rules within this document; those remain downstream artifacts. |
| Support modular orchestration so that Security, Legal, and Procurement logic can evolve independently without redesigning the full pipeline. | |

---

## 5. Governing Engineering Principles

These principles establish the non-negotiable engineering posture of the pipeline. They bridge system architecture in this document and behavioral rules formalized in the Agent Spec.

- **Authoritative sources over convenience sources.** Formal policies, approval matrices, and structured intake records outrank Slack threads, meeting notes, and informal precedent.
- **Escalation over silent inference.** When facts are missing, ambiguous, conflicting, or privilege-sensitive, the pipeline escalates rather than guessing.
- **Least-context necessary.** Each agent receives only the scoped evidence bundle required for its determination; no agent receives unrestricted enterprise context.
- **Permissions-aware retrieval.** Access control is enforced before or during retrieval, not after generation.
- **Recommendations, not autonomous waivers.** The system may classify, summarize, recommend, and route, but may not waive required approvals or finalize protected decisions.
- **Citation-complete outputs.** Every nontrivial determination must be traceable to the source material that supported it.
- **Auditability by default.** Retrieval actions, determinations, escalations, and status changes are append-only and reconstructable.

---

## 6. Retrieval Strategy ⚠️ UPDATE REQUIRED

Retrieval is the most architecturally differentiated component of this pipeline. The retrieval decision shapes context quality, hallucination risk, audit compliance, and access control enforcement.

### Approach Comparison

| APPROACH | STRENGTHS | WEAKNESSES FOR THIS PIPELINE |
|----------|-----------|------------------------------|
| Naive RAG (vector similarity, top-k) | Simple to implement; works well for general-purpose Q&A | Silent failure risk; no source authority enforcement; retrieval lottery on policy documents; cannot enforce access control at retrieval time |
| Raw long-context dump | No chunking required; preserves document structure | Context rot degrades performance beyond ~32k tokens; "lost in the middle" effect buries critical policy clauses; no citation discipline; cannot scale to enterprise data volumes |
| **Hybrid Agentic Retrieval (selected)** | Query decomposition into source-specific subqueries; authority hierarchy applied at retrieval; role-aware access enforcement; structured context bundle per agent; citation-complete | Higher implementation complexity; requires explicit source inventory and authority configuration per retrieval run |

**DECISION: HYBRID AGENTIC RETRIEVAL**

The Supervisor Agent decomposes each domain task into source-specific subqueries rather than issuing a single broad similarity search. Each subquery targets a specific indexed source (e.g., IT Security Policy v4.2, procurement approval matrix) using the retrieval method appropriate to that source type. Results are re-ranked by source authority (defined in the Context Contract) before being assembled into the domain agent's context bundle. This approach eliminates the retrieval lottery, enforces source hierarchy, and produces citation-complete outputs required by the PRD audit constraint.

### Chunking Strategy

Chunking is document-type aware:

- **Policy documents** — chunked by section boundary (preserving numbered clause structure)
- **Procurement approval matrix** — treated as a structured table; rows are not split across chunks
- **Slack threads and meeting notes** — chunked by conversation thread, not by token count
- **Vendor questionnaire responses** — ingested as a single structured object; not chunked

### Source Priority Application

Source priority is applied at the re-ranking stage, after initial retrieval. Retrieved chunks are scored by semantic relevance first, then re-weighted by source authority rank (defined in the Context Contract). Chunks from informal sources (Slack threads, meeting notes) are capped in score regardless of semantic similarity, and are never surfaced as a primary citation — only as supplementary context flagged as low-authority.

### Embedding & Search ⚠️ UPDATE REQUIRED

| COMPONENT | DECISION |
|-----------|----------|
| Embedding model | `sentence-transformers/all-MiniLM-L6-v2` |
| Search method | Hybrid: semantic (vector) + lexical (BM25) combined; BM25 handles policy clause identifiers and section numbers that semantic search misses |
| Re-ranker | Cross-encoder re-ranker applied after hybrid retrieval; source authority weighting applied on top of relevance score |
| Index scope | Per-source indices (not a single shared index); allows source-specific chunking strategy and access control enforcement at index query time |

---

## 7. Data Source Integration

Source authority rules (which source overrides which) and freshness requirements are specified in the Context Contract. This section defines the plumbing — how each source is accessed, indexed, and surfaced.

| SOURCE | TYPE | INTEGRATION METHOD / NOTES |
|--------|------|---------------------------|
| IT Security Policy v4.2 | Static versioned document | Ingested at pipeline initialization; version-pinned; not refreshed during a pipeline run. If a newer version exists, IT Security must confirm before re-indexing (see PRD Q3). |
| DPA Legal Trigger Matrix | Static structured document | Ingested at initialization; Legal must confirm version before pipeline runs. Treated as authoritative for all DPA determinations. |
| Procurement Approval Matrix | Static structured table | Ingested at initialization; row-level chunking preserves approval path logic. Procurement confirms version before run. |
| OptiChain Vendor Questionnaire | Dynamic — intake form | Ingested as a single structured JSON object at intake time. The Supervisor Agent validates completeness before any retrieval begins. |
| Prior vendor decisions (precedents) | Semi-structured | Ingested from a governed precedent store. Access restricted by role (see §8). Serves as supplementary context, not primary citation. |
| Slack / meeting thread notes | Unstructured — low authority | Ingested from a governed export; flagged as low-authority at index time. Never surfaced as primary citation. Access restricted by role. |

### Staleness Handling

Sources are versioned at index time. If a source version cannot be confirmed before a pipeline run, the system treats it as unverified, logs the uncertainty in the audit record, and flags the affected determinations as PROVISIONAL.

PROVISIONAL is a first-class pipeline status (see §10): the pipeline may continue with PROVISIONAL-flagged outputs, but the flag propagates to all downstream determinations that depend on the unverified source, and `overall_status` cannot be emitted as COMPLETE until all PROVISIONAL flags are resolved by the designated confirmation owner.

The authoritative rules governing PROVISIONAL evidence conditions are defined in Context Contract §3 and §4. This constraint directly addresses PRD Q3 (IT Security Policy version status).

---

## 8. Security & Access Control Architecture

Access control is enforced at the retrieval layer, not only at the application layer. It is insufficient to instruct an agent not to surface privileged content — privileged documents must be excluded from the index queries that agent runs against.

### Role-to-Source Access Matrix

| SOURCE | IT SECURITY AGENT | LEGAL AGENT | PROCUREMENT AGENT |
|--------|-------------------|-------------|-------------------|
| IT Security Policy v4.2 | Full access | Read-only (reference) | Read-only (reference) |
| DPA Legal Trigger Matrix | No access | Full access | No access |
| Procurement Approval Matrix | No access | No access | Full access |
| Vendor Questionnaire | Full access | Full access | Full access |
| Prior vendor decisions | Security decisions only | Legal decisions only | Procurement decisions only |
| Slack / meeting notes | No access | No access | Procurement threads only |
| Attorney-client privileged communications | No access | No access (excluded at index level) | No access |

**PRIVILEGED DOCUMENT EXCLUSION:** Attorney-client privileged communications are excluded from retrieval at the index level — they are not indexed, and no agent can retrieve them regardless of query content or instruction. This is a hard infrastructure constraint, not an agent behavioral rule. The Agent Spec may reinforce this exclusion in behavioral guidelines, but the architectural guarantee lives here. This satisfies the PRD non-negotiable constraint on privileged communication access.

### Identity Model

The pipeline enforces a strong identity model: the Supervisor Agent must know, at runtime, which human reviewer is initiating or receiving results from the pipeline. This identity determines which sources are included in each domain agent's context bundle. The system refuses to escalate-of-privilege — if a requesting reviewer does not have access to a source, that source is silently excluded from their view. It is not surfaced with a permission error that would reveal its existence.

---

## 9. Context Budget & Window Management

Context rot is an empirically documented failure mode: LLM performance degrades non-linearly as input length grows, and models disproportionately lose track of information in the middle of long prompts. Per-agent context budgets are an engineering constraint, not an optimization — they must be enforced in the pipeline orchestration layer, not left to the agent's discretion.

### Per-Agent Token Budgets

| AGENT | BUDGET & COMPOSITION RULES |
|-------|---------------------------|
| IT Security Agent | ~8,000 tokens. Questionnaire data fields + relevant IT Security Policy sections (subquery; full doc excluded) + risk classification matrix rows. Supplementary context excluded when budget is constrained. |
| Legal Agent | ~6,000 tokens. IT Security Agent output (`data_classification` only) + relevant DPA trigger matrix rows + any prior DPA precedents for this vendor class. |
| Procurement Agent | ~7,000 tokens. IT Security output + Legal output + relevant approval matrix rows + prior vendor relationship context (Procurement-scoped only). Slack threads excluded unless specifically flagged. |
| Checklist Assembler | ~10,000 tokens. All domain agent outputs (structured JSON) + audit log entries + final status signals. Does not receive raw source documents. |
| Checkoff Agent | ~8,000 tokens. Finalized checklist output + stakeholder map + required approver list + escalation reasons (if any) + relevant domain agent determination summaries. No raw source retrieval. |

### Budget Enforcement & Priority Ordering

When assembled context for a domain agent approaches the token budget, the pipeline applies the following priority ordering for inclusion — highest priority first:

1. Mandatory structured data: vendor questionnaire fields required for this agent's determination.
2. Primary policy source: the highest-authority policy document relevant to this determination (e.g., IT Security Policy for the Security Agent).
3. Secondary structured sources: approval matrices, trigger matrices.
4. Precedent context: prior vendor decisions relevant to this determination.
5. Supplementary context: Slack threads, meeting notes (where access-permitted). Excluded first when budget is constrained.

---

## 10. Output Contract

Every output the pipeline produces must conform to a defined schema. Schema ownership lives in this document. The Agent Spec may constrain agent behavior to produce schema-compliant outputs, but schema definitions are authoritative here.

### Approval Checklist Schema

| FIELD | DESCRIPTION |
|-------|-------------|
| `pipeline_run_id` | Unique identifier for this pipeline run |
| `vendor_name` | OptiChain (or the onboarding candidate name) |
| `overall_status` | `COMPLETE` \| `PROVISIONAL` \| `ESCALATED` \| `BLOCKED` |
| `data_classification` | `REGULATED` \| `UNREGULATED` \| `AMBIGUOUS` |
| `dpa_required` | Boolean; if true, `dpa_blocker = true` |
| `fast_track_eligible` | Boolean; always false if `data_classification = REGULATED` |
| `approval_path` | `STANDARD` \| `FAST_TRACK` \| `EXECUTIVE_APPROVAL` |
| `required_approvals[]` | Array: `{approver, domain, status, blocker, estimated_completion}` |
| `blockers[]` | Array: `{blocker_type, description, resolution_owner}` |
| `citations[]` | Array: `{source_name, version, section, retrieval_timestamp, agent_id}` |

### Audit Log Entry Schema

Every retrieval operation, determination, and escalation event produces an audit log entry. The log is append-only; no entry may be modified or deleted once written.

| FIELD | DESCRIPTION |
|-------|-------------|
| `entry_id` | Unique entry identifier |
| `pipeline_run_id` | Links entry to its pipeline run |
| `agent_id` | Which agent produced this entry |
| `event_type` | `RETRIEVAL` \| `DETERMINATION` \| `ESCALATION` \| `STATUS_CHANGE` |
| `source_queried` | Source name and version (for RETRIEVAL events) |
| `chunks_retrieved` | IDs and relevance scores of retrieved chunks |
| `timestamp` | ISO 8601; all timestamps in UTC |

### Status Signal Model

| CONDITION | SYSTEM BEHAVIOR |
|-----------|----------------|
| **WHEN** all domain agents return `status: resolved` | **→ THE SYSTEM SHALL** emit COMPLETE; generate approval checklist |
| **WHEN** any agent returns `status: escalated` | **→ THE SYSTEM SHALL** emit ESCALATED; include escalation reason; mark affected items as PENDING HUMAN REVIEW |
| **WHEN** questionnaire is missing or incomplete | **→ THE SYSTEM SHALL** emit BLOCKED; halt pipeline; notify Procurement |
| **WHEN** a required policy source version is unverified | **→ THE SYSTEM SHALL** emit PROVISIONAL on all affected determinations; allow the pipeline to continue with PROVISIONAL flags attached; propagate the PROVISIONAL flag to all downstream determinations that depend on the unverified source or ambiguous field; deliver a PROVISIONAL checklist to stakeholders if R-05 completes — this checklist is not final; require human confirmation from the designated source owner before `overall_status` may be updated to COMPLETE. PROVISIONAL is a first-class pipeline status co-equal with COMPLETE, ESCALATED, and BLOCKED. It is not a substate of ESCALATED. A PROVISIONAL pipeline run has produced real output that humans can act on — it is not a failure. The authoritative evidence conditions that trigger PROVISIONAL are defined in Context Contract §3 and §11. |

---

## 11. Failure Modes & Recovery Behavior

The pipeline must fail safely. Failure handling is treated as part of the system architecture, not as an afterthought delegated to agent prompting.

| FAILURE MODE | SYSTEM RESPONSE | RESOLUTION OWNER |
|--------------|----------------|-----------------|
| Missing or incomplete questionnaire submission | Emit BLOCKED; halt all downstream steps; notify Procurement; do not create a partial checklist. | Procurement |
| Conflicting questionnaire versions | Emit ESCALATED; require authoritative version selection before path classification proceeds. | Procurement |
| Ambiguous ERP integration or data-handling facts | Pause onboarding path classification; surface missing fields in the audit log and route for manual Security review. | IT Security |
| Conflicting authoritative policy sources | **Unverified source version:** emit PROVISIONAL on all affected determinations; pipeline may continue with PROVISIONAL flags attached; require human version confirmation before COMPLETE. **Conflicting authoritative sources:** emit ESCALATED on the affected determination; prevent checklist completion for impacted items until the conflict is resolved by the relevant domain owners. These are distinct cases — PROVISIONAL applies when evidence is present but unverified; ESCALATED applies when evidence is present but conflicting. | IT Security + Legal |
| Unverified source version at runtime | Allow retrieval only if explicitly permitted as provisional; flag all dependent outputs for human confirmation. | Owning domain team |
| Unauthorized or out-of-scope retrieval attempt | Fail closed; exclude the source from the context bundle; log the attempt without revealing restricted content. | Platform / Security |
| Malformed or schema-invalid agent output | Reject the output object; keep the step unresolved; require rerun or human intervention before downstream use. | Engineering / Supervisor Agent |
| Index unavailable or source retrieval timeout | Return provisional unresolved state for the affected determination; preserve completed upstream outputs; avoid silent fallback to low-authority context. | Engineering |

---

## 12. Technology Decisions Log ⚠️ UPDATE REQUIRED

Every architectural technology choice is documented here with explicit rationale tied to a requirement or constraint. When a decision changes, the old entry is superseded in the Version Log — never deleted.

| DECISION | RATIONALE | REQ. SATISFIED | ALTERNATIVES REJECTED |
|----------|-----------|---------------|----------------------|
| Sequential gate orchestration model | The PRD requirement chain (R-01 → R-02 → R-03 / R-04 → R-05) creates hard dependencies. A parallel dispatch model would allow downstream agents to run on unresolved inputs, producing incorrect determinations. Sequential gating is the only model that respects the dependency structure. | R-01 through R-05; PRD §7 non-negotiables | Parallel dispatch (rejected: violates R-02 gate function); Event-driven pipeline (rejected: adds complexity without benefit for this dependency graph) |
| Hybrid agentic retrieval (semantic + lexical) | Policy document clause retrieval requires both semantic understanding and exact-match on clause identifiers. Pure vector search misses clause IDs; pure keyword search misses semantic variants. Hybrid search with cross-encoder re-ranking addresses both failure modes. | Retrieval quality; citation completeness; PRD success criterion 'accepted without major revision' | Naive top-k RAG (rejected: silent failure, no authority enforcement); Long-context dump (rejected: context rot at enterprise data volumes) |
| Per-source indices (not a unified index) | Role-based access control is enforced at index query time. A unified index would require post-retrieval filtering, which creates risk of accidental inclusion. Per-source indices allow access control to be applied before retrieval begins. | PRD §7 non-negotiable: attorney-client privilege exclusion; role-based access | Single unified vector store (rejected: access control at post-retrieval stage is insufficient); Application-layer filtering only (rejected: insufficient for privileged content) |
| Append-only audit log | The PRD requires a complete, auditable approval record. An immutable log ensures that no retrieval operation or determination can be suppressed after the fact. Required for post-process audit compliance. | PRD success criterion 'zero compliance gaps'; PRD §7 auditability constraint | Mutable event log (rejected: does not satisfy audit requirement); No log (rejected: non-starter for compliance) |
| Structured JSON output per agent | Downstream agents (Checklist Assembler) consume outputs programmatically. Free-text outputs would require parsing and introduce extraction errors. Structured JSON ensures deterministic handoff between agents. | R-05: complete approval checklist generation; output contract reliability | Free-text agent outputs (rejected: parsing errors; no schema enforcement); YAML (rejected: no meaningful advantage; less common for API contracts) |

---

## 13. Non-Functional Requirements

These requirements translate the PRD's R-06 cycle time target and success criteria into engineering targets. They are minimum thresholds, not optimization goals.

| REQUIREMENT | METRIC | TARGET | SOURCE |
|-------------|--------|--------|--------|
| Latency — AI assessment | End-to-end pipeline runtime (all inputs available) | < 1 business day (PRD R-06); target: < 4 hours for standard path | PRD R-06 |
| Latency — human review | Total elapsed time including human review steps | ≤ 10 business days | PRD R-06 / Success Criteria |
| Auditability | Coverage of audit log | 100% of retrieval operations, determinations, and status changes logged; zero silent failures | PRD §7; PRD Success Criteria |
| Citation completeness | Proportion of determinations with source citation | 100%; every determination cites an authoritative source or is flagged as provisional | PRD Success Criteria 'accepted without major revision' |
| Checklist accuracy | Required approvals omitted from AI-generated checklist | Zero omissions, verified by post-process audit | PRD Success Criteria 'zero omissions' |
| Access control enforcement | Privileged documents surfaced to unauthorized reviewers | Zero incidents | PRD §7 non-negotiable |
| Compliance gap rate | Compliance gaps attributable to this pipeline | Zero, per internal audit | PRD Success Criteria 'zero compliance gaps' |
| Availability | Pipeline availability during business hours | > 99% (target); graceful degradation if a source is unavailable (log, flag as provisional, continue) | Engineering baseline |

---

## 14. Handoff Map — What This Document Does Not Answer

This Design Document defines how the system is built. It does not specify which sources are authoritative, how agents should behave, or how agents are evaluated. Those questions are answered in downstream documents.

| CONTEXT CONTRACT | AGENT SPEC |
|-----------------|------------|
| Which sources are authoritative | Agent roster & behavioral rules |
| Source authority hierarchy & override rules | DOs and DON'Ts per agent |
| Freshness & staleness requirements | Output format enforcement |
| Context budget & prioritization | Exception handling rules |
| Conflict resolution protocol | Evaluation criteria |
| Retrieval endpoint permissions | Constraint Success Rate benchmarks |

---

## 15. Open Technical Questions

**Q1: ERP Integration Type — Direct or Export-Only? (Maps to PRD Q1)**

Determines the data classification ruling in R-02 and the access control scope in §6. If OptiChain pulls directly from ERP, the data classification is REGULATED, which affects the Security Agent context bundle composition and the Legal Agent DPA determination. If export-only, classification may be lower, narrowing the retrieval scope. **Owner:** Operations, to confirm with OptiChain before retrieval indices are built.

---

**Q2: Existing Vendor Relationship? (Maps to PRD Q2)**

An existing NDA or MSA may modify the approval path routing in the Procurement Agent. If confirmed, the Technology Decisions Log entry for 'Sequential gate orchestration model' may need to be revisited for the approval path step. **Owner:** Procurement, to confirm before pipeline configuration is finalized.

---

**Q3: IT Security Policy Version — Is v4.2 Current? (Maps to PRD Q3)**

The retrieval index for IT Security Policy will be pinned to v4.2 at initialization. If a newer version exists or is in draft, the index must be rebuilt against the confirmed authoritative version before the pipeline runs. Until confirmed, all Security Agent determinations will be flagged PROVISIONAL. **Owner:** IT Security, to confirm before pipeline initialization.

---

**Q4: Embedding Model Selection (Engineering — new)**

The embedding model choice affects retrieval quality for policy documents. The Technology Decisions Log entry currently carries a placeholder. A side-by-side retrieval quality test on a sample of IT Security Policy clauses is recommended before the index is built. **Owner:** Engineering, to resolve before retrieval layer implementation begins.

---

## Version Log

| VERSION | DATE | AUTHOR | CHANGE |
|---------|------|--------|--------|
| v0.1 | 2026-03-31 | Engineering / IT Architecture | Initial draft. Architecture overview, agent orchestration model, retrieval strategy, security model, output contracts, and technology decisions established. |
| v0.2 | 2026-04-07 | Engineering / IT Architecture | PROVISIONAL status formalized as first-class pipeline status. Changes: (1) cover status updated to Draft v0.2; (2) gate model definition extended with formal PROVISIONAL gate state, distinct from BLOCKED and ESCALATED; (3) routing logic table: new PROVISIONAL routing row added; (4) Checklist Assembler output contract updated to include PROVISIONAL in status signal list; (5) overall_status schema field updated to COMPLETE \| PROVISIONAL \| ESCALATED \| BLOCKED; (6) Status Signal Model: PROVISIONAL row expanded with full first-class definition, flag propagation rules, and cross-reference to Context Contract §3 and §11; (7) Staleness Handling paragraph updated to use PROVISIONAL consistently with the formalized definition; (8) Failure Modes table: "PROVISIONAL or ESCALATED" case split into two distinct entries per the unified BLOCKED/ESCALATED/PROVISIONAL convention. Harmonized with Context Contract CC-001 v1.1. |
