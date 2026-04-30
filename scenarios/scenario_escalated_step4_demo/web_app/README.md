# scenario_escalated_step4_demo — STEP-04 ESCALATED on no matching PAM-001 row

Fourth demo scenario for the web app. Sits alongside:

- `scenario1_docs_for_web_app/` — happy path, all six steps COMPLETE, fast-track approved.
- `scenario2_docs_for_web_app/` — Legal escalation, STEP-03 ESCALATED on DPA + NDA blockers, downstream halted.
- `scenario_blocked_demo/` — STEP-04 BLOCKED on missing PAM-001 (matrix entirely absent from the registry).
- **this scenario** — STEP-04 ESCALATED on a vendor profile that doesn't match any PAM-001 row (matrix is present and retrieved; no row applies).

## Narrative

OptiChain is being onboarded as **Class D — Technology Professional Services**. The procurement approval matrix shipped for this scenario (a curated three-row subset of PAM-001 v2.0 covering only Class A-T1, B-T1, and C-T1) does not include any Class D row — the vendor's class genuinely sits in a coverage gap. Otherwise the engagement is clean: regulated SAP S/4HANA direct-API integration, no EU personal data, NDA executed, no DPA required.

The pipeline reaches STEP-04 with valid upstream outputs from IT Security and Legal. The Procurement Agent retrieves rows from the procurement matrix, inspects them, and finds that none match the `(vendor_class="Class D", integration_tier="T1")` profile on the matrix's primary keys. Per Procurement Agent Spec §8.5 and CC-001 §12, "no matching row" is **insufficient evidence to resolve an approval path** — the agent must emit `status: escalated` and surface the gap to the Procurement Director, **not** silently substitute the nearest row. Supervisor halts; STEP-05 and STEP-06 never run.

Demo value: it shows that the Supervisor's three terminal signals (`COMPLETE`, `ESCALATED`, `BLOCKED`) are governed by **distinct evidence conditions**. Paired with `scenario_blocked_demo`, this scenario tells the contrast story: same step, same evidence layer, two failure modes — "evidence absent entirely" → BLOCKED versus "evidence present but unresolvable" → ESCALATED. It also catches the single highest-risk failure mode for the Procurement Agent: silent path fabrication (the model invents an `approval_path` value by picking the nearest non-matching row).

## Expected per-step outcomes

| Step | Status | Verdict | Why |
|---|---|---|---|
| STEP-01 intake | COMPLETE | n/a | Questionnaire present and complete; deterministic. |
| STEP-02 IT Security | COMPLETE | PASS | `erp_type=DIRECT_API` → TIER_1; ERP-connected data → REGULATED; REGULATED → `fast_track_eligible=false`. |
| STEP-03 Legal | COMPLETE | PASS | `eu_personal_data_flag=false` → no DPA matrix row applies → `dpa_required=false`; NDA EXECUTED → `nda_blocker=false`. |
| STEP-04 Procurement | **ESCALATED** | PASS | Bundle admissible: IT Security + Legal outputs present, vendor relationship fields present, PAM-001 rows retrieved. But no retrieved row matches `vendor_class="Class F"`. Agent emits `status=escalated`, `approval_path=null` (or absent), no PAM-001 PRIMARY citation, `fast_track_eligible=false` passed through from upstream. |
| STEP-05 Checklist | PENDING | — | Supervisor halts on STEP-04 ESCALATED. |
| STEP-06 Checkoff | PENDING | — | Supervisor halts on STEP-04 ESCALATED. |

`overall_status: ESCALATED`. `halted_at: STEP-04`.

## Mock document deltas vs scenario_blocked_demo

This scenario reuses everything from `scenario_blocked_demo` except the vendor classification. PAM-001 is **included** in the registry and chunks (the gap is in coverage, not presence). Other corpora (IT Security Policy, DPA Legal Trigger Matrix, Slack threads, Stakeholder Map) are reused unchanged from scenario 1.

| Field | scenario_blocked_demo | scenario_escalated_step4_demo | Why |
|---|---|---|---|
| `vendor_class` (top-level questionnaire field) | `Class A — Enterprise Platform` | `Class D — Technology Professional Services` | Drives STEP-04's matrix lookup. The scenario's curated PAM CSV contains only Class A/B/C T1 rows — no Class D row exists for the agent to match. |
| `contract_details.vendor_class_assigned` | `Class A — Enterprise Platform` | `Class D — Technology Professional Services` | Same field, different location in the canonical questionnaire schema. Both must agree. |
| `Procurement_Approval_Matrix_v2_0.csv` (mock document) | full production matrix (20 rows, A–E × T1–T4) | curated three-row subset (A-T1, B-T1, C-T1) | Mirrors the per-agent scenario_7 fixture pattern. The narrow row set makes the Class D gap unambiguous — the agent sees only A/B/C rows and recognizes none match. |
| `contract_details.annual_contract_value_usd` (canonical questionnaire baseline) | `210000` | `150000` | T2 deal size — close to common matrix coverage to make the "should match" expectation natural, even though no Class F row exists. |
| `contract_value_annual` (top-level mock field) | `210000` | `150000` | Same value, mirrored in the legacy top-level field. |

