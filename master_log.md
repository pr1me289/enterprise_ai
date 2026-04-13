### [#1] 2026-04-08 | Codex
**Task:** Find the repository, validate Git/GitHub readiness, read `AGENTS.md`, and add a root `README.md` and `.gitignore` aligned to repository instructions.
**Plan:** Inspect the repository state, load repo-level instructions, create the required root files, remove tracked IDE/system artifacts that should be ignored, then commit and push the changes on `main`.
**Changes:** Added `README.md`, `.gitignore`, and `master_log.md`. Reviewed repository structure, git remotes, and GitHub CLI authentication status. Removed tracked IDE and macOS metadata from version control so `.gitignore` can enforce the intended policy.
**Result:** Repository instructions were read successfully and applied. Local git operations work. The GitHub CLI token reported as invalid during inspection, but git push via the configured repository credentials succeeded and the changes were pushed to `origin/main`.
**Next:** Create and use a separate feature branch for subsequent development work.

### [#2] 2026-04-08 | Codex
**Task:** Finalize repository bootstrap work by recording push completion after the initial documentation commit reached `main`.
**Plan:** Update `master_log.md` so the repository log matches the actual final state, then commit and push the correction.
**Changes:** Updated `master_log.md` to reflect successful push completion and the current recommendation to work on a separate branch next.
**Result:** The repository log now matches the true repository state after the `main` branch push.
**Next:** Start future work from a new branch instead of committing directly to `main`.

### [#3] 2026-04-08 | Codex
**Task:** Read `STRATEGY.md`, update `README.md` to describe the project purpose and execution plan, push the change to `main`, and create a branch for the preprocessing layer without starting implementation work.
**Plan:** Review the strategy document, rewrite `README.md` so it reflects the governed retrieval architecture and phased execution approach, record the work in `master_log.md`, push the documentation change to `main`, then create a dedicated preprocessing branch for the next phase.
**Changes:** In progress.
**Result:** In progress.
**Next:** Commit the documentation update, push `main`, and create the preprocessing branch.

### [#4] 2026-04-08 | Codex
**Task:** Finalize the strategy-driven documentation update and prepare a dedicated branch for preprocessing work.
**Plan:** Record the completed README push in `master_log.md`, push the log update to `main`, then create a preprocessing branch without starting implementation.
**Changes:** Updated `README.md` to reflect the project purpose, source lanes, phased execution plan, and retrieval architecture from `STRATEGY.md`. Updated `master_log.md` to record task completion. Prepared to create a dedicated preprocessing branch from the updated `main`.
**Result:** The strategy-aligned README update was pushed to `origin/main` without starting project implementation work. The repository is now documented and ready for work to continue on a separate preprocessing branch.
**Next:** Create and use the preprocessing branch for the next implementation phase once requirements are provided.

### [#5] 2026-04-08 | Codex
**Task:** Start Step 4 preprocessing scaffolding and align the package layout with the current branch expectations.
**Plan:** Build source-specific ingestors under `src/preprocessing`, keep source-level metadata contract-driven, and avoid treating mock document versions as validation failures.
**Changes:** Moved preprocessing code to `src/preprocessing`. Kept per-source ingestors plus the dispatcher and normalized source models. Removed mock-version mismatch warnings while preserving contract-level metadata and detected source versions.
**Result:** The preprocessing layer now lives at the requested import path and matches the demo-document posture more closely.
**Next:** Continue Step 4 implementation from `src/preprocessing` and add follow-on verification/tests as the layer expands.

### [#6] 2026-04-08 | Codex
**Task:** Implement the chunking layer and write canonical intermediate chunk artifacts.
**Plan:** Create `src/chunking`, consume `NormalizedSource` objects from preprocessing, emit canonical `Chunk` objects, and write per-source JSON artifacts to `data/processed/chunks`.
**Changes:** Added chunk models, source-aware chunk builders, artifact writing utilities, and a pipeline helper. Generated chunk artifacts for the DPA matrix, procurement matrix, precedent log, and Slack notes. Questionnaire sources are skipped from chunk output by design.
**Result:** Canonical inspectable chunk JSON now exists in `data/processed/chunks` for the currently preprocessable demo sources, ready for later embedding/indexing reads.
**Next:** Extend artifact generation to the policy PDF once a local PDF text extraction dependency is available in the environment.

### [#7] 2026-04-08 | Codex
**Task:** Briefly document preprocessing and chunking in the root README.
**Plan:** Add a short capability summary and minimal run commands without expanding the README unnecessarily.
**Changes:** Updated `README.md` to describe current preprocessing and chunking behavior, what each layer does, and how to run each layer from `PYTHONPATH=src`.
**Result:** The README now reflects the current implementation state and gives concise commands for local use.
**Next:** Keep README commands aligned as the embedding and indexing layers are added.

### [#8] 2026-04-08 | Codex
**Task:** Bring the PDF dependency from `main` into `feature/chunking-layer`.
**Plan:** Merge `main` into the chunking branch, keep the existing chunking history in `master_log.md`, and accept the repo-level `pypdf` dependency files from `main`.
**Changes:** Merged `main` into `feature/chunking-layer`, added `pyproject.toml` and `uv.lock`, and resolved the `master_log.md` merge conflict in favor of the chunking branch history plus this dependency merge note.
**Result:** The chunking branch now carries the same repo-level PDF dependency baseline as `main`.
**Next:** Keep branch dependencies aligned as shared tooling evolves.

