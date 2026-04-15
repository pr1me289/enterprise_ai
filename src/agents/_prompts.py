"""Spec-file loader for the LLM call layer.

Each domain agent has a spec `.md` file in `agent_spec_docs/` that defines
its behavioral contract and output contract. The spec file is used as the
system prompt verbatim, with a short output instruction appended so the
model returns a single JSON object with no surrounding text.
"""

from __future__ import annotations

from pathlib import Path

# Agent name -> spec file path, relative to repo root.
SPEC_PATHS: dict[str, Path] = {
    "it_security_agent": Path("agent_spec_docs/IT_Security_Agent_Spec.md"),
    "legal_agent": Path("agent_spec_docs/Legal_Agent_Spec.md"),
    "procurement_agent": Path("agent_spec_docs/Procurement_Agent_Spec.md"),
    "checklist_assembler": Path("agent_spec_docs/Checklist_Assembler_Spec.md"),
    "checkoff_agent": Path("agent_spec_docs/Checkoff_Agent_Spec.md"),
}

OUTPUT_INSTRUCTION = """

---

# Output Format (enforced by the LLM call layer)

Return a single valid JSON object that satisfies the output contract
defined above. The response must contain the JSON object and nothing
else — no prose, no explanation, and no markdown code fences. Begin
your response with `{` and end it with `}`.
""".lstrip("\n")


def load_system_prompt(agent_name: str, *, repo_root: Path | str) -> str:
    """Load the agent's spec file and append the output instruction."""
    relative = SPEC_PATHS[agent_name]
    spec_text = (Path(repo_root) / relative).read_text(encoding="utf-8")
    return spec_text + "\n\n" + OUTPUT_INSTRUCTION
