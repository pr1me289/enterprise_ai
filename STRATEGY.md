# Enterprise AI Demo — Chunking, Embedding, Storage, and Hybrid Agentic Retrieval Strategy

This strategy aligns with the architecture already locked in the project materials: most sources go into an indexed hybrid retrieval lane, the questionnaire remains in a direct structured lane, and checklist/audit state stays outside retrieval entirely. The purpose of this system is not merely to "chunk then embed," but to perform **source-governed preprocessing + lane-specific retrieval preparation + agent-planned retrieval later**.

---

## 1. Core Mental Model

The pipeline is:

1. **Take source document**
2. **Chunk it** into meaningful evidence units
3. **Attach metadata** to each chunk
4. **Embed the chunks** if that source belongs in the indexed semantic lane
5. **Store/index them** for retrieval
6. Later, when an agent needs context, the system retrieves the relevant chunks and builds a context bundle

So:

* **chunking = defining the evidence units**
* **embedding = representing those units for semantic retrieval**
* **retrieval = pulling the right units later**
* **context bundle assembly = feeding selected evidence to the agent**

The most important framing for this demo is:

> The interesting part is not embedding by itself.
> The interesting part is **governed evidence delivery**.

That is what makes this an enterprise-context demo rather than a generic vector-search demo.

---

## 2. What We Are Actually Building

This system should be built as a **Python-based ingestion, indexing, retrieval, and orchestration pipeline**.

The build has two major layers:

### Layer A — Governed Retrieval Infrastructure

This includes:

* source ingestion
* chunking
* metadata attachment
* embedding
* storage/indexing
* lane definitions

### Layer B — Agentic Retrieval Behavior

This includes:

* task decomposition
* source-specific query planning
* retrieval routing
* hybrid search
* authority-aware reranking
* context bundle assembly

Hybrid search is just the engine.
Hybrid **agentic** retrieval is the planner + router + judge + assembler. This matches the design choice that the Supervisor Agent decomposes a domain task into source-specific subqueries rather than doing one naive broad search.

---

## 3. Source Treatment and Retrieval Lanes

The source treatment is already locked and should remain fixed:

### Indexed hybrid lane

These sources are chunked, metadata-tagged, embedded, and indexed:

* IT Security Policy v4.2
* DPA Legal Trigger Matrix
* Procurement Approval Matrix
* Prior Vendor Decisions / Precedent Log
* Slack / Meeting Thread Notes

### Direct structured lane

These sources are not embedded and are accessed directly by field:

* OptiChain Vendor Questionnaire JSON

### Non-retrieval state lane

These are runtime outputs and should never be embedded or indexed:

* checklist state
* audit state
* pipeline state objects

This is the correct compromise for the demo because it keeps implementation lightweight while preserving the important architectural distinction that operational intake data should not be semantically retrieved.

---

## 4. Preprocessing Layer

Before retrieval exists, each source must be normalized into an internal representation that the system can work with.

This should be built as a small Python ingestion layer with source-specific functions, for example:

* `ingest_policy()`
* `ingest_matrix()`
* `ingest_questionnaire()`
* `ingest_precedent_log()`
* `ingest_slack_threads()`

Each ingestion function outputs either:

* a list of chunk objects, or
* one structured object if the source belongs in the direct structured lane

The goal is not to treat every source identically. The goal is to convert each source into **retrieval-ready evidence units** in a way that preserves its enterprise meaning.

### Suggested Python tooling

* `pathlib` for file handling
* `json` / `csv`
* `pandas` for structured inputs where helpful
* markdown/text parsing via custom functions
* `python-docx` only when direct DOCX parsing is required

---

## 5. Chunking Strategy

Chunking should be **document-type aware**, not token-count aware.

The chunking plan is already effectively locked:

* policy → **section-boundary chunking**
* DPA matrix → **row-level chunking**
* procurement matrix → **row-level chunking**
* questionnaire → **no chunking**
* precedents → **record-level chunking**
* Slack notes → **thread-level chunking**

This is important because the demo is built around preserving natural evidence units rather than splitting arbitrarily.

### Per-source chunking behavior

#### IT Security Policy

Split on numbered headings or clause boundaries such as:

* `1.`
* `1.1`
* `§4.2`
* `12.2.1`

Each policy section becomes one chunk.

#### DPA Legal Trigger Matrix

Each row becomes one chunk.
Even though the matrix is embedded for simplicity, row atomicity must be preserved so the condition-to-outcome logic remains intact.

#### Procurement Approval Matrix

Each row becomes one chunk for the same reason.

#### Questionnaire

No chunking.
This should be loaded as a structured JSON object keyed by fields.

#### Prior Vendor Decisions / Precedent Log

Each precedent case becomes one chunk.

#### Slack / Meeting Thread Notes

Each thread becomes one chunk, not each individual message.

This preserves conversational coherence and avoids over-fragmenting weak evidence.

