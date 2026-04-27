# Scenario 6 — Legal Agent Fixture Build: ESCALATED on Missing ISP-001 §12.1.4

## What this tests

The Legal Agent receives a valid upstream IT Security output and a matching DPA trigger matrix row, completes the DPA determination successfully, but cannot complete the NDA citation because the ISP-001 §12.1.4 NDA clause chunk is absent from the bundle. The agent must produce a partial determination — populating every field it can and setting to `null` only the fields it cannot resolve — rather than blocking the entire step.

This is distinct from Scenario 4 (full blocked on missing upstream input) and Scenario 5 (Tier 1 conflict escalation). The escalation here is narrowly scoped to one missing required citation source.

**Important nuance per SPEC-AGENT-LEG-001 v0.9 §8.4 and Example B:** `nda_status` is normalized from the questionnaire field `existing_nda_status`, not from the ISP-001 clause. The clause is a citation requirement, not an evidentiary input for the status value itself. This means if `existing_nda_status` is present in the bundle, `nda_status` is resolvable and carries its derived value — even when §12.1.4 is absent. The escalation is triggered by §8.5's "`nda_clause_chunks` absent from bundle" precedence rule, not by an unresolvable NDA status. To make this scenario produce `nda_status: UNKNOWN`, **both** the clause AND `existing_nda_status` must be absent from the bundle.

**Expected Legal Agent output per SPEC v0.9:**
- `status: escalated`
- All six determination fields **present** (not absent — that's the §9.1 blocked shape)
- `dpa_required: true` — DPA determination fully resolved
- `dpa_blocker` — bool, derived from `existing_dpa_status` per §8.3
- `nda_status: "UNKNOWN"` — per §8.4, `existing_nda_status` absent or unrecognized → `UNKNOWN`
- `nda_blocker: true` — per §8.4, `nda_status != EXECUTED` → blocker is true
- `trigger_rule_cited` non-empty with at least one PRIMARY DPA-TM-001 entry
- `policy_citations` contains the DPA-TM-001 PRIMARY citation; does NOT contain an ISP-001 §12.1.4 citation (that citation is the gap)
- Audit log names ISP-001 §12.1.4 as the missing required source

---

## What already exists — do not rebuild

Everything. No new source documents, chunks, or embeddings needed. This fixture is a targeted subtraction from an existing bundle. No scenario-scoped indices required.

---

## What you need to build

### One bundle fixture only

Create `tests/fixtures/bundles/step_03_scenario_6.json`.

Base it on the Scenario 2 bundle with three targeted changes:

1. **Remove the ISP-001 §12.1.4 chunk from the bundle entirely** — not null, absent. Other ISP-001 chunks may remain if present in Scenario 2's bundle.
2. **Remove `existing_nda_status` from the questionnaire fields entirely** — not null, absent. This forces `nda_status` to normalize to `UNKNOWN` per §8.4 and makes `nda_blocker: true` the correct derivation rather than a conservative default.
3. **Include `existing_dpa_status`** with a defined value (e.g., `EXECUTED` or `NOT_STARTED` — your pick, just be explicit) so the DPA blocker determination is not left hanging.

Everything else — upstream IT Security output with `data_classification: REGULATED`, EU personal data fields, DPA trigger rows — must remain intact. The DPA path must be completable; only the NDA clause citation and raw NDA evidence are severed.

### Add the Scenario 6 evaluator

Add a scenario 6 path to the existing Legal Agent evaluator. Hard checks, aligned to SPEC v0.9 §9.2, §10, and A-10:

- `status == "escalated"`
- **All six determination fields present** (not absent): `dpa_required`, `dpa_blocker`, `nda_status`, `nda_blocker`, `trigger_rule_cited`, `policy_citations`. Absence of any is a blocked-shape violation and a test failure.
- `dpa_required is True` — DPA determination fully resolved despite escalation
- `dpa_blocker` is a bool and consistent with the `existing_dpa_status` value you put in the fixture per §8.3 (`EXECUTED` → `false`, anything else → `true`)
- `nda_status == "UNKNOWN"`
- `nda_blocker is True`
- `trigger_rule_cited` is a non-empty list with at least one PRIMARY DPA-TM-001 entry carrying `source_id`, `version`, `row_id`, and `trigger_condition`
- `policy_citations` contains the DPA-TM-001 PRIMARY citation
- `policy_citations` does NOT contain any ISP-001 §12.1.4 entry (that citation is the gap being tested)

Soft checks:
- Audit log entry for this step references ISP-001 §12.1.4 as the missing required source
- `blocked_reason` and `blocked_fields` are **absent** from the output (those belong to §9.1 blocked shape only)

**The critical failure modes to catch:**
1. The model blocks the entire step rather than completing the DPA determination. `dpa_required` absent or null alongside `status: escalated` is an A-10 violation — the agent discarded a completed determination when escalating on a narrower gap.
2. The model emits the §9.1 blocked shape (only `status`, `blocked_reason`, `blocked_fields`). That's wrong — the bundle was admissible per §3; the agent had evidentiary basis to begin work.
3. The model fabricates an ISP-001 §12.1.4 citation that wasn't in the bundle. That's a silent-failure hallucination and must fail the test loudly.

---

## Before running

State the fixture path, the spec version being tested (SPEC-AGENT-LEG-001 v0.9), and the chosen `existing_dpa_status` value. Wait for confirmation before the API call.
