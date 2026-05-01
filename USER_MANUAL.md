# USER_MANUAL

Operator reference for the `enterprise_ai` repo. For _why_ over _how_, see `README.md` and `core_documents/`.

## Stack at a glance

Python 3.12+ · `uv` (deps + venv) · `pytest` · Anthropic SDK (`anthropic`) · `sentence-transformers/all-MiniLM-L6-v2` (embeddings) · Chroma (vector store) · `rank_bm25` (lexical) · `pandas`, `python-docx`, `openpyxl` (source ingestion) · `ruff` (lint). macOS / Linux. No CI/CD wired yet.

## Repo structure

```
src/                              # Application code
├── preprocessing/                # Source loading + normalization (NormalizedSource)
│   └── scenario_sources.py       # SCENARIO_DIRS registry — where each scenario reads from
├── chunking/                     # Document-type-aware chunkers + scenario chunk-artifact builder
│   └── pipeline.py               # build_scenario_chunk_artifacts(name)
├── indexing/                     # Embedding + Chroma + BM25 + structured stores + index registry
│   ├── pipeline.py               # build_and_persist_embeddings_for_scenario(name)
│   │                             # build_storage_indices_for_scenario(name)
│   └── index_registry.py         # SOURCE_STORE_CONFIG, scenario path helpers
├── retrieval/                    # Hybrid search primitives (legacy/standalone)
├── orchestration/                # Supervisor state machine + 6 step handlers
│   ├── supervisor.py             # Drives STEP-01 → STEP-06 in sequence
│   ├── steps/                    # step01_intake.py, step02_security.py, ..., step06_checkoff.py
│   ├── retrieval/                # Router, bundle assembler, hybrid backend
│   ├── audit/                    # AuditLogger (in-memory append-only)
│   └── scenarios.py              # Mock-pipeline scenario fixtures (complete_demo_scenario, …)
└── agents/
    ├── llm_caller.py             # AnthropicLLMAdapter — real-API agent dispatcher
    └── _prompts.py               # Loads system prompts from agent_spec_docs/

tests/                            # Pytest suites
├── conftest.py                   # API-key gating, cost guards, live_monitor fixture
├── unit/                         # Fast unit tests (per-module)
├── integration/                  # Cross-module tests
├── acceptance/                   # End-to-end correctness on the mock pipeline
├── orchestration/                # Supervisor + step-handler tests
├── chunking/, indexing/, preprocessing/   # Layer-specific tests
├── per_agent_live/               # Per-agent live-API smoke + assertions
├── full_pipeline/                # Live end-to-end runs (4 scenarios, ANTHROPIC_API_KEY required)
│   ├── README.md                 # ← read this before running live tests
│   └── test_end_to_end.py
├── support/                      # Test helpers (bundle_builder, pipeline_evaluator, recorder, etc.)
├── recorded_responses/           # Captured live-API outputs (one JSON per agent invocation)
└── fixtures/bundles/             # Per-agent scenario bundles (scenarios 3–15 isolation tests)

test_harness/                     # Deterministic mock pipeline (no LLM)
├── run_test_scenario.py          # CLI: --scenario <name>
├── bundle_aware_adapter.py       # Mock LLM adapter
├── scenario_fixtures.py          # The 6 deterministic scenarios
└── reporters/                    # Console + event log writers

per_agent_test_env/               # Per-agent isolated live-API testing
├── cli.py                        # CLI: --agent <name> --scenario <name> [--model <id>]
├── bundle_loader.py              # Loads fixture bundles by (agent, scenario)
├── runner.py                     # Single-agent invocation
└── evaluators.py                 # Per-scenario contract checks

scripts/                          # Reproducible scenario-data builders
├── rebuild_scenario_{7,8,9,10,13,14,15}_artifacts.py
└── rebuild_scenario_1_pam.py     # Rebuild scenario_1's PAM-001 chunks/index

scenarios_full_pipeline/          # Demo scenarios (4) — both source mocks + captured artefacts
├── scenario_1/                   # Happy-path COMPLETE
├── scenario_2/                   # Legal-blockers ESCALATED (STEP-03)
├── scenario_blocked_demo/        # STEP-04 BLOCKED (missing PAM-001 from registry)
└── scenario_escalated_step4_demo/# STEP-04 ESCALATED (no matching matrix row)
    Each scenario directory contains:
      source_mock_documents/      # Source docs that get chunked + indexed
      web_app/                    # Captured run artefacts (mirrored into the web-app repo)
      narrative.md                # (scenario_1 + scenario_2 only) demo narrative
      README.md                   # (scenario_blocked_demo + escalated_step4_demo) build notes

scenarios_per_agent/              # Scenario-scoped retrieval data for the per-agent isolation suite
                                  # (scenarios 3–15). Bundle fixtures live under
                                  # tests/fixtures/bundles/. Used by per_agent_test_env, NOT by the
                                  # live demo pipeline.

mock_documents/                   # Canonical mock corpus (master copy, fed by overrides at runtime)
mock_documents_csv_versions/      # CSV variants of the matrices

core_documents/                   # Authoritative governance + design docs
├── context_contract.md           # CC-001 — source authority, retrieval permissions, admissibility
├── design_doc.md                 # System architecture
└── supervisor_orchestration_plan.md  # ORCH-PLAN-001 — runtime contract

agent_spec_docs/                  # Per-agent behavioural specs (loaded as system prompts)
├── IT_Security_Agent_Spec.md
├── Legal_Agent_Spec.md
├── Procurement_Agent_Spec.md
├── Checklist_Assembler_Agent_Spec.md
└── Checkoff_Agent_Spec.md

data/                             # Generated artefacts (mostly gitignored)
├── processed/<scenario>/chunks/  # Chunk JSON per source
├── indexes/<scenario>/           # Chroma collections + index_registry.json
├── bm25/<scenario>/              # BM25 .pkl bundles
└── structured/<scenario>/        # Direct-structured stores (questionnaire, stakeholder map)

artifacts/test_runs/              # test_harness mock-pipeline run captures (audit logs, bundles)
results/                          # full_pipeline_test_results.md + test_results.md (append-only logs)
```