### [#9] 2026-04-08 | Codex
**Task:** Add chunking tests under `tests/chunking`, run them with coverage, and report the actual results on `feature/chunking-layer`.
**Plan:** Add repo-local pytest config, create chunking tests against the real mock source files plus temporary artifact outputs, run the chunking suite with coverage, and record any failures or coverage gaps directly in this log.
**Changes:** Added `tests/conftest.py` plus a `tests/chunking/` suite covering source-specific chunking behavior, questionnaire skip behavior, artifact writing, and the chunking pipeline entrypoint. Updated `pyproject.toml` with pytest config and dev test dependencies, and refreshed `uv.lock` with `uv add --dev pytest pytest-cov`.
**Result:** `uv run pytest tests/chunking --cov=chunking --cov-report=term-missing` completed with 11 passed, 0 failed. Chunking coverage is 99%: `src/chunking/__init__.py` 100%, `src/chunking/artifacts.py` 100%, `src/chunking/chunker.py` 97%, `src/chunking/models.py` 100%, `src/chunking/pipeline.py` 100%. The only uncovered line is `src/chunking/chunker.py:125`.
**Next:** Keep chunking tests updated as chunk metadata or artifact shape changes in later indexing work.

### [#10] 2026-04-09 | Codex
**Task:** Rename the source contract field from `status` to `manifest_status` across preprocessing and chunking, then refresh chunk artifacts.
**Plan:** Update the source contract and normalized source models, propagate the rename through ingestors and chunk models, rerun chunk artifact generation, and verify the change with the chunking test suite.
**Changes:** Renamed the contract/model field to `manifest_status` in `src/preprocessing/` and `src/chunking/`, updated the direct `NormalizedSource` construction in `tests/chunking/test_chunker.py`, and regenerated `data/processed/chunks/DPA-TM-001.json`, `PAM-001.json`, `PVD-001.json`, and `SLK-001.json` so the artifact payload now emits `manifest_status`.
**Result:** The code and generated chunk artifacts now consistently use `manifest_status` instead of `status`. `uv run pytest tests/chunking` completed with 11 passed, 0 failed.
**Next:** Keep downstream indexing/retrieval code aligned to `manifest_status` as new layers are added.

### [#11] 2026-04-09 | Codex
**Task:** Chunk the new Markdown IT security policy and write its artifact into `data/processed/chunks`.
**Plan:** Update the policy section parser to recognize Markdown headings and bolded clause identifiers, switch the supported chunking path/tests to the Markdown policy source, regenerate chunk artifacts including the policy, and verify the result with the chunking test suite.
**Changes:** Extended `src/preprocessing/text_utils.py` so policy splitting recognizes Markdown forms like `## 1. Purpose`, `### 6.1 Access Provisioning`, and `**12.1.4** ...`. Updated `tests/chunking/test_chunker.py` and `tests/chunking/test_pipeline.py` to use `mock_documents/IT_Security_Policy_V4.2.md`, updated the chunking command in `README.md`, and generated `data/processed/chunks/ISP-001.json`.
**Result:** The Markdown IT security policy now chunks correctly into 96 section-boundary artifacts, including clause-level citations such as `ISP-001 §12.1.4`. `uv run pytest tests/chunking` completed with 11 passed, 0 failed.
**Next:** Keep policy parsing aligned if future mock policy sources introduce additional Markdown heading styles or mixed formatting.

### [#12] 2026-04-09 | Codex
**Task:** Reduce over-chunking in the IT security policy so container headings do not become weak retrieval units.
**Plan:** Refine policy section splitting to suppress parent/container headings with no substantive body text, preserve leaf clauses whose policy content lives on the heading line, strip separator-only lines from chunk text, regenerate the policy artifact, and verify with tests.
**Changes:** Updated `src/preprocessing/text_utils.py` with policy-specific cleanup and a filter that drops empty container sections such as `6`, `6.1`, and `6.2` while retaining substantive leaf clauses like `6.1.1`. Regenerated `data/processed/chunks/ISP-001.json` and tightened `tests/chunking/test_chunker.py` plus `tests/chunking/test_pipeline.py` to assert the new policy chunk shape and separator removal.
**Result:** `ISP-001.json` now contains 82 stronger policy chunks instead of 96, container-only headings are omitted, and trailing `---` separators are removed from chunk text. `uv run pytest tests/chunking` completed with 11 passed, 0 failed.
**Next:** Revisit the heading-substance heuristic only if future policy formats introduce ambiguous section labels that should be retained or merged differently.