All other questionnaire fields (regulated ERP integration, no EU personal data, NDA executed, no DPA needed) are identical to `scenario_blocked_demo`. The matrix CSV is curated to three rows so the Class D gap is unmistakable — the same fixture pattern that the per-agent `scenario_7` test uses successfully.

### Why curated, not full production matrix

A first attempt used the full production PAM v2.0 (20 rows) with `vendor_class="Class F — Specialty Consulting Practice"` (a class label entirely outside A–E). On run #8, Haiku 4.5 collapsed the BLOCKED/ESCALATED distinction and emitted `status: blocked` even though the bundle was admissible. Switching to the per-agent scenario_7 fixture pattern — curated three-row matrix + Class D vendor (a class label that's structurally similar to A/B/C but absent from the visible matrix) — produced the spec-correct ESCALATED shape on run #9. Lesson: when prompting for a "no matching row" judgment, a narrow visible row set with an absent-but-recognizable class is more legible to the agent than a wide row set with a foreign class.

## Build sequence

1. **Source dir** — `scenario_escalated_step4_demo_mock_documents/` containing all six source documents, with the questionnaire updated to the Class F profile.
2. **Preprocessing wiring** — register `scenario_escalated_step4_demo` in `src/preprocessing/scenario_sources.py`.
3. **Chunk generation** — `build_scenario_chunk_artifacts("scenario_escalated_step4_demo")` produces five chunk JSONs in `data/processed/scenario_escalated_step4_demo/chunks/`. PAM-001 is included this time.
4. **Embeddings + storage indices** — same SOURCE_STORE_CONFIG in-memory patch as `scenario_blocked_demo` so DPA-TM-001 + PAM-001 land as `vector_bm25` (matching the historical scenario_1/2 registry shape rather than the in-progress structured_direct migration). PAM-001 is fully indexed.
5. **Test wiring** — `tests/full_pipeline/test_end_to_end.py` gets a fourth `ScenarioCase`; `tests/support/bundle_builder.py` gets a `scenario_escalated_step4_demo_questionnaire_overrides()` factory; `tests/support/expected_outputs.py` gets per-step expectations; `pyproject.toml` gets a `scenario_escalated_step4_demo` marker.
6. **Live run** — `uv run pytest tests/full_pipeline/test_end_to_end.py -m "api and scenario_escalated_step4_demo" -v`.
7. **Artifact assembly** — populate this directory with raw agent outputs, agent input bundles, supervisor audit log, mock documents, and the per-run results block.

## Integrity check

Step-by-step reasoning for each expected status given the planned fixture and current codebase behavior.

### STEP-02 IT Security → COMPLETE

Identical reasoning to `scenario_blocked_demo`'s STEP-02 (same questionnaire integration + data fields). The IT Security Agent doesn't read `vendor_class`, so changing it to "Class F" has no impact on STEP-02. Empirically validated: scenario_blocked_demo run #7 produced `DIRECT_API`, `TIER_1`, `REGULATED`, `fast_track_eligible=false`, `status=complete`.

### STEP-03 Legal → COMPLETE

Identical reasoning to `scenario_blocked_demo`'s STEP-03 (same legal-and-contractual fields). The Legal Agent doesn't read `vendor_class` either. Empirically validated by run #7: `dpa_required=false`, `nda_status=EXECUTED`, `status=complete`.

### STEP-04 Procurement → ESCALATED

This is the load-bearing step.

- **Retrieval succeeds**: PAM-001 IS in the registry. The router routes the R04-SQ-04 query to `idx_procurement_matrix` and returns matching rows by semantic + lexical score. Likely returns a handful of rows (maybe Class A or B rows that mention regulated SaaS, or Class C/D rows that mention deal sizes near $150K).
- **Bundle is admissible**: IT Security output present, Legal output present, questionnaire vendor relationship fields present (`vendor_class`, `annual_contract_value_usd`, `existing_nda_status`, `existing_msa`), PAM-001 candidate rows present. Per Procurement Agent Spec §8.5, every admissibility requirement is satisfied.
- **Primary-key match fails**: The agent inspects each retrieved row's `(Class, Tier)` columns. None of them carry `Class: D` — the curated matrix subset has only A/B/C T1 rows. Per Procurement Spec §14 A-04, "no `approval_path` may be asserted from a row that does not match on both primary keys."
- **Correct emission per Spec §9.2 (escalated shape)**: `status: escalated`, all determination fields **present** (not absent — that's the blocked shape), `approval_path: null` (or absent depending on agent's enum-vs-null discipline), no PAM-001 `PRIMARY` citation, `fast_track_eligible=false` passed through from upstream IT Security without re-derivation.
- **Supervisor halts**: STEP-04 ESCALATED is terminal → STEP-05 / STEP-06 stay PENDING. `overall_status=ESCALATED`.

