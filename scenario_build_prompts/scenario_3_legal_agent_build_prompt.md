# Scenario 3 — Legal Agent Fixture Build

## What this tests

A case where `dpa_required: true` but `dpa_blocker: false` — because a GDPR Art. 28 DPA is required by the trigger matrix AND an executed DPA is already confirmed on file. This is the third distinct Legal Agent state not currently covered by Scenario 1 or Scenario 2.

The model must distinguish between the DPA being required and the DPA being a blocker. Conflating the two is the specific failure mode this test is designed to catch.

Expected output:
- `dpa_required: true`
- `dpa_blocker: false`
- `nda_blocker` — your call based on NDA state you choose for the fixture
- `status: complete`

---

## What already exists — do not rebuild

- ISP-001 chunks, including the §12 / §12.1.4 NDA clause chunks
- DPA-TM-001 trigger matrix rows — reuse whichever row already fires on EU personal data (row A-01 or equivalent)
- The existing Chroma and BM25 indices for `idx_dpa_matrix` and `idx_security_policy`
- The Legal Agent spec and system prompt

Do not re-chunk or re-embed any existing source document.

---

## What you need to build

### 1. Questionnaire variant — minimal diff from Scenario 2

Create a new questionnaire JSON at `scenario_data/scenario_3/vendor_questionnaire.json`.

Base it on the Scenario 2 questionnaire. Change only the fields that matter for this test:

- `eu_personal_data_flag`: `true` — keep EU data in scope so the DPA trigger still fires
- `existing_dpa_status`: `EXECUTED` — this is the field that separates Scenario 3 from Scenario 2
- `existing_nda_status`: your choice — `EXECUTED` keeps the output clean; `PENDING` adds an `nda_blocker: true` to the mix if you want to test that combination simultaneously

Do not change vendor class, deal size, or integration fields — those are irrelevant to what this fixture is testing.

### 2. Step 03 bundle fixture

Create `tests/fixtures/bundles/step_03_scenario_3.json`.

Structure it the same way as `step_03_scenario_2.json`. The meaningful differences:

- Upstream IT Security output should show `data_classification: REGULATED` and `eu_personal_data_present: true` — same as Scenario 2, so the DPA trigger fires
- Questionnaire fields must include `existing_dpa_status: EXECUTED` — this is the key signal the Legal Agent needs to set `dpa_blocker: false`
- `dpa_trigger_rows` should include the same DPA-TM-001 row used in Scenario 2 — the trigger still applies, the distinction is that the DPA obligation is already satisfied

### 3. No new indexing required

The bundle fixture provides the DPA trigger row directly as structured evidence. No new chunks need to be embedded. The existing indices are not touched.

---

## Evaluator expectations

The evaluator should hard-check:
- `dpa_required: true`
- `dpa_blocker: false`
- `trigger_rule_cited` non-empty — the DPA trigger fired, so a matrix row must still be cited even though there is no blocker
- `status: complete`

The last two in combination are the crux of the test. The model must cite the trigger row that requires a DPA while simultaneously determining that the DPA obligation is already satisfied. If it returns `dpa_blocker: true` despite `existing_dpa_status: EXECUTED` in the bundle, that is the specific failure mode this fixture exists to catch.

---

## Before running

State the fixture path, spec, and scenario per the testing procedure. Wait for confirmation before the API call.