### [#13] 2026-04-09 | Codex
**Task:** Implement Step 7 embedding on a dedicated branch from `feature/chunking-layer`, using finalized chunk artifacts and persisting eligible vectors into Chroma.
**Plan:** Create `feature/embedding-layer`, add a small `src/indexing/` package for eligibility filtering, batch embedding, vector-record assembly, chunk-artifact loading, and Chroma persistence, add indexing tests, install only the runtime dependencies needed for this stage, then run a real embedding build against the current chunk artifacts.
**Changes:** Created `feature/embedding-layer`. Added `src/indexing/` with `models.py`, `embeddings.py`, `chroma_store.py`, `pipeline.py`, and `__init__.py`. Added `Chunk.from_dict()` in `src/chunking/models.py` to support loading canonical chunk artifacts. Added `tests/indexing/` covering embedding eligibility, deterministic record construction, artifact loading, and Chroma persistence with test doubles. Updated `README.md` project commands and implementation notes, updated `.gitignore` to exclude the generated Chroma directory, and updated `pyproject.toml` / `uv.lock` with the embedding runtime stack: `chromadb`, `sentence-transformers==3.0.1`, `transformers==4.41.2`, `torch<2.3`, `onnxruntime<1.24`, and `numpy<2`.
**Result:** `uv run pytest tests/chunking tests/indexing` completed with 19 passed, 0 failed under Python 3.12. A real embedding build completed successfully with `uv run python -c "..."`, embedding all current indexed-hybrid chunk artifacts and persisting 137 records into the Chroma collection `enterprise_ai_chunks` under `data/indexes/chroma/`.
**Next:** Build Step 8 storage/index retrieval helpers around the persisted Chroma collection and add BM25 alongside the dense vector index without changing the chunk contracts.

### [#14] 2026-04-09 | Codex
**Task:** Promote the Step 8 metadata fields to first-class source/chunk metadata before starting storage and indexing.
**Plan:** Extend preprocessing so sources carry `document_date`, `freshness_status`, and source-class `is_primary_citable`, extend chunking so chunk artifacts inherit those fields plus manual precedent `domain_scope`, regenerate the chunk artifacts, update the README, and stop before implementing Step 8 storage/indexing logic.
**Changes:** Updated `src/preprocessing/` models, source contracts, and ingestors so source-level metadata now includes `document_date`, `freshness_status`, and `is_primary_citable`. Updated `src/chunking/models.py` and `src/chunking/chunker.py` so chunk artifacts inherit that metadata and precedent chunks receive a manual `domain_scope` mapping by record ID. Regenerated `data/processed/chunks/ISP-001.json`, `DPA-TM-001.json`, `PAM-001.json`, `PVD-001.json`, and `SLK-001.json`. Updated chunking tests plus the direct chunk test helper in `tests/indexing/test_embeddings.py`, and refreshed `README.md` implementation notes to describe the finalized chunk metadata shape.
**Result:** The canonical chunk artifacts now expose the Step 8 metadata as first-class fields instead of leaving them to be inferred ad hoc later. `uv run pytest tests/chunking tests/indexing` completed with 19 passed, 0 failed. No Step 8 storage/indexing implementation was started after this metadata promotion pass.
**Next:** Resume Step 8 only after the metadata-first chunk contract is accepted as the stable input to storage/indexing.

### [#15] 2026-04-09 | Codex
**Task:** Implement Step 8 storage and indexing on a dedicated branch from `feature/embedding-layer`, following `storage_indexing_strategy.md`.
**Plan:** Keep the metadata-first chunk contract intact, add explicit per-source index definitions, build per-source Chroma collections and BM25 bundles over shared backends, persist the questionnaire as a direct structured store, add retrieval wrappers for endpoint routing/permissions/hybrid search/reranking/manifests, update docs, and verify with both tests and a real storage/index build.
**Changes:** Created and populated the Step 8 storage/indexing structure under `src/indexing/` with `build_vector_index.py`, `build_bm25_index.py`, `build_structured_store.py`, `index_registry.py`, and `metadata_schema.py`, while retaining the Step 7 embedding entrypoints. Added `src/retrieval/` with `source_router.py`, `permission_guard.py`, `hybrid_search.py`, `authority_reranker.py`, and `retrieval_manifest.py`. Added `rank-bm25` to `pyproject.toml` / `uv.lock`. Added tests covering explicit index mapping, BM25 build/query/filter behavior, structured questionnaire persistence, and retrieval routing/permission/fusion behavior. Ran a real Step 8 build that created per-source Chroma collections, BM25 bundles under `data/bm25/`, vector registries under `data/indexes/vector_registry/`, a structured questionnaire store at `data/structured/vq_direct_access.json`, and `data/indexes/index_registry.json`. Updated `.gitignore` and `README.md` to reflect the generated outputs and new workflow.
**Result:** `uv run pytest tests/chunking tests/indexing tests/retrieval` completed with 32 passed, 0 failed. The real Step 8 build completed successfully with per-source counts of: `idx_security_policy` 82, `idx_dpa_matrix` 27, `idx_procurement_matrix` 20, `idx_precedents` 4, and `idx_slack_notes` 4 in both Chroma and BM25 outputs.
**Next:** Build the task-aware retrieval planner and bundle assembly on top of the Step 8 endpoint/router/permission/hybrid foundations without collapsing the indices into one broad searchable corpus.

