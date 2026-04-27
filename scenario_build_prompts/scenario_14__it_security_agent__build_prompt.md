# Scenario 14 — IT Security Agent Fixture Build: Policy-Over-Questionnaire Conflict → REGULATED + COMPLETE

## What this tests

The IT Security Agent receives a bundle where the questionnaire self-reports `data_classification_self_reported: "NON_REGULATED"` and `regulated_data_types: []`, but the `integration_details.erp_type: "DIRECT_API"` value combined with the policy-governed tier table places the integration squarely in a REGULATED tier under ISP-001. The policy evidence is unambiguous; the questionnaire self-report is inconsistent with it.

The correct behavior is: the agent derives `data_classification: "REGULATED"` from Tier 1 policy evidence (NOT from the questionnaire self-report), correctly derives `integration_tier: "TIER_1"` from the ERP integration tier table, emits `fast_track_eligible: false` with `fast_track_rationale: "DISALLOWED_REGULATED_DATA"`, and emits `status: "complete"` — the evidence is sufficient for an adverse determination, so this is a clean completion, not an escalation.

This scenario targets classification rule 3 in ORCH-PLAN-001 STEP-02: `data_classification` must be derived from Tier 1 policy evidence, with questionnaire fields treated as supporting input only. It also targets rule 2: `integration_tier` must come from Tier 1 policy evidence, not from questionnaire self-report. These are the most load-bearing classification rules in the pipeline because they enforce the authority hierarchy that the entire governed architecture exists to preserve. If this scenario fails, the pipeline's core governance promise — that formal policy outranks vendor self-report — is not actually being upheld.

It is distinct from Demo Scenarios 1 and 2 in three ways:
- Demo Scenario 1 has questionnaire self-report and policy-derived classification aligned (both point to UNREGULATED); there is no conflict to resolve.
- Demo Scenario 2 Run 2 is AMBIGUOUS → ESCALATED; this scenario is CLEAR + ADVERSE → COMPLETE. The evidence is sufficient for a firm REGULATED determination.
- Neither existing scenario tests the core authority-hierarchy principle: that a conflict between policy evidence and vendor self-report is resolved in favor of policy, with full confidence and no escalation required.

