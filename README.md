# enterprise_ai

## Overview

`enterprise_ai` is a Python-based enterprise AI demo focused on governed evidence delivery, not generic vector search. The project will ingest enterprise source material, convert it into retrieval-ready evidence units, route those units through the correct retrieval lane, and later deliver scoped context bundles to downstream agents in a way that preserves authority, permissions, freshness, and auditability.

The current repository contains mock procurement, legal, security, and stakeholder documents that are used to build and demonstrate this pipeline. Preprocessing, chunking, embedding, storage/indexing, and retrieval scaffolding now exist under `src/`.

## Required Reading Before Implementation

Before starting any implementation work, read the core repository documents in this order:

1. `core_documents/context_contract.md`
2. `core_documents/design_doc.md`
3. `STRATEGY.md`

`core_documents/context_contract.md` is the authoritative governance document for source authority, retrieval permissions, provenance requirements, conflict resolution, freshness/versioning, and evidence admissibility. `core_documents/design_doc.md` is the engineering architecture reference for pipeline topology, orchestration, output contracts, and retrieval-system design. If these documents conflict, defer to `core_documents/context_contract.md` for retrieval and source-governance decisions.

Implementation should not begin until these documents have been reviewed alongside this README.

## Architecture

The architecture is intentionally split into two major layers.

- Governed retrieval infrastructure
- Agentic retrieval behavior

The governed retrieval infrastructure is responsible for source ingestion, document-type-aware chunking, metadata attachment, embeddings for indexed sources, and storage/index preparation. The agentic retrieval layer is responsible for later query planning, source routing, hybrid retrieval execution, authority-aware reranking, and context bundle assembly.

The core design principle is that the system should not treat all inputs the same. It should preserve enterprise meaning by normalizing each source into the correct internal form for its role in the pipeline.

Current repository contents:

- `mock_documents/` contains sample enterprise documents in PDF, JSON, Markdown, and spreadsheet formats.
- `AGENTS.md` and `CLAUDE.md` define repository-level engineering and AI workflow rules.
- Implementation code lives in `src/` and tests live in `tests/`.
- `STRATEGY.md` defines the target retrieval architecture, preprocessing rules, and build sequence.

## Source Lanes

The project strategy fixes three source treatment lanes.

- Indexed hybrid lane: policy, legal matrix, procurement matrix, precedent log, and Slack or meeting notes will be chunked, metadata-tagged, embedded, and indexed.
- Direct structured lane: the vendor questionnaire JSON will be loaded as a structured object and accessed directly by field rather than embedded.
- Non-retrieval state lane: checklist, audit, and runtime pipeline state will remain outside retrieval entirely.

This separation is the core architectural choice for the demo. It shows that enterprise AI systems need governed source treatment rather than one undifferentiated search layer.

## Execution Plan

The current plan is phased and deliberately incremental.

1. Build the preprocessing layer first.
2. Normalize each source into enterprise-meaningful evidence units.
3. Attach source-derived metadata needed for filtering, permissions, citations, freshness, and audit logging.
4. Embed only indexed-hybrid sources with `sentence-transformers/all-MiniLM-L6-v2`.
5. Store dense vectors in Chroma and build BM25 indices with `rank_bm25`.
6. Keep questionnaire access in a direct structured store such as JSON, Python dicts, or lightweight SQLite.
7. Build retrieval planning, lane routing, reranking, and context bundle assembly after preprocessing is stable.
8. Keep the Supervisor as the retrieval planner rather than allowing domain agents to search the full corpus freely.

Planned preprocessing behavior by source:

- IT security policy: section-boundary chunking
- DPA legal trigger matrix: row-level chunking
- Procurement approval matrix: row-level chunking
- Vendor questionnaire: no chunking, direct structured access
- Prior vendor decisions: record-level chunking
- Slack or meeting notes: thread-level chunking

## Purpose

The purpose of this project is to demonstrate how an enterprise system converts heterogeneous source material into governed evidence units and later delivers curated evidence bundles to specialized agents. The intended outcome is a demo that clearly shows:

- source-governed preprocessing
- lane-specific retrieval preparation
- hybrid retrieval across dense, lexical, and structured access paths
- authority-aware evidence ranking
- permission-aware evidence delivery
- auditable context bundle construction

The project should not read like "we built a vector database and called it enterprise AI." The value is in the governance model around retrieval.

## Setup

This repository now includes a `pyproject.toml`, `uv.lock`, and a growing automated test suite.

Prerequisites for the next build stage:

1. Install Git.
2. Install GitHub CLI if you plan to push changes with `gh`.
3. Install `uv` for Python dependency and environment management.
4. Use external environment variables or `gh auth login` for authentication. Do not commit secrets.

Environment variables:

