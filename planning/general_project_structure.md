## OptiChain Demo Build Plan

---

### Step 1 — Generate Mock Data Sources

Generate the six to eight mock enterprise data sources that the pipeline will operate on. Content is arbitrary; what matters is structural fidelity to how these sources would actually exist in a real enterprise environment.

**Sources to build:**
- IT Security Policy v4.2 (multi-section markdown/PDF-style document, ~8–12 pages with numbered clauses)
- DPA Legal Trigger Matrix (structured table — rows map vendor data-handling conditions to DPA requirements)
- Procurement Approval Matrix (structured table — rows map vendor class and deal size to approval path)
- OptiChain Vendor Questionnaire Submission (structured JSON object — single intake record)
- Prior Vendor Decisions / Precedent Log (semi-structured records — 3–4 past onboarding outcomes with rationale)
- Slack / Meeting Thread Notes (unstructured — 2–3 short threads relevant to the OptiChain evaluation, marked low-authority)

**Implementation note:** AI-generate the content for all of these. The questionnaire and matrices should include at least one deliberately ambiguous field and one deliberate compliance edge case (for example, ERP integration type unclear or existing NDA status unconfirmed). These should trigger the PROVISIONAL and ESCALATED states during the demo, since that is where the system’s behavior becomes most visible.

**Important design point:** The value of the demo is not the source content itself; it is that the sources differ in format and must be handled differently by the system.

---

### Step 2 — Initial Retrieval Strategy

We are making the retrieval strategy simple enough to build quickly, while still preserving the architectural principle that not all enterprise context should be treated the same way.

**Final retrieval decision:**
- We will **embed and index most mock documents**
- We will **not embed the questionnaire**
- We will **not embed the checklist / pipeline state output**
- We will keep the retrieval story simple, but preserve the important distinction that some enterprise data should remain directly structured rather than semantically retrieved

**How each source will be treated:**

| Source                                 | Retrieval Treatment           | Notes                                                                         |
| -------------------------------------- | ----------------------------- | ----------------------------------------------------------------------------- |
| IT Security Policy v4.2                | Embedded + indexed            | Retrieved through hybrid search (vector similarity + BM25)                    |
| DPA Legal Trigger Matrix               | Embedded + indexed            | For demo simplicity, treat as text-like evidence with preserved row structure |
| Procurement Approval Matrix            | Embedded + indexed            | For demo simplicity, treat as text-like evidence with preserved row structure |
| OptiChain Questionnaire                | Direct structured access only | No embedding; fields are read directly from JSON                              |
| Prior Vendor Decisions / Precedent Log | Embedded + indexed            | Retrieved semantically, optionally with simple metadata filtering             |
| Slack / Meeting Thread Notes           | Embedded + indexed            | Retrieved semantically/BM25 but treated as low-authority supplemental context |
| Checklist / final output object        | Never embedded                | This is assembled output/state, not a retrieval source                        |

**Why this is the right compromise for the demo:**
- it keeps implementation lightweight
- it avoids building multiple retrieval backends too early
- it still preserves one important architectural distinction: **operational structured intake data should not be embedded**
- it lets us tell a credible story that the system is mostly retrieval-driven, but not naively embedding absolutely everything

**Working retrieval model:**
- **Embedded + indexed lane**
  - policies
  - matrices
  - precedents
  - Slack / notes
- **Direct structured lane**
  - questionnaire JSON
- **Non-retrieval state lane**
  - checklist / audit / pipeline state objects

**Important note:**  
Even though we are embedding the matrices for simplicity, we should still preserve their row structure during preprocessing so they remain interpretable and citation-friendly. This keeps the door open to later upgrading them into exact structured lookup if we want a more advanced version.

---

### Step 3 — Finalize and Lock the Context Contract

This must exist before orchestration is built, because it defines the rules that orchestration enforces.

It should answer:
- which sources are authoritative
- what retrieval method applies to each source
- what source priority hierarchy applies
- what freshness and versioning rules apply
- which agents are permitted to access which sources