**Risk: silent path fabrication** (highest-priority failure mode per scenario 7 build prompt §5):

> The model picks the nearest PAM-001 row and emits `approval_path: STANDARD | FAST_TRACK | EXECUTIVE_APPROVAL` with `status: complete`. This is the dangerous case — the evaluator must fail loudly if any approval_path enum value is present alongside `status: complete` without a PAM-001 PRIMARY citation backing it.

The scenario 7 spec specifically warns about this. To minimize the chance:
- The vendor class label ("Class D — Technology Professional Services") is structurally adjacent to the visible A/B/C labels in the curated matrix, so the agent recognizes it as a real-but-unseen class rather than treating it as a missing input.
- The narrow three-row matrix subset makes the gap unambiguous by inspection.
- The agent's system prompt already includes the §14 A-04 strict-primary-key-matching rule.

**If the model fabricates** anyway (status=complete with a nearest-row approval_path), this scenario surfaces exactly the failure mode it's designed to surface, and we treat the outcome as either:
- A useful "this is what governance enforcement is preventing" demo moment (if we can show the audit log catching it), or
- An iteration target — we can either tighten the agent prompt or curate a smaller PAM CSV that makes the gap unmistakable.

I'll accept whichever the live model emits and report it.

**Risk: blocked-shape leakage**: The agent might emit the blocked output shape (determination fields absent) instead of the escalated shape. Per spec, that would be a contract violation — the bundle was admissible, the agent had evidence to begin work, so escalated (with fields populated and `approval_path: null`) is the correct shape. If we see blocked-shape leakage, the per-step evaluator will catch it.

### Downstream halt invariant

Same logic as scenario 2 (STEP-03 ESCALATED) and scenario_blocked_demo (STEP-04 BLOCKED): once a step terminates as ESCALATED or BLOCKED, every downstream step stays PENDING. The full-pipeline test already enforces this; we just add per-case assertions for STEP-04 ESCALATED + STEP-05/06 PENDING + overall_status ESCALATED.

## Risks / open questions

1. **Silent path fabrication** — verified empirically not to happen. Run #9 emitted `approval_path: null` and `status: escalated`. The model correctly refused to substitute a non-matching row.
2. **BLOCKED/ESCALATED collapse** — DID happen on the first attempt (run #8 with full production matrix + Class F). Resolved by switching to the curated-matrix + Class D pattern documented above.
3. **`approval_path: null` vs absent** — the agent emits `null` (acceptable per spec for ESCALATED shape).
4. **`SCENARIO_SOURCE_CANDIDATES` requires procurement_matrix file** — the file IS included (we want PAM-001 in the index, just with curated rows), so no special handling needed.

## Output layout (after build)

```
scenario_escalated_step4_demo/
  README.md                       (this file)
  agent_outputs/
    pipeline_N__it_security_agent__scenario_escalated_step4_demo_pass.json
    pipeline_N__legal_agent__scenario_escalated_step4_demo_pass.json
    pipeline_N__procurement_agent__scenario_escalated_step4_demo_pass.json
  agent_input_bundles/
    scenario_escalated_step4_demo__STEP-02__bundle.json
    scenario_escalated_step4_demo__STEP-03__bundle.json
    scenario_escalated_step4_demo__STEP-04__bundle.json
  supervisor_audit_log.json
  full_pipeline_test_results.md
  mock_documents/
    OptiChain_VSQ_001_v2_1_escalated_step4_demo.json
    IT_Security_Policy_V4.2.md
    DPA_Legal_Trigger_Matrix_v1_3.csv
    DPA_Legal_Trigger_Matrix_v1_3.xlsx
    Procurement_Approval_Matrix_v2_0.csv     (curated three-row subset: A-T1, B-T1, C-T1 — no Class D coverage)
    Slack_Thread_Export_scenario01.json
    Slack_Thread_Export_scenario01.md
    Stakeholder_Map_PRQ_2024_0047.json
```

The `Procurement_Approval_Matrix_v2_0.csv` here is a deliberately curated three-row subset of the production matrix (A-T1, B-T1, C-T1). Its presence in this directory and in the index — combined with its lack of Class D coverage — is the visible artifact of the ESCALATED condition.