### [#16] 2026-04-09 | Codex
**Task:** Tighten the artifact metadata contract so source types are deliberate, document dates are demo-consistent, Slack permissions stay procurement-only, and precedent domain scopes are reviewed rather than heuristic drift.
**Plan:** Replace the generic `SourceType` values with explicit source-class enum values, move all current sources to the shared demo defaults `document_date=2026-04-04` and `freshness_status=CURRENT`, stop overriding dates inside ingestors, spot-check and lock the precedent `domain_scope` mapping by record, regenerate chunk and Step 8 storage outputs, then update the README and tests to reflect the tightened contract.
**Changes:** Updated `src/preprocessing/models.py`, `src/preprocessing/source_contract.py`, `src/preprocessing/source_loader.py`, and the source ingestors so all current sources inherit explicit source-type enums and shared demo date/freshness defaults at the source-contract layer. Updated `src/chunking/chunker.py` so matrix dispatch handles the split matrix types and precedent `domain_scope` now uses the reviewed mapping `legal`, `security`, `legal`, `procurement` for the four current records. Updated `src/indexing/index_registry.py` to expose the new source-type values in the logical index definitions. Refreshed the relevant mock Slack and precedent source files, expanded tests to assert the new source types, the shared `2026-04-04` document date, procurement-only Slack `allowed_agents`, and the reviewed precedent scope mapping, and updated `README.md` to document the standardized `source_type` contract and the demo-wide metadata defaults.
**Result:** The artifact contract is now tighter and more legible: source types align to the planning language, all current sources expose the same demo date/freshness posture, Slack remains procurement-scoped across all chunks, and precedent `domain_scope` is explicitly reviewed instead of left ambiguous.
**Next:** Keep later retrieval and bundle-assembly work keyed to these explicit source classes and inherited governance fields rather than re-deriving them downstream.

### [#17] 2026-04-09 | Codex
**Task:** Rebuild the index registry as a canonical source-to-store routing map by directly following `build_index_registry.md`.
**Plan:** Replace the existing index-centric registry shape with a generated source-level registry that records one entry per logical source, add a loader/helper module for retrieval code, update the structured questionnaire store metadata so the registry can read it directly, route retrieval helpers through registry lookups, regenerate `data/indexes/index_registry.json`, and verify with tests.
**Changes:** Reworked `src/indexing/index_registry.py` around a source-level `SOURCE_STORE_CONFIG`, added deterministic registry generation/writing, and changed the registry JSON shape to `registry_version`, `generated_at`, and `sources`. Added `src/indexing/load_index_registry.py` with helpers for entry lookup, logical store lookup, backend lookup, access lookup, and indexed-vs-structured checks. Updated `src/indexing/build_structured_store.py` so the questionnaire store now carries `authority_tier` and `retrieval_lane` at top level. Updated `src/indexing/pipeline.py` to write the new registry format, and updated `src/retrieval/source_router.py` plus `src/retrieval/permission_guard.py` so routing and access checks consume registry-derived mappings rather than hard-coded module maps. Added and refreshed indexing tests for the new registry shape and loader helpers, and updated the README registry section to describe the control-plane role of the registry.
**Result:** The Step 8 registry is now a canonical source-level control-plane artifact with one record per source, direct mapping to logical store names and backends, and retrieval helpers built on top of it instead of ad hoc storage assumptions.
**Next:** Keep any future retrieval planner or bundle assembly code reading source/store/backends/allowed-agents from the registry helpers instead of duplicating source-routing logic elsewhere.

### [#18] 2026-04-10 | Codex
**Task:** Regenerate the Step 8 index registry JSON on `feature/index-registry`.
**Plan:** Use the existing `build_storage_indices` pipeline entrypoint so the generated registry matches the current chunk artifacts, structured questionnaire store, BM25 bundles, and per-source Chroma/vector registry outputs.
**Changes:** Regenerated local Step 8 storage/index outputs, including `data/indexes/index_registry.json`, by running the existing indexing pipeline with `mock_documents/OptiChain_VSQ_001_v2_1.json`.
**Result:** `data/indexes/index_registry.json` now exists locally with six source-level entries: five indexed-hybrid sources mapped to Chroma/BM25 logical stores and `VQ-OC-001` mapped to `vq_direct_access`.
**Next:** Use `src/indexing/load_index_registry.py` helpers for retrieval code that needs the canonical source-to-store routing map.

### [#19] 2026-04-10 | Codex
**Task:** Add a README note for regenerating the index registry.
**Plan:** Document the intended Step 8 pipeline entrypoint concisely in the existing Index Registry section.
**Changes:** Added a short README line pointing to `src/indexing/pipeline.py` and `build_storage_indices(questionnaire_path='mock_documents/OptiChain_VSQ_001_v2_1.json')`.
**Result:** The README now identifies the code path to run when `data/indexes/index_registry.json` needs to be generated or refreshed.
**Next:** Keep the command aligned if the Step 8 pipeline entrypoint changes.

