# Deterministic Orchestration Test Harness Prompt for Coding Agent

## Purpose

Build a deterministic, monitorable testing harness for the orchestration layer before any live LLM agents are integrated.

The purpose of this phase is to prove that:

- the supervisor can initialize and drive the pipeline correctly
- retrieval routing works per step
- the correct documents and chunks flow into the correct step bundles
- step handlers are invoked in the correct order
- pipeline state mutates correctly
- audit entries are emitted correctly
- the system halts correctly on `COMPLETE`, `BLOCKED`, and `ESCALATED`
- Scenario 1 and Scenario 2 both behave exactly as expected

This is a pre-LLM validation phase.

Do not introduce live LLM calls in this phase.

---

## Why This Test Phase Must Happen Now

This testing phase should happen now, not later.

It should happen after:

- runtime models exist
- supervisor loop exists
- retrieval router exists
- bundle assembly exists
- admissibility logic exists
- step handlers exist in deterministic or mockable form

It should happen before:

- live LLM domain agents
- UI polish
- prompt tuning
- human escalation workflow
- advanced retrieval ranking

### Reason

If the system fails after live LLMs are introduced, it will be unclear whether the problem came from:

- supervisor sequencing
- retrieval routing
- bundle assembly
- admissibility rules
- step handler contract mismatch
- model behavior

So first prove that the orchestration runtime itself works deterministically.

---

## Core Testing Goal

Create a test harness that can run the full sequence:

1. supervisor initializes
2. run begins
3. questionnaire is located or not located
4. STEP-01 executes
5. STEP-02 executes if allowed
6. STEP-03 executes if allowed
7. STEP-04 executes if allowed
8. STEP-05 executes if allowed
9. STEP-06 executes if allowed
10. pipeline halts with the correct terminal state

This harness must support:

- `COMPLETE`
- `BLOCKED`
- `ESCALATED`

---

## High-Level Approach

Use the existing pre-built Scenario 1 and Scenario 2 corpora as the main testing cases.

Do not invent a new third corpus unless necessary.

Scenario coverage should be:

### Scenario 1

Use the clean fast-track / complete corpus to validate:

- happy path
- correct evidence routing
- complete state mutation
- final `COMPLETE`

### Scenario 2

Use the escalated corpus to validate:

- proper escalation behavior
- correct halt at the intended first escalation
- final `ESCALATED`

### Additional blocked test

Use a minimal synthetic missing-intake test to validate:

- questionnaire absent
- STEP-01 emits `BLOCKED`
- downstream steps never execute

This blocked case does not need a full new corpus. It can simply be a run configuration where the questionnaire structured source is absent or intentionally disabled.

---

## Important Design Choice: Use Mock Domain Agents

Yes — use mock domain agents for this phase.

But do not make them trivial pass-through stubs that always return `COMPLETE`.

Instead, make them bundle-aware deterministic agents.

They should:

- receive the current step’s assembled context bundle
- verify that required evidence is present
- verify that forbidden or out-of-scope evidence is absent where applicable
- verify that the bundle metadata is correct enough to proceed
- return a deterministic output object consistent with the scenario

This gives real value.

### What mock agents should do

Each mock step agent should:

1. inspect the received bundle
2. assert that required sources, chunks, and structured fields are present
3. assert that excluded evidence was not improperly admitted
4. emit the expected determination for that scenario
5. emit the expected terminal status for that step

### What mock agents should not do

They should not:

- call an LLM
- improvise reasoning
- retrieve their own sources
- bypass supervisor-provided bundle boundaries

---

## What to Build

Build a realtime-friendly deterministic orchestration test harness with the following components.

---

## 1. Test Runner

Create a top-level runner that can execute named test scenarios.

Suggested commands:

```bash
python run_test_scenario.py --scenario scenario_1_complete
python run_test_scenario.py --scenario scenario_2_escalated
python run_test_scenario.py --scenario scenario_blocked_missing_questionnaire
```

The runner should:

- initialize scenario data paths
- initialize pipeline state
- attach the mock agent implementations
- execute the supervisor loop
- stream events to the console
- optionally write a structured event log file
- exit with pass/fail result based on expected final outcome

---

## 2. Realtime Monitoring Output

Build a simple but good-enough runtime monitor that prints events as the run proceeds.

This does not need to be a full UI.

A clean console event stream is enough for now.

### Console output should show

For each major event, print:

- timestamp
- current step
- event type
- short summary
- resulting state if applicable

Examples:

