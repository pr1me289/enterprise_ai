Give CODEX these implementation instructions for **Step 8 — Storage and Indexing**.

## Goal of this step

Build the indexed semantic lane so the system can search chunked evidence through:

* **Chroma** for dense vector retrieval
* **BM25** for exact / lexical retrieval
* **metadata filtering** for governance-aware narrowing

The questionnaire stays outside both systems as direct structured access. Checklist state, audit state, and runtime pipeline objects are never indexed.

## What each backend is used for

### 1) Chroma vector store

Use Chroma for **semantic retrieval**.

This is what helps the system find chunks that are conceptually similar even when the wording differs. It is especially useful for:

* policy clauses phrased differently than the query
* precedent cases that are semantically similar
* Slack threads that use informal language
* matrix rows that match the scenario conceptually, not only by exact term match

### 2) BM25 backend

Use BM25 for **lexical / exact-match retrieval**.

This is what helps recover:

* exact clause references like `§12.2.1`
* row labels
* acronyms like `DPA`, `ERP`, `NDA`, `SSO`
* exact policy / legal / security terms that dense retrieval may miss

### 3) Why both exist

Hybrid retrieval is the point. Dense search catches meaning; BM25 catches exact identifiers and language. The architecture explicitly selected **hybrid agentic retrieval**, not naive top-k vector search.

---

## Important architecture decision to follow

There is a slight framing difference across your docs:

* the strategy says **one Chroma backend + one BM25 backend**, with metadata-based filtering by source, authority tier, permissions, and source type
* the design doc says **per-source indices**, because access control should be enforced at query time, not only after retrieval

Tell CODEX to reconcile those like this:

> Implement **one storage technology per backend**, but expose it as **per-source logical indices**.

That means:

* one Chroma client / persistence directory overall
* one BM25 subsystem overall
* but **separate collections / index objects per source**
* plus shared retrieval wrappers on top

This preserves the simplicity of “one backend” while honoring the design doc’s “per-source indices” access-control posture.
In other words,
Stick with the Design Doc — per-source Chroma collections — and reread the strategy's "one Chroma backend" as meaning one Chroma client instance, not one collection. In implementation terms this is almost no extra work: you're calling chroma_client.get_or_create_collection("idx_security_policy") five times instead of once. The overhead is trivial. What you gain is that your collection names map directly to the index endpoint names in CC §6.1, the access boundaries are structural rather than filter-dependent, and the demo narrative is cleaner — you can show the Supervisor routing a subquery to idx_dpa_matrix and make it visually obvious that the IT Security Agent never touches that collection.
The one Chroma backend + BM25 backend is still correct — those are the two retrieval engines. The per-source organization is just how the collections within Chroma are arranged.
---

## Final storage/indexing design to implement

Implement these logical indices:

### Chroma collections

* `idx_security_policy`
* `idx_dpa_matrix`
* `idx_procurement_matrix`
* `idx_precedents`
* `idx_slack_notes`

### BM25 indices

* `idx_security_policy`
* `idx_dpa_matrix`
* `idx_procurement_matrix`
* `idx_precedents`
* `idx_slack_notes`

### Structured lane

* `vq_direct_access` as plain JSON / Python dict / optional SQLite
* not embedded
* not added to Chroma
* not added to BM25

### Never index

* checklist state
* audit log
* pipeline state objects

---

## Source-to-index mapping

CODEX should hard-wire the source mapping from the contract:

* **ISP-001** → `idx_security_policy`
* **DPA-TM-001** → `idx_dpa_matrix`
* **PAM-001** → `idx_procurement_matrix`
* **PVD-001** → `idx_precedents`
* **SLK-001** → `idx_slack_notes`
* **VQ-OC-001** → `vq_direct_access` only

Do not let retrieval choose a different lane than the contract says. The contract explicitly says each source has a designated lane and agents may not retrieve it through another lane.

---

## Metadata schema to persist on every indexed chunk

Persist this metadata on every Chroma record and mirror it in the BM25 document registry:

* `chunk_id`
* `source_id`
* `source_name`
* `source_type`
* `authority_tier`
* `retrieval_lane`
* `version`
* `document_date`
* `freshness_status`
* `allowed_agents`
* `is_primary_citable`
* `section_id` or `row_id` or `thread_id`
* `text`

