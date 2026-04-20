"""LLM call layer for the five domain agents.

Public surface:
- `call_it_security_agent`, `call_legal_agent`, `call_procurement_agent`,
  `call_checklist_assembler`, `call_checkoff_agent` — each takes a
  pre-assembled context bundle dict and a `pipeline_run_id` string and
  returns the parsed JSON output dict from the real Anthropic model.
- `AnthropicLLMAdapter` — implements the orchestration layer's
  `LLMAdapter` protocol by dispatching on `agent_name` to one of the
  five functions above. Plug this into `Supervisor(llm_adapter=...)`
  to run the pipeline against the real API.

Contract with the state machine:
- Every exception (API error, JSON parse failure, anything) is caught
  and converted to a minimal blocked-status return dict. The state
  machine never sees an unhandled exception from this layer.
- Validation is presence-only; partial output is still returned so the
  downstream `OutputValidator` and audit log can inspect it.
- Model and API key are read from env vars; neither is hard-coded.
"""

from __future__ import annotations

import json
import logging
import os
import re
import time
from pathlib import Path
from typing import Any

from agents._prompts import OUTPUT_INSTRUCTION, load_system_prompt
from agents._validator import find_missing_fields

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "claude-haiku-4-5"
DEFAULT_MAX_TOKENS = 4096

# Default repo root used by module-level call_* convenience functions.
# The orchestration layer uses `AnthropicLLMAdapter(repo_root=...)` and
# does not rely on this value.
_DEFAULT_REPO_ROOT = Path(__file__).resolve().parents[2]

_CODE_FENCE_RE = re.compile(r"^\s*```(?:json)?\s*|\s*```\s*$", re.IGNORECASE)


# ---------------------------------------------------------------------------
# Anthropic client factory
# ---------------------------------------------------------------------------


def _load_env_once() -> None:
    """Best-effort load of a local .env so the SDK sees ANTHROPIC_API_KEY."""
    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    load_dotenv()


def _build_client() -> Any:
    """Instantiate the Anthropic client. Raises if the SDK is missing."""
    _load_env_once()
    from anthropic import Anthropic

    return Anthropic()


# ---------------------------------------------------------------------------
# Shared call pipeline
# ---------------------------------------------------------------------------


def _user_message_from_bundle(bundle: dict[str, Any], step_metadata: dict[str, Any] | None) -> str:
    """Serialize the pre-assembled bundle + step metadata for the model."""
    payload: dict[str, Any] = {"evidence_bundle": bundle}
    if step_metadata:
        payload["step_metadata"] = step_metadata
    return json.dumps(payload, indent=2, sort_keys=True, default=str)


def _strip_code_fences(text: str) -> str:
    """Remove ```json ... ``` wrappers if the model produced them."""
    stripped = text.strip()
    # Fast path — no fences.
    if not stripped.startswith("```"):
        return stripped
    # Drop leading ```json / ``` and trailing ```.
    lines = stripped.splitlines()
    if lines and lines[0].startswith("```"):
        lines = lines[1:]
    if lines and lines[-1].startswith("```"):
        lines = lines[:-1]
    return "\n".join(lines).strip()


def _parse_json_response(text: str) -> dict[str, Any]:
    """Parse the model's text response into a dict. May raise ValueError."""
    cleaned = _strip_code_fences(text)
    if not cleaned:
        raise ValueError("empty response from model")
    parsed = json.loads(cleaned)
    if not isinstance(parsed, dict):
        raise ValueError(f"expected JSON object, got {type(parsed).__name__}")
    return parsed


def _blocked_output(agent_name: str, reason: str, *, pipeline_run_id: str, bundle: dict[str, Any]) -> dict[str, Any]:
    """Minimal blocked-status payload shaped to the step's output contract.

    STEP-05 (Checklist Assembler) uses `overall_status` as the halt
    signal instead of `status`, so the blocked payload must match or
    the orchestration's OutputValidator will reject it.
    """
    if agent_name == "checklist_assembler":
        return {
            "pipeline_run_id": pipeline_run_id or bundle.get("pipeline_run_id") or "",
            "vendor_name": bundle.get("vendor_name") or "",
            "overall_status": "BLOCKED",
            "error": reason,
        }
    return {"status": "blocked", "error": reason}