**What the Context Contract needs to define for build purposes:**
- source authority ranking (for example, IT Security Policy > prior decisions > Slack threads)
- retrieval method per source type
- per-agent source permissions (maps directly to the Role-to-Source Access Matrix in the Design Doc §8)
- freshness handling rules (version pinning at pipeline initialization; provisional flag if source version is unconfirmed)
- token budget per agent (pulls from Design Doc §9)
- citation requirements for each determination type

**Important:**  
Keep this document focused on retrieval rules and source governance. Do not overload it with agent behavior that belongs in the Agent Spec.

---

### Step 4 — Chunking Strategy and Index Construction

Chunking and index-building should follow the retrieval strategy.

**Chunking strategy per source type:**

| Source                      | Chunking Method                                         | Rationale                                                                    |
| --------------------------- | ------------------------------------------------------- | ---------------------------------------------------------------------------- |
| IT Security Policy v4.2     | Section-boundary chunking (split on numbered headings)  | Preserves numbered clause structure and keeps citations stable               |
| DPA Legal Trigger Matrix    | Row-level chunking                                      | Keeps each matrix row as one atomic decision unit even though it is embedded |
| Procurement Approval Matrix | Row-level chunking                                      | Same as above                                                                |
| OptiChain Questionnaire     | No chunking — ingest as a single structured JSON object | Retrieved by field, not by similarity search                                 |
| Prior Vendor Decisions      | Record-level chunking (each decision is one chunk)      | Each precedent is a discrete case                                            |
| Slack / Meeting Notes       | Thread-level chunking (one thread = one chunk)          | Preserves conversational coherence                                           |

**Index construction:**
- Build a dense vector index over all chunked sources except the questionnaire and checklist
- Build a BM25 index over those same indexed sources
- The questionnaire remains a direct-access structured object and is not part of either index
- The checklist and audit state are runtime outputs and are never part of retrieval

**Note on embedding model:**  
Use a lightweight local model such as `sentence-transformers/all-MiniLM-L6-v2`. The embedding model does not need to be sophisticated for this demo; the bigger point is the system’s retrieval design, not maximizing retrieval benchmark performance.

---

### Step 5 — Embedding Plan

Use a simple, lightweight embedding setup for all sources that are part of the indexed retrieval lane.

**Recommended scope for embeddings:**
- **Embed**
  - policy documents
  - legal trigger matrix
  - procurement approval matrix
  - prior vendor precedents
  - Slack / meeting notes
- **Do not embed**
  - questionnaire JSON
  - checklist state objects
  - deterministic outputs / audit state

**Why this is our final choice:**
- simpler to implement quickly
- allows one unified index for most source material
- still preserves the important architectural boundary that structured intake data is handled directly
- keeps the system easy to explain and demo

**Important clarification:**  
The questionnaire should remain a direct operational object, not something retrieved semantically. The checklist should remain assembled state/output, not a searchable knowledge source.

---

### Step 6 — Orchestration Layer

Build the agent infrastructure and execution graph that the Context Contract specifies. Behavioral rules belong in the Agent Spec; what we are building here is the execution graph, gate logic, and context-bundle assembly.

**What to build:**
- **Supervisor Agent class**
  - manages the execution graph (R-01 → R-02 → R-03/R-04 parallel → R-05 → R-06)
  - evaluates gate status per step
  - handles BLOCKED / ESCALATED / RESOLVED transitions
  - routes escalations
- **Domain agent stubs**
  - IT Security Agent
  - Legal Agent
  - Procurement Agent
  - Checklist Assembler
- **Pipeline state object**
  - tracks gate status
  - tracks audit log entries
  - stores retrieval summaries
  - stores final checklist output
- **Audit log writer**
  - append-only
  - writes one entry per retrieval operation, determination, escalation, and status change

**Framework decision:**  
No need for LangGraph at this demo scale. A clean Python state machine is enough and makes the architecture easier to inspect and explain.

---

### Step 7 — Agentic Retrieval Pipeline