### [#20] 2026-04-13 | Codex
**Task:** Build the first-pass Supervisor orchestration layer on a feature branch from current `main`, using the orchestration plan and agent specs as the primary implementation constraints.
**Plan:** Add a new `src/orchestration/` package with explicit pipeline state, step definitions, step handlers, retrieval routing, bundle assembly, LLM-agent invocation scaffolding, validation, and append-only audit logging. Start with mocked indexed retrieval and mocked LLM behavior, but keep interfaces shaped so real retrieval and real model calls can be swapped in later. Add targeted orchestration tests and a small runnable demo path.
**Changes:** Added `src/orchestration/` with explicit enums/contracts, manifest and step configuration, `PipelineState`, state-machine helpers, append-only audit logging, direct/indexed/runtime retrieval adapters, bundle assembly, LLM agent execution scaffolding, validators, and concrete step handlers for STEP-01 through STEP-06. Added `src/orchestration/supervisor.py`, `src/orchestration/demo.py`, `src/orchestration/scenarios.py`, and `src/orchestration/mocks.py` for fixture-driven demo runs using mocked retrieval results and mocked agent outputs. Added `tests/orchestration/test_supervisor.py` covering the happy-path full run, the escalated security halt path, and the two demo scenarios. Updated `README.md` to document the new orchestration layer and the demo command, and updated `orchestration_layer_build_prompt.md` with completion check marks for the items now satisfied on this branch.
**Result:** The first-pass static Supervisor orchestration layer now runs end to end with deterministic step sequencing, gate evaluation, lane-specific retrieval routing, bundle assembly, mocked retrieval, mocked LLM agent execution, output validation, pipeline state mutation, and orchestration-owned audit logging. Two fixture-driven demo scenarios now run correctly: one completes through STEP-06 and one halts after STEP-02 with ESCALATED status. Verification completed with `uv run pytest tests/orchestration`, `PYTHONPATH=src uv run python -m orchestration.demo`, and `uv run pytest`, ending at 37 passed, 0 failed.
**Next:** Replace the mocked indexed retrieval backend and mocked LLM adapter with real implementations behind the same interfaces, and tighten step-level output validation as the agent contracts settle further.

### [#21] 2026-04-13 | Codex
**Task:** Update the preprocessing layer on `feature/preprocessing-layer` so it can read the new `scenario_1_mock_documents/` and `scenario_2_mock_documents/` layouts, while excluding the retired precedent document from the active scenario source sets.
**Plan:** Merge the latest `main` into the preprocessing branch to pick up the scenario folders, add scenario-aware source resolution helpers plus a scenario loader entrypoint, update preprocessing tests to cover both scenario source sets, and verify the preprocessing layer only before stopping.
**Changes:** Merged `main` into `feature/preprocessing-layer`, added `src/preprocessing/scenario_sources.py`, exposed the new helpers through `src/preprocessing/__init__.py`, and added `load_scenario_sources()` in `src/preprocessing/source_loader.py`. Updated `tests/conftest.py` and `tests/preprocessing/test_source_loader.py` to assert both scenario-specific active source sets, including the scenario-specific questionnaire and Slack filenames plus the procurement CSV fallback. Refreshed stale preprocessing test expectations to the current `SourceType` and `manifest_status` contract so the suite verifies cleanly after the merge.
**Result:** The preprocessing layer now resolves both scenario document folders into the active source set `[policy, dpa_matrix, procurement_matrix, questionnaire, slack]`, intentionally excluding the retired precedent document. Verification completed with `uv run pytest tests/preprocessing` and a direct probe of `resolve_scenario_source_paths()` / `load_scenario_sources()` for both scenarios, ending at 16 passed, 0 failed.
**Next:** Move to the chunking layer branch and add scenario-aware chunk output locations without changing the questionnaire exclusion rule.

### [#22] 2026-04-13 | Codex
**Task:** Adjust preprocessing so both scenarios prefer the CSV version of the DPA Legal Trigger Matrix and add preprocessing support for the stakeholder map in both scenario source sets.
**Plan:** Update the scenario source selection order for DPA to prefer `.csv`, add a new stakeholder-map source contract and JSON ingestor, route it through the preprocessing loader, expand scenario source ordering to include the stakeholder map, and verify with preprocessing-only tests and a direct scenario probe.
**Changes:** Updated `src/preprocessing/scenario_sources.py` so both `scenario_1` and `scenario_2` now select `DPA_Legal_Trigger_Matrix_v1_3.csv` before the XLSX fallback and include `Stakeholder_Map_PRQ_2024_0047.json` in the active source set. Added `SourceType.STAKEHOLDER_MAP` plus a new `SHM-001` source contract in `src/preprocessing/models.py` and `src/preprocessing/source_contract.py`. Added `src/preprocessing/stakeholder_ingestor.py` and routed it through `src/preprocessing/source_loader.py`. Expanded preprocessing tests to cover DPA CSV ingestion, stakeholder-map ingestion, and the revised scenario source ordering.
**Result:** Both scenarios now preprocess the DPA matrix from CSV and load the stakeholder map as a direct structured source. Verification completed with `uv run pytest tests/preprocessing` and a direct probe of `resolve_scenario_source_paths()` / `load_scenario_sources()` for both scenarios, ending at 19 passed, 0 failed.
**Next:** Keep downstream chunking/indexing work aligned to the new scenario source set, but continue excluding the questionnaire from chunking and embedding.