Root docs: `README.md`, `llm_agent_output_evaluation_checklist.md`, `USER_MANUAL.md` (this file).

## Pipeline architecture

Six sequential steps driven by `Supervisor.run()` (`src/orchestration/supervisor.py`). Each step has its own handler under `src/orchestration/steps/`. Status signals are `COMPLETE`, `ESCALATED`, `BLOCKED` — terminal-halt invariant: once a step reaches a non-COMPLETE terminal state, every downstream step stays `PENDING`.

| Step | Agent | What it does |
| --- | --- | --- |
| STEP-01 | (deterministic, no LLM) | Intake validation: questionnaire present + complete |
| STEP-02 | IT Security Agent | Integration tier + data classification + fast-track eligibility |
| STEP-03 | Legal Agent | DPA requirement + NDA status + blockers |
| STEP-04 | Procurement Agent | Approval-path lookup against PAM-001 |
| STEP-05 | Checklist Assembler | Roll-up of all upstream determinations |
| STEP-06 | Checkoff Agent | Stakeholder guidance documents |

## Setup

```bash
brew install uv                      # if not installed
uv sync                              # install deps from pyproject.toml + uv.lock
echo "ANTHROPIC_API_KEY=sk-ant-..." > .env   # required for live API tests
```

## Commands (from repo root)

### List every prepared testing scenario

```bash
uv run python scripts/scenarios.py                        # full catalog
uv run python scripts/scenarios.py --env full_pipeline    # only the 4 demo scenarios
uv run python scripts/scenarios.py --env per_agent        # only the per-agent isolation scenarios
uv run python scripts/scenarios.py --agent legal_agent    # one agent's per-agent scenarios
```

Prints, for each scenario, the agent it exercises, the expected terminal status, and what it proves. The catalog is hand-curated against `per_agent_test_env/evaluators.py` (per-agent expected statuses) and `tests/full_pipeline/test_end_to_end.py` (full-pipeline cases) — update `scripts/scenarios.py` when you add a scenario.

### Build scenario data (chunks + indexes)

```bash
# Build chunks for one scenario (writes to data/processed/<name>/chunks/)
PYTHONPATH=src uv run python -c "from chunking.pipeline import build_scenario_chunk_artifacts; build_scenario_chunk_artifacts('scenario_1')"

# Embed + persist Chroma vectors for a scenario's chunks
PYTHONPATH=src uv run python -c "from indexing.pipeline import build_and_persist_embeddings_for_scenario; build_and_persist_embeddings_for_scenario('scenario_1')"

# Build BM25 + structured stores + index_registry.json
PYTHONPATH=src uv run python -c "from indexing.pipeline import build_storage_indices_for_scenario; build_storage_indices_for_scenario('scenario_1')"
```

### Run tests

```bash
# Full non-API suite (unit + integration + acceptance + chunking/indexing/preprocessing/orchestration)
uv run pytest -m "not api"

# Live full-pipeline tests (real Anthropic API; gated by -m api + ANTHROPIC_API_KEY)
uv run pytest tests/full_pipeline/test_end_to_end.py -m api -v                          # all 4 scenarios
uv run pytest tests/full_pipeline/test_end_to_end.py -m "api and scenario1" -v          # one scenario
uv run pytest tests/full_pipeline/test_end_to_end.py -m "api and scenario_blocked_demo" -v

# Per-agent isolated live-API runs
PYTHONPATH=src uv run python -m per_agent_test_env.cli --agent legal_agent --scenario scenario_2

# Deterministic mock-pipeline runs (no LLM, no API key)
PYTHONPATH=src uv run python test_harness/run_test_scenario.py --scenario scenario_1_complete
PYTHONPATH=src uv run python test_harness/run_test_scenario.py --scenario scenario_2_escalated
# Available: scenario_1_complete, scenario_2_escalated, scenario_blocked_missing_questionnaire,
#            scenario_step02_escalated, scenario_step03_blocked, scenario_step04_escalated
```

### Lint / format

```bash
uv run ruff check .
uv run ruff format .
```

## Pytest markers (in `pyproject.toml`)

