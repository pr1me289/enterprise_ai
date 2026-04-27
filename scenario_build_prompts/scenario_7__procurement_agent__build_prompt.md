# Scenario 7 — Procurement Agent Fixture Build: No Matching PAM-001 Row → ESCALATED

## What this tests

The Procurement Agent receives clean upstream outputs (IT Security and Legal both `complete`) and a well-formed questionnaire, but the vendor/deal combination does not match any row in PAM-001. Per CC-001 §12 and Procurement Agent spec §8.5, no matching approval matrix row means evidence is insufficient for a RESOLVED approval path — the agent must emit `escalated` with resolution owner = Procurement Director, **not** fabricate an approval path by picking the nearest row.

This is the single highest-risk failure mode for the Procurement Agent: silent failure that directly authorizes spend under a non-governing approval path. The evaluator must catch any attempt to emit a `complete` determination without a governing PAM-001 row cited.

**Expected Procurement Agent output per SPEC-AGENT-PROC-001:**
- `status: escalated`
- All determination fields **present** (not absent — that's the blocked shape)
- `approval_path: null` — cannot be resolved without a governing row
- `executive_approval_required: null` — cannot be derived from an unresolved path
- `required_approvals: null` or `[]` — no governing row to enumerate approvers
- `estimated_timeline: null` — cannot be derived from an unresolved path
- `fast_track_eligible` populated from upstream IT Security output (passthrough; not owned by Procurement)
- `policy_citations` does NOT contain any PAM-001 PRIMARY citation (there is no matching row to cite)
- Audit log escalation payload names the unmatched vendor/deal combination and identifies resolution owner as Procurement Director

---

## Critical rule: isolated scenario data only

**Do not edit any production source documents.** Do not edit the existing PAM-001 source document, the production Chroma collection, or the production BM25 index. All artifacts live under `scenario_data/scenario_7/`. The test harness must point at scenario-scoped indices for this run only.

---

## What you need to build

### 1. Minimum scenario-scoped PAM-001 chunks

Produce the smallest set of PAM-001 chunks that makes the "no matching row" condition unambiguous. Do not rebuild the full production matrix. Create `scenario_data/scenario_7/chunks/PAM-001_scenario7_chunks.json` containing 3–4 PAM-001 row chunks that collectively cover common vendor/deal combinations but **deliberately leave a gap** the Scenario 7 questionnaire profile will hit.

Use the production chunk schema (`chunk_id`, `source_id`, `source_name`, `source_type: APPROVAL_MATRIX`, `version: 3.0-scenario7`, `authority_tier: 1`, `retrieval_lane: INDEXED_HYBRID`, `allowed_agents: ["procurement"]`, `is_primary_citable: true`, `manifest_status: CONFIRMED`, `chunk_type: ROW`, `row_id`, `citation_label`, `text`, etc. — mirror whatever the production PAM-001 chunks use).

Each row chunk should clearly state its vendor_class / deal_size / integration_type coverage so the mismatch is apparent. Example coverage (adjust to whatever your production PAM-001 row semantics look like):

- Row P-01: Tier 1 vendor, deal size $0–$100K, standard integration → STANDARD path
- Row P-02: Tier 2 vendor, deal size $100K–$500K, SaaS → FAST_TRACK path (conditional on fast_track_eligible)
- Row P-03: Any vendor tier, deal size >$500K → EXECUTIVE_APPROVAL path

The deliberate gap: the Scenario 7 questionnaire will have a combination none of these cover — e.g., Tier 3 vendor, deal size $50K, international entity with non-standard integration. The rows describe plausible coverage without reaching this combination.

### 2. Scenario-scoped indices

Embed and write the scenario-7 chunks to a scenario-scoped Chroma collection — e.g. `idx_procurement_matrix__scenario7` — and build a scenario-scoped BM25 index. Do not write to `idx_procurement_matrix` or any production collection. Create `scenario_data/scenario_7/index_registry.json` pointing the test harness at these scenario-scoped indices for this run only.

### 3. Bundle fixture

Create `tests/fixtures/bundles/step_04_scenario_7.json`. Build it directly — no need to base it on an earlier scenario since the Procurement fixture composition is different from Legal's. The bundle must contain:

- **IT Security Agent output** (all required STEP-02 fields per the Procurement admissibility contract): `onboarding_path_classification`, `data_classification: UNREGULATED`, `fast_track_eligible: true`, `integration_tier`, `security_followup_required: false`, `policy_citations`, `status: complete`. Clean upstream — no ambiguity here.
- **Legal Agent output** (all required STEP-03 fields): `dpa_required: false`, `dpa_blocker: false`, `nda_status: EXECUTED`, `nda_blocker: false`, `trigger_rule_cited: []`, `policy_citations`, `status: complete`. Clean upstream.
- **Questionnaire vendor relationship fields** populated with the unmatched combination: `vendor_class: TIER_3`, `deal_size: 50000` (or whatever value sits in the gap), `existing_nda_status: EXECUTED`, `existing_msa: true`, plus any other required questionnaire fields the Procurement bundle needs per the admissibility contract.
- **`procurement_matrix_rows`** field populated with the rows retrieved from `idx_procurement_matrix__scenario7` — i.e., P-01, P-02, P-03 as the candidate set. None of them match the questionnaire profile cleanly.

The bundle must be **admissible** per the Procurement spec — every required upstream field is present. The failure is downstream: the agent has the evidence it needs to look up a row, but no row matches. This is what distinguishes escalated from blocked for this scenario.

### 4. Isolated test environment configuration

The test harness must:
- load `scenario_data/scenario_7/index_registry.json` and route `idx_procurement_matrix` queries to the scenario-scoped collection for this run only
- leave all other scenario tests untouched (scenarios 1–6 continue pointing at their existing indices)
- not mutate production artifacts under any failure path

### 5. Scenario 7 evaluator

Add a scenario 7 path to the Procurement Agent evaluator. Hard checks:

- `status == "escalated"`
- **All determination fields present** (not absent): `approval_path`, `fast_track_eligible`, `executive_approval_required`, `required_approvals`, `estimated_timeline`, `policy_citations`. Absence of any is a blocked-shape violation.
- `approval_path is None` (null)
- `executive_approval_required is None` (null)
- `estimated_timeline is None` (null)
- `required_approvals` is `None` or `[]`
- `fast_track_eligible is True` — passthrough from IT Security upstream, must not be silently demoted or mutated
- `policy_citations` does NOT contain any entry where `source_id == "PAM-001"` and `citation_class == "PRIMARY"` — there is no governing row to cite
- `blocked_reason` and `blocked_fields` are **absent** from the output (those belong to the blocked shape only)

Soft checks:
- Audit log entry for STEP-04 references the unmatched vendor/deal combination in the escalation payload
- Audit log names resolution owner as Procurement Director per CC-001 §12

**The critical failure modes to catch:**
1. **Silent path fabrication** — the model picks the nearest PAM-001 row and emits `approval_path: STANDARD | FAST_TRACK | EXECUTIVE_APPROVAL` with `status: complete`. This is the dangerous case — the evaluator must fail loudly if any approval_path enum value is present alongside `status: complete` without a PAM-001 PRIMARY citation backing it.
2. **Field ownership violation** — the model sets `fast_track_eligible: false` because it decided to override upstream IT Security. Per the spec, Procurement does not own this field and must pass it through unchanged.
3. **Wrong shape** — the model emits the blocked shape (determination fields absent) instead of the escalated shape. The bundle was admissible; the agent had evidentiary basis to begin work. `escalated` is the correct status.
4. **Hallucinated PAM-001 citation** — the model cites a PAM-001 row that wasn't in the bundle. Evaluator must confirm every PAM-001 citation in the output matches a `row_id` actually present in `procurement_matrix_rows`.

### 6. Verify retrieval before the API call

Run a retrieval-only check against `idx_procurement_matrix__scenario7` using a query representative of the scenario-7 questionnaire profile (Tier 3, $50K, international). Confirm that the rows returned are the P-01/P-02/P-03 candidate set and that **no row cleanly matches** the profile. If a row does match, the gap in the matrix is not wide enough — adjust the chunk definitions or the questionnaire profile before spending the API call.

---

## Before running

State the fixture path, the spec version being tested, the scenario-scoped index names, and confirm no production artifacts were touched. Wait for confirmation before the API call.
