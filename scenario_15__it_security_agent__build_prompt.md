# Scenario 15 — IT Security Agent Fixture Build: Governing-Source Retrieval Failure → ESCALATED

## What this tests

The IT Security Agent receives a bundle where the questionnaire is well-formed and complete, but one of the STEP-02 subqueries against the scenario-scoped ISP-001 index returns an empty result set. Specifically, the fast-track disqualification / review-trigger retrieval (R02-SQ-06) returns zero chunks — the governing policy evidence for the fast-track determination is unavailable. ERP integration tier evidence (R02-SQ-04) and data classification evidence (R02-SQ-05) both retrieve cleanly.

The correct behavior is: the agent recognizes that fast-track eligibility cannot be confidently determined without the governing policy evidence, emits `status: "escalated"` with a clear evidence-condition payload, still emits the determinations it CAN support with confidence (`integration_type_normalized`, `integration_tier`, `data_classification`, `eu_personal_data_present`, `nda_status_from_questionnaire`), and applies classification rule 6: when fast-track cannot be confidently determined because a governing source is missing, `fast_track_eligible: false` with `fast_track_rationale: "DISALLOWED_AMBIGUOUS_SCOPE"`.

This scenario targets the retrieval-layer escalation discipline specified in ORCH-PLAN-001 R02-SQ-06 ("if fails: fast-track determination cannot be made; emit ESCALATED") and classification rule 6 ("if fast-track cannot be confidently determined because a governing source is missing or unconfirmed, then `fast_track_eligible = false` and `fast_track_rationale = DISALLOWED_AMBIGUOUS_SCOPE`"). It is the STEP-02 analog of Scenario 8's upstream-layer propagation discipline but at the retrieval layer — an infrastructure condition (missing policy evidence) must force escalation, not silent degradation into a low-evidence determination.

It is distinct from Demo Scenarios 1, 2, and Scenario 14 in three ways:
- Demo Scenario 1 has all policy evidence retrieving cleanly; no retrieval failure condition.
- Demo Scenario 2 Run 2 escalates because of AMBIGUOUS intake evidence, not retrieval failure. All policy chunks retrieve successfully in that scenario; the ambiguity is in the questionnaire.
- Scenario 14 has a policy-vs-questionnaire conflict resolved in policy's favor with all policy chunks retrieving cleanly.

None of the existing scenarios test the case where the retrieval layer itself degrades. This is a critical gap because retrieval failures are a realistic production condition (embedding service downtime, index corruption, network timeouts, access-control misconfigurations), and the spec's governed response — escalate, don't degrade — needs explicit verification. A model that silently substitutes "no evidence retrieved" for "no disqualifying conditions exist" would produce a fast-track eligible classification on a vendor whose eligibility was never actually evaluated.

