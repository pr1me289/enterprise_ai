# Per-Agent Live-LLM Test Environment

Runs exactly **one** domain agent against the real Anthropic API, using its
spec file as the system prompt and a pre-assembled context bundle as the
user message. Records the raw response to disk **before** any evaluation
runs, then evaluates the saved response against the output contract
defined in `llm_agent_output_evaluation_checklist.md`.

No supervisor. No pipeline state. No cascading.

---

## Decision: separate dedicated environment, not an extension of `test_harness/`

The `per_agent_test_environment_prompt.md` required us to choose between
extending the existing test harness or creating a new, dedicated environment.

We chose **separate environment**, installed at `per_agent_test_env/`
(parallel to `test_harness/`).

**Why:**

- `test_harness/` is mock-backed: its runner wires `BundleAwareMockAdapter`
  into `Supervisor` and walks the full next-step queue end-to-end. Every
  design choice in that module assumes a full pipeline run.
- Per-agent isolation needs a fundamentally simpler shape — load spec →
  load bundle → one API call → record raw → evaluate — with no supervisor
  or pipeline state.
- Mixing the two concerns would bloat `test_harness/` and obscure which
  tests drive the whole pipeline vs. which tests isolate a single agent.
- Keeping this module separate lets us:
    - Record raw responses to `tests/recorded_responses/` before evaluation.
    - Halt on first failure by default (no cascading), as required.
    - Reuse the same spec files, bundle fixtures, call-layer helpers, and
      validators that the real pipeline uses — no duplication.

Shared code is reused, not re-implemented:
`agents._prompts.load_system_prompt`, `agents.llm_caller._build_client`,
`agents.llm_caller._user_message_from_bundle`,
`agents.llm_caller._parse_json_response`, `agents._validator.REQUIRED_FIELDS`.

---

## Module layout

```
per_agent_test_env/
├── __init__.py          # public API
├── README.md            # this file
├── bundle_loader.py     # loads the (agent, scenario) fixture from tests/fixtures/bundles/
├── evaluators.py        # deterministic evaluators derived from the output checklist
├── reporter.py          # explicit stdout reporting of agent + scenario + raw + result
├── runner.py            # run_agent_test(agent_name, scenario, ...) -> AgentTestResult
└── cli.py               # argparse entry point for `python -m per_agent_test_env.cli`
```

Raw recorded responses land in `tests/recorded_responses/` as one JSON
file per call:

```
tests/recorded_responses/it_security_agent__scenario_1__20260415T154210Z.json
```

Each record contains: agent name, scenario, pipeline_run_id, model, timestamp,
spec path, bundle fixture path, raw model text, parsed output, and any error
captured during the call.

---

## Usage

### Prerequisites

- `ANTHROPIC_API_KEY` in the environment (or in `.env` at the repo root).
- Dependencies installed with `uv sync`.

### Single agent, single scenario

```bash
uv run python -m per_agent_test_env.cli --agent it_security_agent --scenario scenario_1
```

### Both scenarios for one agent (halts on first failure)

```bash
uv run python -m per_agent_test_env.cli --agent legal_agent --all-scenarios
```

### Every agent × every scenario (halts on first failure)

```bash
uv run python -m per_agent_test_env.cli --all
```

### Overrides

```bash
--model claude-sonnet-4-6        # model override (default: claude-haiku-4-5)
--max-tokens 8192                # max_tokens override (default: 4096)
--recorded-dir custom/out/       # recorded-responses dir override
--repo-root /path/to/enterprise_ai
```

### Exit codes

| Code | Meaning                                                      |
|------|--------------------------------------------------------------|
| 0    | every selected run passed every hard check                   |
| 1    | at least one hard check failed — runner halted, no cascading |
| 2    | configuration / argument error                               |

---

## Programmatic use

```python
from per_agent_test_env import run_agent_test

result = run_agent_test("legal_agent", "scenario_1")
if not result.passed:
    for failure in result.failures:
        print(f"FAIL: {failure}")
print(f"raw response recorded at: {result.recorded.recorded_file}")
```

The function returns an `AgentTestResult` dataclass with the recorded-file
path, the parsed output, any warnings, and the full failure list.

---

## Contract guarantees

These are enforced by the runner and are verifiable from the code:

1. **One agent per invocation.** The runner does not call any other agent
   and does not advance pipeline state. The supervisor module is never
   imported by this environment.
2. **Realistic, contract-shaped bundle per agent.** The loader validates
   that each fixture's declared `agent` and `scenario` match the caller's
   request before the bundle is used.
3. **Both scenarios coverable per agent.** Every `(agent, scenario)` pair
   has a fixture in `tests/fixtures/bundles/`.
4. **Record-before-evaluate.** The raw response is written to
   `tests/recorded_responses/` *before* the evaluator runs. The evaluator
   never re-calls the model and only inspects the saved parsed output.
5. **Explicit reporting.** The runner prints a banner with the agent name
   and scenario, the raw text (truncated with a pointer to the recorded
   file for very long outputs), the parsed output, any warnings, and a
   PASS / FAIL line with explicit failure reasons.
6. **Halt on first failure.** When `--all` or `--all-scenarios` runs hit a
   failure, the runner stops and emits a HALT message. It does not fall
   through to the next agent automatically. The caller must re-invoke
   after a deliberate code or prompt change.

---

## Test-double smoke tests

`tests/per_agent_live/test_runner_smoke.py` exercises the full runner flow
with a stub Anthropic client. These tests run under regular `pytest` (no
`-m api` required) because they make no real API calls — they verify the
record-before-evaluate ordering, the fixture loader, the evaluator logic
on both pass and fail paths, and the CLI exit codes.

```bash
uv run pytest tests/per_agent_live -v
```
