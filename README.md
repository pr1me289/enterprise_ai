# enterprise_ai

## Overview

`enterprise_ai` is a bootstrap repository for enterprise AI workflow development. The current repository contents are mock procurement, legal, security, and stakeholder documents intended to support early design, testing, and prompt or pipeline prototyping before application code is added.

## Architecture

The repository is currently organized around reference artifacts rather than executable application code.

- `mock_documents/` contains sample enterprise documents in PDF, JSON, Markdown, and spreadsheet formats.
- `AGENTS.md` and `CLAUDE.md` define repository-level engineering and AI workflow rules.
- Future application code should live in `src/` and tests should live in `tests/` as the project is scaffolded.

## Setup

This repository is not fully scaffolded yet. There is currently no `pyproject.toml`, `uv.lock`, `src/`, or `tests/` directory.

Prerequisites for the next build stage:

1. Install Git.
2. Install GitHub CLI if you plan to push changes with `gh`.
3. Install `uv` for Python dependency and environment management.
4. Use external environment variables or `gh auth login` for authentication. Do not commit secrets.

Environment variables:

- No project-specific environment variables are required yet.
- When secrets are introduced, keep them outside the repository and document them in `.env.example`.

## Usage

There is no runnable application, test suite, or production build in the repository yet. At this stage, the repository is used as a source of mock enterprise artifacts and repository-level engineering guidance.

Typical current usage:

1. Review the sample documents in `mock_documents/`.
2. Use the repository rules in `AGENTS.md` before adding code or automation.
3. Scaffold the Python project with `uv` when implementation begins.

## System Requirements

- macOS or Linux development environment
- Git 2.x+
- GitHub CLI for GitHub-authenticated workflows
- `uv` for future dependency management
- Python 3.12+ for the planned application codebase

## Project Commands

Keep this section updated as the project evolves.

```bash
# Install dependencies
uv sync  # after pyproject.toml and uv.lock are added

# Run development server
# TODO: define the application entrypoint

# Run tests
uv run pytest  # after test dependencies and tests/ are added

# Lint / format
uv run ruff check .  # after dev dependencies are added
uv run ruff format .

# Build for production
# TODO: define the production build process
```