This exact metadata shape is already aligned with your chunking strategy. `allowed_agents` is denormalized for query-time filtering, but it must be treated as inherited from the source manifest and Context Contract, not invented per chunk.

---

## How metadata-based filtering should work

### Rule 1: source-level access is primary

Filtering is not just for convenience. It is part of governance.

The Design Doc says access control must be enforced **before or during retrieval**, not only after generation. The Context Contract also says unauthorized index queries must fail closed and be logged.

### Rule 2: allowed_agents is inherited

Every chunk from a source inherits the same `allowed_agents` set. That field exists on chunks only to support filtering at query time.

### Rule 3: metadata filtering happens before reranking

Use metadata filters to narrow the candidate set first. Then do hybrid search. Then rerank by authority/freshness. Do not retrieve broadly and “clean it up later.”

---

## What each metadata filter should do

### 1) Filter by `source_id`

Use when the planner already knows the exact source. Example: search only `PAM-001` for procurement path logic.

Implementation:

* in Chroma: query only the mapped collection, or apply `where={"source_id": "PAM-001"}`
* in BM25: run search only over the document list for that source collection

### 2) Filter by `source_type`

Use to narrow within broader reusable code if needed, especially if later you collapse some sources into a shared index.

Expected values:

* `policy`
* `matrix`
* `questionnaire`
* `precedent`
* `slack_thread`

Implementation:

* Chroma `where={"source_type": "policy"}`
* BM25 prefilter document registry on `source_type == "policy"`

### 3) Filter by `authority_tier`

Use this mostly as a retrieval narrowing aid and rerank input, not as the sole mechanism of governance.

Expected tiers:

* Tier 1 = formal governing sources
* Tier 2 = questionnaire
* Tier 3 = precedents
* Tier 4 = Slack / meeting notes

Typical usage:

* when a task needs only authoritative evidence, search Tier 1 first
* only search Tier 4 if formal sources leave unresolved ambiguity
* never let Tier 4 become a primary citation
* suppress Tier 4 if it conflicts with Tier 1–3

### 4) Filter by `allowed_agents`

Use this to enforce which agent may query which source endpoint.

Example:

* Legal can query `idx_dpa_matrix`
* Procurement can query `idx_slack_notes`
* Checkoff Agent cannot query any index endpoint independently

Implementation:

* before query: verify endpoint permission
* at query time: additionally filter candidate docs where agent name is in `allowed_agents`
* if unauthorized: fail closed, return no results, write audit event

This should be enforced in both the source router and the retrieval engine.

### 5) Filter by domain tag for precedents

The Context Contract says precedents are domain-scoped at access time. So PVD chunks should also carry something like:

* `domain_scope = "security" | "legal" | "procurement"`

Then:

* Security Agent sees only security precedents
* Legal only legal precedents
* Procurement only procurement precedents

### 6) Filter by freshness / provisional state

Use `freshness_status` or `manifest_status`-derived metadata so provisional sources remain queryable when allowed, but the result set carries that status into downstream bundle assembly. Unverified versioned sources may be usable only as PROVISIONAL and require confirmation before COMPLETE.

---

## Concrete implementation shape

Tell CODEX to build these modules under `indexing/` and `retrieval/`:

```text
indexing/
  build_vector_index.py
  build_bm25_index.py
  build_structured_store.py
  index_registry.py
  metadata_schema.py

retrieval/
  source_router.py
  permission_guard.py
  hybrid_search.py
  authority_reranker.py
  retrieval_manifest.py
```

This is consistent with the repo structure already recommended in the strategy.

---

## How to implement Chroma

### Chroma persistence model

Use one persistent Chroma client, for example:

* `PersistentClient(path="data/chroma")`

Create one collection per source endpoint:

* `idx_security_policy`
* `idx_dpa_matrix`
* `idx_procurement_matrix`
* `idx_precedents`
* `idx_slack_notes`

Each record added should include:

* `id = chunk_id`
* `documents = [chunk_text]`
* `embeddings = [vector]`
* `metadatas = [metadata_dict]`

### Chroma collection wrapper

Build a thin wrapper class like:

```python
class VectorIndex:
    def add_chunks(self, collection_name, records): ...
    def query(self, collection_name, query_text, k, where=None): ...
    def get_by_ids(self, collection_name, ids): ...
```

This keeps Chroma isolated from the rest of the app.

### Chroma filtering

