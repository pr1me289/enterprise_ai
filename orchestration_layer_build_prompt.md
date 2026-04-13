# Prompt for Coding Agent — Build the Supervisor Orchestration Layer

You are implementing the **Supervisor orchestration layer** for an enterprise AI demo.

Your job is to build the **first working version of the orchestration layer only** — not the full polished product, not a speculative architecture redesign, and not broad refactors.

## Core objective

Build a **static Python state machine** that deterministically executes the pipeline step-by-step, drives retrieval and bundle assembly, invokes LLM-backed agents with their locked spec docs as source-of-truth, updates pipeline state, and writes audit log entries after every meaningful execution event.

The intended control flow is:

1. Supervisor begins run
2. Supervisor evaluates current step and gate conditions
3. Supervisor routes retrieval requests to the correct lane
4. Retrieval engine returns evidence
5. Supervisor assembles a context bundle
6. Domain agent receives the bundle and reasons over it using its spec doc
7. Supervisor validates the returned output
8. Supervisor updates pipeline state
9. Supervisor appends audit log entries
10. Supervisor advances or halts based on status
11. Loop until terminal run state

## Architectural posture you must preserve

Treat the following as **locked**:

- The orchestration layer is a **deterministic sequential state machine**
- The Supervisor is the only orchestration authority
- The Supervisor owns:
  - step sequencing
  - gate evaluation
  - retrieval routing
  - bundle assembly
  - pipeline state mutation
  - audit log creation / append behavior
  - validation of agent outputs
- Domain agents are **LLM reasoners**, not retrievers
- Domain agents do **not** independently search sources
- Agent specs are the behavioral source of truth for each domain agent
- The questionnaire remains in the **direct structured lane**
- Indexed sources go through the **hybrid indexed lane**
- Pipeline state / checklist / audit state are **non-retrieval runtime objects**
- Keep the implementation simple, static, and demo-friendly over abstract or enterprise-heavy generalization

## What you are building in this first pass

Build a minimal but real Python implementation of:

1. **Pipeline state machine**
   - static step order
   - explicit state transitions
   - gate evaluation
   - terminal run handling

2. **Supervisor orchestration class**
   - initialize run
   - execute next step
   - dispatch retrieval
   - assemble bundle
   - call agent
   - validate result
   - append audit entries
   - mutate state
   - continue / halt

3. **Step handlers for**
   - STEP-01 Intake Validation
   - STEP-02 IT Security
   - STEP-03 Legal
   - STEP-04 Procurement
   - STEP-05 Checklist Assembler
   - STEP-06 Checkoff

4. **Retrieval router**
   - route direct structured lookups to questionnaire access
   - route indexed lookups to hybrid retrieval functions
   - route runtime reads to pipeline-state reads
   - no agent may bypass this router

5. **Bundle assembler**
   - build per-step bundles from routed evidence
   - preserve strict per-step allowed inputs
   - do not improvise new sources

6. **LLM agent invocation layer**
   - one wrapper for calling an LLM-backed agent
   - inject that agent’s spec doc as source-of-truth context
   - pass only the assembled evidence bundle plus narrowly necessary runtime context
   - return structured JSON only

7. **Audit log writer**
   - orchestration-owned, not agent-owned
   - append entries for:
     - retrieval attempts
     - retrieved/admitted/excluded evidence
     - determination emissions
     - step status changes
     - escalations
     - blocked conditions
     - run completion / halt

## Important constraint about audit behavior

The orchestration layer must **not assume the agent specs handle audit writing**.

Instead:

- agents return their structured determination
- the Supervisor records the audit events
- if the agent output is missing something required for auditable state mutation, the Supervisor should treat that as a validation issue and handle it explicitly

The audit system should be implemented as a first-class runtime concern of the Supervisor.

## Source-of-truth hierarchy for implementation

When there is ambiguity, use this precedence:

1. Locked orchestration plan
2. Locked agent spec for the current step
3. Design Doc
4. Context Contract
5. Retrieval / chunking strategy notes

Do **not** invent new architecture when these documents already constrain the behavior.

## Implementation style requirements

