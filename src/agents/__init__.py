"""LLM call layer for the OptiChain vendor onboarding pipeline.

This package replaces the deterministic mock domain agents with real
Anthropic API calls. The public surface is the five per-agent call
functions and the `AnthropicLLMAdapter` that fulfills the orchestration
layer's `LLMAdapter` protocol.

Call sites in the orchestration layer do not need to know about the
Anthropic SDK directly — they invoke the adapter, which dispatches by
agent name to the right per-agent function.
"""

from agents.llm_caller import (
    AnthropicLLMAdapter,
    call_checklist_assembler,
    call_checkoff_agent,
    call_it_security_agent,
    call_legal_agent,
    call_procurement_agent,
)

__all__ = [
    "AnthropicLLMAdapter",
    "call_checklist_assembler",
    "call_checkoff_agent",
    "call_it_security_agent",
    "call_legal_agent",
    "call_procurement_agent",
]
