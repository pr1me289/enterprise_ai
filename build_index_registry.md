## Instructions for CODEX — Build the index registry

The purpose of the registry is:

* declare every logical source/store in one place
* map each source to its retrieval lane
* map each source to its backend(s)
* expose allowed agents and authority metadata
* let retrieval code route requests without hard-coded assumptions
* make the storage layer explainable and auditable

### Design intent

The registry is not a search index itself.
It is the **control plane metadata** for the storage layer.

It should answer questions like:

* Which backend does `ISP-001` live in?
* Is `VQ-OC-001` indexed or direct-access only?
* Which collection/bundle/store name belongs to each source?
* Which agents are allowed to access that source?
* What authority tier and source type does that source have?

---

## What CODEX should build

Create:

* `src/indexing/index_registry.py`
* `data/indexes/index_registry.json`

Optional helper:

* `src/indexing/load_index_registry.py`

---

## Core structure to implement

The registry should have **one record per logical source**, not one per chunk.

Use entries for:

* `ISP-001`
* `DPA-TM-001`
* `PAM-001`
* `PVD-001`
* `SLK-001`
* `VQ-OC-001`

### Suggested schema

Each registry entry should include:

* `source_id`
* `source_name`
* `source_type`
* `authority_tier`
* `retrieval_lane`
* `version`
* `document_date`
* `freshness_status`
* `manifest_status`
* `allowed_agents`
* `is_primary_citable`
* `storage_kind`
* `logical_store_name`
* `backends`
* `backend_locations`

### Meaning of the key fields

* `retrieval_lane`

    * `INDEXED_HYBRID`
    * `DIRECT_STRUCTURED`
* `storage_kind`

    * `vector_bm25`
    * `structured_direct`
* `logical_store_name`

    * for indexed sources: logical index name
    * for questionnaire: `vq_direct_access`
* `backends`

    * indexed sources: `["chroma", "bm25"]`
    * questionnaire: `["structured_json"]`
* `backend_locations`

    * paths or collection/bundle names used by the code

---

## Exact mapping CODEX should encode

### Indexed hybrid sources

* `ISP-001`

    * logical store: `idx_security_policy`
    * backends: `chroma`, `bm25`
* `DPA-TM-001`

    * logical store: `idx_dpa_matrix`
    * backends: `chroma`, `bm25`
* `PAM-001`

    * logical store: `idx_procurement_matrix`
    * backends: `chroma`, `bm25`
* `PVD-001`

    * logical store: `idx_precedents`
    * backends: `chroma`, `bm25`
* `SLK-001`

    * logical store: `idx_slack_notes`
    * backends: `chroma`, `bm25`

### Direct structured source

* `VQ-OC-001`

    * logical store: `vq_direct_access`
    * backends: `structured_json`

This should reflect the architecture you already committed to: most sources indexed-hybrid, questionnaire direct structured only.

---

## Implementation rules for CODEX

### 1. Registry values should come from source-level metadata, not chunk sampling

Do not infer source-level metadata by peeking at random chunks during retrieval.

Instead:

* build registry entries from authoritative source definitions or normalized artifacts
* for indexed sources, use the first chunk only if the source is guaranteed homogeneous
* for the questionnaire, read directly from `vq_direct_access.json` top-level metadata

### 2. The registry should be generated, not handwritten forever

Implement it as code that writes `data/indexes/index_registry.json`.

That way:

* paths stay synchronized
* source metadata updates cleanly
* rebuilds remain deterministic

### 3. Retrieval code should use the registry as the canonical source-to-store map

Do not hard-code:

* collection names
* file paths
* backend types
* allowed agents

The router should ask the registry.

### 4. Keep it source-level and concise

Do not dump chunk counts or per-chunk details into the core registry unless you want a small optional diagnostics section.

The main goal is routing and explainability.

---

## Suggested JSON shape

Tell CODEX to produce something like this:

```json
{
  "registry_version": "1.0",
  "generated_at": "2026-04-09T12:00:00Z",
  "sources": {
    "ISP-001": {
      "source_name": "IT Security Policy",
      "source_type": "POLICY_DOCUMENT",
      "authority_tier": 1,
      "retrieval_lane": "INDEXED_HYBRID",
      "version": "4.2",
      "document_date": "2026-04-04",
      "freshness_status": "CURRENT",
      "manifest_status": "PROVISIONAL",
      "allowed_agents": ["it_security", "legal", "procurement"],
      "is_primary_citable": true,
      "storage_kind": "vector_bm25",
      "logical_store_name": "idx_security_policy",
      "backends": ["chroma", "bm25"],
      "backend_locations": {
        "chroma_collection": "idx_security_policy",
        "bm25_bundle": "data/bm25/idx_security_policy.pkl"
      }
    },
    "VQ-OC-001": {
      "source_name": "OptiChain Vendor Questionnaire",
      "source_type": "VENDOR_QUESTIONNAIRE",
      "authority_tier": 2,
      "retrieval_lane": "DIRECT_STRUCTURED",
      "version": "Submission rev. 1",
      "document_date": "2026-04-04",
      "freshness_status": "CURRENT",
      "manifest_status": "PENDING",
      "allowed_agents": ["it_security", "legal", "procurement", "checklist_assembler", "checkoff"],
      "is_primary_citable": true,
      "storage_kind": "structured_direct",
      "logical_store_name": "vq_direct_access",
      "backends": ["structured_json"],
      "backend_locations": {
        "structured_store": "data/structured/vq_direct_access.json"
      }
    }
  }
}
```