- Use Python
- Favor plain classes, dataclasses, enums, and typed functions
- Keep the state machine explicit and inspectable
- Prefer readability and deterministic control flow over abstraction-heavy frameworks
- Do not use LangGraph or any orchestration framework for v1
- Avoid clever dynamic registration unless it clearly improves clarity
- Keep LLM agent invocation behind a simple adapter interface so models can be swapped later
- Build with mocked retrieval and mocked LLM execution where necessary, but structure the code so real retrieval and real model calls can drop in later

## Recommended file structure

You may adjust slightly if needed, but stay close to this shape:

```text
orchestration/
  supervisor.py
  state_machine.py
  pipeline_state.py
  steps/
    step01_intake.py
    step02_security.py
    step03_legal.py
    step04_procurement.py
    step05_checklist.py
    step06_checkoff.py
  retrieval/
    router.py
    direct_structured.py
    hybrid_indexed.py
    runtime_reads.py
    bundle_assembler.py
  agents/
    base.py
    llm_agent_runner.py
    prompts/
  audit/
    audit_logger.py
    schemas.py
  validation/
    output_validator.py
    bundle_validator.py
  models/
    enums.py
    contracts.py
  config/
    step_definitions.py
    source_manifest.py
```

## Functional requirements for v1

Implement the following behaviors now:

### 1. Pipeline initialization
- create `PipelineState`
- lock manifest version
- initialize run metadata
- set all step states to pending
- enqueue STEP-01

### 2. Step execution loop
For each step:
- confirm gate condition
- mark step in progress
- execute defined retrieval plan
- assemble bundle
- call agent or supervisor-native logic where appropriate
- validate output
- write audit entries
- mutate pipeline state
- derive next step or halt

### 3. Status handling
Support the relevant step/run statuses used by the locked orchestration model.
Do not invent extra runtime states beyond what is needed for orchestration bookkeeping.

### 4. Validation
Validate:
- required bundle fields
- required output fields
- schema shape
- prohibited source contamination
- downstream admissibility for state mutation

### 5. Audit logging
Add append-only audit records with enough structure that the full run can be reconstructed later.

## LLM agent invocation requirements

For STEP-02 through STEP-06, assume LLM-backed agents.

Implement an agent runner that:
- accepts:
  - agent name
  - agent spec text
  - bundle
  - step metadata
- constructs a strict prompt telling the agent:
  - use only the provided bundle
  - obey the attached spec doc
  - emit only the required structured JSON
  - do not perform retrieval
  - do not invent sources
- parses the returned JSON
- returns it to the Supervisor for validation

For STEP-01, it is acceptable for the Supervisor to perform the logic directly rather than using an LLM.

## Retrieval implementation guidance

Build the retrieval layer to reflect the locked lane model:

- **direct structured lane**
  - questionnaire JSON / dict field lookup
- **indexed hybrid lane**
  - placeholder or mock hybrid search interface for now
  - should accept source, search terms, metadata filters, and return chunk-like objects
- **runtime read lane**
  - prior step outputs
  - pipeline state
  - audit references

Do not collapse all retrieval into one generic “search everything” function.

## What I want from you in this first coding pass

Produce:

1. a concrete implementation plan
2. the initial Python scaffolding and core files
3. a working first-pass Supervisor execution loop
4. the pipeline state model
5. step handler skeletons with real logic where straightforward
6. retrieval router scaffolding
7. bundle assembly scaffolding
8. LLM agent runner scaffolding
9. audit logger scaffolding
10. a small runnable demo path, even if retrieval/model calls are mocked

## Deliverables format

Return work in this order:

1. **Brief implementation plan**
2. **File tree**
3. **Core code files**
4. **Short explanation of how to run the first-pass demo**
5. **Any assumptions that were necessary**

## Critical guardrails

- Do not redesign the architecture
- Do not introduce parallel execution
- Do not replace the static state machine with a framework
- Do not let agents retrieve directly
- Do not merge audit logic into agents
- Do not add speculative features not required for the orchestration layer
- Do not optimize prematurely
- Do not silently change field names or step responsibilities
- Do not use vague pseudo-code where real Python can reasonably be written

## Development philosophy for this task

Be conservative, literal, and implementation-focused.

This is a **spec-driven build task**.
Your job is to translate locked architecture into a first working orchestration layer, not to invent a better architecture.

## Additional instruction

Start with a mocked retrieval backend and mocked LLM adapter, but structure the code so I can later swap in Chroma/BM25 plus real model calls without refactoring the Supervisor.
