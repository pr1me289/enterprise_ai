# Orchestration Layer Build Prompt for Coding Agent

## Objective

Build the first deterministic version of the orchestration layer for the enterprise AI vendor onboarding demo.

This system must prove that the supervisor can drive the pipeline step by step, retrieve only the allowed evidence for each step, assemble an admissible context bundle, call the appropriate step handler, mutate pipeline state, write audit entries, and halt correctly on `COMPLETE`, `BLOCKED`, or `ESCALATED`.

The immediate goal is **not** to build a fully LLM-driven agent system. The immediate goal is to build a **working deterministic supervisor loop** that runs both demo scenarios correctly using the chunked corpora and structured records already prepared.

---

## Core Mental Model

The orchestration layer is the **supervisor-controlled runtime layer**.

It is responsible for:

- moving the pipeline from step to step
- checking gate conditions
- deciding what retrieval is needed at each step
- invoking the retrieval layer
- assembling the admissible context bundle
- calling the current domain step handler
- validating the returned output
- mutating pipeline state
- writing audit log entries
- halting or advancing based on status

The retrieval engine is functionally part of this orchestration flow, but it is **subordinate to the supervisor**.

The correct runtime model is:

1. **Supervisor / orchestration layer**
   - decides what step is active
   - checks whether the gate is satisfied
   - determines which sources are allowed
   - determines which subqueries should run
   - determines which retrieval lane should be used
   - decides what evidence is admitted into the bundle

2. **Retrieval layer**
   - executes the supervisor’s retrieval requests
   - performs direct structured lookup for questionnaire / structured records
   - performs indexed retrieval for policy / matrix / Slack chunk stores
   - returns retrieved candidates with provenance

3. **Domain step handler**
   - receives only the scoped bundle for the current step
   - produces a determination object for that step

4. **Supervisor again**
   - validates the returned result
   - updates pipeline state
   - appends audit entries
   - determines whether to continue, block, or escalate

The supervisor is therefore both:
- the **traffic controller**
- and the **evidence gatekeeper**

This system is **not** “RAG first, agent second.”

It is:

**supervisor-governed retrieval first, then step-bounded agent execution.**

---

## Immediate Development Goal

Build the **first deterministic end-to-end supervisor loop** with:

- real pipeline state mutation
- real retrieval routing
- real bundle assembly
- real admissibility checks
- mocked or deterministic step reasoning
- full audit logging

This version should be able to run:

- **Scenario 1** → deterministic `COMPLETE`
- **Scenario 2** → deterministic halt at the intended first `ESCALATED` step

Only after this works should live LLM-backed step handlers be introduced.

---

## Required Runtime Models

Finalize and lock the runtime data contracts first.

Implement models for:

- `PipelineState`
- `StepStatus`
- `EscalationPayload`
- `AuditLogEntry`
- `RetrievedChunk`
- `ContextBundle`

Also implement determination models for each step:

- `Step01IntakeDetermination`
- `Step02SecurityDetermination`
- `Step03LegalDetermination`
- `Step04ProcurementDetermination`
- `Step05ChecklistDetermination`
- `Step06CheckoffDetermination`

### Expectations for these models

#### `PipelineState`
Should contain at minimum:
- run identifiers
- current step
- overall status
- step statuses
- step determinations
- escalation payloads
- audit references
- next-step queue

#### `StepStatus`
Use the canonical statuses:
- `PENDING`
- `IN_PROGRESS`
- `COMPLETE`
- `BLOCKED`
- `ESCALATED`

#### `RetrievedChunk`
Should contain:
- source metadata
- chunk identifier
- authority tier
- retrieval lane
- citable flag
- text payload
- provenance / citation label

#### `ContextBundle`
Should contain:
- current step
- admitted evidence
- excluded evidence with reasons
- relevant structured fields
- source provenance
- bundle admissibility status