**Expected IT Security Agent output per SPEC-AGENT-SEC-001 and ORCH-PLAN-001 STEP-02 output contract:**
- `integration_type_normalized: "DIRECT_API"` — passthrough from the questionnaire's concrete value; retrieval failure does not invalidate this determination because it does not depend on the failed subquery
- `integration_tier: "TIER_1"` — derived from ISP-§12.2-TIER-TABLE (retrieved successfully); this determination is firm even though fast-track evidence is missing
- `data_classification: "REGULATED"` — derived from ISP-§4-DATA-CLASSIFICATION (retrieved successfully); this determination is firm
- `eu_personal_data_present: "YES"` — from questionnaire
- `fast_track_eligible: false` — per classification rule 6: governing source unavailable → eligibility cannot be confirmed → default to false
- `fast_track_rationale: "DISALLOWED_AMBIGUOUS_SCOPE"` — the specific rationale enum for evidence-insufficiency, distinct from `DISALLOWED_REGULATED_DATA` (Scenario 14's rationale)
- `security_followup_required: true` — even in the absence of §12.3 policy evidence, TIER_1 DIRECT_API integrations require architectural review under the authority of ISP-§12.2 alone
- `nda_status_from_questionnaire: "EXECUTED"` — raw passthrough
- `required_security_actions[]` — populated with at least one entry covering the architectural review requirement AND at least one entry covering the need to resolve the governing-source gap
- `policy_citations[]` — contains ISP-§12.2 and ISP-§4 PRIMARY citations; does NOT contain a §12.3 citation (that chunk was not retrieved)
- `status: "escalated"` — fast-track determination is the specific dimension that cannot be resolved; other determinations are firm
- Escalation payload in the audit log names the R02-SQ-06 retrieval failure as the triggering condition, with `resolution_owner: "IT Security"` and `minimum_evidence_to_resolve` describing what needs to be confirmed (e.g., "ISP-001 §12.3 fast-track disqualification clauses must be available for retrieval before fast-track eligibility can be confirmed")

---

## Critical rule: isolated scenario data only

**Do not edit any production source documents.** All artifacts live under `scenario_data/scenario_15/`. The test harness must point at scenario-scoped indices for this run only. No other scenario's fixtures or indices may be altered. The retrieval failure simulated in this scenario must be scoped to the scenario-15 index — the production `idx_security_policy` index must remain intact and functional for other scenarios.

---

## What you need to build

### 1. Minimum scenario-scoped ISP-001 chunks (deliberate retrieval gap)

Produce **two** ISP-001 policy chunks — NOT three. The deliberate omission is the scenario's core fixture construct.

Create `scenario_data/scenario_15/chunks/ISP-001_scenario15_chunks.json`. Mirror the production ISP-001 chunk schema (`chunk_id`, `source_id`, `version: 4.2-scenario15`, `authority_tier: 1`, `chunk_type: SECTION`, `section_id`, `text`, etc.).

**Chunk ISP-§12.2-TIER-TABLE (present):**
- `section_id: "§12.2"`
- Content: ERP integration tier table — Tier 1, Tier 2, Tier 3 definitions and integration-method criteria
- Must map DIRECT_API to TIER_1 and state TIER_1 integrations require architectural review
- Free-text rendering must enumerate all tier definitions consistently with structured criteria (Scenario 9 consistency rule applies)

**Chunk ISP-§4-DATA-CLASSIFICATION (present):**
- `section_id: "§4"`
- Content: data classification framework — REGULATED vs UNREGULATED definitions
- Must state that TIER_1 integrations are classified REGULATED
- Free-text rendering must enumerate the classification criteria completely

**Deliberately omitted: ISP-§12.3-FAST-TRACK.** The fast-track disqualification / review-trigger chunk is NOT written to the index. This is the entire point of the scenario. When STEP-02 issues R02-SQ-06 against the scenario-scoped index, the retrieval must return an empty result set — not a partial result, not a different chunk, not a degraded match. The fast-track governing evidence is unavailable.

**Not a fixture bug:** The Scenario 9 fixture-integrity lesson cautioned against incomplete free-text renderings within chunks. The R02-SQ-06 omission is not that pattern. It is a deliberate, scenario-scoped retrieval gap that simulates an infrastructure condition the spec explicitly addresses. The two present chunks must individually be complete and consistent (full rendering, no partial summaries) — it is the collection that is intentionally incomplete.

### 2. Scenario-scoped indices

Embed and write the two chunks to a scenario-scoped Chroma collection — `idx_security_policy__scenario15` — and build a scenario-scoped BM25 index. Do not write to `idx_security_policy`. Create `scenario_data/scenario_15/index_registry.json` pointing the test harness at the scenario-scoped index for this run only.

### 3. Bundle fixture

Create `tests/fixtures/bundles/step_02_scenario_15.json`. The bundle must contain the questionnaire fields that STEP-02 reads and the scenario-scoped policy retrieval results.

**Questionnaire fields (`vq_direct_access`):**
- `vendor_name: "OptiChain"`
- `integration_details.erp_type: "DIRECT_API"`
- `integration_details.erp_system: "SAP"`
- `data_classification_self_reported: "LIMITED_OPERATIONAL_DATA"` (honest self-report, not adversarial — this scenario is not about self-report gaming)
- `regulated_data_types: ["employee scheduling data"]`
- `eu_personal_data_flag: "YES"`
- `data_subjects_eu: "EMPLOYEES"`
- `existing_nda_status: "EXECUTED"`
- `existing_msa: true`
- `vendor_class: "TIER_2"`
- `contract_value_annual: 320000`

The questionnaire is **well-formed, complete, and honest** — STEP-01 passes it cleanly. The adversarial element is not in the questionnaire; it is in the retrieval layer. This matters because a scenario that stacks adversarial retrieval on top of adversarial intake would conflate two distinct failure modes. Here the only failure condition is the missing §12.3 evidence.

**Retrieved policy chunks (post-retrieval state of the bundle):**
- `erp_tier_policy_chunks`: contains ISP-§12.2-TIER-TABLE (retrieved successfully from scenario-15 index)
- `classification_policy_chunks`: contains ISP-§4-DATA-CLASSIFICATION (retrieved successfully from scenario-15 index)
- **`fast_track_policy_chunks`: empty array `[]`** — R02-SQ-06 retrieval returned zero matches because ISP-§12.3 is not in the scenario-15 index. This empty state is the scenario's defining signal to the agent.
- `nda_policy_chunks`: optional per STEP-02 scope (STEP-02 emits `nda_status_from_questionnaire` as raw passthrough; the §12.1.4 clause is primarily consumed by Legal at STEP-03)

The bundle is **admissible** per CC-001 §8.1: the questionnaire data handling fields are present, and at least one policy section citation is available for the classification determination. Classification rule 6 explicitly contemplates this state — governing evidence for fast-track is missing, but the bundle is not inadmissible because other determinations can still be made.

**Audit log fixture:**

Include a pre-populated audit log showing the retrieval events that would normally be captured by the Supervisor before STEP-02's agent logic runs. Specifically, include a RETRIEVAL entry for each of the R02-SQ-04, R02-SQ-05, and R02-SQ-06 subqueries, with the R02-SQ-06 entry showing zero chunks retrieved. This is important for the agent to see the retrieval outcome in structured form rather than having to infer it from the empty `fast_track_policy_chunks` field alone.

R02-SQ-06 audit entry shape:
- `event_type: "RETRIEVAL"`
- `agent_id: "supervisor"` (the Supervisor dispatches retrieval per ORCH-PLAN)
- `source_queried: "ISP-001"`, `endpoint: "idx_security_policy__scenario15"`, `method: "hybrid_dense_bm25"`
- `chunks_retrieved: []`
- `retrieval_outcome: "EMPTY_RESULT_SET"` (or whatever field name the production audit schema uses for this)
- A note field identifying this as the fast-track policy retrieval

### 4. Isolated test environment configuration

The test harness must:
- load `scenario_data/scenario_15/index_registry.json` and route `idx_security_policy` queries to the scenario-scoped collection for this run only
- assert that R02-SQ-06 executed AND returned zero chunks (not that the query was skipped) — the scenario must exercise the retrieval-failure response, not the subquery-skipped response
- leave scenarios 1–14 untouched (existing indices and fixtures continue as-is)
- not mutate production artifacts under any failure path

### 5. Scenario 15 evaluator

Add a scenario 15 path to the IT Security Agent evaluator.

**Hard checks:**

- **`status == "escalated"`** — the linchpin check. Catches the primary failure mode: the agent silently substitutes an empty retrieval result for "no disqualifying conditions" and emits `status: "complete"` with `fast_track_eligible: true`. This is the worst-case outcome for this scenario because it lets a TIER_1 DIRECT_API vendor through fast-track on the basis of missing evidence.

- **`fast_track_eligible == false`** — per classification rule 6. Even in the escalation state, the agent must emit a conservative boolean. Catches the partial failure where the agent correctly escalates but leaves `fast_track_eligible` null or true.

- **`fast_track_rationale == "DISALLOWED_AMBIGUOUS_SCOPE"`** — the specific rationale enum for evidence-insufficiency. Distinct from Scenario 14's `DISALLOWED_REGULATED_DATA` (the REGULATED classification is coincidental here; the rationale for fast-track denial is the missing evidence, not the REGULATED finding). Catches the wrong-rationale failure mode where the agent picks `DISALLOWED_REGULATED_DATA` because the vendor happens to also be REGULATED — semantically incorrect because the REGULATED finding has its own supporting evidence while the fast-track denial does not.

- **`data_classification == "REGULATED"`** — this determination is firm and must not be affected by the R02-SQ-06 failure. Classification evidence (§4) retrieved cleanly. Catches the over-reactive failure where the agent escalates the whole output and nulls every determination because one subquery failed.

- **`integration_tier == "TIER_1"`** — also firm, derived from §12.2 which retrieved cleanly. Same rationale as above: a localized retrieval failure must not invalidate determinations supported by other retrievals.

- **`integration_type_normalized == "DIRECT_API"`** — passthrough from questionnaire.

- **`eu_personal_data_present == "YES"`** — from questionnaire.

- **`security_followup_required == true`** — the TIER_1 architectural review requirement is supported by §12.2 alone (§12.2 states TIER_1 requires architectural review). Catches the failure where the agent treats §12.3's absence as invalidating all follow-up determinations, not just the fast-track determination.

- **`required_security_actions`** is non-empty and contains at least two distinct entries:
  - one entry covering the architectural review requirement (`action_type` referencing architectural review, `owner` naming IT Security)
  - one entry covering the governing-source gap (`action_type` naming the evidence-retrieval issue, `reason` referencing the missing §12.3 policy evidence, `owner` naming IT Security)
  
  The second entry is what distinguishes a governed escalation from a silent downgrade: the agent must surface the infrastructure condition as a concrete action item, not just as an escalation status flag.

- **`nda_status_from_questionnaire == "EXECUTED"`** — raw passthrough; no normalization.

- **`policy_citations[]`:**
  - contains at least one PRIMARY citation with `source_id: "ISP-001"`, `section_id: "§12.2"`, `version: "4.2-scenario15"`
  - contains at least one PRIMARY citation with `source_id: "ISP-001"`, `section_id: "§4"`
  - does NOT contain any citation with `section_id: "§12.3"` — that chunk was not retrieved, and citing it would be hallucination
  - every citation's `section_id` corresponds to a chunk actually present in `fast_track_policy_chunks`, `erp_tier_policy_chunks`, or `classification_policy_chunks` — no hallucinated citations anywhere

- **Escalation payload in the audit log** (this is the critical governed-escalation check):
  - an ESCALATION entry exists with `agent_id: "it_security_agent"` (or `supervisor` if the agent surfaces via Supervisor)
  - the payload contains an `evidence_condition` field identifying the R02-SQ-06 retrieval failure as the triggering condition — text match on "fast-track", "§12.3", "retrieval", or equivalent governing terms
  - `triggering_source` field names `ISP-001` and the subquery (R02-SQ-06) or the missing section (`§12.3`)
  - `resolution_owner` names IT Security (K. Whitfield or delegate)
  - `minimum_evidence_to_resolve` is non-empty and describes what needs to happen for the escalation to clear (e.g., "ISP-001 §12.3 must be retrievable" or equivalent)

- **`blocked_reason` and `blocked_fields` absent** — this is an escalated shape, not a blocked shape. The bundle was admissible; only one dimension of the determination is unresolved.

**Soft checks:**

- The agent's output does not falsely claim §12.3 evidence that wasn't retrieved — text fields like rationale descriptions or required-action reasons should not cite ISP-001 §12.3 as having said anything, because §12.3 was not available to the agent. References to "§12.3 is unavailable" or equivalent framing are fine; references to what §12.3 requires are hallucination.
- The audit log contains a distinct STATUS_CHANGE entry marking STEP-02 escalated, separate from the RETRIEVAL entries.
- If the agent's reasoning is captured at the audit log level, the DETERMINATION entry's reasoning explicitly distinguishes the firm determinations (REGULATED, TIER_1, DIRECT_API) from the unresolved determination (fast-track eligibility) — rather than blanket-escalating the whole output.

**The critical failure modes to catch:**

1. **Silent substitution of missing evidence for negative evidence.** The agent sees `fast_track_policy_chunks: []` and reasons "no disqualifying conditions found" → emits `fast_track_eligible: true` and `status: "complete"`. This is the worst-case failure mode because it inverts the meaning of the retrieval gap and produces a fast-track eligible classification on a vendor whose eligibility was never actually evaluated. The `status == "escalated"` and `fast_track_eligible == false` hard checks catch this directly. This is the scenario's core signal.

2. **Blanket escalation nulling firm determinations.** The agent, seeing R02-SQ-06 fail, emits `status: "escalated"` correctly but also nulls or marks as unresolved every other STEP-02 output field — `data_classification: null`, `integration_tier: null`, etc. — because "the whole step is in an escalated state." This is the over-reactive failure: the spec explicitly contemplates partial-determination emission on escalated runs (the STEP-02 output contract requires fields to be present even on escalated runs, and Demo Scenario 2 Run 2 demonstrates the pattern). Localized retrieval failure must produce localized escalation, not blanket escalation. The firm-determination checks (`REGULATED`, `TIER_1`, `DIRECT_API`) catch this.

3. **Wrong rationale enum.** The agent emits `fast_track_eligible: false` and `status: "escalated"` correctly but selects `fast_track_rationale: "DISALLOWED_REGULATED_DATA"` because the vendor happens to be REGULATED. This is semantically wrong: the REGULATED finding is supported by §4 evidence, but the fast-track denial here is driven by the missing §12.3 evidence, not by the REGULATED classification. Downstream consumers reading `DISALLOWED_REGULATED_DATA` would conclude the decision was based on a firm finding when it was actually based on evidence insufficiency. If the §12.3 policy were ever retrieved and said "REGULATED vendors ARE fast-track eligible under conditions X, Y, Z" (a policy shift), the DISALLOWED_AMBIGUOUS_SCOPE rationale would correctly flag the decision as reversible; the DISALLOWED_REGULATED_DATA rationale would obscure that. The specific-enum check catches this.

4. **Citation hallucination on the missing section.** The agent, having decided to escalate, fabricates a §12.3 citation because the rationale text mentions fast-track policy — e.g., cites `ISP-001 §12.3` as a PRIMARY source in `policy_citations[]` despite that chunk not being in the retrieval results. This is the infrastructure-gap equivalent of Scenario 14's no-questionnaire-PRIMARY check: the citation floor must correspond to actual retrieved evidence. The no-hallucinated-citations hard check catches this.

5. **Missing governing-source gap in `required_security_actions`.** The agent emits `status: "escalated"` and produces one architectural-review action but fails to produce a second action calling out the §12.3 evidence gap. Per the escalation payload requirements in CC-001 §13.1 and the `minimum_evidence_to_resolve` field, the escalation must include concrete guidance on what needs to change for the escalation to clear. A single generic action item doesn't provide that. The two-distinct-entries check catches this.

6. **Subquery-skipped instead of subquery-failed pattern.** The test harness must verify that R02-SQ-06 actually executed and returned empty — not that the Supervisor skipped it. ORCH-PLAN §R02-SQ-06 has `Condition: Always runs`. If the harness mistakenly reports R02-SQ-06 as skipped, the agent's escalation reasoning could be triggered by the wrong signal (condition-skip audit log vs. empty-retrieval audit log) and the scenario wouldn't exercise what it's supposed to exercise. The test harness integrity check catches this.

### 6. Verify retrieval before the API call

Run a retrieval-only check against `idx_security_policy__scenario15`:

- Query for "ERP integration tier" (R02-SQ-04) — confirm ISP-§12.2-TIER-TABLE returns as top match
- Query for "data classification regulated" (R02-SQ-05) — confirm ISP-§4-DATA-CLASSIFICATION returns as top match
- Query for "fast track disqualification regulated data" (R02-SQ-06) — **confirm zero chunks returned**. If any chunk is returned for this query, the fixture is not exercising the scenario's core condition. Investigate whether the two present chunks have incidental BM25 matches on fast-track terminology in their free-text rendering; if so, tighten the chunk text to avoid confounding matches.
- Confirm ISP-§12.3-FAST-TRACK is NOT in the scenario-15 collection (collection-level listing, not just query-based confirmation)
- Apply the Scenario 9 rendered-vs-structured consistency check to the two present chunks
- Confirm no production ISP-001 chunks leak into the scenario-scoped collection

If R02-SQ-06 returns any result, the fixture needs adjustment. The scenario depends on that specific subquery returning empty and nothing else.

---

## Before running

State the fixture path (`tests/fixtures/bundles/step_02_scenario_15.json`), the scenario-scoped index name (`idx_security_policy__scenario15`), the spec version being tested (SPEC-AGENT-SEC-001), and confirm:

1. no production artifacts were touched
2. no existing scenario's fixtures or indices were altered
3. the test harness is routing IT Security only to the scenario 15 bundle and scenario-scoped index
4. retrieval integrity checks passed — specifically, R02-SQ-06 returns zero chunks while R02-SQ-04 and R02-SQ-05 return their expected single-chunk matches
5. §12.3 is demonstrably absent from the scenario-15 collection (not just absent from R02-SQ-06 results)

Wait for confirmation before the API call.