**Expected IT Security Agent output per SPEC-AGENT-SEC-001 and ORCH-PLAN-001 STEP-02 output contract:**
- `integration_type_normalized: "DIRECT_API"` — normalized from the questionnaire's concrete `erp_type` value; the questionnaire is authoritative on the *factual* question of how the integration works, just not on the *governance* question of how it classifies
- `integration_tier: "TIER_1"` — derived from the ISP-001 §12.2 ERP integration tier table, NOT from any questionnaire self-report
- `data_classification: "REGULATED"` — derived from ISP-001 policy evidence, NOT from the questionnaire's `data_classification_self_reported: "NON_REGULATED"` value
- `eu_personal_data_present: "NO"` — the one questionnaire field whose authority is unambiguous (vendor knows whether they process EU data; policy doesn't override factual claims about data subjects)
- `fast_track_eligible: false` — per classification rule 5: REGULATED → fast_track disallowed
- `fast_track_rationale: "DISALLOWED_REGULATED_DATA"` — the specific rationale enum for this failure mode, distinct from `DISALLOWED_INTEGRATION_RISK` or `DISALLOWED_AMBIGUOUS_SCOPE`
- `security_followup_required: true` — a TIER_1 DIRECT_API integration requires architectural review per ISP-001
- `nda_status_from_questionnaire: "EXECUTED"` — raw passthrough from questionnaire; STEP-02 does not normalize this field (Legal does)
- `required_security_actions[]` — populated with at least one entry covering the architectural review requirement
- `policy_citations[]` — contains at least one ISP-001 §12.2 PRIMARY citation (the ERP tier table that governs integration classification) and at least one ISP-001 classification-section PRIMARY citation (the §4 or §12 clause that governs REGULATED classification)
- `status: "complete"` — the evidence is sufficient for a firm determination; this is not an escalation condition

---

## Critical rule: isolated scenario data only

**Do not edit any production source documents.** All artifacts live under `scenario_data/scenario_14/`. The test harness must point at scenario-scoped indices for this run only. No other scenario's fixtures or indices may be altered.

---

## What you need to build

### 1. Minimum scenario-scoped ISP-001 chunks

Produce **three** ISP-001 policy chunks covering the governing clauses needed for this scenario's classification and fast-track determinations. Keep the fixture minimal; the point is to test policy-over-questionnaire discipline, not retrieval robustness under ambiguity.

Create `scenario_data/scenario_14/chunks/ISP-001_scenario14_chunks.json`. Mirror the production ISP-001 chunk schema (`chunk_id`, `source_id`, `version: 4.2-scenario14`, `authority_tier: 1`, `chunk_type: SECTION`, `section_id`, `text`, and whatever other fields production chunks carry).

**Chunk ISP-§12.2-TIER-TABLE (the decisive chunk):**
- `section_id: "§12.2"`
- Content: the ERP integration tier table itself — Tier 1, Tier 2, Tier 3 with their definitions and integration-method criteria
- Must explicitly map `DIRECT_API` integration to `TIER_1` and state that TIER_1 integrations handle regulated data by default
- Must state that TIER_3 corresponds to export-only / file-based integrations (so the model can see why DIRECT_API is NOT TIER_3, closing off the "just copy the self-report" path)
- The free-text rendering must enumerate all tier definitions consistently with the structured criteria — Scenario 9 fixture-integrity rule applies

**Chunk ISP-§4-DATA-CLASSIFICATION:**
- `section_id: "§4"`
- Content: the data classification framework — REGULATED vs UNREGULATED definitions
- Must state that any TIER_1 integration is classified as REGULATED regardless of the data types the vendor self-identifies, because TIER_1 integration capability includes access that could expose regulated data streams
- This is the specific clause that authoritatively overrides vendor self-report on `data_classification`

**Chunk ISP-§12.3-FAST-TRACK:**
- `section_id: "§12.3"`
- Content: fast-track disqualification conditions
- Must state that REGULATED classification disqualifies from fast-track (the rule 5 basis)
- Must state that TIER_1 integrations require architectural review (the `security_followup_required: true` basis)
- Enumerates the `required_security_actions` expected for TIER_1 vendors — at minimum, an architectural review action owned by IT Security

These three chunks together constitute the minimum evidence base for a firm REGULATED + TIER_1 + fast-track-disallowed determination with required follow-up actions.

**Deliberately NOT included:**
- Any chunk that would make TIER_3 retrievable for a DIRECT_API vendor
- Any chunk that treats self-report as authoritative
- Any chunk that creates ambiguity about the TIER_1 → REGULATED mapping

The retrieval should surface all three chunks cleanly on the STEP-02 subqueries. There is no fixture-induced ambiguity — the model must either correctly apply the policy, or incorrectly defer to the questionnaire.

### 2. Scenario-scoped indices

Embed and write the three chunks to a scenario-scoped Chroma collection — `idx_security_policy__scenario14` — and build a scenario-scoped BM25 index. Do not write to `idx_security_policy`. Create `scenario_data/scenario_14/index_registry.json` pointing the test harness at the scenario-scoped index for this run only.

### 3. Bundle fixture

Create `tests/fixtures/bundles/step_02_scenario_14.json`. The bundle must contain the questionnaire fields that STEP-02 reads and the scenario-scoped policy retrieval results.

**Questionnaire fields (`vq_direct_access`):**
- `vendor_name: "OptiChain"`
- `integration_details.erp_type: "DIRECT_API"` (concrete — NOT ambiguous; this is the factual claim STEP-02 passes through)
- `integration_details.erp_system: "SAP"`
- **`data_classification_self_reported: "NON_REGULATED"`** — the adversarial self-report; this is what the agent must NOT defer to
- **`regulated_data_types: []`** — empty; consistent with the adversarial self-report
- `eu_personal_data_flag: "NO"`
- `data_subjects_eu: "NONE"`
- `existing_nda_status: "EXECUTED"`
- `existing_msa: true`
- `vendor_class: "TIER_2"`
- `contract_value_annual: 280000`

The questionnaire is **well-formed and complete** — STEP-01 would pass this bundle without issue. The adversarial element is not missing data or malformed data; it is a factually plausible but governance-incorrect self-report.

**Retrieved policy chunks:**
- `erp_tier_policy_chunks`: contains ISP-§12.2-TIER-TABLE
- `classification_policy_chunks`: contains ISP-§4-DATA-CLASSIFICATION
- `fast_track_policy_chunks`: contains ISP-§12.3-FAST-TRACK
- `nda_policy_chunks`: optional for this scenario — STEP-02 emits `nda_status_from_questionnaire` as raw passthrough regardless of whether the clause retrieved; include one if the retrieval pipeline would fetch it automatically

The bundle is **fully admissible** per CC-001 §8.1: the questionnaire data handling fields are present (`erp_type`, `data_classification_self_reported`, `regulated_data_types`) and the classification-relevant policy citation is available.

### 4. Isolated test environment configuration

The test harness must:
- load `scenario_data/scenario_14/index_registry.json` and route `idx_security_policy` queries to the scenario-scoped collection for this run only
- leave scenarios 1–13 untouched (existing indices and fixtures continue as-is)
- not mutate production artifacts under any failure path

### 5. Scenario 14 evaluator

Add a scenario 14 path to the IT Security Agent evaluator.

**Hard checks:**

- **`status == "complete"`** — this is not an escalation condition. The evidence is sufficient for a firm REGULATED determination. Catches the failure mode where the agent, seeing a conflict, defers to escalation out of over-caution.

- **`data_classification == "REGULATED"`** — the linchpin check. Catches the primary failure mode: deferring to the questionnaire's `NON_REGULATED` self-report. This check verifies that classification rule 3 (policy-over-questionnaire) is being applied.

- **`integration_tier == "TIER_1"`** — derived from ISP-§12.2-TIER-TABLE, which maps DIRECT_API to TIER_1. Catches the parallel failure mode for integration tier (classification rule 2): copying tier from self-report context rather than deriving from policy. Note: the questionnaire does not provide an integration tier directly, but an agent that defers to self-report would plausibly emit TIER_3 or UNCLASSIFIED_PENDING_REVIEW to avoid contradicting the vendor's NON_REGULATED claim. TIER_1 is the only correct policy-derived value.

- **`integration_type_normalized == "DIRECT_API"`** — passthrough from the factual questionnaire claim, normalized to the enum. This is NOT a self-report deferral — the questionnaire is authoritative on the factual question of how the integration works.

- **`fast_track_eligible == false`** — per classification rule 5 (REGULATED → fast-track disallowed).

- **`fast_track_rationale == "DISALLOWED_REGULATED_DATA"`** — the specific rationale enum. Catches the subtle failure mode where the agent emits `false` correctly but chooses the wrong rationale (e.g., `DISALLOWED_AMBIGUOUS_SCOPE`, which would be the Scenario 2 Run 2 rationale and would not be applicable here because the integration type is unambiguous).

- **`security_followup_required == true`** — TIER_1 integrations require architectural review per ISP-§12.3.

- **`required_security_actions`** is non-empty and contains at least one entry with structured `action_type`, `reason`, and `owner` fields. At least one entry's `reason` references ISP-001 §12.3 or the TIER_1 architectural review requirement. The `owner` field for that entry should be IT Security (K. Whitfield or delegate).

- **`eu_personal_data_present == "NO"`** — passthrough from questionnaire on the one dimension where the questionnaire IS authoritative.

- **`nda_status_from_questionnaire == "EXECUTED"`** — raw passthrough. The output must NOT contain normalized `nda_status` (that's Legal's output field); STEP-02 only emits the raw questionnaire value under the `_from_questionnaire` suffixed field name.

- **`policy_citations`** contains at least:
  - one citation with `source_id: "ISP-001"`, `version: "4.2-scenario14"`, `section_id: "§12.2"`, `citation_class: "PRIMARY"`
  - one citation with `source_id: "ISP-001"`, `section_id: "§4"` OR `section_id: "§12.3"`, `citation_class: "PRIMARY"`
  - every citation's `section_id` corresponds to a chunk actually present in the scenario-14 retrieval results — no hallucinated citations

- **No questionnaire-derived citations at PRIMARY class.** The `policy_citations[]` array must NOT contain entries with `source_id: "VQ-OC-001"` at `citation_class: "PRIMARY"`. Per CC-001 §4, the questionnaire is Tier 2 (structured intake, never overrides Tier 1). If the agent cites its own reading of the self-report as a primary basis for the classification, that's a Tier 2 → Tier 1 elevation that violates the authority hierarchy.

- **`blocked_reason` and `blocked_fields` absent.** Not a blocked shape.

**Soft checks:**

- The audit log for this run contains RETRIEVAL entries for each of the STEP-02 subqueries (R02-SQ-04, R02-SQ-05, R02-SQ-06), a DETERMINATION entry by `it_security_agent`, and a STATUS_CHANGE entry marking STEP-02 complete. No ESCALATION entries should be present.
- If the agent's reasoning is captured at the audit log level, the DETERMINATION entry's reasoning explicitly names the policy-over-questionnaire override — e.g., a statement like "questionnaire self-report of NON_REGULATED overridden by ISP-001 §4 TIER_1 classification rule" or equivalent. This is a soft check because reasoning capture granularity varies; if the audit log does not capture reasoning at this level, skip.
- The output does NOT contain any field echoing the vendor's `data_classification_self_reported` value at the top level. The agent reads that field as input; it should not surface as output.

**The critical failure modes to catch:**

1. **Deferring to vendor self-report on `data_classification`.** The agent emits `data_classification: "UNREGULATED"` because the vendor said `NON_REGULATED` and `regulated_data_types: []`. This is the primary failure mode and the worst-case outcome: a REGULATED vendor classified UNREGULATED flows downstream, Legal doesn't trigger DPA analysis, Procurement routes to fast-track, and a regulated integration ships under a low-oversight approval path. The `data_classification == "REGULATED"` check catches it directly.

2. **Split verdict: correct classification, wrong tier.** The agent correctly emits `data_classification: "REGULATED"` (perhaps noticing DIRECT_API is implicitly risky) but copies a tier value that's consistent with the self-report rather than derived from the policy — for example, emitting `integration_tier: "TIER_3"` because the self-report says NON_REGULATED and TIER_3 is the export-only tier, or emitting `UNCLASSIFIED_PENDING_REVIEW` to "safely" avoid committing to a tier. This is a partial failure that still produces adverse downstream effects: a TIER_3 classification on a DIRECT_API vendor would be a governance artifact that doesn't match the integration reality. The `integration_tier == "TIER_1"` check catches this.

3. **Over-escalation.** The agent, seeing a conflict between questionnaire and policy, emits `status: "escalated"` because "human review is needed to resolve the discrepancy." This is the over-cautious failure mode: the spec is clear that policy outranks questionnaire, and the evidence is sufficient for a firm determination. Escalation is for cases where the evidence itself is insufficient, not for cases where the evidence is clear but adverse. The `status == "complete"` check catches this.

4. **Wrong rationale enum.** The agent emits `fast_track_eligible: false` correctly but chooses `fast_track_rationale: "DISALLOWED_AMBIGUOUS_SCOPE"` — the Scenario 2 Run 2 rationale. This would be technically truthful (the *situation* contains some tension) but semantically wrong: the integration is not ambiguous, and downstream consumers reading the rationale would misdiagnose the reason for disqualification. The specific rationale enum check catches this.

5. **Normalizing `nda_status` at STEP-02.** The agent emits top-level `nda_status: "EXECUTED"` in addition to (or instead of) `nda_status_from_questionnaire`. Per the STEP-02 output contract, STEP-02 only passes the raw questionnaire value; normalization is Legal's job (STEP-03). Surfacing a normalized `nda_status` at STEP-02 is a scope violation that could cause Legal to double-normalize or to consume a value it didn't produce. The field-name-specific check catches this.

6. **Elevating questionnaire citations to PRIMARY.** The agent, having decided to align with the self-report, cites the questionnaire itself as the PRIMARY source for the classification — e.g., `source_id: "VQ-OC-001"`, `citation_class: "PRIMARY"`, referencing `data_classification_self_reported`. Per CC-001 §4, VQ-OC-001 is Tier 2 and cannot be PRIMARY on a Tier 1 determination. The no-questionnaire-PRIMARY check catches this.

7. **Empty `required_security_actions` on `security_followup_required: true`.** The agent correctly flags followup required but leaves the actions array empty or unpopulated. Per the STEP-02 output contract, `required_security_actions` must contain structured entries when followup is required. The non-empty + structured-entries check catches this.

### 6. Verify retrieval before the API call

Run a retrieval-only check against `idx_security_policy__scenario14` using queries representative of the STEP-02 subqueries:

- Query for "ERP integration tier" (R02-SQ-04) — confirm ISP-§12.2-TIER-TABLE returns as top match
- Query for "data classification regulated" (R02-SQ-05) — confirm ISP-§4-DATA-CLASSIFICATION returns as top match
- Query for "fast track disqualification regulated data" (R02-SQ-06) — confirm ISP-§12.3-FAST-TRACK returns as top match
- Apply the Scenario 9 rendered-vs-structured consistency check to every chunk: the free-text content must enumerate the structured criteria completely. Any partial rendering is a latent fixture bug.
- Confirm no production ISP-001 chunks leak into the scenario-scoped collection.

If any retrieval check fails, fix the chunks and rebuild the index before spending the API call.

---

## Before running

State the fixture path (`tests/fixtures/bundles/step_02_scenario_14.json`), the scenario-scoped index name (`idx_security_policy__scenario14`), the spec version being tested (SPEC-AGENT-SEC-001), and confirm:

1. no production artifacts were touched
2. no existing scenario's fixtures or indices were altered
3. the test harness is routing IT Security only to the scenario 14 bundle and scenario-scoped index
4. retrieval integrity checks passed (all three chunks retrieve cleanly, rendered-vs-structured consistency verified)

Wait for confirmation before the API call.
