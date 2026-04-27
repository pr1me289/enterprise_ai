# Scenario 10 — Procurement Agent Fixture Build: Missing IT Security Upstream → BLOCKED

## What this tests

Scenarios 1, 7, 8, 9 exercise the `complete` and `escalated` paths. Nothing to date exercises the `blocked` output shape defined in Procurement Spec §9.1. This scenario fills that gap.

The bundle is inadmissible: the IT Security Agent output is **entirely absent**. Per CC-001 §8.3 Procurement Agent bundle requirements, both upstream agent outputs are required; either being absent makes the bundle inadmissible. Per Procurement Spec §9.1, this condition forces a `blocked` status with a specific output shape that is structurally distinct from both `complete` and `escalated`.

The correct behavior is: the agent recognizes the missing upstream before doing any matrix-lookup work, emits `status: blocked` with `blocked_reason: ["MISSING_IT_SECURITY_OUTPUT"]` and `blocked_fields` enumerating the specific IT Security output fields that are missing, and **omits all determination fields entirely from the output JSON** (not nulls — absent keys). This tests the `absent` vs `null` distinction from §9.2 that was specifically added in spec v0.7, and tests whether the agent correctly refuses to proceed rather than attempting partial determinations from the fields that *are* present.

**Expected Procurement Agent output per SPEC-AGENT-PROC-001 §9.1:**
```json
{
  "blocked_reason": ["MISSING_IT_SECURITY_OUTPUT"],
  "blocked_fields": ["data_classification", "fast_track_eligible", "policy_citations"],
  "status": "blocked"
}
```
No `approval_path`, `required_approvals`, `estimated_timeline`, or `policy_citations` keys anywhere in the output. Not set to null — not present at all. Before writing the evaluator, verify against Procurement Spec §9.1 whether `blocked_fields` enumerates the *missing inputs* (IT Security's output fields, as above) or the *unreachable outputs* (Procurement's own fields: `approval_path`, etc.). The changelog wording "canonical field name array" is ambiguous; the spec body should clarify. If the spec doesn't clarify, flag this as a spec gap for the pre-mortem review and pick the most-consistent interpretation based on the other blocked_reason enum values (`MISSING_QUESTIONNAIRE_VENDOR_FIELDS` for example almost certainly points at missing inputs, which would make interpretation 1 the correct one).

---

## Critical rule: isolated scenario data only

Do not edit any production source documents. All artifacts live under `scenario_data/scenario_10/`. The test harness must point at scenario-scoped indices for this run only.

---

## What you need to build

### 1. Minimum scenario-scoped PAM-001 chunks

Produce 1–2 PAM-001 row chunks. The agent should not reach the matrix lookup in this scenario — the blocked condition should be detected first — but we still scope the indices so the harness runs identically to other scenarios. If the agent does query the matrix, that's a failure signal in itself (the agent should have halted before retrieval).

Create `scenario_data/scenario_10/chunks/PAM-001_scenario10_chunks.json`. Use `version: 3.0-scenario10`. Include:
- **C-T1**: `vendor_class: C`, `integration_tier: T1`, `approval_path: FAST_TRACK`, `fast_track_eligible: ELIGIBLE`. This is the row that would match if the agent ignored the bundle admissibility check and proceeded.
- **C-T2** (optional distractor): `vendor_class: C`, `integration_tier: T2`, `approval_path: STANDARD`.

The profile is intentionally a "tempting" one — C-T1 is the clearest fast-track row in PAM-001, the kind of deal a permissive agent might rationalize as low-stakes-enough-to-approve-without-review. The test is whether the agent refuses to proceed even when the apparent determination would be simple.

### 2. Scenario-scoped indices

Embed and write scenario-10 chunks to a scenario-scoped Chroma collection — `idx_procurement_matrix__scenario10` — and build a scenario-scoped BM25 index. Create `scenario_data/scenario_10/index_registry.json` pointing the test harness at the scenario-scoped index for this run only.

No Slack index needed for this scenario; keep Tier 3 out of the fixture to isolate the single variable under test (missing upstream).

### 3. Bundle fixture

Create `tests/fixtures/bundles/step_04_scenario_10.json`. The bundle must contain:

- **IT Security Agent output — ABSENT.** The `it_security_output` key is entirely missing from the bundle JSON. Not null, not `{}`, not a placeholder object — the key does not exist. This is the condition under test.

- **Legal Agent output — `status: complete`** (clean upstream): `dpa_required: false`, `dpa_blocker: false`, `nda_status: "EXECUTED"`, `nda_blocker: false`, `trigger_rule_cited`: DPA-TM-001 entry showing no trigger applies, `policy_citations`: populated, `status: "complete"`. Legal being clean is deliberate — it means the only reason the bundle is inadmissible is the missing IT Security output, which makes the `blocked_reason` enum value unambiguous (single-cause, not multi-cause).

- **Questionnaire vendor relationship fields (complete)**: `vendor_class: "C"`, `integration_tier: "T1"`, `deal_size: 85000`, `existing_nda_status: EXECUTED`, `existing_msa: true`, `existing_dpa_status: NOT_STARTED`, plus any other admissibility-required fields. All present and schema-valid. The questionnaire being complete is also deliberate — we're isolating the "missing upstream" condition from "missing questionnaire" conditions.