def _call_agent(
    *,
    agent_name: str,
    bundle: dict[str, Any],
    pipeline_run_id: str,
    step_metadata: dict[str, Any] | None = None,
    spec_text: str | None = None,
    client: Any = None,
    repo_root: Path | str | None = None,
    model: str | None = None,
    raise_on_error: bool = False,
    call_records: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Shared call pipeline used by every public per-agent function.

    When ``raise_on_error`` is True, exceptions propagate instead of being
    swallowed into a blocked payload. Tests use this so that prompt/parse
    failures surface as real pytest failures. Production callers (the
    Supervisor via ``AnthropicLLMAdapter``) leave it False.

    When ``call_records`` is provided, a summary dict is appended for every
    invocation (agent, pipeline_run_id, model, missing, outcome) so test
    harnesses can inspect per-call metadata.
    """
    model_name = model or os.environ.get("ANTHROPIC_MODEL") or DEFAULT_MODEL
    record: dict[str, Any] = {
        "agent_name": agent_name,
        "pipeline_run_id": pipeline_run_id,
        "model": model_name,
        "outcome": "ok",
    }
    try:
        if spec_text is None:
            system_prompt = load_system_prompt(
                agent_name,
                repo_root=repo_root or _DEFAULT_REPO_ROOT,
            )
        else:
            system_prompt = spec_text + "\n\n" + OUTPUT_INSTRUCTION
        user_message = _user_message_from_bundle(bundle, step_metadata)
        anthropic_client = client or _build_client()
        _t0 = time.monotonic()
        response = anthropic_client.messages.create(
            model=model_name,
            max_tokens=DEFAULT_MAX_TOKENS,
            system=system_prompt,
            messages=[{"role": "user", "content": user_message}],
        )
        record["elapsed_seconds"] = time.monotonic() - _t0
        usage = getattr(response, "usage", None)
        record["input_tokens"] = getattr(usage, "input_tokens", None)
        record["output_tokens"] = getattr(usage, "output_tokens", None)
        text = _extract_text(response)
        output = _parse_json_response(text)
    except Exception as exc:  # noqa: BLE001 — per spec, never leak to state machine
        logger.exception(
            "llm_caller error agent=%s pipeline_run_id=%s",
            agent_name,
            pipeline_run_id,
        )
        record["outcome"] = "error"
        record["error"] = f"{type(exc).__name__}: {exc}"
        if call_records is not None:
            call_records.append(record)
        if raise_on_error:
            raise
        return _blocked_output(
            agent_name,
            f"{type(exc).__name__}: {exc}",
            pipeline_run_id=pipeline_run_id,
            bundle=bundle,
        )

    missing = find_missing_fields(agent_name, output)
    if missing:
        logger.warning(
            "llm_caller missing required fields agent=%s pipeline_run_id=%s missing=%s",
            agent_name,
            pipeline_run_id,
            missing,
        )
    record["missing_fields"] = missing
    record["status"] = output.get("status") or output.get("overall_status")
    if call_records is not None:
        call_records.append(record)
    return output


def _extract_text(response: Any) -> str:
    """Pull the concatenated text out of an Anthropic Message response."""
    parts = getattr(response, "content", None) or []
    chunks: list[str] = []
    for part in parts:
        text = getattr(part, "text", None)
        if text:
            chunks.append(text)
    if not chunks:
        raise ValueError("no text content in model response")
    return "".join(chunks)


# ---------------------------------------------------------------------------
# Public per-agent call functions
# ---------------------------------------------------------------------------


def call_it_security_agent(bundle: dict[str, Any], pipeline_run_id: str) -> dict[str, Any]:
    return _call_agent(
        agent_name="it_security_agent",
        bundle=bundle,
        pipeline_run_id=pipeline_run_id,
    )


def call_legal_agent(bundle: dict[str, Any], pipeline_run_id: str) -> dict[str, Any]:
    return _call_agent(
        agent_name="legal_agent",
        bundle=bundle,
        pipeline_run_id=pipeline_run_id,
    )


def call_procurement_agent(bundle: dict[str, Any], pipeline_run_id: str) -> dict[str, Any]:
    return _call_agent(
        agent_name="procurement_agent",
        bundle=bundle,
        pipeline_run_id=pipeline_run_id,
    )


def call_checklist_assembler(bundle: dict[str, Any], pipeline_run_id: str) -> dict[str, Any]:
    return _call_agent(
        agent_name="checklist_assembler",
        bundle=bundle,
        pipeline_run_id=pipeline_run_id,
    )


def call_checkoff_agent(bundle: dict[str, Any], pipeline_run_id: str) -> dict[str, Any]:
    return _call_agent(
        agent_name="checkoff_agent",
        bundle=bundle,
        pipeline_run_id=pipeline_run_id,
    )


# ---------------------------------------------------------------------------
# Orchestration-layer adapter
# ---------------------------------------------------------------------------


class AnthropicLLMAdapter:
    """Implements the orchestration `LLMAdapter` protocol with real API calls.

    Instantiate once per pipeline run and pass as `llm_adapter` to the
    Supervisor. The adapter keeps a single Anthropic client across all
    five agent invocations in the run.
    """

    def __init__(
        self,
        *,
        repo_root: Path | str | None = None,
        model: str | None = None,
        client: Any = None,
        pipeline_run_id: str | None = None,
        raise_on_error: bool = False,
    ) -> None:
        self.repo_root = Path(repo_root) if repo_root else _DEFAULT_REPO_ROOT
        self.model = model or os.environ.get("ANTHROPIC_MODEL") or DEFAULT_MODEL
        self._client = client  # constructed lazily on first call if None
        self._pipeline_run_id = pipeline_run_id or ""
        self.raise_on_error = raise_on_error
        self.call_records: list[dict[str, Any]] = []

    def _get_client(self) -> Any:
        if self._client is None:
            self._client = _build_client()
        return self._client

    def generate_structured_json(
        self,
        *,
        agent_name: str,
        spec_text: str,
        prompt: str,  # unused — we rebuild a clean user message from the bundle
        bundle: dict[str, Any],
        step_metadata: dict[str, Any],
        context_bundle: Any = None,
    ) -> dict[str, Any]:
        del prompt, context_bundle  # not used by the real adapter
        pipeline_run_id = (
            (step_metadata or {}).get("pipeline_run_id")
            or bundle.get("pipeline_run_id")
            or self._pipeline_run_id
        )
        return _call_agent(
            agent_name=agent_name,
            bundle=bundle,
            pipeline_run_id=pipeline_run_id,
            step_metadata=step_metadata,
            spec_text=spec_text,
            client=self._get_client(),
            repo_root=self.repo_root,
            model=self.model,
            raise_on_error=self.raise_on_error,
            call_records=self.call_records,
        )