The questionnaire fields above should match what is already in your structured store.

---

## Suggested Python structure

Tell CODEX to organize it like this:

### `src/indexing/index_registry.py`

Responsibilities:

* define source-to-store mapping
* load normalized source metadata
* build registry dict
* write `index_registry.json`

### `src/indexing/load_index_registry.py`

Responsibilities:

* load registry from disk
* get entry by `source_id`
* get entry by logical store name
* list all indexed sources
* list all structured sources

---

## Suggested implementation approach

### Step 1 — Define canonical logical mapping

Create a static config map like:

```python
SOURCE_STORE_CONFIG = {
    "ISP-001": {
        "logical_store_name": "idx_security_policy",
        "storage_kind": "vector_bm25",
        "backends": ["chroma", "bm25"],
        "backend_locations": {
            "chroma_collection": "idx_security_policy",
            "bm25_bundle": "data/bm25/idx_security_policy.pkl",
        },
    },
    "DPA-TM-001": {
        "logical_store_name": "idx_dpa_matrix",
        "storage_kind": "vector_bm25",
        "backends": ["chroma", "bm25"],
        "backend_locations": {
            "chroma_collection": "idx_dpa_matrix",
            "bm25_bundle": "data/bm25/idx_dpa_matrix.pkl",
        },
    },
    "PAM-001": {
        "logical_store_name": "idx_procurement_matrix",
        "storage_kind": "vector_bm25",
        "backends": ["chroma", "bm25"],
        "backend_locations": {
            "chroma_collection": "idx_procurement_matrix",
            "bm25_bundle": "data/bm25/idx_procurement_matrix.pkl",
        },
    },
    "PVD-001": {
        "logical_store_name": "idx_precedents",
        "storage_kind": "vector_bm25",
        "backends": ["chroma", "bm25"],
        "backend_locations": {
            "chroma_collection": "idx_precedents",
            "bm25_bundle": "data/bm25/idx_precedents.pkl",
        },
    },
    "SLK-001": {
        "logical_store_name": "idx_slack_notes",
        "storage_kind": "vector_bm25",
        "backends": ["chroma", "bm25"],
        "backend_locations": {
            "chroma_collection": "idx_slack_notes",
            "bm25_bundle": "data/bm25/idx_slack_notes.pkl",
        },
    },
    "VQ-OC-001": {
        "logical_store_name": "vq_direct_access",
        "storage_kind": "structured_direct",
        "backends": ["structured_json"],
        "backend_locations": {
            "structured_store": "data/structured/vq_direct_access.json",
        },
    },
}
```

### Step 2 — Load source-level metadata

For indexed sources:

* read the first chunk from each normalized index JSON artifact
* extract source-level metadata fields

For questionnaire:

* read top-level metadata directly from `vq_direct_access.json`

### Step 3 — Merge metadata + store config

Build one clean registry entry per source.

### Step 4 — Write registry JSON

Write to:

* `data/indexes/index_registry.json`

Make it human-readable:

* `indent=2`
* deterministic source ordering

---

## Important implementation details

### For authority tier

Because the questionnaire is direct structured and not chunked, CODEX may need to assign its authority tier explicitly in registry config if it is not stored top-level yet. Based on your contract model, the questionnaire is Tier 2 structured intake. If that field is absent in the source file, add it in config or add it to the questionnaire store metadata.

### For `document_date`

Keep consistent with your current source metadata contract. Do not reinterpret it during registry generation.

### For `allowed_agents`

Use the source-level list exactly as stored. This is important for explainability and later permission checks. The questionnaire currently allows:

* `it_security`
* `legal`
* `procurement`
* `checklist_assembler`
* `checkoff`

### For future retrieval code

Build helper methods like:

* `get_registry_entry(source_id)`
* `get_logical_store_name(source_id)`
* `get_backends(source_id)`
* `get_allowed_agents(source_id)`
* `is_indexed_source(source_id)`
* `is_structured_source(source_id)`

These will make the retrieval router much simpler.

---

## What to tell CODEX in one block

Use this wording:

> Build an `index_registry` as the canonical source-to-store routing map for Step 8. It should contain one entry per source, not per chunk. For each source, record source metadata (`source_id`, `source_name`, `source_type`, `authority_tier`, `retrieval_lane`, `version`, `document_date`, `freshness_status`, `manifest_status`, `allowed_agents`, `is_primary_citable`) plus storage metadata (`storage_kind`, `logical_store_name`, `backends`, `backend_locations`). Map the five indexed-hybrid sources to per-source Chroma/BM25 logical stores and map `VQ-OC-001` to the direct structured store `vq_direct_access`. Generate `data/indexes/index_registry.json` from code in `src/indexing/index_registry.py`, and provide a small loader/helper module for retrieval code to consume it instead of hard-coding backend assumptions.

If you want, I can turn that into an even shorter CODEX-ready handoff note.
