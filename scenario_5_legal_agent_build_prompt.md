# Scenario 5 — Legal Agent Fixture Build: Tier 1 DPA Matrix Conflict → ESCALATED

## What this tests

Two DPA-TM-001 rows both apply to OptiChain's profile but produce contradictory trigger outcomes. Per CC-001 §4.1, a Tier 1 vs Tier 1 conflict cannot be auto-suppressed — both rows must be cited and the determination must escalate. This simultaneously tests the Legal Agent's conflict handling, the retrieval layer's ability to surface both rows, and the row-level atomicity of the DPA matrix chunking strategy.

Expected output:
- `status: escalated`
- `trigger_rule_cited` non-empty, both conflicting rows cited
- No `dpa_required` determination emitted — the conflict prevents resolution

---

## Work items in order

### 1. Update the DPA trigger matrix source document

Add one new row to the existing DPA-TM-001 source document. The new row must:
- apply to the same vendor profile as an existing EU personal data trigger row (EU employee data, SaaS deployment)
- produce the opposite trigger outcome — DPA **not** required when data is limited to operational scheduling metadata with no persistent storage

The existing row and the new row must both plausibly match OptiChain's questionnaire profile. That ambiguity is intentional — it is what forces the conflict.

Do not alter any other rows. Do not create a new source document — update the existing one and increment its version.

### 2. Re-chunk and re-embed `idx_dpa_matrix` only

Re-chunk the updated DPA-TM-001 source using the existing row-level chunking strategy — one row per chunk, column headers embedded in each chunk. Confirm the new row is stored as its own atomic chunk with its own `chunk_id` and `row_id`.

Re-embed and upsert into the existing `idx_dpa_matrix` Chroma collection and rebuild the `idx_dpa_matrix` BM25 index. Do not touch any other collection or index.

Update `index_registry.json` to reflect the new DPA-TM-001 version and chunk count.

### 3. Build the bundle fixture

Create `tests/fixtures/bundles/step_03_scenario_5.json`.

Base it on the Scenario 2 bundle. The meaningful difference is `dpa_trigger_rows` — populate it with both the original conflicting row and the new contradicting row. Upstream IT Security output should show `data_classification: REGULATED` and `eu_personal_data_present: true` so both rows are plausibly in scope.

### 4. Add the Scenario 5 evaluator

Add a scenario 5 evaluation path to the existing per-agent evaluator for the Legal Agent. Hard-checks:
- `status: escalated`
- `trigger_rule_cited` is non-empty and contains at least two entries
- both conflicting row IDs are present in `trigger_rule_cited`
- `dpa_required` is absent or null — a resolved boolean determination is a test failure

Soft check:
- both entries in `trigger_rule_cited` carry `source_id: DPA-TM-001`, `row_id`, `trigger_condition`, and `citation_class: PRIMARY`

### 5. Verify retrieval before the API call

Before running the live test, run a retrieval-only check against `idx_dpa_matrix` using a query representative of OptiChain's EU employee data profile. Confirm both rows are returned in the candidate set. If only one row surfaces, the retrieval layer is the failure point — do not spend the API call until retrieval is confirmed.

---

## Before running

State the fixture path, spec, and scenario per the testing procedure. Wait for confirmation before the API call.