- No project-specific environment variables are required yet.
- When secrets are introduced, keep them outside the repository and document them in `.env.example`.

## Usage

There is still no user-facing application or retrieval service in the repository yet. At this stage, the repository provides preprocessing, chunking, and embedding/indexing utilities plus tests while the governed retrieval pipeline is being built incrementally.

Typical current usage:

1. Review the sample documents in `mock_documents/`.
2. Review `core_documents/context_contract.md` first. It is the authoritative source for retrieval governance, source permissions, provenance, and conflict handling.
3. Review `core_documents/design_doc.md` next for the engineering architecture and output contracts.
4. Review `STRATEGY.md` for the locked retrieval and preprocessing approach.
5. Use `src/preprocessing/` to normalize raw source files into `NormalizedSource` objects with inherited source-level metadata.
6. Use `src/chunking/` to convert chunkable normalized sources into canonical `Chunk` objects and write JSON artifacts to `data/processed/chunks/`.
7. Use `src/indexing/` to embed indexed-hybrid chunk artifacts and build per-source Chroma collections, BM25 bundles, a direct structured questionnaire store, and an index registry.
8. Use `src/retrieval/` to route source-specific queries through permission checks, hybrid search, authority-aware reranking, and retrieval manifest generation.
9. Use the repository rules in `AGENTS.md` before adding code or automation.

Current implementation notes:

- Preprocessing detects source type, preserves source structure, and attaches source-level metadata before any chunking. For this demo, all current normalized sources inherit the same source-level defaults: `document_date=2026-04-04` and `freshness_status=CURRENT`.
- The `source_type` contract is now intentionally explicit and source-specific: `POLICY_DOCUMENT`, `LEGAL_TRIGGER_MATRIX`, `PROCUREMENT_APPROVAL_MATRIX`, `VENDOR_QUESTIONNAIRE`, `VENDOR_PRECEDENT`, and `SLACK_THREAD`.
- Chunking consumes `NormalizedSource` objects only, attaches finalized chunk metadata at creation time, and writes inspectable intermediate JSON artifacts. Current chunk artifacts carry inherited `document_date`, `freshness_status`, `is_primary_citable`, and reviewed precedent `domain_scope` values needed for later storage/indexing work.
- Indexing now consumes finalized chunk artifacts, embeds only indexed-hybrid chunks with `sentence-transformers/all-MiniLM-L6-v2`, and persists vectors plus inherited chunk metadata into Chroma.
- Storage/indexing now builds per-source logical indices over shared backends: Chroma collections for `idx_security_policy`, `idx_dpa_matrix`, `idx_procurement_matrix`, `idx_precedents`, and `idx_slack_notes`; BM25 bundles under `data/bm25/`; a direct structured questionnaire store at `vq_direct_access`; and `data/indexes/index_registry.json` for explainable build metadata.
- Retrieval scaffolding now includes explicit source routing, endpoint permission guards, hybrid fusion, authority-aware reranking, and retrieval manifest objects under `src/retrieval/`.

## Storage And Index Outputs

Step 8 writes three different persistence forms because the repository does not treat every source the same. These are per-source logical indices over shared backends, not one undifferentiated global store.

- Indexed-hybrid sources are stored twice: once as dense vectors in Chroma and once as lexical BM25 bundles.
- The questionnaire is not embedded. It is stored as a direct structured object for field-level access.
- A central registry records which logical indices and stores exist, what source each one represents, and which backends belong to it.

High-level flow:

1. Finalized chunk artifacts are read from `data/processed/chunks/`.
2. Indexed-hybrid chunks are grouped by source and written into per-source logical indices over shared Chroma and BM25 backends.
3. The questionnaire is loaded directly from its normalized source and written to a structured JSON store.
4. `data/indexes/index_registry.json` is written so retrieval code can route requests to the correct backend with explainable metadata.

### Chroma Collections

Chroma is the dense-vector backend for semantic retrieval over finalized chunk objects, not raw source files.

- Persisted data directory: `data/indexes/chroma/`
- Human-inspectable registry mirror: `data/indexes/vector_registry/`
- Builder code: `src/indexing/build_vector_index.py`
- Collection names:
  - `idx_security_policy`
  - `idx_dpa_matrix`
  - `idx_procurement_matrix`
  - `idx_precedents`
  - `idx_slack_notes`

Each Chroma record stores the chunk text as the retrievable evidence unit plus inherited chunk metadata such as `source_id`, `source_type`, `authority_tier`, `retrieval_lane`, `version`, `document_date`, `freshness_status`, `allowed_agents`, `manifest_status`, and document-specific identifiers like `section_id`, `row_id`, or `thread_id` when present. Governance fields such as `allowed_agents` are inherited from source and contract metadata already attached upstream; indexing persists them for filtering and auditability and does not invent them.

