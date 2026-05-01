# scenario_blocked_demo — STEP-04 BLOCKED on missing Procurement Approval Matrix

Third demo scenario for the web app. Sits alongside:

- `scenario1_docs_for_web_app/` — happy path, all six steps COMPLETE, fast-track approved.
- `scenario2_docs_for_web_app/` — Legal escalation, STEP-03 ESCALATED on DPA + NDA blockers, downstream halted.
- **this scenario** — STEP-04 BLOCKED on missing PAM-001, STEP-01 → STEP-03 COMPLETE, downstream halted.

## Narrative

OptiChain is being onboarded as a **regulated** enterprise vendor (Class A, direct SAP API integration). Unlike scenario 1 it is **not** fast-track eligible — REGULATED data classification disallows fast-track. Unlike scenario 2 there are no Legal blockers — there is no EU personal data so a DPA is not required, and the NDA is already executed.

When the pipeline reaches STEP-04 the Procurement Agent attempts to retrieve approval-matrix rows for the vendor's `(vendor_class, integration_tier, deal_size)` profile. The Procurement Approval Matrix index (`idx_procurement_matrix`) is **not registered** for this scenario — the source has not been ingested. The router fails closed, the bundle's `approval_path_matrix_rows` arrives empty, and per Procurement Agent Spec §10 the agent emits `status=blocked` with `blocked_reason=["MISSING_PAM_001"]`. Supervisor halts; STEP-05 and STEP-06 never run.

Demo value: it shows that the Supervisor honors three terminal signals — `COMPLETE`, `ESCALATED`, **`BLOCKED`** — and that BLOCKED is reserved for "no evidence base", distinct from ESCALATED's "evidence present but unresolvable". It also shows the registry-driven fail-closed model: if a source isn't in the index registry, no agent can silently invent it.

## Expected per-step outcomes

| Step | Status | Verdict | Why |
|---|---|---|---|
| STEP-01 intake | COMPLETE | n/a | Questionnaire present and complete; deterministic. |
| STEP-02 IT Security | COMPLETE | PASS | `erp_type=DIRECT_API` → TIER_1; ERP-connected data → REGULATED; REGULATED → `fast_track_eligible=false`. |
| STEP-03 Legal | COMPLETE | PASS | `eu_personal_data_flag=false` → no DPA matrix row matches → `dpa_required=false`; NDA EXECUTED → `nda_blocker=false`. |
| STEP-04 Procurement | **BLOCKED** | PASS | Registry lacks PAM-001; router returns empty payload + `excluded_items` showing registry denial. Bundle's `approval_path_matrix_rows=[]`. Agent emits `status=blocked, blocked_reason=["MISSING_PAM_001"]`. |
| STEP-05 Checklist | PENDING | — | Supervisor halts on STEP-04 BLOCKED. |
| STEP-06 Checkoff | PENDING | — | Supervisor halts on STEP-04 BLOCKED. |

`overall_status: BLOCKED`. `halted_at: STEP-04`.

## Mock document deltas vs scenario 1

Scenario 1's questionnaire has UNREGULATED + EXPORT_ONLY + Class C — those produce fast-track. We need REGULATED + DIRECT_API + Class A to get a non-fast-track regulated path through STEP-02 and STEP-03 cleanly.

| Field | scenario_1 value | scenario_blocked_demo value | Why |
|---|---|---|---|
| `contract_details.vendor_class_assigned` | `Class C — Non-regulated Software` | `Class A — Enterprise Platform` | Force "regulated enterprise" path; canonical doc already has Class A so we just don't override it. |
| `product_and_integration.erp_integration.erp_type` | `EXPORT_ONLY` | `DIRECT_API` | TIER_1 integration, ERP-connected → REGULATED. |
| `product_and_integration.erp_integration.integration_description` | export-only file transfer | direct OAuth API to SAP S/4HANA OData | Unambiguous TIER_1 evidence so STEP-02 returns COMPLETE without hedging. |
| `data_handling.personal_data_in_scope` | `false` | `false` | No EU personal data → no DPA needed at STEP-03. |
| `data_handling.data_subjects.eu_personal_data_flag` | `false` | `false` | Same. |
| `data_handling.data_subjects.data_subjects_eu` | `false` | `false` | Same. |
| `data_handling.data_categories_in_scope` | `[Inventory exports, Forecast outputs]` | `[Production order data, MRP outputs, Inventory position records]` | Regulated ERP-connected categories. |
| `legal_and_contractual_status.existing_nda_status` | `EXECUTED` | `EXECUTED` | No NDA blocker. |
| `legal_and_contractual_status.dpa_required` | `false` | `false` | No DPA blocker. |
| `legal_and_contractual_status.dpa_status` | `EXECUTED` | `NOT_REQUIRED` | Cosmetic — value isn't read when `dpa_required=false`. |

