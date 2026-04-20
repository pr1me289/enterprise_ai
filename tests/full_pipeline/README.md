# Full-Pipeline Test Suite (Layer 4)

Real-API, end-to-end runs of the Supervisor orchestration layer against the
actual Anthropic API. This is the closure between the per-agent unit suites,
the handoff/acceptance layers, and the deterministic mock harness in
`test_harness/`.

Scope: drive the `Supervisor` through **STEP-01 → STEP-06** with
`AnthropicLLMAdapter`, record every LLM response, evaluate per-step
contracts, and assert orchestration-layer outcomes (overall status,
downstream-halt invariant on escalation).

---

## How it relates to `test_harness/`

| Concern | `test_harness/` | `tests/full_pipeline/` |
| --- | --- | --- |
| Adapter | `BundleAwareMockAdapter` (deterministic) | `AnthropicLLMAdapter` (real API) |
| Purpose | State-machine coverage, bundle/retrieval invariants | End-to-end validation with live models |
| Cost | Free | Paid API calls (Haiku by default) |
| Gated by | None | `@pytest.mark.api` + `ANTHROPIC_API_KEY` |
| Entry point | `test_harness/run_test_scenario.py` | `pytest tests/full_pipeline/test_end_to_end.py` |

`test_harness/__init__.py` explicitly states the mock harness is not for real
LLMs and points here.

---

## Components

### 1. `test_end_to_end.py` — the entry point

One parametrized test: `test_pipeline_end_to_end(case)`, over two scenarios:

- **scenario_1** — happy path. Overrides come from
  `orchestration.scenarios.complete_demo_scenario().questionnaire_overrides`.
  Expected: `overall_status == COMPLETE`, all six steps COMPLETE,
  STEP-05 `overall_status == COMPLETE`, STEP-06 `status == complete`.
- **scenario_2** — escalation. Overrides come from
  `tests.support.bundle_builder.scenario_2_questionnaire_overrides()`.
  Expected: `overall_status == ESCALATED`, at least one step ESCALATED,
  every downstream step remains PENDING (supervisor halt invariant). The
  exact halt step is *not* pinned — scenario_2 can legitimately escalate at
  STEP-02 (tier ambiguity) or STEP-03 (DPA blocker) depending on how the
  live IT Security agent resolves the ambiguity.

Flow:

1. Load questionnaire (`mock_documents/OptiChain_VSQ_001_v2_1.json`) +
   scenario-specific overrides.
2. Point `chunk_dir` at `data/processed/{scenario}/chunks/` (asserted to
   exist — scenarios do not share chunks).
3. Construct `AnthropicLLMAdapter(repo_root, client=anthropic_client)` and
   `Supervisor(..., llm_adapter=adapter)`.
4. Call `supervisor.run()` — this loops `execute_next_step()` until
   terminal, halting on BLOCKED / ESCALATED.
5. Emit a `PIPELINE_STEP` event per step on the live monitor so the
   console output matches the mock-harness shape.
6. Evaluate per-step via `pipeline_evaluator.evaluate_pipeline_run(...)`
   (lifts the per-agent contract checks from `per_agent_test_env`).
7. Record every response to
   `tests/recorded_responses/full_pipeline/pipeline_{N}__{agent}__{scenario}_{pass|fail}.json`.
8. Append a results block to `results/full_pipeline_test_results.md`.
9. Assert per-step verdicts, then the orchestration-layer outcome.

### 2. `tests/conftest.py` — fixtures, gating, cost guard

Key pieces:

- **API gating** (`pytest_collection_modifyitems`) — auto-skips
  `@pytest.mark.api` tests unless invoked with `-m api` **and**
  `ANTHROPIC_API_KEY` is set. A `.env` at repo root is auto-loaded if
  present.
- **Cost guard** (`_enforce_cost_guard`) — refuses to run if
  `ANTHROPIC_MODEL` is set to anything other than a Haiku prefix unless
  `ALLOW_NON_HAIKU=1`. This protects against accidental Sonnet/Opus runs
  (each scenario fans out into five domain-agent calls).
- **Call cap** (`_CapCheckedClient`) — raises once the session hits the
  configured cap (default **50**, override via `ANTHROPIC_MAX_CALLS`).
- **`anthropic_client`** (session) — a single `Anthropic()` client wrapped
  in `InstrumentedAnthropic` (times + token-counts every call) wrapped in
  `_CapCheckedClient`. Threaded into the adapter.