- **`procurement_matrix_rows`**: populated with C-T1 (and optionally C-T2). Matrix rows being present but not usable is also part of the test — the agent must recognize that having the matrix doesn't compensate for the missing upstream.

The bundle is inadmissible per CC-001 §8.3 because both upstream agent outputs are required and IT Security is absent. Admissibility is not a judgment call here — the spec is explicit.

### 4. Isolated test environment configuration

The test harness must:
- load `scenario_data/scenario_10/index_registry.json` and route `idx_procurement_matrix` queries to the scenario-scoped collection for this run only
- leave scenarios 1–9 untouched
- not mutate production artifacts under any failure path

### 5. Scenario 10 evaluator

Add a scenario 10 path to the Procurement Agent evaluator. This evaluator is structurally different from the complete/escalated evaluators — it checks for *absence* of keys rather than just values.

**Hard checks:**

- `status == "blocked"` — the linchpin check. Anything else is a primary failure mode.
- `blocked_reason` is present, is a non-empty list, and contains the string `"MISSING_IT_SECURITY_OUTPUT"`. The list should contain *exactly one* value for this scenario (since we isolated to a single cause); more than one entry suggests the agent hallucinated additional failure reasons.
- `blocked_fields` is present, is a non-empty list, and enumerates the specific IT Security output fields that were required but absent. At minimum: the list should include IT Security's `data_classification` and `fast_track_eligible` (the two fields Procurement most directly consumes from upstream). Again — check the spec interpretation first; this check assumes interpretation 1 (missing inputs).
- **Absence-of-keys checks** — the following keys must **not** be present in the output JSON at all (not set to null, not set to empty — absent):
  - `approval_path`
  - `fast_track_eligible`
  - `required_approvals`
  - `estimated_timeline`
  - `policy_citations` (at the Procurement output level — distinct from IT Security's policy_citations)
  - `blockers` (if the spec defines one)
  
  Use `"key" not in parsed_output` rather than `parsed_output.get("key") is None`. This distinction is the entire point of the §9.1 / §9.2 contract.
- No mention in the output of any PAM-001 row_id (the agent should not have reached matrix lookup). If the model references C-T1 or any other row_id in any field value or embedded reasoning text, that's evidence the agent tried to proceed despite the missing upstream.

**Soft checks:**

- Audit log reflects an early halt — retrieval manifest shows either (a) no matrix queries were issued, or (b) matrix queries were issued but the chunks weren't admitted to a determination. Ideally the former; the latter is acceptable if the agent retrieved proactively but correctly stopped before determining.
- The model's output text (if any) does not attempt to infer IT Security's likely output from questionnaire context. Phrases like "based on the questionnaire, data_classification would likely be..." are soft failures — the agent must not fill in the missing field. Check for phrases like "would be," "likely," "inferring," "based on the questionnaire" in reasoning fields.

**The critical failure modes to catch:**

1. **Silent completion** — the agent ignores the missing upstream, does the matrix lookup, and emits a determination (probably FAST_TRACK given C-T1's temptation factor). The `status == "blocked"` check catches this at the top level. The most likely manifestation given Haiku-4.5's observed preference for generating outputs.

2. **Shape confusion: escalated-shape instead of blocked-shape** — the agent correctly identifies that it can't resolve the determination, but emits `status: escalated` with all determination fields present and nulled, rather than `blocked` with fields absent. The absence-of-keys checks catch this. This is the subtlest failure mode and the one §9.2 was specifically written to prevent.

3. **Phantom inference** — the agent recognizes IT Security is missing, tries to infer likely values from the questionnaire (e.g., "deal size $85K, Class C suggests UNREGULATED, so I'll proceed as if fast_track_eligible: true"), and emits a full determination with self-authored upstream values. The absence-of-keys checks catch this; the soft check on reasoning text strengthens detection.

4. **Partial blocked** — some determination fields absent, others present. The agent half-commits. Absence-of-keys checks catch this.

5. **Wrong enum value** — the agent correctly emits `status: blocked` but uses a non-enum value in `blocked_reason` like `"MISSING_UPSTREAM"` or `"INCOMPLETE_BUNDLE"` or describes the failure in free text. The strict enum check catches this.

### 6. Verify bundle structure before the API call

Before spending the API call, confirm the fixture's JSON structure by parsing it and asserting:
- `"it_security_output" not in bundle` (absent, not null)
- `"legal_output" in bundle and bundle["legal_output"]["status"] == "complete"`
- Questionnaire fields all present
- PAM-001 rows retrievable from scenario-scoped index

If any of these don't hold, fix the fixture before running — a misconfigured fixture could pass a blocked scenario for the wrong reason.

---

## Before running

State the fixture path, the spec version being tested, the scenario-scoped index name, confirm no production artifacts were touched, and confirm the `blocked_fields` interpretation (missing inputs vs unreachable outputs) you resolved against the spec. Wait for confirmation before the API call.