This is the execution engine the orchestrator calls. For each domain agent, the retrieval pipeline takes a task and returns a curated context bundle.

**Components to build:**

#### Query Planner
A lightweight planner that takes the agent’s task description and determines:
- which sources to query
- in what order
- with what subqueries

This can be:
- a simple rule-based planner, or
- a small LLM call that outputs a structured retrieval plan

For demo reliability, a mostly deterministic rule-based planner may be better unless we specifically want to showcase LLM planning.

#### Source Router
Maps each subquery to the correct retrieval lane:
- **Indexed retrieval lane**: vector similarity + BM25 against policies, matrices, precedents, and notes
- **Direct access lane**: questionnaire JSON fetched directly

#### Retrieval Fusion
For indexed sources:
- run BM25 and vector similarity in parallel
- combine results with a simple fusion method such as Reciprocal Rank Fusion (RRF)

#### Re-Ranking
Use a lightweight reranking step after hybrid retrieval to improve result ordering.

**Planned reranking approach:**
- use a simple cross-encoder reranker if time permits
- otherwise use fused retrieval rank order directly for the first version
- keep Slack / meeting notes visibly lower-priority in the final bundle even if they retrieve well

#### Context Bundle Assembler
Assembles the final evidence bundle for the domain agent. It should:
- enforce token budget
- place questionnaire facts first
- place strongest indexed evidence next
- include supplemental notes only when useful
- attach provenance metadata (source, version, section/row, timestamp)

**Recommended bundle order:**
1. questionnaire facts
2. top retrieved policy / matrix evidence
3. relevant precedents
4. supplemental notes, if needed

#### Retrieval Manifest
A structured log entry produced per retrieval run that records:
- what sources were queried
- what items were returned
- what made it into the final bundle
- what was excluded and why

This is important because it makes retrieval visible and auditable during the demo.

**Important simplification:**  
We are not building advanced conflict-resolution or multiple complex retrieval lanes in the first version. The goal is to demonstrate a clean and believable governed retrieval flow, not maximum retrieval sophistication.

---

### Step 8 — Evaluation

Run the same evaluation tasks under multiple retrieval conditions and compare behavior.

**Three retrieval conditions:**
1. **Naive RAG baseline**
   - single vector index over all chunked text documents
   - top-k by cosine similarity
   - no direct structured questionnaire handling
2. **Raw long-context dump**
   - all relevant source text placed into the prompt with no real retrieval strategy
3. **Governed initial pipeline**
   - questionnaire handled directly
   - all other source material retrieved through the indexed hybrid lane
   - context-bundle assembly
   - audit visibility

**Evaluation metrics:**
- task completion accuracy
- hallucination count
- citation completeness
- retrieval transparency
- whether the system correctly identifies seeded edge cases
- whether the system correctly enters PROVISIONAL / ESCALATED states when ambiguity exists

**Deliverable:**  
A before/after comparison table across the three conditions, plus at least one retrieval manifest from the governed pipeline showing what the system retrieved and why.

---

### Remaining Artifacts (parallel to build, not strictly sequential)

- **Agent Spec**
  - behavioral rules
  - DOs / DON’Ts
  - required output schema
  - escalation behavior
  - stop conditions
- **One-page explainer**
  - non-technical summary of what the demo shows and why it matters
- **Demo walkthrough narrative**
  - end-to-end story using the OptiChain case

---

## Recommended working sequence
1. create mock data sources  
2. lock retrieval strategy by source type  
3. write the Context Contract  
4. define chunking and build indices  
5. implement lightweight embeddings for indexed sources  
6. build orchestration and pipeline state handling  
7. build the agentic retrieval pipeline  
8. evaluate against baseline conditions  
9. finalize Agent Spec and demo narrative

---

## One-sentence framing
We are building a lightweight enterprise-AI demo in which agents retrieve most enterprise knowledge through a unified hybrid index, while still preserving direct structured access for operational intake data and keeping final workflow state outside the retrieval system.