Other mock corpora (IT Security Policy, DPA Legal Trigger Matrix, Slack threads, Stakeholder Map) are reused unchanged from scenario 1.

The Procurement Approval Matrix CSV **is** copied into the source dir — `resolve_scenario_source_paths()` requires the file to exist for chunking to run. The "missing" part is handled at the indexing stage: we delete the generated PAM-001 chunk JSON before building indexes so the registry never includes it. This mirrors a real-world situation where a document exists but hasn't been ingested.

## Build sequence

1. **Source dir** — `scenario_blocked_demo_mock_documents/` containing all six source documents (questionnaire updated, others copied verbatim from scenario 1).
2. **Preprocessing wiring** — register `scenario_blocked_demo` in `src/preprocessing/scenario_sources.py` (`SCENARIO_DIRS` + `SCENARIO_SOURCE_CANDIDATES`).
3. **Chunk generation** — `build_scenario_chunk_artifacts("scenario_blocked_demo")` produces five chunk JSONs in `data/processed/scenario_blocked_demo/chunks/`.
4. **Delete PAM-001 chunk** — `rm data/processed/scenario_blocked_demo/chunks/PAM-001.json`. This is the load-bearing step.
5. **Embeddings** — `build_and_persist_embeddings_for_scenario("scenario_blocked_demo")` embeds the four remaining indexed-hybrid sources.
6. **Storage indices** — `build_storage_indices_for_scenario("scenario_blocked_demo")` writes Chroma + BM25 + structured stores + `index_registry.json` **without a PAM-001 entry**.
7. **Test wiring** — `tests/full_pipeline/test_end_to_end.py` gets a third `ScenarioCase`; `tests/support/bundle_builder.py` gets a `scenario_blocked_demo_questionnaire_overrides()` factory; `tests/support/expected_outputs.py` gets per-step expectations; `pyproject.toml` gets a `scenario_blocked_demo` marker.
8. **Live run** — `uv run pytest tests/full_pipeline/test_end_to_end.py -m "api and scenario_blocked_demo" -v`.
9. **Artifact assembly** — populate this directory with raw agent outputs, agent input bundles, supervisor audit log, mock documents, and the per-run results block.

## Integrity check

A walk-through of why each step lands at its expected status given the planned fixture and the actual codebase behavior we verified.

### STEP-02 IT Security → COMPLETE

- IT Security Agent Spec §8 classification rules: "Integration involves regulated, sensitive, or ERP-connected data" → REGULATED. SAP S/4HANA via direct OAuth API qualifies.
- Spec §8.6 fast-track: `data_classification = REGULATED` → `fast_track_eligible = false`, `fast_track_rationale = DISALLOWED_REGULATED_DATA`.
- Spec §9.2 escalated triggers: agent escalates only when it cannot resolve a field. Here every field is resolvable (TIER_1 from direct-API description, REGULATED from ERP integration, false fast-track from REGULATED). → `status = complete`.
- Confirmation: this is the same code path scenario_2 run #6 took (REGULATED + TIER_1 + complete) — empirically validated 2026-04-27.

**Risk:** if the live model treats "no EU personal data" as ambiguity it could hedge. Mitigation: `regulated_data_types` is explicitly populated with concrete categories; `personal_data_in_scope: false` is unambiguous; `integration_description` says "no EU personal data in scope, US manufacturing operational data only".

### STEP-03 Legal → COMPLETE

- Legal Agent Spec: DPA trigger evaluation requires at least one matching DPA-TM-001 row. `eu_personal_data_flag=false` and `data_subjects_eu=false` → no row matches → `dpa_required = false`.
- Per CC-001 §14: when `dpa_required = false`, `dpa_blocker` is moot (no DPA workflow is engaged).
- NDA: `existing_nda_status = EXECUTED` → `nda_status = EXECUTED`, `nda_blocker = false`.
- All bundle admissibility requirements met. → `status = complete`.