Use these collections when the query needs semantic similarity over evidence text. The retrieval path should treat the Chroma hit as a candidate evidence unit and use the mirrored JSON in `data/indexes/vector_registry/` when raw text and full metadata need to be inspected outside the vector store itself.

### BM25 Bundles

BM25 is the lexical retrieval backend for exact-term, acronym, clause, section, and identifier matching over the same per-source logical partitions used by Chroma.

- Persisted data directory: `data/bm25/`
- Builder code: `src/indexing/build_bm25_index.py`
- Bundle naming: one `.pkl` file per logical index, for example `data/bm25/idx_security_policy.pkl`

Each bundle contains the source-partitioned chunk texts, tokenized forms, chunk IDs, and chunk metadata needed to score and return keyword-focused matches. This is the right backend when the query contains exact language such as section numbers, control names, matrix terms, or product/vendor identifiers that may not rank well in dense retrieval alone.

The BM25 layer is meant to be used alongside the Chroma layer, not instead of it. Both operate over the same finalized chunk units so hybrid retrieval can fuse semantic and lexical evidence without changing the evidence boundary.

### Questionnaire Structured Store

The questionnaire bypasses embedding and indexing because it belongs to the direct structured lane. It is not embedded, not added to Chroma, and not added to BM25.

- Persisted store file: `data/structured/vq_direct_access.json`
- Builder code: `src/indexing/build_structured_store.py`
- Logical store name: `vq_direct_access`

This file contains top-level governance metadata for the questionnaire source and a `data` object holding the structured questionnaire payload itself. Use this store for direct field lookup and deterministic access patterns instead of semantic search. The helper in `src/indexing/build_structured_store.py` supports loading the store and retrieving fields by path.

### Index Registry

The registry ties the storage layer together and makes the build explainable.

- Registry file: `data/indexes/index_registry.json`
- Registry definitions: `src/indexing/index_registry.py`
- Registry loader/helpers: `src/indexing/load_index_registry.py`

This file is a source-level control-plane registry, not a chunk registry. It contains one entry per logical source and records the source metadata (`source_id`, `source_name`, `source_type`, `authority_tier`, `retrieval_lane`, `version`, `document_date`, `freshness_status`, `manifest_status`, `allowed_agents`, `is_primary_citable`) plus the storage metadata (`storage_kind`, `logical_store_name`, `backends`, and `backend_locations`) needed for routing and explainability.

Retrieval and routing code should use this registry as the canonical source-to-store map instead of hard-coding collection names, bundle paths, store names, or allowed-agent assumptions in multiple places.

## System Requirements

- macOS or Linux development environment
- Git 2.x+
- GitHub CLI for GitHub-authenticated workflows
- `uv` for dependency and environment management
- Python 3.12+ for the planned application codebase
- Chroma for vector storage during the retrieval build phase
- `rank_bm25` for lexical retrieval during the retrieval build phase
- `sentence-transformers` for local embedding generation during the indexing phase

## Project Commands

Keep this section updated as the project evolves.

```bash
# Run preprocessing on one or more source files from Python
PYTHONPATH=src python3 -c "from preprocessing import load_source; print(load_source('mock_documents/OptiChain_VSQ_001_v2_1.json').to_dict()['source_id'])"

# Build chunk artifacts for chunkable sources
PYTHONPATH=src python3 -c "from chunking.pipeline import build_chunk_artifacts_from_paths; build_chunk_artifacts_from_paths(['mock_documents/IT_Security_Policy_V4.2.md','mock_documents/DPA_Legal_Trigger_Matrix_v1_3.xlsx','mock_documents/Procurement_Approval_Matrix_v2_0.xlsx','mock_documents/Vendor_Precedent_Log_v1_1.json','mock_documents/Slack_Thread_Export_001.json'])"

# Build and persist embeddings for all current chunk artifacts
PYTHONPATH=src python3 -c "from indexing.pipeline import build_and_persist_embeddings_from_chunk_dir; build_and_persist_embeddings_from_chunk_dir()"

# Build Step 8 storage/index outputs
PYTHONPATH=src python3 -c "from indexing.pipeline import build_storage_indices; build_storage_indices(questionnaire_path='mock_documents/OptiChain_VSQ_001_v2_1.json')"

# Install dependencies
uv sync  # after pyproject.toml and uv.lock are added

# Run development server
# TODO: define the preprocessing or orchestration entrypoint

# Run tests
uv run pytest  # after test dependencies and tests/ are added

# Lint / format
uv run ruff check .  # after dev dependencies are added
uv run ruff format .

# Build for production
# TODO: define the retrieval pipeline packaging or deployment process
```
