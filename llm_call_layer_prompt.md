# CLAUDE.md — LLM Call Layer Implementation

## Context

The OptiChain vendor onboarding pipeline has a fully built and tested orchestration layer, retrieval engine, context bundle assembly system, and Python state machine. All domain agents currently run as mocks. Your task is to implement the LLM call layer that replaces those mocks with real Anthropic API calls.

Do not touch anything outside the domain agent call layer unless explicitly required to wire it in.

---

## What You Are Building

A module — `agents/llm_caller.py` — and supporting utilities that sit between the existing orchestration layer and the Anthropic API. When the Supervisor assembles a context bundle for a domain agent step, this layer receives that bundle, calls the appropriate LLM agent, and returns a validated JSON output to the state machine.

The five domain agents requiring LLM calls are:
- IT Security Agent (STEP-02)
- Legal Agent (STEP-03)
- Procurement Agent (STEP-04)
- Checklist Assembler (STEP-05)
- Checkoff Agent (STEP-06)

STEP-01 (intake validation) is pure deterministic Python — no LLM call.

---

## Architecture

Each agent call follows the same pattern:
1. Load the agent's spec `.md` file as the system prompt
2. Format the pre-assembled context bundle as the user message
3. Call the Anthropic API
4. Parse the JSON response
5. Validate required output fields are present
6. Return the output dict to the state machine

The state machine reads `output["status"]` to decide whether to advance (`complete`) or halt (`escalated` / `blocked`). This interface does not change from the mock implementation.

---

## File Structure to Create

```
agents/
  __init__.py
  llm_caller.py       ← primary implementation target
  _prompts.py         ← spec file loader with output instruction appended
  _validator.py       ← required field presence check per agent output contract

specs/                ← agent spec .md files (already exist)
```

---

## Agent Spec Files

Each agent has a corresponding spec document in `specs/`. These files define the agent's behavioral contract and output contract. The spec file is the system prompt — load it as-is and append a short output instruction block telling the model to return only a valid JSON object with no surrounding text.

Spec file to agent mapping:
- STEP-02 → `IT_Security_Agent_Spec_v0_8.md`
- STEP-03 → `Legal_Agent_Spec_v0_7.md`
- STEP-04 → `Procurement_Agent_Spec_v0_6.md`
- STEP-05 → `Checklist_Assembler_Spec_v0_2.md`
- STEP-06 → `Checkoff_Agent_Spec_v0_2.md`

---

## Environment

API key and model are read from environment variables. Use `python-dotenv`. Model defaults to `claude-haiku-4-5` — this is for development and testing. Never hardcode the model or API key.

---

## Error Handling

Every exception — JSON parse failure, API error, validation failure, anything — must be caught and converted to a minimal `status: blocked` return dict. The state machine must never receive an unhandled exception from this layer. Log all failures with the `pipeline_run_id` and agent ID for traceability.

If the model returns JSON wrapped in markdown code fences despite the output instruction, strip them before parsing.

---

## Validation

Each agent has a defined output contract in its spec doc. The validator checks that required fields are present and non-null. On failure, log the missing fields but still return whatever the model produced — do not silently discard partial output. The state machine's `status` field handling determines what happens next.

---

## Wiring Into the Orchestration Layer

Locate the existing mock agent call sites in the orchestration layer and replace them with the corresponding functions from `llm_caller.py`. The function signature is identical to the mocks: takes `(bundle: dict, pipeline_run_id: str)`, returns `dict`. Do not change the state machine, PipelineState mutation rules, bundle assembly, or audit logging.

---

## Constraints

- Do not modify the state machine, PipelineState, audit logger, or bundle assembly
- No retry logic — that is a later pass
- No Instructor or Pydantic validation — that is a later pass
- Model always read from env var
- All exceptions must be caught and returned as blocked-status — no unhandled exceptions reach the state machine
- `llm_caller.py` should stay lean — if it grows large, the abstraction is wrong

---

## Success Criteria

1. A smoke test script calling each agent with a minimal valid bundle passes against the real API
2. A full pipeline run with real agents completes without crashing
3. The state machine's advance and halt logic behaves identically to the mock run
4. All five mock call sites in the orchestration layer are replaced with `llm_caller.py` functions
5. No mock agent code remains in the active execution path