| Marker | What it gates |
| --- | --- |
| `api` | Tests that hit the real Anthropic API. Auto-skipped unless `-m api` is on the CLI **and** `ANTHROPIC_API_KEY` is set. |
| `scenario1`, `scenario2`, `scenario_blocked_demo`, `scenario_escalated_step4_demo` | Per-scenario filters for the live full-pipeline suite. |
| `full_pipeline`, `layer_unit`, `layer_handoff`, `layer_acceptance` | Layer filters for the broader test taxonomy. |

## Live-API safety rails (enforced by `tests/conftest.py`)

| Var | Purpose | Default |
| --- | --- | --- |
| `ANTHROPIC_API_KEY` | Required for any `-m api` run | — |
| `ANTHROPIC_MODEL` | Override default model | `claude-haiku-4-5` |
| `ANTHROPIC_MAX_CALLS` | Per-pytest-session call cap | `50` |
| `ALLOW_NON_HAIKU` | Set to `1` to permit Sonnet/Opus | unset |

The cost guard aborts the session if `ANTHROPIC_MODEL` is set to anything non-Haiku unless `ALLOW_NON_HAIKU=1`.

## Demo scenarios

Four scenarios drive both the live full-pipeline tests and the web-app demo page.

| Scenario | Halt step | Status | Mechanism |
| --- | --- | --- | --- |
| `scenario_1` | — | COMPLETE | Class C non-regulated software, fast-track happy path |
| `scenario_2` | STEP-03 | ESCALATED | DPA + NDA blockers (EU personal data, no DPA on file) |
| `scenario_blocked_demo` | STEP-04 | BLOCKED | PAM-001 absent from registry (no matrix at all) |
| `scenario_escalated_step4_demo` | STEP-04 | ESCALATED | Curated 3-row matrix; vendor profile (Class D) has no row |

Per-scenario captured artefacts live under `scenarios_full_pipeline/<name>/web_app/`:
- `agent_outputs/` — raw `parsed_output` per agent invocation (`pipeline_N__<agent>__<scenario>_pass.json`)
- `agent_input_bundles/` — the bundle each agent received as context
- `supervisor_audit_log.json` — append-only audit trail captured in-memory during the run
- `mock_documents/` — copy of the source corpus the run used
- `full_pipeline_test_results.md` — extracted markdown block for that scenario's last passing run
- `README.md` — build/integrity notes (scenarios 3 + 4 only)

## Adding or modifying a scenario

1. Source documents — drop into `scenarios_full_pipeline/<new_name>/source_mock_documents/` (use an existing scenario as the template; rename the questionnaire file).
2. Register in `src/preprocessing/scenario_sources.py` — add to `SCENARIO_DIRS` + `SCENARIO_SOURCE_CANDIDATES`.
3. Build the data:
   ```bash
   PYTHONPATH=src uv run python -c "from chunking.pipeline import build_scenario_chunk_artifacts; build_scenario_chunk_artifacts('<new_name>')"
   PYTHONPATH=src uv run python -c "from indexing.pipeline import build_and_persist_embeddings_for_scenario; build_and_persist_embeddings_for_scenario('<new_name>')"
   PYTHONPATH=src uv run python -c "from indexing.pipeline import build_storage_indices_for_scenario; build_storage_indices_for_scenario('<new_name>')"
   ```
4. Wire the test:
   - `pyproject.toml` — add a pytest marker
   - `tests/full_pipeline/test_end_to_end.py` — add a `ScenarioCase` + per-case assertions
   - `tests/support/bundle_builder.py` — add a `<new_name>_questionnaire_overrides()` factory
   - `tests/support/expected_outputs.py` — add per-step expectations
5. Run live: `uv run pytest tests/full_pipeline/test_end_to_end.py -m "api and <marker>" -v`
6. Mirror artefacts to `scenarios_full_pipeline/<new_name>/web_app/` for the demo.

For per-agent isolation tests (scenarios 3–15 pattern), see existing `scripts/rebuild_scenario_*_artifacts.py` and `scenarios_per_agent/` as templates.

## Workflow reminders

- Never commit to `main` directly — branch as `feat/...`, `fix/...`, `chore/...`, `content/...`.
- Live API tests cost real money. Default Haiku run is ~$0.05 per scenario; the 50-call session cap is your safety net.
- After a live full-pipeline run, the `bundles/` files under `tests/recorded_responses/full_pipeline/bundles/` are **overwritten**. Recorded agent outputs are appended (`pipeline_N__...`).
- The `data/` subdirs are mostly gitignored (Chroma + BM25 + structured stores). Source chunks under `data/processed/<scenario>/chunks/` are **not** gitignored — they're the canonical chunk artefacts.
- The Anthropic adapter `AnthropicLLMAdapter` (`src/agents/llm_caller.py`) **never raises** to the state machine on parse/API errors — failures become a minimal blocked payload. To debug, set `raise_on_error=True` when constructing the adapter in a one-off script.
- Re-running a scenario does NOT replace the captured artefacts in `scenarios_full_pipeline/<name>/web_app/` — those have to be mirrored manually if you want them refreshed for the demo.