---

## 6. Metadata Strategy

Every chunk should carry metadata that allows:

* retrieval filtering
* source-aware reranking
* citation construction
* freshness handling
* audit logging
* permission enforcement

### Recommended chunk metadata fields

Each chunk should include:

* `chunk_id`
* `source_id`
* `source_name`
* `source_type`
* `authority_tier`
* `retrieval_lane`
* `version`
* `section_id` or `row_id` or `thread_id`
* `document_date`
* `allowed_agents`
* `is_primary_citable`
* `freshness_status`
* `text`

### Important clarification on `allowed_agents`

`allowed_agents` should **not** be treated as independently assigned chunk-level permissions.

The Context Contract governs permissions at the **source level**, not the chunk level. So if `ISP-001` is restricted to `["it_security", "supervisor"]`, then every chunk derived from `ISP-001` carries the same `allowed_agents` value. In implementation, this is acceptable as a **denormalized field for query-time filtering**, but it must be treated as **derived metadata from the source manifest**, not as a separate permissions layer. Otherwise chunk-level and source-level permissions can drift.

So the rule is:

> `allowed_agents` on each chunk exists for convenience and query-time filtering, but it is inherited from source-level permissions defined by the Context Contract and source manifest.

### Example chunk object

```json
{
  "chunk_id": "ISP-001__sec_12_2_1",
  "source_id": "ISP-001",
  "source_name": "IT Security Policy v4.2",
  "source_type": "policy",
  "authority_tier": 1,
  "retrieval_lane": "indexed_hybrid",
  "version": "4.2",
  "section_id": "12.2.1",
  "allowed_agents": ["it_security", "supervisor"],
  "is_primary_citable": true,
  "freshness_status": "PROVISIONAL",
  "text": "Vendors processing regulated employee data must..."
}
```

This fits the Context Contract model: sources have authority tiers, versions, permissions, and admissibility rules, and retrieval must respect those constraints.

---

## 7. Embedding Plan

Only embed chunks that belong in the indexed semantic lane.

### Embed these sources

* policy documents
* legal trigger matrix
* procurement approval matrix
* prior vendor precedents
* Slack / meeting notes

### Do not embed

* questionnaire JSON
* checklist state objects
* deterministic output objects
* audit state

### Embedding model

Use:

* `sentence-transformers/all-MiniLM-L6-v2`

This is sufficient because:

* it is lightweight
* local
* fast
* cheap
* good enough for a portfolio demo

The goal of this project is not to maximize retrieval benchmark performance. The goal is to demonstrate correct enterprise retrieval architecture.

---

## 8. Storage and Indexing

The implementation should commit to **Chroma** for the vector store. The strategy has already effectively locked Chroma, so this should no longer remain an open implementation question.

### Final storage decision

Use:

* **Chroma** for dense vector storage
* **BM25** for lexical retrieval
* **JSON/dict or SQLite** for direct structured questionnaire access
* runtime Python objects for checklist/audit/pipeline state

### Recommended indexing model

Use:

* one Chroma vector store backend
* one BM25 backend
* metadata-based filtering by source, authority tier, permissions, and source type

This is the right compromise because:

* it is simpler to build than truly separate backends per source
* it still preserves source-aware retrieval behavior
* it still supports permissions and authority-aware reranking
* it keeps the system easy to explain in a portfolio demo

### BM25 implementation

Use:

* `rank_bm25`

This matters because BM25 helps recover:

* exact clause references
* row labels
* acronyms
* exact legal/security terms like `DPA`, `NDA`, `ERP`

### Structured storage for questionnaire

The questionnaire should remain outside Chroma and outside BM25.
It should be stored as a directly addressable structured object, either:

* plain JSON loaded into memory
* a Python dict
* or a tiny SQLite table if desired

---

## 9. How Retrieval Will Work Later

The retrieval system should not be one broad top-k vector search over everything.

Instead, retrieval should be:

* task-aware
* source-aware
* lane-aware
* authority-aware
* permission-aware

The design intent is that the Supervisor Agent decomposes a domain task into source-specific subqueries, routes them to the correct retrieval lane, gathers evidence, reranks it according to governance rules, and assembles a context bundle.

This is what makes the retrieval system **hybrid agentic retrieval** instead of just hybrid search.

---

## 10. Hybrid Agentic Retrieval

Hybrid agentic retrieval should be understood as having two interacting components:

### Hybrid retrieval engine

This combines:

* dense vector retrieval
* BM25 lexical retrieval
* direct structured field lookup

### Agentic retrieval planner

This decides:

* what the actual question is
* which subqueries need to be issued
* which sources should be consulted
* which retrieval lane each query belongs in
* what evidence should be suppressed
* how the final bundle should be assembled

The recommendation is:

> Do not let each domain agent freely search every source on its own.

Instead:

