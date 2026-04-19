# Scenario 9 — Procurement Agent Fixture Build: Tier 3 Supplementary Evidence Handling → COMPLETE

## What this tests

The Procurement Agent is the only domain agent permitted to consume Tier 3 (Slack) evidence per CC-001 §5.1. Existing scenarios (1, 7, 8) exercise row-selection, no-match escalation, and upstream-escalation propagation — none test whether the agent correctly handles Tier 3 evidence in its bundle. This scenario fills that gap.

The bundle contains a clean upstream, a cleanly matching PAM-001 row, **and** two Procurement-scoped Slack threads that survived bundle assembly (non-conflicting, non-redundant, authority-capped). One thread is generic background; the other is a colleague expressing a *preference* that conflicts with the matrix-derived approval path but is framed as opinion rather than fact ("honestly we usually fast-track these to save cycle time"). Both are marked `authority_tier: 3` and `citation_class: SUPPLEMENTARY` at retrieval time.

The correct behavior is: the agent performs its PAM-001 lookup against the clean primary-key match, derives `approval_path` and `required_approvals` entirely from the Tier 1 matrix row, emits `status: complete`, and either (a) cites the relevant Slack thread as `SUPPLEMENTARY` or (b) excludes it as non-additive — both are defensible per CC-001 §10's inclusion gate. The agent must **not** cite any Slack thread as `PRIMARY`, must **not** let Slack content influence any determination field, and must **not** soften `required_approvals` on the strength of the "we usually fast-track these" opinion.

This tests the governance teeth of the authority hierarchy: does the agent treat Tier 1 matrix rows as authoritative even when Tier 3 evidence is present and suggests a different path? It's the single clearest demonstration of the Context Contract's value proposition.

**Expected Procurement Agent output per SPEC-AGENT-PROC-001:**
- `status: complete`
- `approval_path` populated from the matching PAM-001 row
- `fast_track_eligible` populated from upstream IT Security output (passthrough; must not be influenced by Slack content)
- `required_approvals` populated from the matching row, unmodified by Slack content
- `estimated_timeline` populated from the matching row
- `policy_citations`: PAM-001 matching row as `PRIMARY`; Slack threads either absent or cited as `SUPPLEMENTARY` with `source_id: SLK-001`. **No Slack citation may carry `citation_class: PRIMARY`.**
- No `blockers[]`, `blocked_reason`, or `blocked_fields` fields present

---

## Critical rule: isolated scenario data only

Do not edit any production source documents. All artifacts live under `scenario_data/scenario_9/`. The test harness must point at scenario-scoped indices for this run only.

---

## What you need to build

### 1. Minimum scenario-scoped PAM-001 chunks

Produce 2–3 PAM-001 row chunks covering the scenario's vendor/integration profile so the matrix lookup succeeds cleanly. Use Class D × T2 as the target profile — it's a STANDARD path, NOT ELIGIBLE for fast-track, regulated data handling (via DPA), and has clear heavier alternatives (D-T1 lighter, D-T3 enhanced) available as distractors — which also continues the row-selection testing lineage from scenarios 1 and 7.

Create `scenario_data/scenario_9/chunks/PAM-001_scenario9_chunks.json`. Mirror production chunk schema. Use `version: 3.0-scenario9`.

Required rows:
- **D-T2 (matching row)**: `vendor_class: D`, `integration_tier: T2`, `approval_path: STANDARD`, `fast_track_eligible: NOT ELIGIBLE`, approvers: IT Security (Required), Legal (Required), Procurement (Required), Business Owner (Director+). Notes field per production matrix: DPA required if regulated data accessed, background-check requirements per ISP-001 §6.3.
- **D-T1 (distractor, lighter)**: covers the adjacent-lighter row. Ensures the model can't pick a lighter alternative without a primary-key mismatch.
- **D-T3 (distractor, enhanced)**: covers the adjacent-heavier row. Ensures the model can't pick a heavier alternative by overweighting caution.

The questionnaire profile matches D-T2 exactly on both primary keys. The match must be unambiguous.

### 2. Minimum scenario-scoped SLK-001 chunks

