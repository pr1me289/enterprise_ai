# enterprise_ai

## Overview

`enterprise_ai` is a Python-based enterprise AI demo focused on governed evidence delivery, not generic vector search. The project will ingest enterprise source material, convert it into retrieval-ready evidence units, route those units through the correct retrieval lane, and later deliver scoped context bundles to downstream agents in a way that preserves authority, permissions, freshness, and auditability.

The current repository contains mock procurement, legal, security, and stakeholder documents that will be used to build and demonstrate this pipeline. No implementation work has started yet beyond repository setup and project planning.

## Architecture

The architecture is intentionally split into two major layers.

- Governed retrieval infrastructure
- Agentic retrieval behavior

The governed retrieval infrastructure is responsible for source ingestion, document-type-aware chunking, metadata attachment, embeddings for indexed sources, and storage/index preparation. The agentic retrieval layer is responsible for later query planning, source routing, hybrid retrieval execution, authority-aware reranking, and context bundle assembly.

The core design principle is that the system should not treat all inputs the same. It should preserve enterprise meaning by normalizing each source into the correct internal form for its role in the pipeline.

Current repository contents:

- `mock_documents/` contains sample enterprise documents in PDF, JSON, Markdown, and spreadsheet formats.
- `AGENTS.md` and `CLAUDE.md` define repository-level engineering and AI workflow rules.
- Future application code will live in `src/` and tests will live in `tests/` as the project is scaffolded.
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

This repository is not fully scaffolded yet. There is currently no `pyproject.toml`, `uv.lock`, `src/`, or `tests/` directory, and no project implementation should begin until the next phase is explicitly authorized.

Prerequisites for the next build stage:

1. Install Git.
2. Install GitHub CLI if you plan to push changes with `gh`.
3. Install `uv` for Python dependency and environment management.
4. Use external environment variables or `gh auth login` for authentication. Do not commit secrets.

Environment variables:

- No project-specific environment variables are required yet.
- When secrets are introduced, keep them outside the repository and document them in `.env.example`.

## Usage

There is no runnable application, test suite, retrieval service, or production build in the repository yet. At this stage, the repository is being used to define architecture, preserve source materials, and prepare for implementation.

Typical current usage:

1. Review the sample documents in `mock_documents/`.
2. Review `STRATEGY.md` for the locked retrieval and preprocessing approach.
3. Use the repository rules in `AGENTS.md` before adding code or automation.
4. Scaffold the Python project with `uv` only when implementation begins.

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