#### `AuditLogEntry`
Should capture:
- timestamp
- step
- event type
- event details
- source reference if applicable
- status transition if applicable

---

## Retrieval Architecture to Build

Build a retrieval router that operates under supervisor control.

### Responsibilities of the retrieval router
Given:
- current step
- allowed sources
- retrieval lane
- step subquery plan

it should return:
- retrieved candidate chunks and records
- source metadata
- provenance labels
- exclusion reasons when applicable

### Retrieval lanes to support now

#### 1. `DIRECT_STRUCTURED`
Used for structured access like:
- questionnaire JSON
- stakeholder map JSON if still used downstream

Behavior:
- direct field lookup
- no semantic ranking
- exact retrieval from structured store

#### 2. `INDEXED_HYBRID`
Used for:
- IT Security Policy chunks
- DPA Legal Trigger Matrix chunks
- Procurement Approval Matrix chunks
- Slack thread chunks

Behavior:
- deterministic lookup from prebuilt chunk JSON files for now
- may simulate ranking if needed, but should remain deterministic
- preserve citation and source metadata

### Important rule
The retrieval layer must **not** decide authority, admissibility, or escalation on its own.

It may return candidates.

The **supervisor / bundle assembly logic** decides:
- what is admissible
- what is excluded
- what is supplementary only
- whether evidence is sufficient
- whether ambiguity requires escalation

---

## Bundle Assembly and Admissibility

This is the heart of the orchestration layer.

Implement bundle assembly logic that, for each step:

1. collects retrieved candidates
2. applies source-permission constraints
3. applies authority hierarchy rules
4. excludes out-of-scope or non-admissible evidence
5. records exclusion reasons
6. assembles the final context bundle
7. determines whether the bundle is:
   - admissible
   - incomplete
   - escalation-worthy

### Bundle assembly must enforce

- source authority hierarchy
- lane-specific retrieval behavior
- primary citation rules
- low-authority suppression for Slack
- scenario-specific relevance filtering
- exclusion of irrelevant retrieved threads
- deterministic provenance

### Specific things the system must demonstrate

- Thread 4 in Slack is excluded from OptiChain determinations
- Slack is supplementary only and never primary evidence
- structured questionnaire facts are passed through cleanly
- matrix rows are retrieved as atomic rule-table evidence
- policy sections are retrieved with stable citation labels

---

## Step Handlers to Implement

Implement deterministic step handlers first.

Create functions such as:

- `run_step_01_intake()`
- `run_step_02_security()`
- `run_step_03_legal()`
- `run_step_04_procurement()`
- `run_step_05_checklist()`
- `run_step_06_checkoff()`

These do **not** need live LLMs yet.

They may use deterministic logic over the assembled bundle.

### Step 01 — Intake
Must:
- confirm questionnaire exists
- confirm completeness
- confirm no version conflict
- emit `COMPLETE` or `BLOCKED`

### Step 02 — Security
Must:
- evaluate ERP integration tier
- evaluate data classification
- evaluate fast-track eligibility inputs from security perspective
- preserve ambiguity where formal evidence is insufficient
- emit `COMPLETE` or `ESCALATED`

### Step 03 — Legal
Must:
- inspect DPA trigger applicability
- inspect NDA status
- determine legal blockers
- emit `COMPLETE` or `ESCALATED`

### Step 04 — Procurement
Must:
- derive approval path from structured procurement matrix logic
- incorporate upstream outputs
- determine required approvals and timeline
- emit `COMPLETE` or `ESCALATED`

### Step 05 — Checklist
Must:
- compile prior determinations
- assemble final approval checklist
- emit overall checklist status

### Step 06 — Checkoff
Must:
- generate downstream stakeholder guidance only
- not alter the substantive checklist result
- use finalized outputs plus stakeholder map / downstream config

---

## Control Flow Expectations

Implement a sequential supervisor loop that:

