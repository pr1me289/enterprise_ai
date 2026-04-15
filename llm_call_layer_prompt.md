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

---

## Implementation Log

### 2026-04-15 — Infrastructure built on `feat/llm-call-layer`

**Branch:** `feat/llm-call-layer` (off `main`)

**New package — `src/agents/`:**
- `__init__.py` — exports `AnthropicLLMAdapter` and the five `call_*` functions
- `_prompts.py` — `SPEC_PATHS` map + `load_system_prompt(agent_name, repo_root)`; appends an `OUTPUT_INSTRUCTION` block instructing the model to return a single JSON object with no prose or code fences
- `_validator.py` — `REQUIRED_FIELDS` map (mirrors `orchestration.validation.output_validator.REQUIRED_OUTPUT_FIELDS`) and `find_missing_fields(agent_name, output)`; never raises, never mutates
- `llm_caller.py` — the call layer:
  - `_build_client()` — loads `.env` via `python-dotenv`, constructs `anthropic.Anthropic()`
  - `_user_message_from_bundle()` — JSON-serializes `{evidence_bundle, step_metadata}` for the user turn
  - `_strip_code_fences()` + `_parse_json_response()` — tolerate ` ```json ... ``` ` wrappers and enforce dict shape
  - `_blocked_output()` — STEP-05 gets `{pipeline_run_id, vendor_name, overall_status: "BLOCKED", error}`; all other agents get `{status: "blocked", error}` (matches each step's OutputValidator halt signal)
  - `_call_agent()` — shared pipeline wrapping spec load → API call → parse → presence-check; every `Exception` is caught and converted to a blocked payload (logged with agent name + pipeline_run_id)
  - `call_it_security_agent`, `call_legal_agent`, `call_procurement_agent`, `call_checklist_assembler`, `call_checkoff_agent` — each `(bundle, pipeline_run_id) -> dict`
  - `AnthropicLLMAdapter` — implements the orchestration `LLMAdapter` protocol; lazy client construction; one instance reused across all five agent calls in a run; plugs into `Supervisor(llm_adapter=...)`

**Wiring change — `src/orchestration/supervisor.py`:**
- Default `llm_adapter` flipped from `MockLLMAdapter()` to `AnthropicLLMAdapter(repo_root=..., pipeline_run_id=...)`
- Type on the constructor parameter widened from `MockLLMAdapter | None` to `LLMAdapter | None` so the Protocol is the contract, not the mock
- No state machine / PipelineState / bundle assembly / audit changes

**Dependencies added via `uv add`:**
- `anthropic>=0.95.0`
- `python-dotenv>=1.2.2`

**Smoke test — `scripts/smoke_test_llm_agents.py`:**
- Default mode: full `complete_demo_scenario` pipeline run with `AnthropicLLMAdapter`, prints `overall_status`, per-step statuses, audit entry count, and the STEP-05 / STEP-06 top-level status fields
- `--per-agent` mode: captures each step's real `ContextBundle.structured_fields` from a mock run (via `supervisor.last_bundle_by_step`), then invokes each of the five `call_*` functions directly
- Loads `.env` and exits 2 if `ANTHROPIC_API_KEY` is not set

**Verification (no API key required):**
- `PYTHONPATH=src uv run python -c "from agents import AnthropicLLMAdapter, call_it_security_agent, call_legal_agent, call_procurement_agent, call_checklist_assembler, call_checkoff_agent"` — public API imports clean
- `PYTHONPATH=src uv run python -c "import scripts.smoke_test_llm_agents"` — smoke script imports clean
- `PYTHONPATH=src uv run pytest tests/orchestration -q` — **162 passed** (all existing tests continue to pass; `ScenarioLLMAdapter` is still explicitly injected everywhere tests need it)

**Deviation from prompt:**
- Spec filenames on disk do not carry version suffixes. The actual files are `IT_Security_Agent_Spec.md`, `Legal_Agent_Spec.md`, `Procurement_Agent_Spec.md`, `Checklist_Assembler_Spec.md`, `Checkoff_Agent_Spec.md` — not the `_v0_8` / `_v0_7` / etc. forms named in the prompt. `SPEC_PATHS` in `_prompts.py` uses the on-disk names.

**Open items:**
- Execute the smoke test with a live `ANTHROPIC_API_KEY` (user said they'd provide the key when needed) — both default and `--per-agent` modes
- Commit `feat/llm-call-layer` once the user approves (per CLAUDE.md: feature branches only, no direct commits to main; conventional commit format)
- Add a `master_log.md` entry for this session once the commit lands