Use Chroma `where` filters for:

* `source_id`
* `source_type`
* `authority_tier`
* `freshness_status`

For `allowed_agents`, Chroma metadata array filtering can be awkward depending on representation, so there are two good options:

#### Option A — store `allowed_agents` as a pipe-delimited string

Example:

* `"allowed_agents_str": "|legal|procurement|"`

Then prefilter in Python after candidate retrieval.

#### Option B — do permission filtering before query

Since you already have per-source collections and endpoint permissions, a lot of the access control can happen before query. Then `allowed_agents` remains mainly a safety-check and audit field.

For this project, I would tell CODEX to do both:

* enforce endpoint permissions before query
* also preserve `allowed_agents` in metadata for traceability and fallback filtering

---

## How to implement BM25

Use `rank_bm25`. That is already the recommended lexical backend.

### BM25 storage model

BM25 does not need a database. For this demo, persist BM25 as:

* one serialized document registry per source index
* one tokenized corpus per source index
* one `BM25Okapi` object rebuilt at init or lazily loaded

Suggested persisted files:

```text
data/bm25/
  idx_security_policy.pkl
  idx_dpa_matrix.pkl
  idx_procurement_matrix.pkl
  idx_precedents.pkl
  idx_slack_notes.pkl
```

Each BM25 source bundle should store:

* `docs`: list of raw texts
* `doc_ids`: list of `chunk_id`
* `metadata_by_id`: dict from `chunk_id` to metadata
* `tokenized_docs`: pre-tokenized corpus

### BM25 tokenizer

Keep it simple and deterministic:

* lowercase
* preserve section IDs / acronyms where useful
* split mostly on whitespace + punctuation
* do not over-normalize away identifiers like `12.2.1`, `DPA`, `ERP`

BM25’s value here is exactness, so do not destroy exact terms during preprocessing.

### BM25 wrapper

Build something like:

```python
class BM25Index:
    def build(self, collection_name, chunk_records): ...
    def query(self, collection_name, query_text, k, metadata_filter=None): ...
```

### BM25 filtering

Because BM25 libraries do not natively do metadata filters like a vector DB, implement filtering like this:

1. load all docs for the collection
2. apply metadata filter to candidate docs first
3. score only the filtered docs
4. return top-k chunk IDs + scores

This is important. Do not BM25-score the entire corpus and only then discard unauthorized results.

---

## Recommended indexing pipeline

Tell CODEX to make the index build deterministic:

### Step 1

Load finalized chunk artifacts from Step 6/7.

### Step 2

Partition chunks by source endpoint.

### Step 3

For each source endpoint:

* write records into the matching Chroma collection
* build the matching BM25 index
* store metadata mirror / registry locally

### Step 4

Write an `index_registry.json` that records:

* collection names
* source IDs
* versions
* chunk counts
* build timestamp
* embedding model
* manifest status / freshness info

This registry will help with debugability and portfolio explainability.

---

## Retrieval flow CODEX should prepare for

The strategy says retrieval later should be:

* task-aware
* source-aware
* lane-aware
* authority-aware
* permission-aware

So Step 8 should be implemented with that future flow in mind.

### Intended flow

1. Supervisor / planner chooses the relevant source endpoint
2. Permission guard validates agent access
3. Hybrid search runs on that endpoint:

    * vector search in Chroma
    * lexical search in BM25
4. Results are fused
5. Authority / freshness reranking is applied
6. Bundle assembler suppresses or caps low-authority evidence when needed
7. Domain agent receives the curated bundle

---

## Hybrid search design CODEX should target

Tell him to structure retrieval so both backends return a common result shape:

```python
{
  "chunk_id": "...",
  "text": "...",
  "source_id": "...",
  "source_type": "...",
  "authority_tier": 1,
  "freshness_status": "CONFIRMED",
  "allowed_agents": ["legal"],
  "backend": "vector" | "bm25",
  "score": 0.0
}
```

Then a fusion layer can merge by `chunk_id`.

### Fusion recommendation

Use a simple weighted reciprocal rank fusion or normalized-score merge for v1.

A clean v1 approach:

* take top `k_vector`
* take top `k_bm25`
* merge by `chunk_id`
* sum weighted normalized scores
* pass merged candidates into reranker

No need to overengineer the math yet.

---

## Authority and governance behavior to preserve