1. initializes `PipelineState`
2. sets current step to `STEP-01`
3. evaluates gate conditions before each step
4. retrieves only the sources allowed for that step
5. assembles the context bundle
6. calls the step handler
7. validates the returned object
8. updates step status and pipeline state
9. writes audit entries
10. halts or advances

### Transition rules
A step must move:
- `PENDING -> IN_PROGRESS -> TERMINAL_STATE`

Terminal states:
- `COMPLETE`
- `BLOCKED`
- `ESCALATED`

A terminal step must not revert within the same run.

### Run-level expectations
The supervisor should:
- halt on the first required blocking condition
- halt on the first escalation condition if the scenario requires that behavior
- preserve escalation payloads and audit entries
- keep all transitions deterministic

---

## Audit Logging Requirements

Every important runtime event should write an audit entry.

At minimum, log:

- step status changes
- retrieval attempts
- retrieved candidates
- excluded evidence and exclusion reason
- admitted evidence
- gate evaluation results
- domain determinations
- escalation payload creation
- pipeline halt or completion

The audit log is not optional. It is part of the demo value.

---

## Scenario Execution Requirements

### Scenario 1
The system must prove that it can:
- retrieve the correct evidence
- exclude irrelevant Slack thread content
- assemble admissible bundles
- produce the clean fast-track path
- emit final `COMPLETE`

### Scenario 2
The system must prove that it can:
- retrieve the correct evidence
- preserve ambiguity where required
- assemble admissible but escalation-worthy bundles
- halt at the intended first escalation
- emit the correct `ESCALATED` outcome

---

## Suggested Initial File / Module Layout

Use a structure roughly like this:

```text
supervisor.py
pipeline_state.py
models/
  step_status.py
  determinations.py
  retrieved_chunk.py
  context_bundle.py
  escalation.py
  audit_log.py
step_handlers/
  step_01_intake.py
  step_02_security.py
  step_03_legal.py
  step_04_procurement.py
  step_05_checklist.py
  step_06_checkoff.py
retrieval/
  router.py
  index_lookup.py
  structured_lookup.py
bundle_assembler.py
admissibility.py
audit_logger.py
scenario_data/
  scenario_1/
  scenario_2/
```

This does not need to be exact, but the separation of concerns should remain clear.

---

## Implementation Priorities

Build in this order:

1. runtime data contracts
2. pipeline state initialization and mutation logic
3. retrieval router
4. structured and indexed lookup helpers
5. bundle assembly
6. admissibility checks
7. deterministic step handlers
8. supervisor execution loop
9. audit logging
10. scenario 1 and scenario 2 end-to-end verification

Do **not** introduce live LLM calls until the deterministic version works.

---

## Explicit Non-Goals for This Phase

Do **not** prioritize the following yet:

- polished UI
- multi-model orchestration
- live human escalation workflow
- probabilistic retrieval
- prompt tuning
- agent memory beyond pipeline state
- generalized autonomous behavior

This phase is about proving the pipeline runtime and governed context flow.

---

## Success Condition for This Phase

This phase is successful when the system can:

- run Scenario 1 deterministically to `COMPLETE`
- run Scenario 2 deterministically to the intended first `ESCALATED` halt
- retrieve the right chunks / records for each step
- exclude irrelevant or low-authority misuse
- assemble clean step bundles
- preserve provenance and auditability
- produce stable state transitions

That is the milestone to hit before integrating live LLM-backed domain agents.

---

## Final Instruction to Coding Agent

Implement the orchestration layer as a **deterministic supervisor-governed runtime**, not as a loose agentic workflow.

The supervisor must remain the authority over:
- execution sequencing
- gate logic
- retrieval routing
- source permissions
- bundle admissibility
- escalation behavior
- pipeline state mutation
- audit logging

The retrieval layer must remain an execution component under supervisor control.

The domain step handlers must remain bounded to the scoped bundle they are given.

Build the deterministic version first. Prove both scenarios end to end. Only then introduce live LLM-backed step handlers.
