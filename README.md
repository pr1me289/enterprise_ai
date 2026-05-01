# Spec-Driven Enterprise Context Engineering

> A Python-built pipeline for **governed enterprise AI** — turning heterogeneous source material into auditable, permission-aware, citation-complete evidence bundles for downstream LLM agents.

This project demonstrates how to build an AI workflow that doesn't treat all enterprise data the same. Instead of a single undifferentiated vector search, it routes each source through the correct retrieval lane (indexed-hybrid, direct-structured, or non-retrieval), preserves authority hierarchies, enforces per-agent permissions, and produces an audit log of every retrieval and determination.

The reference scenario is an AI-assisted vendor onboarding pipeline at a fictional manufacturer ("Lichen Manufacturing"), evaluating a fictional vendor ("OptiChain"). Six sequential agent steps decide whether the vendor passes intake, what data classification applies, whether a DPA is required, what approval path the procurement team should follow, and what guidance to surface to stakeholders.

Link to the narrative web-app presentation: [https://www.piercenellessen.com](https://www.piercenellessen.com)

Github repo for the web-app: [https://github.com/pr1me289/web-app-enterprise-ai](https://github.com/pr1me289/web-app-enterprise-ai)

---

## Table of contents

- [Architecture at a glance](#architecture-at-a-glance)
- [Demo scenarios](#demo-scenarios)
- [Quick start](#quick-start)
- [Repository layout](#repository-layout)
- [Tech stack](#tech-stack)
- [Documentation](#documentation)
- [License](#license)

---

## Architecture at a glance

```
   ┌──────────────────────┐
   │  source documents    │  PDFs, Markdown, JSON, CSV, XLSX
   └──────────┬───────────┘
              │
   ┌──────────▼───────────┐
   │  preprocessing       │  → NormalizedSource objects (typed metadata)
   ├──────────────────────┤
   │  chunking            │  → document-type-aware chunks (section / row / thread)
   ├──────────────────────┤
   │  indexing            │  → Chroma (dense) + BM25 (lexical) + structured stores
   ├──────────────────────┤
   │  retrieval           │  → router + permission gates + authority-aware reranker
   ├──────────────────────┤
   │  orchestration       │  → Supervisor state machine driving STEP-01 → STEP-06
   └──────────┬───────────┘
              │
   ┌──────────▼───────────┐
   │  approval checklist  │  + audit log + stakeholder guidance
   └──────────────────────┘
```

Three retrieval **lanes** govern how each source is reached:

| Lane | Examples | How |
|---|---|---|
| **Indexed hybrid** | IT Security Policy, DPA Trigger Matrix, Procurement Approval Matrix, Slack notes | Chunked → embedded (Chroma) + BM25 → fused → reranked by source authority |
| **Direct structured** | Vendor questionnaire JSON, Stakeholder map | Loaded as a typed object → field-path lookup, never embedded |
| **Non-retrieval** | Audit log, pipeline state, checklist output | Runtime state, never indexed |

Six **agent steps**:

| Step | Agent | Determines |
|---|---|---|
| STEP-01 | (deterministic, no LLM) | Questionnaire intake validation |
| STEP-02 | IT Security | Integration tier · data classification · fast-track eligibility |
| STEP-03 | Legal | DPA requirement · NDA status · blockers |
| STEP-04 | Procurement | Approval path lookup against PAM-001 |
| STEP-05 | Checklist Assembler | Roll-up of all upstream determinations |
| STEP-06 | Checkoff Agent | Stakeholder guidance documents |

The Supervisor halts on any non-`COMPLETE` terminal status — `ESCALATED` and `BLOCKED` both stop downstream execution and surface the run for human review.

---

## Demo scenarios

Four end-to-end scenarios exercise every terminal status and the major escalation paths. All four are runnable against the real Anthropic API.

| Scenario | Halt step | Final status | What it shows |
|---|---|---|---|
| `scenario_1` | — | **COMPLETE** | Happy path. Class C non-regulated vendor, fast-track approval, full pipeline runs through STEP-06 |
| `scenario_2` | STEP-03 | **ESCALATED** | Legal blockers — DPA required but not executed, NDA pending. Halts at Legal |
| `scenario_blocked_demo` | STEP-04 | **BLOCKED** | Procurement Approval Matrix is missing from the index. No evidence base to begin work |
| `scenario_escalated_step4_demo` | STEP-04 | **ESCALATED** | Curated 3-row matrix; vendor profile (Class D) doesn't match any row. Evidence present but unresolvable |

Captured run artefacts (raw agent outputs, input bundles, supervisor audit logs, source corpora) live under `scenarios_full_pipeline/<name>/web_app/` and feed a separate web-app demo of the pipeline.

To list every prepared testing scenario (full-pipeline + per-agent) with the agent it exercises and what it proves:

```bash
uv run python scripts/scenarios.py                        # everything
uv run python scripts/scenarios.py --env full_pipeline    # 4 demo scenarios
uv run python scripts/scenarios.py --agent legal_agent    # one agent's per-agent scenarios
```

---

## Quick start

**Prerequisites:** macOS or Linux, Python 3.12+, [`uv`](https://docs.astral.sh/uv/) (`brew install uv`), an Anthropic API key for live tests.

```bash
# 1. Install dependencies
uv sync

# 2. Set your Anthropic API key (only needed for live tests)
echo "ANTHROPIC_API_KEY=sk-ant-..." > .env

# 3. Run the deterministic mock pipeline (no API key required)
PYTHONPATH=src uv run python test_harness/run_test_scenario.py --scenario scenario_1_complete

# 4. Run the full non-API test suite
uv run pytest -m "not api"

# 5. Run a live end-to-end scenario against the Anthropic API
uv run pytest tests/full_pipeline/test_end_to_end.py -m "api and scenario_1" -v
```

**Cost note:** live tests default to `claude-haiku-4-5`. A single full-pipeline run is roughly 5 API calls (~$0.05). A 50-call session cap (`ANTHROPIC_MAX_CALLS`) protects against runaway loops. Sonnet/Opus runs are blocked unless you explicitly opt in with `ALLOW_NON_HAIKU=1`.

For complete operator instructions (rebuilding scenario data, adding a new scenario, running per-agent isolated tests, etc.), see **[USER_MANUAL.md](USER_MANUAL.md)**.

---

## Repository layout

```
src/                  # Pipeline implementation (preprocessing → chunking → indexing → retrieval → orchestration)
├── preprocessing/    # NormalizedSource model + scenario source-path registry
├── chunking/         # Document-type-aware chunkers
├── indexing/         # Chroma + BM25 + structured stores + index registry
├── retrieval/        # Hybrid search primitives
├── orchestration/    # Supervisor state machine + 6 step handlers + audit logger
└── agents/           # AnthropicLLMAdapter + system-prompt loader

tests/                # pytest suites — unit, integration, acceptance, orchestration, full_pipeline
test_harness/         # Deterministic mock pipeline (no LLM, no API key required)
per_agent_test_env/   # Per-agent isolated live-API testing harness
scripts/              # Reproducible scenario-data builders

scenarios_full_pipeline/  # Demo scenarios (source mocks + captured run artefacts) — 4 scenarios for the end-to-end suite
scenarios_per_agent/      # Scenario-scoped retrieval data for the per-agent isolation suite (scenarios 3–15)
mock_documents/       # Canonical mock corpus
core_documents/       # Authoritative governance + design docs
agent_spec_docs/      # Per-agent behavioural specs (loaded as system prompts)

data/                 # Generated artefacts: chunks, Chroma collections, BM25 bundles, structured stores
results/              # Append-only test run logs
```

Detailed file-by-file map: [USER_MANUAL.md](USER_MANUAL.md).

---

## Tech stack

- **Python 3.12+** managed via [`uv`](https://docs.astral.sh/uv/) (deps + venv)
- **Anthropic SDK** (`anthropic`) — live agent calls; default model `claude-haiku-4-5`
- **`sentence-transformers/all-MiniLM-L6-v2`** — local embedding generation
- **Chroma** — dense vector storage
- **`rank_bm25`** — lexical retrieval
- **`pandas`, `python-docx`, `openpyxl`** — source document ingestion
- **`pytest`** — test framework with custom markers for live-API gating
- **`ruff`** — linting + formatting

No web framework, no UI in this repo. The companion web-app project consumes the captured artefacts under `scenarios_full_pipeline/`.

---

## Documentation

| Doc | Audience | What it covers |
|---|---|---|
| **[USER_MANUAL.md](USER_MANUAL.md)** | Operators | Step-by-step commands for every workflow: install, build scenarios, run tests, add a scenario |
| **[core_documents/context_contract.md](core_documents/context_contract.md)** | Governance | Source authority hierarchy, retrieval permissions, evidence admissibility, conflict resolution, citation requirements (CC-001) |
| **[core_documents/design_doc.md](core_documents/design_doc.md)** | Engineers | Pipeline topology, agent orchestration model, retrieval strategy, security model, output contracts |
| **[core_documents/supervisor_orchestration_plan.md](core_documents/supervisor_orchestration_plan.md)** | Engineers | Runtime contract for supervisor execution, per-step gate conditions, subqueries, output contracts (ORCH-PLAN-001) |
| **[agent_spec_docs/](agent_spec_docs/)** | Engineers + LLM | Per-agent behavioural specs — these files are loaded as system prompts at runtime |
| **[tests/full_pipeline/README.md](tests/full_pipeline/README.md)** | Operators | Live-API test harness: cost guards, fixtures, expected behaviour per scenario |

If `core_documents/context_contract.md` and `core_documents/design_doc.md` conflict, the Context Contract wins for retrieval and source-governance decisions; the Design Doc wins for orchestration mechanics.

---

## License

All rights reserved. © 2026 Pierce Nellessen.
