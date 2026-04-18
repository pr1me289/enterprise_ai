# Scenario 5 — Legal Agent Fixture Build: Tier 1 DPA Matrix Conflict → ESCALATED

## What this tests

Two DPA-TM-001 rows both apply to OptiChain's profile but produce contradictory trigger outcomes. Per CC-001 §4.1, a Tier 1 vs Tier 1 conflict cannot be auto-suppressed — both rows must be cited and the determination must escalate. This simultaneously exercises the Legal Agent's conflict handling, the retrieval layer's ability to surface both rows, and the row-level atomicity of the DPA matrix chunking strategy.

**Expected Legal Agent output per SPEC-AGENT-LEG-001 v0.9:**
- `status: escalated`
- All six determination fields **present** (not absent — that's the blocked shape)
- `dpa_required: null`, `dpa_blocker: null` — per §9.2 and Example D, the conflict makes the DPA determination unresolvable
- `trigger_rule_cited: null` — per §9.2, no citation can be made for an unresolved determination
- `nda_status` and `nda_blocker` populated from questionnaire evidence (NDA is independently resolvable)
- `policy_citations` includes the resolved ISP-001 §12.1.4 NDA citation but omits unresolvable DPA citations
- Audit log captures both conflicting row IDs as the escalation payload (per §9.2 note: "`policy_citations` array on an escalated output must cite both conflicting chunks when the escalation is clause-level" — for this scenario the two conflicting rows go into the audit payload since `trigger_rule_cited` must be `null` when `dpa_required` is `null`)

---

## Critical rule: isolated scenario data only

**Do not edit any production source documents.** Do not edit the existing DPA-TM-001 source document, the production Chroma collection, or the production BM25 index. All artifacts for this scenario live under `scenario_data/scenario_5/` and the test harness must point at scenario-scoped indices for this run only.

---

## Work items in order

### 1. Build the scenario-5 DPA trigger matrix source

Create `scenario_data/scenario_5/sources/DPA-TM-001_scenario5.json` (or the format parallel to how DPA-TM-001 is stored in production). Copy the full existing DPA-TM-001 v2.1 row set, then add one additional row.

The new row (`row_id: A-07`) must describe the **same fact pattern** as row A-01 — EU/EEA employee personal data processed by a SaaS vendor for workforce-adjacent analytics — and produce the opposite outcome (`DPA Required?: NOT REQUIRED`). The trigger condition should ground the different outcome in a plausible legal theory (e.g., Art. 6(1)(f) legitimate interest for internal workforce analytics, or a controller-to-controller framing that sidesteps Art. 28). The row must not carve itself out of A-01's scope via anonymization, aggregation, no-persistent-storage, or any other factual limitation. Both rows must fire on OptiChain's exact questionnaire profile with no principled way to pick one over the other — the conflict is in the legal conclusion, not in the factual predicates.

Mark this file's version as `2.1-scenario5` so it cannot be confused with the production v2.1.

### 2. Build scenario-scoped indices

Re-chunk the scenario-5 DPA source using the production row-level chunking strategy (one row per chunk, column headers embedded in each chunk). Verify the new row is stored as its own atomic chunk with its own `chunk_id` and `row_id`.

Embed and write to a **scenario-scoped** Chroma collection — e.g. `idx_dpa_matrix__scenario5` — and build a **scenario-scoped** BM25 index. Do not write to `idx_dpa_matrix` or any production collection. Create `scenario_data/scenario_5/index_registry.json` pointing the test harness at these scenario-scoped indices.

### 3. Build the bundle fixture

Create `tests/fixtures/bundles/step_03_scenario_5.json`. Base it on the Scenario 2 bundle. The meaningful difference is `dpa_trigger_rows` — populate with both the original conflicting row and the new contradicting row pulled from the scenario-5 source. Upstream IT Security output must show `data_classification: REGULATED` and questionnaire fields must show `eu_personal_data_flag: true` / `data_subjects_eu: true` so both rows are plausibly in scope. Include `nda_clause_chunks` (ISP-001 §12.1.4) and `existing_nda_status: EXECUTED` so NDA is independently resolvable — this isolates the test to the DPA conflict only.

### 4. Configure isolated test environment

The test harness must:
- load `scenario_data/scenario_5/index_registry.json` and route `idx_dpa_matrix` queries to the scenario-scoped collection for this run only
- leave all other scenario tests untouched (scenarios 1–4 continue pointing at their existing indices)
- not mutate production artifacts under any failure path

### 5. Add the Scenario 5 evaluator

Add a scenario 5 path to the existing Legal Agent evaluator. Hard checks, aligned to SPEC-AGENT-LEG-001 v0.9 §9.2, §10, and A-10:

- `status == "escalated"`
- **All six determination fields present** (not absent): `dpa_required`, `dpa_blocker`, `nda_status`, `nda_blocker`, `trigger_rule_cited`, `policy_citations`. Absence of any is a blocked-shape violation and a test failure.
- `dpa_required is None` (null)
- `dpa_blocker is None` (null — per §9.2, cannot derive blocker from unresolved determination)
- `trigger_rule_cited is None` (null — per §9.2, no citation for unresolved determination)
- `nda_status in {"EXECUTED","PENDING","NOT_STARTED","UNKNOWN"}` and non-null
- `nda_blocker` is a bool and is consistent with `nda_status` per §8.4
- `policy_citations` contains the ISP-001 §12.1.4 entry (NDA citation resolvable) and does NOT contain a DPA-TM-001 PRIMARY citation (cannot cite an unresolved determination)

Soft checks:
- Audit log entry for this step contains both conflicting `row_id`s and both `trigger_condition` strings in the escalation payload
- `blocked_reason` and `blocked_fields` are **absent** from the output (those belong to the §9.1 blocked shape only)
- The model did not silently pick one row and emit `dpa_required: true|false` — that's a conflict-handling failure and A-05 violation

### 6. Verify retrieval before the API call

Run a retrieval-only check against `idx_dpa_matrix__scenario5` using a query representative of OptiChain's EU employee data profile. Confirm both conflicting rows appear in the candidate set. If only one row surfaces, the retrieval layer is the failure point — fix chunking or embedding before spending the API call.

---

## Before running

State the fixture path, the spec version being tested (SPEC-AGENT-LEG-001 v0.9), the scenario-scoped index names, and confirm no production artifacts were touched. Wait for confirmation before the API call.
