# CLAUDE.md — LLM Call Layer Testing Suite

## Context

The LLM call layer (`agents/llm_caller.py`) is built and waiting for an API key. Before connecting real agents, build a comprehensive test suite that verifies each domain agent returns correct outputs given known inputs. The pipeline has two complete scenario sets with known ground-truth outcomes — these drive all tests.

Do not modify `llm_caller.py`, the state machine, or any orchestration code. Build only the test infrastructure.

---

## Source File Notes — Read Before Building

Two inconsistencies exist in the repo source files that affect fixture construction:

**Slack export (`Slack_Thread_Export_001.json`):** Contains `"authority_tier": 4` — this predates the tier renumbering. Treat Slack / meeting notes as Tier 3 throughout all tests and fixtures. Do not assert on the `authority_tier` field value in this source file.

**Procurement Approval Matrix CSV:** Confirm you are using the corrected version where `STREAMLINED` has been replaced with `FAST_TRACK` on Class C/T1, E/T1, and E/T2 rows. If the file in your working directory still contains `STREAMLINED`, use the corrected version at `Procurement_Approval_Matrix_v2_0.csv` (the fixed output from the earlier conversion pass).

---

## What You Are Testing

Three distinct validation layers, each catching different failure modes:

**1. Output contract compliance** — does the agent return all required fields in the correct format and types? Mechanical pass/fail.

**2. Determination correctness** — given a specific scenario bundle, does the agent return the correct field *values*? This is the core test. Expected outputs are fully specified below for both scenarios.

**3. Behavioral discipline** — does the agent follow its spec rules under adversarial or edge-case inputs? Maps directly to the acceptance checks (A-01 through A-07) in each agent spec doc.

---

## Scenario Ground Truth

### Scenario 1 — Clean Governed Completion

Source documents: `OptiChain_VSQ_001_v2_1_scenario01.json`, `OptiChain_Procurement_Classification_Memo_scenario01.csv`, `Slack_Thread_Export_scenario01.json`

Key facts: export-only Tier 3 integration, no personal data, no EU data subjects, NDA executed January 2024, existing MSA from prior engagement PRQ-2023-0031, Class C vendor, $45K TCV / T1.

Expected outputs:

| Step | Field | Expected Value |
|------|-------|----------------|
| STEP-02 | `data_classification` | `UNREGULATED` |
| STEP-02 | `integration_type_normalized` | `EXPORT_ONLY` |
| STEP-02 | `integration_tier` | `TIER_3` |
| STEP-02 | `eu_personal_data_present` | `NO` |
| STEP-02 | `fast_track_eligible` | `true` |
| STEP-02 | `fast_track_rationale` | `ELIGIBLE_LOW_RISK` |
| STEP-02 | `security_followup_required` | `false` |
| STEP-02 | `required_security_actions` | `[]` |
| STEP-02 | `nda_status_from_questionnaire` | `EXECUTED` |
| STEP-02 | `status` | `complete` |
| STEP-03 | `dpa_required` | `false` |
| STEP-03 | `dpa_blocker` | `false` |
| STEP-03 | `nda_status` | `EXECUTED` |
| STEP-03 | `nda_blocker` | `false` |
| STEP-03 | `trigger_rule_cited` | `[]` |
| STEP-03 | `status` | `complete` |
| STEP-04 | `approval_path` | `FAST_TRACK` |
| STEP-04 | `fast_track_eligible` | `true` |
| STEP-04 | `status` | `complete` |
| STEP-05 | `overall_status` | `COMPLETE` |
| STEP-05 | `blockers` | `[]` |
| STEP-05 | `fast_track_eligible` | `true` |
| STEP-05 | `approval_path` | `FAST_TRACK` |
| STEP-06 | `status` | `complete` |

---

### Scenario 2 — Escalated Path (Regulated Vendor)

Source documents: `OptiChain_VSQ_001_v2_1.json`, `Slack_Thread_Export_001.json`, `Stakeholder_Map_PRQ_2024_0047.json`, `Procurement_Approval_Matrix_v2_0.csv`, `DPA_Legal_Trigger_Matrix_v1_3.csv`, `IT_Security_Policy_V4_2.md`

