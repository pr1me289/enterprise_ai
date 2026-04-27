# Scenario 4 — Legal Agent Fixture Build: BLOCKED on Missing Upstream Input

## What this tests

The Legal Agent receives a bundle with no IT Security Agent output. Without upstream `data_classification`, the bundle is inadmissible — the Legal Agent cannot make a DPA determination and must return `status: blocked`.

This is a pure gate condition test. It does not test the model's reasoning over evidence. It tests whether the model correctly identifies an inadmissible bundle and halts rather than inferring through the missing input.

Expected output:
- `status: blocked`
- No DPA determination attempted

---

## What already exists — do not rebuild

Everything. No new source documents, chunks, embeddings, or indices are needed for this fixture.

---

## What you need to build

### One bundle fixture only

Create `tests/fixtures/bundles/step_03_scenario_4.json`.

It should be a minimal Legal Agent bundle with the IT Security Agent output block absent or explicitly null. Everything else — questionnaire EU fields, DPA trigger rows, NDA clause chunk — may be present or absent, it does not matter. The missing upstream output is the only condition being tested.

---

## Evaluator expectations

Hard-check:
- `status: blocked`

No other field checks are meaningful here. If the model attempts a DPA or NDA determination despite missing upstream input, that is the failure mode — flag it and halt.

---

## Before running

State the fixture path, spec, and scenario per the testing procedure. Wait for confirmation before the API call.
