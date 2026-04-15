# Per-Agent LLM Test Environment

## Context

The pipeline's orchestration layer and test harness are already built. We are now moving into live LLM testing. Before any full pipeline run is executed, each domain agent must be tested and validated in isolation.

## Your Task

Build a testing environment that allows each domain agent to be invoked and evaluated individually, one at a time, against real Anthropic API calls.

**First, make a decision:** assess whether the existing test harness can be extended to support per-agent live LLM invocation, or whether a separate, dedicated test environment is the cleaner approach. Choose whichever keeps the test logic isolated, readable, and easy to run agent-by-agent without triggering the full pipeline. Document your choice briefly.

## Requirements

- Each agent must be testable in complete isolation — invoking one agent must not trigger any other agent or advance pipeline state
- Each agent must receive a realistic, valid input bundle for its step, matching the input contract for that agent
- Both demo scenarios (clean path and escalation path) must be coverable per agent
- Raw API responses must be recorded to disk before any evaluation logic runs — evaluation always operates on the saved response, never on a live re-call
- The test runner must make it explicit which agent is under test, which scenario is running, and what the raw output was
- A failed agent test must halt and report — it must not cascade into testing the next agent automatically

## What This Is Not

This is not a full pipeline smoke test. Do not wire agents together here. The goal is rigid, isolated, one-agent-at-a-time validation against the output contracts defined in the accompanying evaluation checklist.