* the **Supervisor / retrieval planner** performs query planning and source routing
* the **retrieval engine** executes the searches and structured lookups
* the **domain agent** receives the already-curated evidence bundle and reasons over it

This keeps the system more auditable, more governed, easier to explain, and more credible as an enterprise architecture demo.

---

## 11. Retrieval Flow

### Step A — Supervisor receives a task

Examples:

* determine whether OptiChain requires a DPA
* determine the vendor approval path
* determine whether ERP ambiguity requires escalation

### Step B — Supervisor decomposes the task into subqueries

Instead of issuing one vague query like "What should we do about OptiChain?", the Supervisor creates targeted subqueries such as:

* read questionnaire fields about EU personal data
* retrieve DPA matrix rows relevant to employee data handling
* retrieve policy clauses related to regulated data
* retrieve precedent cases with similar ambiguity
* retrieve Slack notes only if formal sources leave unresolved ambiguity

### Step C — Route each subquery to the correct lane

* questionnaire facts → direct structured access
* policy clause search → BM25 + dense vector retrieval
* matrix row retrieval → BM25 + dense vector retrieval
* precedents → semantic retrieval plus optional metadata filtering
* Slack notes → semantic/BM25 retrieval, treated as low-authority supplemental evidence

### Step D — Aggregate results

The system gathers candidate evidence from multiple sources and lanes.

### Step E — Rerank according to governance

The reranker should not simply return "most semantically similar." It should rank by:

* relevance
* source authority
* source admissibility
* permission compliance
* freshness status
* citation usefulness

Low-authority evidence should be score-capped or suppressed when higher-tier evidence addresses the same point.

### Step F — Assemble a context bundle

The bundle order should remain:

1. questionnaire facts
2. top policy/matrix evidence
3. relevant precedents
4. supplemental notes if needed

### Step G — Send the bundle to the domain agent

* IT Security Agent receives its scoped bundle and returns a structured determination
* Legal Agent receives its scoped bundle and returns a structured determination
* Procurement Agent receives its scoped bundle and returns a structured determination
* Checklist assembler combines these into pipeline state/output

---

## 12. Why This Is Better Than Letting Agents Search Freely

Although the system is "agentic," it is better in v1 not to let every domain agent search the full data estate independently. That would make permissions harder to reason about, auditability weaker, authority conflicts less transparent, and repo architecture less legible.

Instead, the architecture should make the Supervisor Agent the retrieval planner and make domain agents downstream consumers of curated evidence bundles.

This allows the demo to clearly show:

* governed access
* source routing
* authority-aware evidence selection
* controlled bundle construction

---

## 13. Recommended Python Tooling

| Purpose | Tool |
|---|---|
| Core language | Python |
| File handling | `pathlib` |
| Structured data | `json`, `csv`, `pandas` |
| DOCX parsing | `python-docx` (only where needed) |
| Embeddings | `sentence-transformers` / `all-MiniLM-L6-v2` |
| Vector store | Chroma |
| Lexical retrieval | `rank_bm25` |
| Structured access | JSON / Python dict / optional SQLite |
| Orchestration | Plain Python state machine (not LangGraph) |

---

## 14. Recommended Repo / Module Layout

```text
ingest/
  policy_ingestor.py
  matrix_ingestor.py
  questionnaire_ingestor.py
  precedent_ingestor.py
  slack_ingestor.py

chunking/
  chunk_policy.py
  chunk_matrix.py
  chunk_precedent.py
  chunk_thread.py

indexing/
  embed_chunks.py
  build_vector_index.py
  build_bm25_index.py
  build_structured_store.py

retrieval/
  query_planner.py
  source_router.py
  hybrid_search.py
  authority_reranker.py
  bundle_assembler.py
  retrieval_manifest.py

orchestration/
  supervisor.py
  pipeline_state.py
  audit_logger.py
  it_security_agent.py
  legal_agent.py
  procurement_agent.py
  checklist_assembler.py
```

Do **not** use a single `domain_agents.py` file. Even at demo scale, splitting agents into separate files keeps the repo legible and makes agent boundaries easier for a reviewer to understand.

---

## 15. Final Architectural Framing

The system should be described as follows:

* chunking defines the evidence units
* metadata governs admissibility and filtering
* embeddings support the indexed semantic lane
* BM25 supports exact/legal/identifier retrieval
* structured access handles operational intake cleanly
* the Supervisor plans retrieval
* retrieval executes across the right lane for each source
* reranking applies authority, freshness, and permissions
* context bundles give agents scoped evidence rather than raw corpora

The main weakness to avoid is making the project look like:

> "we built a vector database and called it enterprise AI."

What it is actually demonstrating is:

> Here is how an enterprise converts heterogeneous source material into governed evidence units, routes them through the correct retrieval lane, and delivers scoped context bundles to agents in a way that preserves authority, permissions, and auditability.

That is the real value of the architecture.