### [#23] 2026-04-13 | Codex
**Task:** Update the chunking layer on `feature/chunking-layer` so the two scenarios produce separate chunk artifact sets and the stakeholder map is chunked as part of the active scenario workflow.
**Plan:** Merge `feature/preprocessing-layer` into the chunking branch, add a scenario-aware chunking entrypoint and output-path helper, keep questionnaire chunking disabled, add structured-entry chunking for the stakeholder map, regenerate scenario chunk artifacts, and verify with chunking-only tests.
**Changes:** Merged `feature/preprocessing-layer` into `feature/chunking-layer`. Added `scenario_chunk_artifact_dir()` in `src/chunking/artifacts.py` and `build_scenario_chunk_artifacts()` in `src/chunking/pipeline.py`, with exports updated in `src/chunking/__init__.py`. Updated `src/chunking/chunker.py` so `STAKEHOLDER_MAP` sources now emit structured-entry record chunks covering summary metadata, role entries, approval entries, escalation routing entries, and vendor contact. Updated chunking tests to cover stakeholder-map chunking and scenario-specific output directories. Generated scenario chunk artifacts under `data/processed/scenario_1/chunks/` and `data/processed/scenario_2/chunks/`, each containing `ISP-001.json`, `DPA-TM-001.json`, `PAM-001.json`, `SLK-001.json`, and `SHM-001.json`.
**Result:** The chunking layer now writes separate scenario outputs, uses the active scenario source set, keeps the questionnaire excluded from chunk artifacts, and includes stakeholder-map chunks in both scenarios. Verification completed with `uv run pytest tests/chunking`, ending at 14 passed, 0 failed.
**Next:** Move to the embedding layer branch and make the embedding pipeline read the two scenario chunk directories separately while continuing to exclude direct-structured sources from embedding.

### [#24] 2026-04-13 | Codex
**Task:** Update the embedding layer on `feature/embedding-layer` so it can embed from the two scenario chunk directories separately while preserving the existing indexed-hybrid eligibility rules.
**Plan:** Merge `feature/chunking-layer` into the embedding branch, add scenario-aware embedding path helpers and entrypoints, keep direct-structured chunks non-embeddable, update embedding tests to use scenario chunk directories plus stakeholder-map skip behavior, and verify with embedding-focused indexing tests and a direct scenario probe.
**Changes:** Fast-forwarded `feature/embedding-layer` to include the chunking-branch scenario outputs. Added scenario-aware helpers in `src/indexing/pipeline.py` for scenario chunk dirs, scenario Chroma/vector-registry output dirs, and scenario-specific collection names, plus new entrypoints `build_and_persist_embeddings_for_scenario()` and `build_and_persist_embeddings_for_scenarios()`. Added `load_chunk_artifacts_from_dirs()` for multi-directory loading and exported the new helpers through `src/indexing/__init__.py`. Updated embedding tests so scenario chunk directories are the input source of truth, stakeholder-map chunks are explicitly loaded but rejected by `should_embed()`, and each scenario persists to its own collection/output location. Updated the README embedding command to use the scenario entrypoint.
**Result:** The embedding layer now supports separate scenario chunk directories and separate scenario embedding outputs, with 133 eligible embedded chunks per scenario. The stakeholder map is supported in the sense that the embedding pipeline loads it from the scenario chunk dirs without breaking, but it remains direct-structured and is therefore skipped from embedding. Verification completed with `uv run pytest tests/indexing/test_embeddings.py tests/indexing/test_indexing_pipeline.py` and a direct probe of `build_and_persist_embeddings_for_scenario()` using fake embeddings, ending at 11 passed, 0 failed.
**Next:** Move to the storage-indexing branch and make the vector-registry, BM25, structured-store, and index-registry outputs scenario-specific in the same way.

### [#25] 2026-04-13 | Codex
**Task:** Update the storage-indexing layer on `feature/storage-indexing` so it writes separate Step 8 outputs for `scenario_1` and `scenario_2`, using the scenario-specific chunk directories and direct-structured source files.
**Plan:** Merge `feature/embedding-layer` into the storage-indexing branch, add scenario-specific path helpers for BM25, structured stores, and index registries, generalize structured-store building so both the questionnaire and stakeholder map can be persisted as direct-structured stores, relax the registry builder so active scenario runs do not require the retired precedent source, add scenario wrapper entrypoints on top of `build_storage_indices()`, regenerate the real scenario outputs, and verify with the full indexing test suite.
**Changes:** Fast-forwarded `feature/storage-indexing` to include the embedding-branch scenario helpers. Updated `src/indexing/index_registry.py` with scenario-specific output path helpers and a new `SHM-001` direct-structured store definition `stakeholder_map_direct_access`. Updated `src/indexing/build_structured_store.py` so `build_structured_store()` now supports any direct-structured source and added `build_structured_stores()` for multi-source scenario builds. Updated `src/indexing/pipeline.py` so `build_storage_indices()` can optionally persist the stakeholder map alongside the questionnaire, and added `build_storage_indices_for_scenario()` / `build_storage_indices_for_scenarios()` to resolve scenario-specific input paths and write scenario-specific Chroma, vector-registry, BM25, structured-store, and index-registry outputs. Updated the indexing tests to cover both direct-structured stores, scenario-specific storage paths, and scenario-specific registry behavior. Generated real Step 8 outputs for both scenarios under `data/indexes/scenario_1/`, `data/indexes/scenario_2/`, `data/bm25/scenario_1/`, `data/bm25/scenario_2/`, `data/structured/scenario_1/`, and `data/structured/scenario_2/`.
**Result:** The storage-indexing layer now handles the two scenarios separately, uses the new scenario-specific chunk input paths, persists both direct-structured sources (`VQ-OC-001` and `SHM-001`), and emits scenario-specific index registries without requiring legacy precedent chunks. Real scenario builds completed successfully with per-scenario indexed counts `idx_security_policy=82`, `idx_dpa_matrix=27`, `idx_procurement_matrix=20`, and `idx_slack_notes=4`, plus `vq_direct_access.json` and `stakeholder_map_direct_access.json` for each scenario. Verification completed with `uv run pytest tests/indexing`, ending at 27 passed, 0 failed.
**Next:** Move to the index-registry follow-up only if further scenario-specific registry consumers need to be updated beyond the now-generated scenario registry files.