```text
[12:00:01] RUN_INIT        pipeline_run_id=run_001 scenario=scenario_1_complete
[12:00:01] STEP_ENTER      step=STEP-01
[12:00:01] RETRIEVE_START  step=STEP-01 source=VQ-OC-001 lane=DIRECT_STRUCTURED
[12:00:01] RETRIEVE_OK     step=STEP-01 source=VQ-OC-001 records=1
[12:00:01] BUNDLE_READY    step=STEP-01 admitted=1 excluded=0 admissible=true
[12:00:01] HANDLER_START   step=STEP-01 handler=mock_intake_agent
[12:00:01] HANDLER_OK      step=STEP-01 status=COMPLETE
[12:00:01] STATE_UPDATE    step=STEP-01 overall_status=IN_PROGRESS next_step=STEP-02
```

For failure conditions, print clearly:

```text
[12:00:02] HANDLER_RESULT  step=STEP-01 status=BLOCKED reason=questionnaire_missing
[12:00:02] RUN_HALT        overall_status=BLOCKED halted_at=STEP-01
```

and

```text
[12:00:03] HANDLER_RESULT  step=STEP-03 status=ESCALATED reason=dpa_required_not_executed
[12:00:03] RUN_HALT        overall_status=ESCALATED halted_at=STEP-03
```

---

## 3. Structured Run Log

In addition to console streaming, write a machine-readable run log to disk.

Suggested output files per run:

```text
artifacts/test_runs/<scenario_name>/<run_id>/events.jsonl
artifacts/test_runs/<scenario_name>/<run_id>/final_state.json
artifacts/test_runs/<scenario_name>/<run_id>/bundle_trace.json
artifacts/test_runs/<scenario_name>/<run_id>/audit_log.json
```

### `events.jsonl`

Append one event per line:

- timestamp
- step
- event_type
- payload

### `final_state.json`

Store the terminal `PipelineState`.

### `bundle_trace.json`

Store, per step:

- admitted chunks
- excluded chunks
- exclusion reasons
- structured fields used
- citations and provenance labels

### `audit_log.json`

Store the append-only audit entries generated by the orchestration layer.

---

## 4. Scenario Fixtures

Build explicit scenario fixture definitions for:

- `scenario_1_complete`
- `scenario_2_escalated`
- `scenario_blocked_missing_questionnaire`

Each fixture should declare:

- scenario name
- expected terminal run status
- expected terminal step
- available sources
- expected step-by-step statuses
- expected bundle invariants
- expected exclusions
- expected final assertions

---

## 5. Step-by-Step Expected Flow

The harness must test not just the final result, but the full sequence.

### Scenario 1 — Complete

Expected step progression:

- STEP-01 → `COMPLETE`
- STEP-02 → `COMPLETE`
- STEP-03 → `COMPLETE`
- STEP-04 → `COMPLETE`
- STEP-05 → `COMPLETE`
- STEP-06 → may execute as downstream guidance, but must not change substantive checklist outcome
- final run status → `COMPLETE`

#### Scenario 1 bundle expectations

##### STEP-01

Must include:

- questionnaire structured record

Must validate:

- exists
- complete
- correct version

##### STEP-02

Must include:

- questionnaire integration fields
- relevant IT Security Policy chunks for ERP tier, classification, and fast-track support
- may include supplementary Slack thread if allowed by source permissions, but must not use Slack as primary evidence

Must exclude:

- irrelevant Slack thread 4
- any unrelated chunks

Expected result:

- clean security determination
- no escalation

##### STEP-03

Must include:

- questionnaire personal-data and NDA fields
- relevant DPA matrix rows or legal trigger evidence
- relevant NDA-related policy chunk if needed

Expected result:

- no DPA required
- NDA executed
- legal blockers absent
- status `COMPLETE`

##### STEP-04

Must include:

- upstream security output
- upstream legal output
- relevant procurement matrix row
- relevant questionnaire procurement fields

Expected result:

- fast-track or streamlined procurement determination
- status `COMPLETE`

##### STEP-05

Must include:

- prior determinations
- audit references if required by assembler contract

Expected result:

- checklist assembled
- final substantive status `COMPLETE`

##### STEP-06

Must include:

- finalized checklist
- stakeholder map or downstream config
- no raw-source re-retrieval unless your architecture explicitly allows it

Expected result:

- stakeholder guidance generated
- no status downgrade

---

### Scenario 2 — Escalated

Use the existing scenario-2 corpus and expected stop point already defined in the project.

Expected step progression:

- STEP-01 → `COMPLETE`
- STEP-02 → `COMPLETE` or scenario-aligned non-terminal security determination if that is your locked behavior
- STEP-03 → first intended `ESCALATED` step
- supervisor halts immediately
- STEP-04 through STEP-06 do not execute
- final run status → `ESCALATED`