Key facts: ERP integration ambiguous — vendor describes a possible extraction agent with service account credentials that does not clearly map to Tier 2 or Tier 3 under ISP-001 §12.2. EU employee personal data confirmed in scope (shift schedules, employee IDs for EU-based facilities). NDA draft transmitted 2024-02-19, not countersigned as of submission. No executed DPA. No prior relationship. Class A vendor. $675K TCV / T3. Three blocking items: ERP tier unclassified (PROVISIONAL), DPA not executed (ESCALATED — hard blocker per DPA-TM-001 rows A-01 and E-01), NDA unconfirmed (PROVISIONAL per ISP-001 §12.1.4).

Expected outputs:

| Step | Field | Expected Value |
|------|-------|----------------|
| STEP-02 | `data_classification` | `REGULATED` |
| STEP-02 | `integration_type_normalized` | `AMBIGUOUS` |
| STEP-02 | `integration_tier` | `UNCLASSIFIED_PENDING_REVIEW` |
| STEP-02 | `eu_personal_data_present` | `YES` |
| STEP-02 | `fast_track_eligible` | `false` |
| STEP-02 | `fast_track_rationale` | `DISALLOWED_AMBIGUOUS_SCOPE` or `DISALLOWED_REGULATED_DATA` (either is correct) |
| STEP-02 | `security_followup_required` | `true` |
| STEP-02 | `required_security_actions` | non-empty array |
| STEP-02 | `nda_status_from_questionnaire` | `PENDING` |
| STEP-02 | `status` | `escalated` |
| STEP-03 | `dpa_required` | `true` |
| STEP-03 | `dpa_blocker` | `true` |
| STEP-03 | `nda_status` | `PENDING` |
| STEP-03 | `nda_blocker` | `true` |
| STEP-03 | `trigger_rule_cited` | non-empty; must include row A-01 or E-01 |
| STEP-03 | `status` | `escalated` |
| STEP-04 | `approval_path` | `STANDARD` |
| STEP-04 | `fast_track_eligible` | `false` |
| STEP-04 | `status` | `escalated` |
| STEP-05 | `overall_status` | `ESCALATED` |
| STEP-05 | `blockers` | non-empty; must include entries for DPA and NDA conditions |
| STEP-05 | `fast_track_eligible` | `false` |
| STEP-06 | `guidance_documents` | non-empty; must include entries for CISO, General Counsel, CPO, VP Operations, SVP Operations |
| STEP-06 | `status` | `complete` |

**Note on STEP-02 `fast_track_rationale`:** both `DISALLOWED_AMBIGUOUS_SCOPE` and `DISALLOWED_REGULATED_DATA` are correct — the agent may key on the unclassified integration tier or the EU personal data flag. Assert that the value is one of the two valid enums, not a specific one.

**Note on STEP-06 guidance documents:** the stakeholder map (`Stakeholder_Map_PRQ_2024_0047.json`) defines five required approvers: CISO (K. Whitfield), General Counsel, CPO, VP Operations (P. Horak), SVP Operations. Assert that `guidance_documents` contains at least one entry per role. Do not assert on the `instructions` prose content.

---

## Test Architecture

### Layer 1 — Per-Agent Unit Tests (`tests/unit/`)

One test file per domain agent. Each test case loads a JSON fixture, calls the agent via `llm_caller.py`, and asserts expected field values.

**Required fixtures per agent (minimum):**
- Scenario 1 happy-path bundle → assert complete-status outputs from table above
- Scenario 2 escalated-path bundle → assert escalated-status outputs from table above
- Missing required upstream field → assert `status = blocked`
- One agent-specific edge case drawn from that agent's acceptance checks

**Assertion rules:**
- Exact match on all enum and boolean fields per the tables above
- `policy_citations` non-empty on any non-blocked determination
- `required_security_actions` is `[]` only when `security_followup_required = false`
- `blockers` is `[]` only when `overall_status = COMPLETE`
- `trigger_rule_cited` is `[]` only when `dpa_required = false`
- Do not assert on free-text fields: `estimated_timeline`, citation chunk IDs, `instructions` prose in guidance documents

---

### Layer 2 — Cross-Agent Handoff Tests (`tests/integration/`)

Tests the contracts between steps that per-agent unit tests cannot catch in isolation.