CODEX should not let storage/indexing become “just searchable blobs.”

The contract requires these behaviors later, so the index design must support them:

* Tier 4 Slack is low-authority supplemental only
* Tier 4 conflicting with Tier 1–3 should be suppressed
* Tier 3 precedent cannot override Tier 1 or Tier 2
* Tier 1 vs Tier 1 conflict is not auto-suppressed; both remain and the determination escalates
* unauthorized retrieval attempts fail closed and are logged

That means the metadata and result objects need to preserve:

* source identity
* authority tier
* version / freshness
* permission scope

---

## Specific design suggestions for this repo

### 1) Keep index definitions explicit

Create a central `index_registry.py` that declares:

```python
INDEX_CONFIG = {
  "idx_security_policy": {
    "source_id": "ISP-001",
    "source_type": "policy",
    "backend": ["vector", "bm25"],
    "allowed_agents": ["it_security", "legal", "procurement"],
  },
  ...
}
```

This keeps the mapping explainable and avoids scattering rules across files.

### 2) Add a retrieval manifest object

Each retrieval call should produce a manifest entry like:

* who queried
* which endpoint
* what filters were applied
* which chunks were returned
* which chunks were suppressed and why

That will matter later for auditability and for showing enterprise-grade design. The architecture repeatedly emphasizes append-only auditability and reconstructable retrieval.

### 3) Keep source collections separate

Even if Chroma technically could hold everything in one collection, do not do that for this demo. Separate collections make permissions and source-specific debugging much clearer, and they align better with the design doc.

### 4) Preserve row / section / thread atomicity

Do not modify chunk boundaries at indexing time. Storage/indexing must preserve the chunk units defined earlier:

* policy section
* matrix row
* precedent record
* Slack thread

### 5) Include chunk text in both systems’ registries

Even if Chroma stores documents, keep a local metadata/text registry as the source of truth for bundle assembly and citation generation.

---

## Pseudocode for CODEX

```python
# build_vector_index.py
def build_vector_indices(chunk_records, chroma_client, index_config):
    grouped = group_by_index_name(chunk_records, index_config)

    for index_name, records in grouped.items():
        collection = chroma_client.get_or_create_collection(index_name)
        collection.upsert(
            ids=[r["chunk_id"] for r in records],
            documents=[r["text"] for r in records],
            embeddings=[r["embedding"] for r in records],
            metadatas=[r["metadata"] for r in records],
        )

# build_bm25_index.py
def build_bm25_indices(chunk_records, index_config, output_dir):
    grouped = group_by_index_name(chunk_records, index_config)

    for index_name, records in grouped.items():
        docs = [r["text"] for r in records]
        doc_ids = [r["chunk_id"] for r in records]
        metadata_by_id = {r["chunk_id"]: r["metadata"] for r in records}
        tokenized_docs = [tokenize(text) for text in docs]

        bm25 = BM25Okapi(tokenized_docs)
        save_pickle(
            output_dir / f"{index_name}.pkl",
            {
                "bm25": bm25,
                "docs": docs,
                "doc_ids": doc_ids,
                "metadata_by_id": metadata_by_id,
                "tokenized_docs": tokenized_docs,
            },
        )
```

```python
# permission_guard.py
def assert_endpoint_access(agent_name: str, index_name: str, access_matrix: dict):
    if agent_name not in access_matrix.get(index_name, []):
        raise UnauthorizedRetrieval(index_name, agent_name)
```

```python
# hybrid_search.py
def hybrid_search(agent_name, index_name, query_text, filters, k=5):
    assert_endpoint_access(agent_name, index_name, ACCESS_MATRIX)

    vector_hits = vector_index.query(index_name, query_text, k=k, where=filters)
    bm25_hits = bm25_index.query(index_name, query_text, k=k, metadata_filter=filters)

    merged = reciprocal_rank_fusion(vector_hits, bm25_hits)
    reranked = authority_rerank(merged)

    return reranked
```

---

## Final guidance to give CODEX

Tell him this step should produce a retrieval layer that is:

* easy to explain
* source-aware
* permission-aware
* deterministic
* auditable

The failure mode to avoid is building “a big searchable corpus.” The right outcome is a **governed set of per-source indices behind shared Chroma and BM25 backends**, with metadata strong enough to support permissions, authority rules, freshness handling, and clean bundle assembly later.