- **`live_monitor`** (session) — shared `LiveMonitor` used by hooks and
  tests for SESSION_START / TEST_RESULT / AGENT_CALL_* / PIPELINE_STEP /
  SESSION_END events.
- **Hooks** — `pytest_configure`, `pytest_sessionstart`,
  `pytest_collection_finish`, `pytest_runtest_logstart`,
  `pytest_runtest_logreport`, `pytest_sessionfinish` emit banner, per-test
  timing, and final summary through `live_monitor`.

### 3. `tests/support/` — helpers used by the suite

- **`bundle_builder.py`** — `build_bundles(scenario)` produces the upstream
  bundles needed when entering a step mid-pipeline.
  `scenario_2_questionnaire_overrides()` returns the questionnaire patch
  that forces a tier/DPA escalation. Also contains
  `validate_scenario_2_literals_against_spec()` to keep the fixture in
  sync with the design doc.
- **`pipeline_evaluator.py`** — `evaluate_pipeline_run(scenario, supervisor)`
  returns `{StepId: EvaluationReport}` by lifting
  `per_agent_test_env.evaluators.evaluate_recorded()`. Exports
  `format_failures(reports)` and `verdicts_from_reports(reports)`.
- **`pipeline_recorder.py`** — `next_pipeline_run_number(record_dir)` and
  `record_pipeline_run(scenario, supervisor, record_dir, verdicts,
  pipeline_run_number)` write one JSON file per agent invocation. STEP-01
  is intentionally skipped (deterministic intake, no LLM).
- **`pipeline_results_writer.py`** — `append_results_block(...)` appends a
  markdown block (status grid + totals + per-step failures + recorded-
  response paths) to `results/full_pipeline_test_results.md`.
- **`live_monitor.py`** — `LiveMonitor`, `InstrumentedAnthropic`,
  `InstrumentedMessages`. Captures elapsed seconds and input/output token
  counts as `live_monitor._last_call` on every `messages.create` call.
- **`expected_outputs.py`** / **`field_reporter.py`** — declarative field
  expectations and a "collect all failures, assert once" reporter. Used
  by per-agent tests; available here for ad-hoc checks.

### 4. `AnthropicLLMAdapter` (`src/agents/llm_caller.py`)

Implements the orchestration `LLMAdapter` protocol
(`generate_structured_json(agent_name, spec_text, prompt, bundle,
step_metadata, context_bundle)`). The adapter:

- Dispatches on `agent_name` to one of five domain agents.
- Loads the agent's system prompt via `load_system_prompt`.
- Serializes `evidence_bundle` + `step_metadata` as the user message.
- Calls `client.messages.create(model=..., max_tokens=4096, system=...,
  messages=[...])`.
- Strips ```json fences, parses JSON, runs presence-only validation via
  `find_missing_fields`.
- **Never leaks exceptions** to the state machine — errors become a minimal
  blocked payload (STEP-05 uses `overall_status: BLOCKED`; others use
  `status: blocked`). Tests can flip `raise_on_error=True` to surface
  parse/prompt bugs as pytest failures; the real adapter leaves it False.
- Records per-call telemetry into `self.call_records`.

Default model: `claude-haiku-4-5` (overridable via `ANTHROPIC_MODEL`).

### 5. Supervisor (`src/orchestration/supervisor.py`)

`Supervisor.run()` drives `execute_next_step()` in a loop until it returns
False (terminal state or completion). On each step the Supervisor:

1. Builds the per-step subquery bundle.
2. Invokes the injected `llm_adapter.generate_structured_json(...)`.
3. Runs the per-step `OutputValidator`.
4. Transitions status (COMPLETE / ESCALATED / BLOCKED), halting
   immediately on terminal non-COMPLETE.

Exposed for test inspection: `last_bundle_by_step`, `state.determinations`,
`state.step_statuses`, `state.overall_status`.

---

## Prerequisites

Before running the suite:

1. `uv sync` — install dependencies.
2. `.env` at repo root with `ANTHROPIC_API_KEY=...` (or export in shell).
3. Chunks present at:
   - `data/processed/scenario_1/chunks/`
   - `data/processed/scenario_2/chunks/`
4. Indices present at `data/indexes/`, `data/bm25/`, `data/structured/`.
5. Questionnaire file at `mock_documents/OptiChain_VSQ_001_v2_1.json`.

The test will fail fast with a readable message if any chunk directory is
missing.

---

## Environment variables

| Var | Purpose | Default |
| --- | --- | --- |
| `ANTHROPIC_API_KEY` | Required for any `-m api` run | — |
| `ANTHROPIC_MODEL` | Override default model | `claude-haiku-4-5` |
| `ANTHROPIC_MAX_CALLS` | Session-wide cap before the fixture raises | `50` |
| `ALLOW_NON_HAIKU` | Set to `1` to permit Sonnet/Opus runs | unset |

---

## Running the suite

From the repo root:

```bash
# Scenario 1 (happy path) — ~5 real API calls
uv run pytest tests/full_pipeline/test_end_to_end.py -m "api and scenario1" -v

