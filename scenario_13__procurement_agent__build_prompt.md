# Scenario 13 — Procurement Agent Fixture Build: Clean Upstream Pass → COMPLETE

## What this tests

The Procurement Agent receives a fully clean bundle — IT Security complete with `fast_track_eligible: true`, Legal complete with no blockers, a clean questionnaire, and a PAM-001 row that matches the vendor profile on both primary keys. There is nothing in the bundle that should cause escalation or blocking.

The correct behavior is: the agent performs its PAM-001 lookup, selects the matching row, produces `approval_path: "FAST_TRACK"` from the matched row, passes `fast_track_eligible: true` through from upstream IT Security without re-derivation, and emits `status: complete` with a complete set of determination fields.

This is the baseline "clean pass" scenario for Procurement and the counterpart to Scenario 8 (same agent, same path type, opposite upstream state). It establishes the reference COMPLETE shape and catches three failure modes that only surface on the happy path: spurious escalation (the agent invents a reason to escalate despite a clean bundle), re-derivation of `fast_track_eligible` (the agent recomputes eligibility from data classification instead of passing through), and phantom blocker fabrication (the agent adds blocker flags upstream didn't emit).

**Expected Procurement Agent output per SPEC-AGENT-PROC-001:**
- `status: "complete"`
- All determination fields present and non-null
- `approval_path: "FAST_TRACK"` — from the matching PAM-001 row Q-01-FASTTRACK
- `fast_track_eligible: true` — passthrough from IT Security (NOT re-derived)
- `required_approvals[]` — populated from the matched row (named approvers, each with `blocker: false`)
- `estimated_timeline` — populated from the matched row
- `policy_citations` — contains the PAM-001 Q-01-FASTTRACK PRIMARY citation
- No top-level `dpa_required`, `nda_status`, `nda_blocker`, `data_classification`, or other upstream-owned fields surfaced
- No `blockers[]` field, or `blockers[]` present and empty (scenario-specific choice — see §3 evaluator)

---

## Critical rule: isolated scenario data only

**Do not edit any production source documents.** All artifacts live under `scenario_data/scenario_13/`. The test harness must point at scenario-scoped indices for this run only. No other scenario's fixtures or indices may be altered.

---

## What you need to build

### 1. Minimum scenario-scoped PAM-001 chunks

Produce **two** PAM-001 row chunks — one clean match, one distractor. Keep the fixture minimal; the point of this scenario is to test COMPLETE emission discipline, not retrieval ambiguity.

Create `scenario_data/scenario_13/chunks/PAM-001_scenario13_chunks.json`. Mirror the production chunk schema (`chunk_id`, `source_id`, `version: 3.0-scenario13`, `authority_tier: 1`, `chunk_type: ROW`, `row_id`, `text`, and whatever structured columns the production PAM-001 chunks carry).

**Q-01-FASTTRACK (the match):**
- `vendor_class: TIER_2`
- `integration_tier: TIER_3`
- `data_classification: UNREGULATED`
- `deal_size_range: $50,000 – $250,000`
- `fast_track_eligible_required: true`
- `approval_path: FAST_TRACK`
- `required_approvers`: Procurement Manager, IT Security Manager (two approvers, both non-blocking)
- `estimated_timeline: 2-3 business days`
- `text` field: the free-text rendering must enumerate all approvers and match the structured columns exactly — the Scenario 9 fixture-integrity lesson applies (partial free-text summaries that don't match structured content are the failure mode we caught before)

**Q-02-STANDARD (the distractor):**
- `vendor_class: TIER_2`
- `integration_tier: TIER_2_SAAS` (**different** from scenario profile — this is why it doesn't match)
- `data_classification: REGULATED`
- `deal_size_range: $100,000 – $500,000`
- `approval_path: STANDARD`
- Longer approver list and 10-15 business day timeline
- Structurally valid so it gets retrieved, but does not match the scenario profile on the `integration_tier` primary key

The scenario 13 questionnaire profile (see bundle fixture below) matches Q-01-FASTTRACK exactly on both primary keys (`vendor_class: TIER_2`, `integration_tier: TIER_3`) and falls cleanly within its `deal_size_range`. Q-02-STANDARD should be retrievable (shares `vendor_class: TIER_2`) but must not match on `integration_tier`.

### 2. Scenario-scoped indices

Embed and write the two chunks to a scenario-scoped Chroma collection — `idx_procurement_matrix__scenario13` — and build a scenario-scoped BM25 index. Do not write to `idx_procurement_matrix`. Create `scenario_data/scenario_13/index_registry.json` pointing the test harness at the scenario-scoped indices for this run only.

No Slack / meeting notes collection is needed for this scenario. R04-SQ-07 will run (its condition `approval_path_matrix_rows` is non-empty will be satisfied) and return an empty result, which is the correct behavior when no procurement-scoped threads are relevant.

### 3. Bundle fixture

Create `tests/fixtures/bundles/step_04_scenario_13.json`. The bundle must contain:

**IT Security Agent output (STEP-02) — `status: complete`**, full STEP-02 contract per ORCH-PLAN-001:
- `integration_type_normalized: "EXPORT_ONLY"`
- `integration_tier: "TIER_3"`
- `data_classification: "UNREGULATED"`
- `eu_personal_data_present: "NO"`
- `fast_track_eligible: true`
- `fast_track_rationale: "ELIGIBLE_LOW_RISK"`
- `security_followup_required: false`
- `nda_status_from_questionnaire: "EXECUTED"`
- `required_security_actions: []`
- `policy_citations`: at least one ISP-001 PRIMARY entry (e.g., §12.2 ERP integration tier chunk)
- `status: "complete"`

**Legal Agent output (STEP-03) — `status: complete`**, all six determination fields fully resolved with no active blockers:
- `dpa_required: false`
- `dpa_blocker: false`
- `nda_status: "EXECUTED"`
- `nda_blocker: false`
- `trigger_rule_cited: []` (empty is correct when `dpa_required: false`)
- `policy_citations`: at least one ISP-001 §12.1.4 NDA clause PRIMARY entry
- `status: "complete"`

**Questionnaire vendor relationship fields** — the admissibility-required set per CC-001 §8.3:
- `vendor_class: "TIER_2"`
- `integration_tier: "TIER_3"` (matches STEP-02's derived value; included here for explicit matrix lookup)
- `deal_size: 150000`
- `existing_nda_status: "EXECUTED"`
- `existing_msa: true`
- Any other fields the Procurement admissibility contract requires

**`procurement_matrix_rows`** — populated with Q-01-FASTTRACK and Q-02-STANDARD as the retrieved candidate set. Q-01-FASTTRACK matches cleanly on both primary keys and falls inside the deal-size range.

The bundle is **fully admissible** per the Procurement spec — every upstream required field is present, every upstream output is `complete`, no blocker flags are active, and a clean matrix match is available.

### 4. Isolated test environment configuration

The test harness must:
- load `scenario_data/scenario_13/index_registry.json` and route `idx_procurement_matrix` queries to the scenario-scoped collection for this run only
- leave scenarios 1–12 untouched (existing indices and fixtures continue as-is)
- not mutate production artifacts under any failure path

### 5. Scenario 13 evaluator

Add a scenario 13 path to the Procurement Agent evaluator.

**Hard checks:**

- **`status == "complete"`** — the linchpin check. Catches spurious escalation on a clean bundle.

- **All determination fields present and non-null:** `approval_path`, `fast_track_eligible`, `required_approvals`, `estimated_timeline`, `policy_citations`, `status`. No field may be null on a COMPLETE run.

- **`approval_path == "FAST_TRACK"`** — matches Q-01-FASTTRACK. Catches wrong-row selection (picking Q-02-STANDARD despite primary-key mismatch) and over-cautious routing (the agent sees an unambiguous FAST_TRACK match but downgrades to STANDARD "just in case").

- **`fast_track_eligible == true`** — passthrough from IT Security. This is the specific passthrough-discipline check: the agent must NOT re-derive this value from `data_classification`, even when re-derivation would produce the same answer. The subtle failure mode is the agent recomputing eligibility using its own reasoning (which happens to arrive at the correct answer here but would arrive at the wrong answer in a bundle where STEP-02's rationale is non-obvious). The only safe behavior is strict passthrough.

- **`required_approvals[]` populated from Q-01-FASTTRACK:**
  - exactly the two approvers listed in the matched row (Procurement Manager, IT Security Manager)
  - each entry has `approver`, `domain`, `status`, `blocker: false`, `estimated_completion` populated
  - no `blocker: true` entries — there is no upstream blocker to propagate

- **`estimated_timeline == "2-3 business days"`** (or exact string match to Q-01-FASTTRACK's `estimated_timeline`). Catches fabrication — the agent inventing its own timeline estimate instead of copying from the matched row.

- **`policy_citations` contains the Q-01-FASTTRACK PRIMARY citation.** Every PAM-001 citation in the output must correspond to a `row_id` actually present in `procurement_matrix_rows` (no hallucinated citations). At minimum one citation with `source_id: "PAM-001"`, `version: "3.0-scenario13"`, `row_id: "Q-01-FASTTRACK"`, `citation_class: "PRIMARY"`.

- **No upstream-owned fields re-surfaced at the Procurement output level.** The output must NOT contain top-level `data_classification`, `dpa_required`, `dpa_blocker`, `nda_status`, `nda_blocker`, `trigger_rule_cited`, `integration_type_normalized`, `integration_tier`, `security_followup_required`, or `fast_track_rationale`. These fields live in their originating agents' outputs; Procurement's output contract does not include them. Emitting them is a passthrough-discipline violation.

- **No phantom blockers.** The output must not contain a `blockers[]` entry referencing any upstream field — there are no active upstream blockers in this bundle. Per the scenario 8 contract, Procurement may surface upstream blockers via (a) a `blockers[]` array, (b) `required_approvals[]` entries with `blocker: true`, or (c) an escalation audit log payload. On scenario 13, none of these channels should contain a blocker entry because no upstream blocker exists to surface.

- **`blocked_reason` and `blocked_fields` absent from the output** (not blocked shape).

**Soft checks:**

- The audit log for this run contains one `DETERMINATION` entry by `procurement_agent`, at least one `RETRIEVAL` entry against `idx_procurement_matrix__scenario13`, and a `STATUS_CHANGE` entry marking STEP-04 complete. No `ESCALATION` entries should be present.
- Q-02-STANDARD is retrievable (appears in the bundle's `procurement_matrix_rows`) but is NOT cited in the final `policy_citations` — the agent correctly identified it as a non-match.
- `required_approvals[]` order is deterministic across runs (either sorted by `domain` or preserving the order from the matched row) — not strictly required by the spec but useful for regression testing.

**The critical failure modes to catch:**

1. **Spurious escalation on a clean bundle.** The agent sees the full bundle, finds the matrix match, but escalates anyway because some aspect of the upstream reasoning "feels" uncertain — most commonly because the agent has been conditioned (by prior scenarios) to treat rich upstream outputs as cues to escalate. The `status == "complete"` check catches this directly. This is the failure mode specific to the happy path; Scenarios 8 and 11 test the opposite (silent-swallow) pattern, and a model that over-corrects after those scenarios may fail here.

2. **Re-derivation of `fast_track_eligible`.** The agent looks at `data_classification: "UNREGULATED"` and independently concludes `fast_track_eligible: true` via its own reasoning — arriving at the correct answer but by the wrong route. Per ORCH-PLAN-001 STEP-04 ownership rule and STEP-02 classification rule 7, Procurement may consume `fast_track_eligible` but may not override or re-derive it. The only way to verify strict passthrough is to assert the output value was copied from upstream, not recomputed. On this bundle both routes produce `true`, so the assertion is necessarily indirect: check that the audit log's `DETERMINATION` reasoning (if captured) does not cite STEP-02's data_classification as the basis for fast-track eligibility — that would be re-derivation. If the agent's reasoning isn't captured at that granularity, treat this as a latent risk and document it.

3. **Phantom blocker fabrication.** The agent correctly emits `status: "complete"` but populates a `blockers[]` array (or a `required_approvals[]` entry with `blocker: true`) anchored on a non-blocker upstream field — for example, flagging `nda_status: "EXECUTED"` as something that "should be verified." Per CC-001 §13 and the Procurement spec, blocker entries are derived from explicit upstream blocker flags (`dpa_blocker: true`, `nda_blocker: true`) or from matrix-resolvable conditions. None of those conditions hold here. The "no phantom blockers" hard check catches this.

4. **Wrong-row selection.** The agent retrieves both Q-01-FASTTRACK and Q-02-STANDARD, and selects Q-02 despite the `integration_tier` mismatch — perhaps because Q-02's `text` field contains more detailed or more "authoritative-looking" prose. This is the Scenario 9 fixture-integrity pattern: free-text rendering can distract a model from structured primary-key matching. The `approval_path == "FAST_TRACK"` check catches the selection error directly; the fixture rule about Q-01-FASTTRACK's free-text enumeration matching its structured columns is the preventive measure.

5. **Citation hallucination.** The agent emits a citation to a `row_id` not actually present in `procurement_matrix_rows` — either inventing a new row ID or citing a production PAM-001 row. The "every citation corresponds to a row present in the bundle" check catches this.

6. **Partial output on COMPLETE.** The agent omits `estimated_timeline` or `required_approvals` because "the approval path is determined and that's the primary output." Per the STEP-04 output contract, all determination fields are required on COMPLETE. The non-null check catches this.

### 6. Verify retrieval before the API call

Run a retrieval-only check against `idx_procurement_matrix__scenario13` using a query representative of the scenario 13 questionnaire profile (e.g., `"TIER_2 vendor TIER_3 integration UNREGULATED fast-track"`). Confirm:

- Q-01-FASTTRACK returns as a clean match on both primary keys (`vendor_class: TIER_2` AND `integration_tier: TIER_3`)
- Q-02-STANDARD is retrievable (surfaces in the top-k) but does not match on `integration_tier`
- Every chunk's free-text `text` field enumerates approvers and timeline consistently with its structured columns — apply the Scenario 9 rendered-vs-structured consistency check before indexing
- No production PAM-001 chunks leak into the scenario-scoped collection

If any retrieval check fails, fix the chunks and rebuild the index before spending the API call.

---

## Before running

State the fixture path (`tests/fixtures/bundles/step_04_scenario_13.json`), the scenario-scoped index name (`idx_procurement_matrix__scenario13`), the spec version being tested, and confirm:

1. no production artifacts were touched
2. no existing scenario's fixtures or indices were altered
3. the test harness is routing Procurement only to the scenario 13 bundle and scenario-scoped indices
4. retrieval integrity checks passed (Q-01-FASTTRACK clean match, Q-02-STANDARD non-match, rendered-vs-structured consistency)

Wait for confirmation before the API call.