#### Scenario 2 bundle expectations

Test that:

- the correct legal or upstream evidence is present
- the escalation-worthy condition is preserved
- the system does not continue past the first intended escalation
- audit entries capture reason, owner, and evidence references

---

### Scenario Blocked — Missing Questionnaire

This is a minimal gate test.

Expected progression:

- STEP-01 → `BLOCKED`
- STEP-02 through STEP-06 never execute
- final run status → `BLOCKED`

#### Blocked test setup

Use a run fixture where:

- questionnaire source is absent
- or the direct structured questionnaire store is unavailable
- or the supervisor is configured to simulate missing intake

This test is specifically for gate behavior, not for full corpus validation.

---

## 6. Mock Agent Contract

Implement mock agents with strict contracts.

Each mock agent should expose something like:

```python
def run(bundle: ContextBundle, scenario_name: str) -> Determination:
    ...
```

### Mock agent behavior pattern

Each agent should:

1. validate required evidence exists
2. validate forbidden evidence is excluded if applicable
3. validate bundle admissibility is true before reasoning
4. return a deterministic determination for the given scenario
5. return the expected status for that step

### If bundle is malformed

The mock agent should fail loudly with a useful diagnostic:

- missing required structured field
- missing required chunk
- invalid authority composition
- inadmissible bundle passed to handler
- out-of-scope thread admitted
- forbidden step execution after terminal halt

This is useful because it turns the mock agent into a bundle validator, not just a dummy completion stub.

---

## 7. Assertions the Harness Must Enforce

### Global assertions

For every scenario:

- supervisor starts at STEP-01
- step order is correct
- no skipped step executes unless explicitly permitted by design
- terminal halt is respected
- no downstream step executes after terminal halt
- audit entries are appended for major events
- final `PipelineState` matches expected scenario outcome

### Retrieval assertions

- only allowed sources are queried per step
- retrieval lane matches source type
- irrelevant Slack thread 4 is excluded where applicable
- low-authority Slack is never primary evidence
- structured questionnaire access occurs through direct structured lookup

### Bundle assertions

- bundle contains correct admitted evidence
- excluded evidence includes reason
- provenance labels are preserved
- authority tier metadata is preserved
- bundle handed to handler is step-scoped

### Status assertions

- Scenario 1 ends `COMPLETE`
- Scenario 2 ends `ESCALATED`
- blocked test ends `BLOCKED`

---

## 8. Recommended Implementation Shape

Suggested files:

```text
test_harness/
  run_test_scenario.py
  scenario_fixtures.py
  console_monitor.py
  result_assertions.py
  mock_agents/
    mock_step_01_intake.py
    mock_step_02_security.py
    mock_step_03_legal.py
    mock_step_04_procurement.py
    mock_step_05_checklist.py
    mock_step_06_checkoff.py
  reporters/
    event_logger.py
    bundle_trace_writer.py
    final_state_writer.py
```

If your repo structure differs, keep the same separation of concerns.

---

## 9. Monitoring Requirements

The system must be easy to watch in real time.

Implement at least one of the following:

### Minimum acceptable

A rich console monitor with:

- clear event lines
- color or tags by event type if easy
- step entry and exit
- retrieval summary
- bundle summary
- handler summary
- state transition summary
- halt summary

### Nice-to-have

A very lightweight local HTML report or terminal table refreshed per event.

This is optional. Do not overbuild this.

Console-first monitoring is enough for this phase.

---

## 10. Success Criteria

This testing harness is successful when a developer can run:

```bash
python run_test_scenario.py --scenario scenario_1_complete
python run_test_scenario.py --scenario scenario_2_escalated
python run_test_scenario.py --scenario scenario_blocked_missing_questionnaire
```

and clearly observe:

- which step is active
- what was retrieved
- what was excluded
- what bundle was formed
- what the mock handler returned
- how pipeline state changed
- why the run completed, blocked, or escalated

The system should also write structured artifacts to disk for later inspection.

---

## 11. Final Instruction to Coding Agent

Build this testing harness now, before live LLM integration.

Use the existing Scenario 1 and Scenario 2 corpora.

Use mock step agents that validate bundles and return deterministic scenario-consistent determinations.

Add one additional blocked-intake test for STEP-01 gate validation.

Make the harness easy to monitor in real time through a clean console event stream and saved structured artifacts.

This phase is not about intelligence.

It is about proving that the orchestration layer, retrieval flow, bundle assembly, and terminal-state control all work correctly.
