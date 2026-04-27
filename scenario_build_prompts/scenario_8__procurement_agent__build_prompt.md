# Scenario 8 — Procurement Agent Fixture Build: Upstream Blocker Propagation → ESCALATED

## What this tests

The Procurement Agent receives a clean IT Security output and a *schema-valid but escalated* Legal output carrying `dpa_required: true` and `dpa_blocker: true` (DPA required but not executed). The bundle is admissible — Legal produced every required field, its `status: escalated` is a workflow-consequence escalation per Legal Spec §8.3, not an evidence gap. The questionnaire profile cleanly matches one PAM-001 row.

The correct behavior is: the agent performs its PAM-001 lookup (the matrix path determination is still valid work — the deal still needs an approval route once the blocker clears), produces `approval_path` from the matching row, and emits `status: escalated` with the upstream blocker surfaced in its escalation payload. The determination is "here is the approval path, but it cannot proceed until upstream resolves."

This tests cross-agent dependency handling — Procurement is the only domain agent that consumes two full upstream outputs, and its spec doesn't provide explicit handling rules for "upstream admissible but escalated." The failure modes are subtle and not covered by Scenarios 1–7.

**Expected Procurement Agent output per SPEC-AGENT-PROC-001:**
- `status: escalated`
- All determination fields **present** (not absent — that's the blocked shape)
- `approval_path` populated from the matching PAM-001 row (determination is still valid)
- `fast_track_eligible` populated from upstream IT Security output (passthrough; not owned by Procurement)
- `executive_approval_required`, `required_approvals`, `estimated_timeline` populated from the matching row
- `policy_citations` contains the PAM-001 PRIMARY citation for the matched row
- Upstream blocker surfaced — either via a dedicated `blockers[]` field, the escalation payload written to the audit log, or the `required_approvals[]` entries flagged with `blocker: true` referencing the upstream DPA gap
- Audit log escalation payload names the upstream `dpa_blocker` as the condition forcing escalation, with resolution owner = Legal / General Counsel

---

## Critical rule: isolated scenario data only

**Do not edit any production source documents.** All artifacts live under `scenario_data/scenario_8/`. The test harness must point at scenario-scoped indices for this run only.

---

## What you need to build

### 1. Minimum scenario-scoped PAM-001 chunks

Produce 2–3 PAM-001 row chunks covering the vendor/deal combination the Scenario 8 questionnaire will hit, so the matrix lookup **succeeds cleanly**. The gap-in-coverage pattern from Scenario 7 is not what this scenario tests — here we want the opposite: unambiguous matrix match, with escalation forced by upstream state, not matrix state.

Create `scenario_data/scenario_8/chunks/PAM-001_scenario8_chunks.json`. Use the production chunk schema (mirror whatever fields the production PAM-001 chunks use — `chunk_id`, `source_id`, `version: 3.0-scenario8`, `authority_tier: 1`, `chunk_type: ROW`, `row_id`, `text`, etc.).

Write rows that clearly cover the Scenario 8 questionnaire profile. Example:
- Row Q-01: `vendor_class: TIER_2`, `integration_tier: TIER_2_SAAS`, deal_size $100K–$500K, standard integration → STANDARD path with named approvers and timeline
- Row Q-02: a distractor row covering a different Class / Tier combination (so the match isn't trivially the only row available)

The questionnaire profile matches Q-01 exactly on both primary keys (`vendor_class` and `integration_tier`) per the strict-lookup language we're tightening in §8.3. The match should be unambiguous.

### 2. Scenario-scoped indices

Embed and write the scenario-8 chunks to a scenario-scoped Chroma collection — `idx_procurement_matrix__scenario8` — and build a scenario-scoped BM25 index. Do not write to `idx_procurement_matrix`. Create `scenario_data/scenario_8/index_registry.json` pointing the test harness at the scenario-scoped indices for this run only.

### 3. Bundle fixture

Create `tests/fixtures/bundles/step_04_scenario_8.json`. The bundle must contain:

- **IT Security Agent output — `status: complete`** (clean upstream, all required STEP-02 fields per the Procurement admissibility contract): `onboarding_path_classification`, `data_classification: REGULATED`, `fast_track_eligible: false` (consistent with REGULATED), `integration_tier: TIER_2_SAAS`, `security_followup_required: false`, `policy_citations`, `status: complete`.

- **Legal Agent output — `status: escalated` with `dpa_blocker: true`**. This is the key payload. All six determination fields must be present (escalated-shape, not blocked-shape) and all fully resolved — the escalation is a workflow consequence, not an evidence gap, per Legal Spec §8.3 and Example A:
  - `dpa_required: true`
  - `dpa_blocker: true`
  - `nda_status: "EXECUTED"`
  - `nda_blocker: false`
  - `trigger_rule_cited`: non-empty with at least one DPA-TM-001 PRIMARY entry
  - `policy_citations`: populated with DPA-TM-001 and ISP-001 §12.1.4 PRIMARY entries
  - `status: "escalated"`

- **Questionnaire vendor relationship fields**: `vendor_class: TIER_2`, `integration_tier: TIER_2_SAAS`, `deal_size: 250000` (or whatever value lands cleanly in Q-01's coverage), `existing_nda_status: EXECUTED`, `existing_msa: true`, plus any other admissibility-required fields. **Critically: `existing_dpa_status: NOT_STARTED`** — this is what makes `dpa_blocker: true` consistent with the bundle rather than contradictory.

- **`procurement_matrix_rows`**: populated with Q-01 and Q-02 as the retrieved candidate set. Q-01 matches cleanly on both primary keys.

The bundle is **admissible** per the Procurement spec — every upstream required field is present and schema-valid. Legal's `status: escalated` is not an admissibility violation per CC-001 §8.3 and Procurement Spec §3 (the upstream-output admissibility rule checks for the required fields being present, not for upstream status being `complete`).

### 4. Isolated test environment configuration

The test harness must:
- load `scenario_data/scenario_8/index_registry.json` and route `idx_procurement_matrix` queries to the scenario-scoped collection for this run only
- leave all other scenario tests untouched (scenarios 1–7 continue pointing at their existing indices)
- not mutate production artifacts under any failure path

### 5. Scenario 8 evaluator

Add a scenario 8 path to the Procurement Agent evaluator. Hard checks:

- `status == "escalated"` — **this is the linchpin check**. The primary failure mode this scenario catches is emitting `complete` despite upstream being escalated.
- **All determination fields present** (not absent): `approval_path`, `fast_track_eligible`, `executive_approval_required`, `required_approvals`, `estimated_timeline`, `policy_citations`. Absence of any is a blocked-shape violation.
- `approval_path == "STANDARD"` (matches Q-01) — the determination is still valid work; the agent must not refuse to produce it just because upstream escalated.
- `fast_track_eligible == False` — passthrough from IT Security upstream; must not be silently flipped or nulled.
- `executive_approval_required`, `estimated_timeline`, `required_approvals` all populated (from Q-01).
- `policy_citations` contains the PAM-001 Q-01 PRIMARY citation. Every PAM-001 citation in the output must correspond to a `row_id` actually present in `procurement_matrix_rows` (no hallucination).
- **Upstream blocker is surfaced somewhere in the output.** Check at least one of:
  - a `blockers[]` field exists and contains an entry referencing the upstream DPA blocker
  - a `required_approvals[]` entry carries `blocker: true` with a description tying it to the upstream `dpa_blocker`
  - the Procurement escalation payload in the audit log names the upstream `dpa_blocker` as the cause
  
  If none of the three channels surface the upstream blocker, the evaluator fails — this is the silent-swallow mode.
- `blocked_reason` and `blocked_fields` are absent from the output.

Soft checks:
- Audit log escalation payload names Legal / General Counsel as the resolution owner for the DPA blocker, distinct from any Procurement-owned escalation reasons
- The Procurement output does not overwrite or mutate Legal's determination fields — it reads them, surfaces them, but doesn't rewrite `dpa_required`, `dpa_blocker`, `nda_status`, `nda_blocker` in its own output. (Procurement's output is a separate object; those fields live in Legal's output downstream.)

**The critical failure modes to catch:**

1. **Silent swallow of upstream escalation** — the model produces a clean PAM-001 path match and emits `status: complete`, ignoring that Legal was escalated. This is the Scenario 7 pattern recurring at the cross-agent boundary: the agent reasons "my matrix lookup succeeded, therefore my step is complete" and drops the upstream dimension. The `status` check catches this directly.

2. **Over-defer to upstream** — the model sees `dpa_blocker: true` upstream and refuses to produce an `approval_path`, emitting `approval_path: null` or the blocked shape. This is the opposite failure: the agent is supposed to still do its matrix-lookup work; the escalation is about propagation, not about refusing to determine. The `approval_path == "STANDARD"` check catches this.

3. **Blocker invisibility** — the model emits `status: escalated` but the escalation reason in the output doesn't tie back to the upstream `dpa_blocker`. Downstream humans reading the output see "escalated" with no visible cause. The "upstream blocker surfaced" hard check catches this.

4. **Upstream field mutation** — the model rewrites Legal's fields in its own output (e.g., emits `dpa_required: true` at the Procurement level). Procurement doesn't own these fields. Soft check catches this.

### 6. Verify retrieval before the API call

Run a retrieval-only check against `idx_procurement_matrix__scenario8` using a query representative of the scenario-8 questionnaire profile. Confirm Q-01 returns as a clean match on both primary keys and Q-02 is retrievable but doesn't match. If the match is ambiguous, adjust chunk definitions before spending the API call.

---

## Before running

State the fixture path, the spec version being tested, the scenario-scoped index names, and confirm no production artifacts were touched. Wait for confirmation before the API call.