**Risk:** the DPA trigger matrix has rows for non-EU triggers too (e.g., system access, hosted processing). If the model interprets "direct API to ERP" as a system-access trigger, it could fire `dpa_required = true`. Mitigation: per ORCH-PLAN-001 v0.10 (session #59 master_log entry), the system-access DPA trigger retrieval path was explicitly removed, and STEP-03's only DPA subquery (R03-SQ-04) is conditional on `eu_personal_data_confirmed == YES OR upstream_data_classification == REGULATED`. The OR branch (REGULATED) WILL fire here, returning DPA matrix rows. The model then has to evaluate whether any retrieved row applies — and per the matrix, A-01/E-01 are EU-conditional. The model should still emit `dpa_required = false` if it reads the rows correctly. **This is the riskiest step in the integrity check.** If the live model mis-applies a row, STEP-03 could escalate instead of complete and we'd never reach STEP-04.

  Fallback: if STEP-03 escalates, adjust the questionnaire to remove ERP-connected data category strings that might cue "system access" interpretations, or hardcode `regulated_data_types` to an obviously-non-DPA set ("Inventory position counts", "Production schedule").

### STEP-04 Procurement → BLOCKED

- Bundle assembly: STEP-04's R04-SQ-04 issues a hybrid query against `idx_procurement_matrix`. The router (`src/orchestration/retrieval/router.py:135-143`) calls `get_allowed_agents("PAM-001")` against the registry. `PAM-001` is absent from `data/indexes/scenario_blocked_demo/index_registry.json`. The router catches `KeyError`, returns `(denied=True, reason="Source 'PAM-001' not found in index registry.")`. `RetrievalResult` carries `payload=[]` and `excluded_items=[{source_id: "PAM-001", reason: "..."}]`.
- Bundle assembler writes `approval_path_matrix_rows: []` into the Procurement Agent's bundle.
- Procurement Agent Spec §10 BLOCKED conditions: enum value `MISSING_PAM_001` covers exactly this. Spec §9.1 requires the BLOCKED output shape: `{status: "blocked", blocked_reason: ["MISSING_PAM_001"], blocked_fields: [...]}` with all determination fields absent (not null).
- Supervisor handler `step04_procurement.py` reads `status = blocked` and sets `state.step_statuses[STEP_04] = BLOCKED`. Per state machine, BLOCKED is terminal → halt downstream. `state.overall_status = BLOCKED`.

**Risk:** the live model might emit `status = escalated` instead of `blocked`. The mock pipeline does this (it's overly permissive). The real model should follow the spec, but spec adherence on a brand-new condition is not guaranteed. If we get ESCALATED, two options:
- Accept it and rename the demo to "STEP-04 ESCALATED on missing matrix" (still a valid distinct demo from scenario 2's STEP-03 escalation).
- Strengthen the bundle's `bundle_meta` to explicitly carry `excluded_items` so the agent has unambiguous evidence the source was unavailable rather than just empty. (May require code change.)

I'll accept whichever the live model emits and report it. If the user wants strict BLOCKED I'll iterate on the bundle metadata.

### Downstream halt invariant

- `tests/full_pipeline/test_end_to_end.py` already enforces "after escalation/halt, every downstream step remains PENDING" for scenario_2. Same assertion logic will apply for scenario_blocked_demo. The only new piece is `expected_overall_status="BLOCKED"`.

## Risks / open questions

1. **STEP-03 misclassification on DPA** (medium risk) — addressed above with fallback.
2. **STEP-04 emits ESCALATED instead of BLOCKED** (low-medium risk) — addressed above; demo still works either way.
3. **Bundle metadata may not carry `excluded_items` to the agent prompt** — need to verify after STEP-04 runs whether the agent has signal to distinguish "source missing" from "no rows match". If not, the spec compliance test for BLOCKED becomes a model-prompt question, not a determinism question.
4. **`SCENARIO_SOURCE_CANDIDATES` requires procurement_matrix file** — solved by including the file and deleting the generated chunk before indexing.

## Output layout (after build)

```
scenario_blocked_demo/
  README.md                       (this file)
  agent_outputs/
    pipeline_N__it_security_agent__scenario_blocked_demo_pass.json
    pipeline_N__legal_agent__scenario_blocked_demo_pass.json
    pipeline_N__procurement_agent__scenario_blocked_demo_pass.json
  agent_input_bundles/
    scenario_blocked_demo__STEP-02__bundle.json
    scenario_blocked_demo__STEP-03__bundle.json
    scenario_blocked_demo__STEP-04__bundle.json
  supervisor_audit_log.json
  full_pipeline_test_results.md
  mock_documents/
    OptiChain_VSQ_001_v2_1_blocked_demo.json
    IT_Security_Policy_V4.2.md
    DPA_Legal_Trigger_Matrix_v1_3.csv
    DPA_Legal_Trigger_Matrix_v1_3.xlsx
    Procurement_Approval_Matrix_v2_0.csv     (kept for reference; NOT in the index)
    Slack_Thread_Export_scenario01.json
    Slack_Thread_Export_scenario01.md
    Stakeholder_Map_PRQ_2024_0047.json
```

The `Procurement_Approval_Matrix_v2_0.csv` in `mock_documents/` is the file that *would have been* ingested. Its presence in this directory but absence from the live registry is the visible artifact of the BLOCKED condition.