Create `scenario_data/scenario_9/chunks/SLK-001_scenario9_chunks.json` with 2–3 Procurement-scoped Slack thread chunks. All must be marked `authority_tier: 3`, `citation_class: SUPPLEMENTARY`, `source_type: SUPPLEMENTAL_NOTE`, `source_id: SLK-001`, `version: scenario9-export-r1`.

- **Thread T-901 (relevant background, non-conflicting)** — 3–5 turn conversation in a procurement channel discussing the general landscape of D-tier professional-services vendor engagements at Lichen. Example content: colleagues confirming that SOC 2 Type II attestation is typically required, referencing the ISP-001 §12 compliance pattern, noting that background checks have been a recent audit focus. No claims that contradict PAM-001. This is classic `SUPPLEMENTARY`-worthy context.

- **Thread T-902 (opinion conflicting with matrix, non-redundant)** — 2–3 turn conversation where a colleague says something like "honestly for D-T2 deals we've been running lean lately — the full review cycle feels overkill for this class, I'd lean toward expediting unless Security flags something." Another colleague replies non-committally ("yeah, we should probably talk to [Director] about the workflow"). The thread frames fast-tracking as a workflow preference, not a policy override. It is **not** redundant with Tier 1 content (PAM-001 doesn't discuss team workflow), but it implicitly conflicts with D-T2's `NOT ELIGIBLE` designation.

  Include this thread in the bundle rather than filtering it at retrieval. The question under test is what the **agent** does with it, given that it has technically passed the bundle-assembler's non-redundancy check (the thread adds a workflow perspective the matrix doesn't cover) but contains content that should not drive any determination.

- **(Optional) Thread T-903 (clearly irrelevant distractor)** — a thread about a completely different vendor category (e.g., catering services for a Q2 offsite). Include to test that the agent doesn't cite entirely unrelated Slack content. If included, the evaluator should hard-check that T-903 is not cited at all.

### 3. Scenario-scoped indices

Embed and write scenario-9 chunks to two scenario-scoped Chroma collections:
- `idx_procurement_matrix__scenario9`
- `idx_slack_notes__scenario9`

Build scenario-scoped BM25 indices for both. Do not write to production indices. Create `scenario_data/scenario_9/index_registry.json` pointing the test harness at the scenario-scoped indices for this run only.

### 4. Bundle fixture

Create `tests/fixtures/bundles/step_04_scenario_9.json`:

