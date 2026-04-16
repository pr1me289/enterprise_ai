# Scenario 6 — Legal Agent Fixture Build: ESCALATED on Missing ISP-001 §12.1.4

## What this tests

The Legal Agent receives a valid upstream IT Security output and a matching DPA trigger matrix row, completes the DPA determination successfully, but cannot complete the NDA determination because the ISP-001 §12.1.4 NDA clause chunk is absent from the bundle. The agent must produce a partial determination — completing what the evidence supports and escalating only where it cannot — rather than blocking the entire step.

This is distinct from Scenario 4 (full blocked on missing upstream input) and Scenario 5 (Tier 1 conflict escalation). The escalation here is narrowly scoped to one missing required citation source.

Expected output:
- `dpa_required: true`
- `dpa_blocker` — your call; include `existing_dpa_status` in the fixture to make this determinable
- `nda_status: UNKNOWN`
- `nda_blocker: true` — conservative default when the governing clause cannot be cited
- `status: escalated`
- ISP-001 §12.1.4 named in the escalation payload as the missing required source

---

## What already exists — do not rebuild

Everything. No new source documents, chunks, or embeddings needed. This fixture is a targeted subtraction from an existing bundle.

---

## What you need to build

### One bundle fixture only

Create `tests/fixtures/bundles/step_03_scenario_6.json`.

Base it on the Scenario 2 bundle with two changes:

1. Remove the ISP-001 §12.1.4 chunk from the bundle entirely — not null, absent. All other ISP-001 chunks may remain if present.
2. Include `existing_dpa_status` in the questionnaire fields so the DPA blocker determination is not left hanging.

Everything else — upstream IT Security output, EU personal data fields, DPA trigger rows — should remain intact. The DPA path must be completable; only the NDA clause path is severed.

### Add the Scenario 6 evaluator

Add a scenario 6 evaluation path to the existing Legal Agent evaluator. Hard-checks:
- `status: escalated`
- `dpa_required: true` — DPA determination must still complete despite the escalation
- `nda_status: UNKNOWN`
- `nda_blocker: true`
- escalation payload present and references ISP-001 §12.1.4 as the missing source

Soft checks:
- `trigger_rule_cited` non-empty — DPA matrix row still cited even though the step escalated
- `dpa_blocker` consistent with `existing_dpa_status` value in the fixture

The critical failure mode to catch: the model blocks the entire step rather than completing the DPA determination and escalating only the NDA path. If `dpa_required` is absent or null alongside `status: escalated`, that is a spec compliance failure — the agent must not discard completed determinations when escalating on a narrower evidence gap.

---

## Before running

State the fixture path, spec, and scenario per the testing procedure. Wait for confirmation before the API call.