**Required handoff checks:**
- `fast_track_eligible` from STEP-02 must equal `fast_track_eligible` in STEP-04 output exactly in a paired run
- When STEP-03 `status = escalated`, STEP-04 `status` must also be `escalated` even when `approval_path` was determinable
- `overall_status` in STEP-05 must be `ESCALATED` when any upstream step has `status = escalated`
- `overall_status` in STEP-05 must be `BLOCKED` when any upstream step has `status = blocked`
- STEP-06 must run and return `status = complete` when STEP-05 `overall_status = ESCALATED`
- STEP-06 must return `status = blocked` when STEP-05 output is absent from the bundle

---

### Layer 3 — Acceptance Check Tests (`tests/acceptance/`)

Each agent spec doc contains numbered acceptance checks. The following must have a corresponding test case:

| Check | Agent | Test Input | Assert |
|-------|-------|-----------|--------|
| A-03 | IT Security | Bundle with `data_classification = REGULATED` | `fast_track_eligible = false`, no exceptions |
| A-03 variant | IT Security | Bundle with ambiguous ERP type | `fast_track_eligible = false` |
| A-04 | IT Security | Any non-blocked run | No `policy_citations` entry has `citation_class = PRIMARY` with a Tier 3 `source_id` |
| A-02 | Legal | `dpa_required = true`, no executed DPA | `dpa_blocker = true`, no exceptions |
| A-03 | Legal | Any bundle where `nda_status != EXECUTED` | `nda_blocker = true`, no exceptions |
| A-07 | Legal | Bundle where `dpa_blocker = true` | `status = escalated`, never `complete` |
| A-02 | Procurement | Scenario 1 paired run | STEP-04 `fast_track_eligible` exactly equals STEP-02 `fast_track_eligible` |
| A-04 | Procurement | Any non-blocked run | No `policy_citations` entry has `citation_class = PRIMARY` with Tier 3 `source_id` |
| A-01 | Checklist | Bundle with one upstream step `escalated` | `overall_status = ESCALATED`, never `COMPLETE` |
| A-05 | Checklist | Missing one domain agent output | `overall_status = BLOCKED` |

---

## Fixture Design

Store fixtures in `tests/fixtures/` as JSON files with two top-level keys: `bundle` (input to the agent) and `expected` (assertions dict). Name files descriptively: `step_02_scenario1.json`, `step_03_scenario2.json`, `step_04_missing_legal.json`.

Construct bundles from the actual scenario source documents in the repo. Do not invent field values. For downstream agent fixtures, use the expected output values from the ground truth tables above as the upstream inputs — this makes fixtures self-consistent without requiring a live prior-step run.

---

## Test Runner Design

- Use pytest
- Tests calling the real API are marked `@pytest.mark.api` — skipped by default, run with `pytest -m api`
- Shared fixture loading and assertion logic lives in `tests/conftest.py`
- Each test logs `pipeline_run_id`, agent called, each field asserted, and pass/fail per field — not just a binary result
- Model is read from the same env var as the main application — tests must pass on both `claude-haiku-4-5` and `claude-sonnet-4-6` without modification
- All tests are independent — no test depends on another test's output or side effects

---

## Constraints

- Do not modify `llm_caller.py`, the state machine, bundle assembly, or orchestration code
- Do not assert on free-text fields or citation content — only enums, booleans, and structural presence or emptiness
- Fixtures must be derived from actual scenario documents in the repo — no invented data
- Every test is independently runnable
- All test files live under `tests/` — not in the main application package

---

## Success Criteria

1. All Layer 1 unit tests pass for both scenarios across all five agents
2. All Layer 2 handoff tests pass end-to-end for both scenarios
3. Every acceptance check in the table above has a passing test case
4. Scenario 1 full run produces `overall_status = COMPLETE`, `approval_path = FAST_TRACK`, `blockers = []`
5. Scenario 2 full run produces `overall_status = ESCALATED` with `dpa_blocker` and `nda_blocker` in `blockers[]` and five stakeholder guidance documents in STEP-06 output
6. `pytest -m api` with a valid API key produces a clear per-field pass/fail report
7. No test is model-specific — suite passes on both Haiku and Sonnet