# Scenario 2 (escalation) — halts mid-pipeline, fewer calls
uv run pytest tests/full_pipeline/test_end_to_end.py -m "api and scenario2" -v

# Both scenarios
uv run pytest tests/full_pipeline/test_end_to_end.py -m api -v
```

Without `-m api` the test is auto-skipped. Without `ANTHROPIC_API_KEY` it
is auto-skipped even with `-m api`.

---

## Artifacts produced per run

### Recorded responses

Per-agent JSON files under `tests/recorded_responses/full_pipeline/`:

```
pipeline_{N}__{agent_name}__{scenario}_{pass|fail}.json
```

Where:

- `{N}` — auto-incremented pipeline run number (via
  `next_pipeline_run_number`).
- `{agent_name}` — `it_security_agent`, `legal_agent`, `procurement_agent`,
  `checklist_assembler`, `checkoff_agent` (STEP-01 is skipped — no LLM).
- `{scenario}` — `scenario_1` | `scenario_2`.
- `{pass|fail}` — per-agent evaluator verdict for that step.

### Results block

Appended to `results/full_pipeline_test_results.md`:

```
## Pipeline Run #{N} — {scenario} — {YYYY-MM-DD}
**Overall verdict:** PASS | FAIL
**Supervisor status:** COMPLETE | ESCALATED | BLOCKED
**Pipeline run id:** {uuid}
**Halted at:** STEP-XX

| Step | Agent | Status | Verdict | Elapsed | In tokens | Out tokens |
| --- | --- | --- | --- | --- | --- | --- |
| ... | ... | ... | ... | ... | ... | ... |
| **Totals** | | | | {sum} | {sum} | {sum} |

Per-step failures: {…}

Recorded responses:
- {relative paths}
```

---

## Assertions

### Per-step (both scenarios)

`pipeline_evaluator.evaluate_pipeline_run(...)` runs the per-agent
contract checks (enum/boolean/structural field expectations from
`expected_outputs.SCENARIO_*_EXPECTATIONS`). All failures are collected
and surfaced via `format_failures(reports)` — one assertion, all missing
fields reported.

### Orchestration-layer

**scenario_1:**

- `supervisor.state.overall_status == COMPLETE`
- Every `StepId` has status `COMPLETE`
- `determinations["step_05_checklist"]["overall_status"] == "COMPLETE"`
- `determinations["step_06_guidance"]["status"] == "complete"`

**scenario_2:**

- `supervisor.state.overall_status == ESCALATED`
- At least one step has status `ESCALATED`
- Every step *after* the escalation point has status `PENDING`
  (supervisor halted — downstream steps must not have run)

---

## Cost guard details

The full pipeline fans out to five domain-agent calls per scenario. Running
both scenarios on Sonnet/Opus with retries could burn significant budget,
so:

- Default model is pinned to Haiku (`claude-haiku-4-5`).
- Overriding via `ANTHROPIC_MODEL` to a non-Haiku model **aborts** the
  session unless `ALLOW_NON_HAIKU=1` is also set (`pytest.exit` with
  return code 2).
- A hard 50-call session cap protects against runaway loops or accidental
  re-runs. Raise via `ANTHROPIC_MAX_CALLS=N`.

---

## Troubleshooting

- **Test skipped silently** — check `-m api` is on the command line and
  `ANTHROPIC_API_KEY` is set (or `.env` is at repo root and `python-dotenv`
  is installed).
- **`chunk directory not found for scenario_X`** — run the chunker for that
  scenario; the suite will not fall back to `data/processed/chunks/`.
- **`live-API call cap reached (50)`** — raise `ANTHROPIC_MAX_CALLS` or
  investigate why the run is making more calls than expected.
- **Refusing to run with ANTHROPIC_MODEL=...** — set `ALLOW_NON_HAIKU=1`
  explicitly, and confirm you want to pay for it.
- **scenario_2 escalated at a different step than expected** — this is
  legitimate. The test only requires *some* step to escalate and all
  downstream steps to remain PENDING. See the docstring in
  `test_end_to_end.py` for the reasoning.