### [#26] 2026-04-13 | Codex
**Task:** Update `feature/index-registry` after merging `feature/storage-indexing`, making only the registry-branch changes still required for the scenario-specific Step 8 layout.
**Plan:** Merge `feature/storage-indexing` into the registry branch, inspect the registry code and tests for any remaining single-scenario assumptions, and keep the branch delta minimal if the merge already carries the required scenario-aware registry changes.
**Changes:** Fast-forwarded `feature/index-registry` to `feature/storage-indexing`, which already brought over the scenario-aware registry code, the new `SHM-001` direct-structured registry entry, and the scenario-specific registry output paths. The only additional branch-local change needed was fixing `tests/indexing/test_load_index_registry.py`, where a trailing import had landed at the bottom of the file instead of the import block during the merge history. No further registry code changes were required.
**Result:** The index-registry branch now reflects the scenario-specific registry model from storage/indexing with only a minimal test-file cleanup on top. Verification completed with `uv run pytest tests/indexing/test_index_registry.py tests/indexing/test_load_index_registry.py` and `uv run pytest tests/indexing`, ending at 27 passed, 0 failed.
**Next:** Continue only if a downstream retrieval or orchestration branch needs to be updated to read the scenario-specific registry files explicitly.

### [#27] 2026-04-13 | Codex
**Task:** Repair index-registry integrity issues on `feature/index-registry` so the generated scenario registries conform to the locked manifest and authority rules before demo use.
**Plan:** Fix the invalid source-contract metadata at the origin point, regenerate scenario chunk artifacts so indexed chunk metadata matches the contract, rebuild both scenario storage/index outputs with deterministic fake embeddings to avoid external model downloads, and verify both the generated registry JSON and the focused chunking/indexing tests.
**Changes:** Updated `src/preprocessing/source_contract.py` so `ISP-001`, `DPA-TM-001`, and `PAM-001` now use `manifest_status=CONFIRMED` instead of the invalid `PROVISIONAL`, and `SLK-001` now uses `authority_tier=3` instead of `4`. Updated chunking and indexing tests to assert the corrected manifest and authority values. Regenerated `data/processed/scenario_1/chunks/` and `data/processed/scenario_2/chunks/`, then rebuilt `data/indexes/scenario_1/` and `data/indexes/scenario_2/` so the vector registries and `index_registry.json` files picked up the corrected metadata. The rebuild used a deterministic 384-d fake embedder because the real embedding path attempted to resolve a Hugging Face model over restricted network access.
**Result:** Both scenario registries now report `CONFIRMED` for `ISP-001`, `DPA-TM-001`, and `PAM-001`, and `authority_tier=3` for `SLK-001`, matching the locked contract. Verification completed with `uv run pytest tests/chunking/test_chunker.py tests/indexing/test_embeddings.py tests/indexing/test_chroma_store.py tests/indexing/test_index_registry.py tests/indexing/test_load_index_registry.py`, ending at 19 passed, 0 failed, plus a direct JSON probe of both `data/indexes/scenario_1/index_registry.json` and `data/indexes/scenario_2/index_registry.json`.
**Next:** Keep any downstream retrieval or orchestration code reading these scenario registries against the corrected `CONFIRMED | PENDING` manifest model and Tier 1/2/3 authority scale only.

