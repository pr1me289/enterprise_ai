# Engineering & Project Development Guidelines

---

## 🚨 SECURITY REQUIREMENT (MANDATORY)

This repository must NEVER contain:

- Personal Access Tokens (PATs)
- API keys
- Private SSH keys
- `.env` files containing secrets
- Any hard-coded credentials

Authentication must be handled via:
- `gh auth login`
- SSH keys
- Environment variables stored outside the repository

Under no circumstances should secrets be committed.

---

## Seek Clarification When Necessary

Whenever you encounter conflicting information, unclear instructions, or uncertainty about the meaning or implications of a prompt, stop development and ask the user for clarification before proceeding. Do not implement uncertain features or make ambiguous changes. Only act when the instructions, development philosophy, and rationale for the requested work are clearly understood.

---

## Dependency & Environment Management

This project uses `uv` for dependency and environment management.

### Dependency Rules

- All runtime dependencies must be added via `uv add`.
- All development dependencies (ruff, pytest, type-checkers, etc.) must also be added via `uv add --dev`.
- Never use `pip install` directly.
- Never rely on globally installed packages.
- Always commit the lockfile.

Rule of thumb:
If CI depends on it → it must be a project dependency.

### uv vs uvx

- Use `uv` for:
  - Application runtime dependencies
  - Testing
  - Linting
  - CI execution

- Use `uvx` only for:
  - One-off CLI tools
  - Personal utilities not required by the project

---

## Token & Model Efficiency

- Prefer minimal tool calls; batch related operations when it reduces overhead.
- Scope agent/subagent tasks narrowly — one clear responsibility per agent.
- Do not spawn subagents for tasks achievable in a single pass.
- Be concise by default; provide detailed reasoning only when requested or necessary.
- Avoid redundant analysis or repeated explanations.

---

## Project Structure Expectations

Standard layout:

project-root/
│
├── src/
├── tests/
├── pyproject.toml
├── uv.lock
├── README.md
├── CLAUDE.md
├── .gitignore
├── master_log.md
└── past_prompts.md


Rules:
- Application code lives in `src/`
- Tests live in `tests/`
- No business logic in notebooks unless explicitly exploratory
- No experimental files in root directory

---

## Code Quality Standards

- Linting must pass (`ruff`)
- Tests must pass (`pytest`)
- Code must be deterministic and reproducible
- No commented-out large blocks of legacy code
- Prefer explicit imports and clear module boundaries

CI must:
- Install dependencies using `uv`
- Run lint checks
- Run tests
- Fail on any error

---

## .gitignore Essentials

Never commit:

- `.venv/`
- `.idea/`
- `.vscode/`
- `__pycache__/`
- `*.pyc`
- `.env`
- `.env.*`
- `.DS_Store`
- `*.log`
- `.coverage`
- `htmlcov/`
- `.pytest_cache/`
- `.mypy_cache/`
- `.ruff_cache/`
- `dist/`
- `build/`
- `*.egg-info/`

---

## master_log.md

Record all changes, plans, and execution results in `master_log.md` at the project root.

**Entry format:**
```
### [#N] YYYY-MM-DD | {Claude Code | Codex}
**Task:** What was requested
**Plan:** Steps taken or intended
**Changes:** Files created/modified/deleted, commands run
**Result:** Outcome, errors hit, anything left incomplete
**Next:** Remaining work or open questions (if any)
```

- Session number is ever-incrementing starting from `#1` — never reset it
- Log *before* starting long tasks (plan) and *after* completing them (result)
- If a task fails mid-way, log the failure state so the next session can resume cleanly

---

## README.md

Keep this file accurate and current. Update it whenever you change:
- How to install or run the project
- Environment variables or required secrets
- Major architectural decisions

**Sections to maintain:**
- **Overview** — what the product does and why it exists
- **Architecture** — high-level system diagram or description; key components
- **Setup** — prerequisites, installation steps, environment variables (reference `.env.example`)
- **Usage** — how to run, build, test, and deploy
- **System Requirements** — language versions, OS constraints, dependencies

Include 'Project Commands'

> Keep this section updated as the project evolves.
```bash
# Install dependencies


# Run development server


# Run tests


# Lint / format


# Build for production
```

---

## past_prompts.md

Do not touch past_prompts.md

---

## Core Engineering Principles

1. Simplicity over cleverness.
2. Readability over micro-optimization.
3. Performance only when necessary.
4. Less code = less technical debt.
5. Code must be testable and maintainable.
6. Prefer clean logic; push complexity to boundaries.
7. Build iteratively — verify minimal functionality before expanding.

---

## Code Standards

- Use descriptive names (prefix event handlers with `handle`).
- Prefer early returns to avoid nesting.
- Follow DRY principles.
- Keep functions small and focused.
- Prefer immutable/functional style when it improves clarity.
- Define composing functions before their subcomponents.
- Mark existing issues with `TODO:` prefix.
- Keep file organization proportional to project scale.
- Document public APIs clearly.

---

## AI Modification Protocol (MANDATORY)

When modifying code:

- Make minimal changes required to solve the task.
- Do not refactor unrelated sections.
- Do not rename variables unless necessary.
- Do not introduce new dependencies without justification.
- Preserve existing structure and conventions.
- Prefer extending code over rewriting it.
- Ask before large structural changes.
- Keep changes atomic and logically isolated.

---

## Git Workflow Protocol

- Never commit directly to `main`.
- Always use feature branches: `feat/...`, `fix/...`, `chore/...`
- One logical change per branch.
- Make atomic commits.
- Use conventional commit format:
  - `feat(api): add pagination`
  - `fix(auth): handle token expiry`
- Open draft PRs early.
- Ensure tests pass locally before marking ready.
- CI must pass before merging.
- Reference or create an issue before starting work.

---

## CI Enforcement

CI runs on every push/PR and executes:

- `ruff check .`
- `black --check .`
- `pytest`

All checks must pass before merging.

CI must install dependencies via uv sync (or equivalent)

---

## Error Resolution Order

When CI fails, fix in this order:

1. Formatting
2. Type errors
3. Linting
4. Test failures

Guidelines:
- Run formatters before type checks.
- Keep changes minimal.
- Follow existing patterns.
- Test with realistic inputs.

---

## 🚨 Security Requirement (Non-Negotiable)

Never commit:

- Personal Access Tokens (PATs)
- API keys
- `.env` files
- Secrets of any kind

Authentication must use:
- `gh auth login`
- SSH keys
- Secure environment variables

If unsure whether something is sensitive, assume it is and do not commit it.