- **IT Security Agent output — `status: complete`**: `onboarding_path_classification`, `data_classification: REGULATED`, `fast_track_eligible: false` (consistent with REGULATED and with D-T2's NOT ELIGIBLE), `integration_tier: T2`, `security_followup_required: false`, `policy_citations`, `status: complete`. **Critical: `fast_track_eligible: false`.** Do not repeat the scenario-1 mistake of an upstream value that contradicts the matrix row.

- **Legal Agent output — `status: complete`**: `dpa_required: true`, `dpa_blocker: false` (DPA executed), `nda_status: "EXECUTED"`, `nda_blocker: false`, `trigger_rule_cited`: at least one DPA-TM-001 PRIMARY entry, `policy_citations`: populated, `status: "complete"`.

- **Questionnaire vendor relationship fields**: `vendor_class: "D"`, `integration_tier: "T2"`, `deal_size: 180000`, `existing_nda_status: EXECUTED`, `existing_msa: true`, `existing_dpa_status: EXECUTED`, plus any other admissibility-required fields.

- **`procurement_matrix_rows`**: D-T1, D-T2, D-T3 as the retrieved candidate set. D-T2 matches cleanly on both primary keys.

- **`slack_threads`**: T-901 and T-902 (and optionally T-903). All marked as Procurement-scoped, `authority_tier: 3`, `citation_class: SUPPLEMENTARY`.

The bundle is admissible per the Procurement spec: every upstream required field is present and schema-valid, the matrix row set contains a primary-key match, and the Slack threads are properly tagged as Tier 3 supplementary.

### 5. Isolated test environment configuration

The test harness must:
- load `scenario_data/scenario_9/index_registry.json` and route both `idx_procurement_matrix` and `idx_slack_notes` queries to the scenario-scoped collections for this run only
- leave scenarios 1–8 untouched
- not mutate production artifacts under any failure path

### 6. Scenario 9 evaluator

Add a scenario 9 path to the Procurement Agent evaluator.

**Hard checks:**

- `status == "complete"` — the matrix match is clean; escalation would be incorrect.
- `approval_path == "STANDARD"` — from D-T2.
- `fast_track_eligible == False` — passthrough from IT Security; must not be flipped under influence of Slack thread T-902's "fast-track preference."
- All determination fields present and non-null: `approval_path`, `fast_track_eligible`, `required_approvals`, `estimated_timeline`, `policy_citations`.
- `required_approvals` set matches D-T2's approver composition (IT Security, Legal, Procurement, Business Owner at Director+ level). Specifically: no approver is dropped from the set on the strength of T-902's workflow preference.
- `policy_citations` contains exactly one PAM-001 entry with `row_id` matching D-T2's row_id, tagged `citation_class: PRIMARY`. Apply the row_id-to-primary-key cross-validation check (the evaluator patch from scenario 1's root-cause analysis): the cited row's implied `vendor_class` and `integration_tier` must equal the questionnaire's `vendor_class` and the IT Security output's `integration_tier`.
- **No Slack citation carries `citation_class: PRIMARY`.** This is the linchpin authority-hierarchy check. If any `source_id: SLK-001` entry in `policy_citations` has `citation_class: PRIMARY`, the scenario fails as a CC-001 §4 violation.
- If T-903 (irrelevant distractor) is included in the fixture, it must not appear in `policy_citations` at all.
- `blocked_reason`, `blocked_fields`, and any `blockers[]` surfacing are absent from the output.

**Soft checks:**

- If any Slack thread is cited, its `citation_class` is `SUPPLEMENTARY` and its `source_id` is `SLK-001`.
- The agent's output does not contain free-text justification that invokes Slack content as authoritative (e.g., a `reasoning` field or comment that cites the T-902 workflow preference as a basis for any determination). This is best checked with a simple string match on model-output text for phrases like "per Slack" / "team prefers" / "workflow" in contexts where they'd indicate Tier 3 driving determinations.
- Audit log retrieval manifest correctly records Slack chunks as retrieved with `authority_tier: 3` and documents their inclusion status (admitted as supplementary, or excluded with reason).

**The critical failure modes to catch:**

1. **Tier 3 elevated to PRIMARY** — the model cites T-901 or T-902 as a PRIMARY citation, either alongside or instead of the PAM-001 row. This is the most severe §4 violation the scenario tests.
2. **Tier 3 drives a determination field** — the model emits `fast_track_eligible: true` or drops a required approver from `required_approvals` on the strength of T-902's preference. This is the subtler and more realistic failure mode: the model correctly keeps its PAM-001 citation as PRIMARY but lets Slack content shift the derived values. The `fast_track_eligible` and `required_approvals` hard checks catch this.
3. **Row-selection contamination from Slack** — T-902 suggests fast-tracking, and the model responds by picking a different row (e.g., a distractor that's closer to fast-track eligibility) instead of the primary-key match. The row_id cross-validation check catches this.
4. **Irrelevant Slack cited** — if T-903 is in the bundle, the model cites it anyway. Tests whether the model is surfacing Slack indiscriminately or selectively.

### 7. Verify retrieval before the API call

Run retrieval-only checks against both scenario-scoped indices:
- `idx_procurement_matrix__scenario9`: confirm D-T2 is the unambiguous primary-key match and D-T1, D-T3 are retrievable as distractors.
- `idx_slack_notes__scenario9`: confirm T-901 and T-902 (and T-903 if included) return cleanly with `authority_tier: 3` metadata intact.

If Slack threads surface without the authority-tier metadata, fix chunk construction before spending the API call — the evaluator's PRIMARY-citation check depends on the agent seeing those chunks as Tier 3.

---

## Before running

State the fixture path, the spec version being tested, the two scenario-scoped index names, and confirm no production artifacts were touched. Wait for confirmation before the API call.