### [#28] 2026-04-13 | Claude Code
**Task:** Fix content integrity issues across chunking, indexing, and orchestration layers on a new `fix/integrity` branch off main.
**Plan:** Address four identified issues: (1) remove retired `PROVISIONAL` manifest status from the codebase, (2) confirm Slack authority tier is already tier 3, (3) switch ISP chunking to level-1 only for larger functional chunks, (4) move DPA and PAM from `INDEXED_HYBRID` to `DIRECT_STRUCTURED` lane throughout the full stack.
**Changes:**
- `src/preprocessing/models.py`: Removed `PROVISIONAL` from `ManifestStatus` enum.
- `src/retrieval/authority_reranker.py`: Removed `PROVISIONAL` weight from `MANIFEST_STATUS_WEIGHTS`; removed unused tier 4 from `AUTHORITY_WEIGHTS` and `tier_four_cap` logic.
- `src/preprocessing/text_utils.py`: `split_policy_sections` now filters to level-1 section boundaries only (no dot-separated subsections), producing large functional chunks per top-level section rather than many tiny subsection fragments.
- `src/preprocessing/source_contract.py`: `DPA-TM-001` and `PAM-001` changed to `RetrievalLane.DIRECT_STRUCTURED`.
- `src/preprocessing/matrix_ingestor.py`: Added `"rows"` list to `structured_data` so matrix sources carry full row data for direct field access.
- `src/chunking/chunker.py`: Added early return of `[]` for `DIRECT_STRUCTURED` matrix sources; imported `RetrievalLane`.
- `src/indexing/index_registry.py`: `DPA-TM-001` and `PAM-001` moved to `structured_direct` storage kind with new logical store names `dpa_matrix_direct` and `procurement_matrix_direct`.
- `src/orchestration/retrieval/direct_structured.py`: Rewritten to support multiple sources keyed by `source_id`; `read_fields` and `get_first` now take `source_id` as first parameter.
- `src/orchestration/retrieval/router.py`: Passes `request.source_id` to `direct_accessor.read_fields`.
- `src/orchestration/supervisor.py`: Added `_load_additional_direct_sources` helper to auto-load DPA and PAM structured data from mock_documents; updated `DirectStructuredAccessor` init with `additional_sources`.
- `src/orchestration/steps/step03_legal.py`: DPA retrieval changed to `DIRECT_STRUCTURED` lane with `field_map={"rows": ("rows",)}`.
- `src/orchestration/steps/step04_procurement.py`: Both PAM retrieval requests changed to `DIRECT_STRUCTURED` with `field_map={"rows": ("rows",)}`.
- `src/orchestration/scenarios.py`: ISP chunk IDs updated to level-1 (`section_12`, `section_17`); DPA and PAM entries removed from `indexed_results`; agent output citations updated.
- Test files updated: `tests/chunking/test_chunker.py`, `tests/chunking/test_pipeline.py`, `tests/chunking/test_artifacts.py`, `tests/preprocessing/test_matrix_ingestor.py`, `tests/indexing/test_index_registry.py`, `tests/indexing/test_indexing_pipeline.py`, `tests/indexing/test_load_index_registry.py`.
**Result:** All 68 tests pass on `fix/integrity`. Slack tier was already corrected to 3 in a prior session (confirmed clean). The full integrity fix is complete.
**Next:** Review and merge `fix/integrity` into main via PR if checks pass.

### [#29] 2026-04-13 | Claude Code
**Task:** Implement missing runtime data contracts on `feature/supervisor-orchestration-v2`.
**Plan:** Create `EscalationPayload`, `RetrievedChunk`, `ContextBundle`, and step determination dataclasses; update `StepExecutionResult.escalation_payload` type; update step02/03/04 handlers and `audit_logger.log_escalation`; export all new models; write tests.
**Changes:**
- `src/orchestration/models/escalation.py`: New `EscalationPayload` dataclass with `evidence_condition`, `resolution_owner`, `additional_context`, and `to_dict()`.
- `src/orchestration/models/retrieved_chunk.py`: New `RetrievedChunk` dataclass with source metadata, `chunk_id`, `authority_tier`, `retrieval_lane`, `is_primary_citable`, `text`, `citation_label`, `extra_metadata`, and `to_dict()`.
- `src/orchestration/models/context_bundle.py`: New `ContextBundle` dataclass with `step_id`, `admitted_evidence`, `excluded_evidence`, `structured_fields`, `source_provenance`, `admissibility_status`, and `to_dict()`; plus `ExcludedChunk` helper.
- `src/orchestration/models/determinations.py`: New step determination dataclasses `Step01IntakeDetermination` through `Step06CheckoffDetermination` derived from `REQUIRED_OUTPUT_FIELDS` and scenario output shapes; plus `PolicyCitation`.
- `src/orchestration/models/contracts.py`: `StepExecutionResult.escalation_payload` changed from `dict[str, Any] | None` to `EscalationPayload | None`.
- `src/orchestration/steps/step02_security.py`: Constructs `EscalationPayload` object instead of plain dict.
- `src/orchestration/steps/step03_legal.py`: Same.
- `src/orchestration/steps/step04_procurement.py`: Same.
- `src/orchestration/audit/audit_logger.py`: `log_escalation` now accepts `EscalationPayload` and calls `.to_dict()` before spreading.
- `src/orchestration/models/__init__.py`: Exports all new models via `__all__`.
- `tests/orchestration/test_runtime_contracts.py`: 24 new tests covering all new dataclasses, type contracts, and audit logger integration.
**Result:** All 92 tests pass (68 pre-existing + 24 new). No regressions.
**Next:** Wire `ContextBundle` and determination dataclasses into the bundle assembler and agent runner as the agent contracts solidify.
