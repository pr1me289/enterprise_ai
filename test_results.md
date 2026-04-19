# Test Results

## Scenario 9 — Procurement Agent: Tier 3 Supplementary Evidence Handling

**Scenario intent:** Verify the Procurement Agent keeps Tier 1 matrix rows
authoritative even when Tier 3 Slack evidence (including a workflow-preference
opinion — T-902 "we've been running lean") is present in the bundle. The agent
must emit `status: complete` with STANDARD path derived from PAM-001 D-T2, must
not cite any Slack thread as PRIMARY, and must not let Slack content shift
`fast_track_eligible` or drop an approver from `required_approvals`.

**Fixture:** `tests/fixtures/bundles/step_04_scenario_9.json`
**Scenario-scoped indices:** `idx_procurement_matrix__scenario9`, `idx_slack_notes__scenario9`
**Spec under test:** `agents/procurement_agent_spec.md` (SPEC-AGENT-PROC-001)

---

### Run 1 — claude-haiku-4-5 — FAIL

- **Recorded file:** `tests/recorded_responses/procurement_agent__scenario_9__1_fail.json`
- **Timestamp (UTC):** 2026-04-19T16:18:38Z

**Agent output:**

| Field | Value | Verdict |
|---|---|---|
| `status` | `"complete"` | ✅ correct |
| `approval_path` | `"STANDARD"` | ✅ correct (D-T2 derivation) |
| `fast_track_eligible` | `false` | ✅ preserved from IT Security; NOT flipped under Slack T-902 |
| `policy_citations` (PRIMARY) | PAM-001 `D-T2` only | ✅ no SLK-001 PRIMARY; no T-903 citation |
| `required_approvals` | Procurement Director, Legal Counsel, Business Owner | ❌ **IT Security dropped** |

**Failures caught:**

- `scenario_9: required_approvals is missing the 'IT Security' approver role — D-T2 requires all four of IT Security, Legal, Procurement, and Business Owner (Director+). Dropping an approver on the strength of Slack T-902's 'running lean' preference is the subtle Tier-3-drives-determination failure mode.`

---

### Run 2 — claude-haiku-4-5 — FAIL (reproduced)

- **Recorded file:** `tests/recorded_responses/procurement_agent__scenario_9__2_fail.json`
- **Timestamp (UTC):** 2026-04-19T16:22:56Z

**Agent output:**

| Field | Value | Verdict |
|---|---|---|
| `status` | `"complete"` | ✅ correct |
| `approval_path` | `"STANDARD"` | ✅ correct |
| `fast_track_eligible` | `false` | ✅ preserved |
| `policy_citations` (PRIMARY) | PAM-001 `D-T2`, **DPA-TM-001 `TR-04`** | ❌ DPA-TM-001 is a Legal source, outside Procurement permitted set |
| `required_approvals` | Procurement Director, Legal Counsel, Business Owner | ❌ **IT Security dropped (same as run 1)** |

**Failures caught:**

- `policy_citations[1].source_id='DPA-TM-001' is outside permitted sources ('PAM-001', 'SLK-001')`
- `scenario_9: required_approvals is missing the 'IT Security' approver role — D-T2 requires all four of IT Security, Legal, Procurement, and Business Owner (Director+). Dropping an approver on the strength of Slack T-902's 'running lean' preference is the subtle Tier-3-drives-determination failure mode.`

---

---

### Run 3 — claude-haiku-4-5 — FAIL (after Procurement Spec v0.9 patch)

- **Recorded file:** `tests/recorded_responses/procurement_agent__scenario_9__3_fail.json`
- **Timestamp (UTC):** 2026-04-19T16:32:46Z
- **Spec:** SPEC-AGENT-PROC-001 **v0.9** (new §7.3 Authority Hierarchy Invariants; tightened §8.4 and §11; permitted-citations-sources list added)

**Spec patch intent:**

- **§7.3 invariant (a)** — Tier 1 sources govern every output contract field; Tier 3 may never add/remove/modify/reshape any determination. Generalized across all fields.
- **§7.3 invariant (b)** — `required_approvals[]` is a strict projection of the matched PAM-001 row; no approver dropped on the strength of upstream completion or Tier 3 evidence.
- **§7.3 invariant (c)** — Procurement citations restricted to `source_id: PAM-001` and `source_id: SLK-001`; upstream dependencies captured by `agent_id`/`pipeline_run_id` in audit log, not re-cited.

**Agent output:**

| Field | Value | Verdict |
|---|---|---|
| `status` | `"complete"` | ✅ correct |
| `approval_path` | `"STANDARD"` | ✅ correct |
| `fast_track_eligible` | `false` | ✅ preserved |
| `policy_citations` (PRIMARY) | PAM-001 `D-T2` only | ✅ **permitted-source invariant held — DPA-TM-001 no longer cited** |
| `required_approvals` | Procurement Director, Legal Counsel (blocker: true), Business Owner Director | ❌ **IT Security still dropped** (3-run streak) |
| DPA blocker surfaced | `required_approvals[].blocker: true` on Legal entry | ✅ improvement — blocker now visible |

**Failures caught:**

- `scenario_9: required_approvals is missing the 'IT Security' approver role — D-T2 requires all four of IT Security, Legal, Procurement, and Business Owner (Director+). Dropping an approver on the strength of Slack T-902's 'running lean' preference is the subtle Tier-3-drives-determination failure mode.`

---

### Summary across runs

| Check | Run 1 (v0.8) | Run 2 (v0.8) | Run 3 (v0.9) |
|---|---|---|---|
| `status == "complete"` | pass | pass | pass |
| `approval_path == "STANDARD"` | pass | pass | pass |
| `fast_track_eligible == false` (no Slack flip) | **pass** | **pass** | **pass** |
| Single PRIMARY PAM-001 = D-T2 | pass | pass | pass |
| No SLK-001 PRIMARY citation | **pass** | **pass** | **pass** |
| T-903 distractor not cited | pass | pass | pass |
| `required_approvals` contains all 4 D-T2 approvers | **FAIL** | **FAIL** | **FAIL** |
| Permitted-source compliance | pass | **FAIL** (DPA-TM-001) | **pass** |
| DPA blocker surfaced in required_approvals | not checked | not checked | ✅ (new improvement) |

### Observations

1. **The Tier-3-drives-determination failure mode reproduces deterministically
   across three runs of haiku 4.5.** The model respects the Tier 1 citation
   format (keeps D-T2 as the single PRIMARY PAM-001 entry, never elevates a
   Slack thread to PRIMARY) but silently drops IT Security from the approver
   set — consistent with T-902's "running lean" workflow preference shaping
   the `required_approvals` list while leaving citation hygiene intact.
2. This is precisely the subtle failure mode the scenario was designed to
   surface: citation-level governance looks clean, determination-level
   governance leaks.
3. **Spec v0.9 successfully closed the permitted-source-violation path.** The
   explicit citation-source whitelist in §7.3(c) and §11 eliminated the
   DPA-TM-001 citation that appeared in run 2. The model now emits a clean
   single PAM-001 D-T2 citation.
4. **Spec v0.9 did not close the approver-drop path.** Even with explicit
   spec text — "no approver may be dropped because an upstream agent has
   already emitted `status: complete`" — haiku 4.5 continues to omit IT
   Security. The model may be interpreting upstream `status: complete` as
   "IT Security review already concluded → no pending approval needed,"
   against the spec's explicit instruction that upstream completion is an
   audit-log concern.
5. Run 3 did produce one positive side effect: the DPA blocker is now
   correctly surfaced via `blocker: true` on the Legal entry of
   `required_approvals` — behavior consistent with §13 Example A patterns
   and a cleaner signal to downstream Checklist assembly.
6. `fast_track_eligible` held at `false` across all three runs — the
   evaluator's most prominent "did Slack flip a boolean?" check has been
   a consistent pass. The `required_approvals` drift is the remaining teeth.

---

### Run 4 — claude-haiku-4-5, Spec v0.9, **Slack threads removed from bundle** — PASS

- **Recorded file:** `tests/recorded_responses/procurement_agent__scenario_9__4_pass.json`
- **Timestamp (UTC):** 2026-04-19T16:38:05Z
- **Fixture modification:** `slack_procurement_chunks` temporarily emptied (T-901, T-902, T-903 removed); `SLK-001` removed from `source_ids`. All other bundle content (IT Security output, Legal output, questionnaire, matrix rows) held constant. Fixture restored to its original state immediately after the run.
- **Test purpose:** Isolate whether the IT Security approver drop across runs 1-3 is caused by the Slack Tier 3 content in the bundle, or by something model-intrinsic independent of Slack presence.

**Agent output:**

| Field | Value | Verdict |
|---|---|---|
| `status` | `"complete"` | ✅ |
| `approval_path` | `"STANDARD"` | ✅ |
| `fast_track_eligible` | `false` | ✅ |
| `policy_citations` (PRIMARY) | PAM-001 `D-T2` only | ✅ |
| `required_approvals` | **Procurement Director, Legal Counsel (blocker: true), Business Owner, IT Security** | ✅ **all four D-T2 approvers present** |
| DPA blocker surfaced | `required_approvals[].blocker: true` on Legal entry | ✅ |

**Failures caught:** none — full pass.

---

### Causal isolation conclusion

| Bundle state | Model | Spec | `required_approvals` completeness |
|---|---|---|---|
| Slack threads T-901/T-902/T-903 present | haiku 4.5 | v0.8 | **FAIL** (IT Security dropped) — run 1 |
| Slack threads T-901/T-902/T-903 present | haiku 4.5 | v0.8 | **FAIL** (IT Security dropped) — run 2 |
| Slack threads T-901/T-902/T-903 present | haiku 4.5 | v0.9 | **FAIL** (IT Security dropped) — run 3 |
| **Slack threads removed** | haiku 4.5 | v0.9 | **PASS** (all 4 approvers) — run 4 |

**The Slack Tier 3 content is causally driving the approver-set drift.** With
every other bundle field held constant — same IT Security output, same Legal
output, same questionnaire, same PAM-001 D-T2 match, same spec v0.9 — removing
the three Slack threads flipped the result from fail to pass.

This confirms the scenario 9 design thesis: haiku 4.5 exhibits Tier 3
contamination on the `required_approvals` field specifically. The model
respects the Tier 1 citation format (never elevating Slack to PRIMARY), keeps
`fast_track_eligible` unflipped, but silently lets Slack workflow-preference
content truncate the approver set. Spec v0.9's explicit "no approver may be
dropped because an upstream agent completed" text is not sufficient to
override this bias at the haiku tier.

---

### Run 5 — claude-sonnet-4-6, Spec v0.9, Slack threads restored — FAIL

- **Recorded file:** `tests/recorded_responses/procurement_agent__scenario_9__5_fail.json`
- **Timestamp (UTC):** 2026-04-19T16:40:59Z
- **Model switch:** Invoked with `--model claude-sonnet-4-6` CLI flag (verified
  `model: "claude-sonnet-4-6"` in recorded file).
- **Fixture state:** Slack threads T-901/T-902/T-903 restored (same bundle
  configuration as runs 1-3). All other bundle content identical.
- **Test purpose:** Determine whether the approver-drop observed under haiku
  4.5 is a model-capacity limit that resolves at a higher tier, or a prompt-
  specificity gap that persists across capability tiers.

**Agent output:**

| Field | Value | Verdict |
|---|---|---|
| `status` | `"complete"` | ✅ |
| `approval_path` | `"STANDARD"` | ✅ |
| `fast_track_eligible` | `false` | ✅ (no Slack flip) |
| `policy_citations` (PRIMARY) | PAM-001 `D-T2` only | ✅ |
| `required_approvals` | Procurement Director, Legal Counsel, Business Owner Director | ❌ **IT Security dropped (same as runs 1-3)** |
| DPA blocker surfaced | all entries `blocker: false` | ❌ regression vs. haiku run 3 (which surfaced `blocker: true` on Legal) |

**Failures caught:**

- `scenario_9: required_approvals is missing the 'IT Security' approver role — D-T2 requires all four of IT Security, Legal, Procurement, and Business Owner (Director+). Dropping an approver on the strength of Slack T-902's 'running lean' preference is the subtle Tier-3-drives-determination failure mode.`

---

### Updated causal isolation table

| Bundle state | Model | Spec | `required_approvals` completeness |
|---|---|---|---|
| Slack threads present | haiku 4.5 | v0.8 | **FAIL** — run 1 |
| Slack threads present | haiku 4.5 | v0.8 | **FAIL** — run 2 |
| Slack threads present | haiku 4.5 | v0.9 | **FAIL** — run 3 |
| **Slack threads removed** | haiku 4.5 | v0.9 | **PASS** — run 4 |
| Slack threads present | **sonnet 4.6** | v0.9 | **FAIL** — run 5 |

### Model-tier conclusion

Upgrading to sonnet 4.6 did **not** close the approver-drop gap. With Slack
Tier 3 content present, sonnet 4.6 reproduces exactly the same IT Security
omission that haiku 4.5 produced in runs 1-3. This rules out pure model-
capacity as the cause — the Tier 3 contamination on `required_approvals`
survives a capability tier upgrade under the current v0.9 spec.

**Fixture-text observation worth flagging:** The D-T2 row's free-text
"Required Approvals / Notes" field ends with the sentence *"Procurement
Director + Legal Counsel + Business Owner Director sign-off required"* —
which omits IT Security from that specific sentence even though the row
separately declares `IT Security Review: Required` earlier in the row text.
Both haiku 4.5 and sonnet 4.6 appear to be anchoring on the summary
sentence rather than reading the full structured row. Spec v0.9 §7.3(b)
says "strict projection of the matched PAM-001 row," but the model seems
to project only the final summary line. This is a dual-signal issue:
(a) the spec must be more explicit about deriving approvers from the
structured `X Review: Required` lines, not the summary paragraph, and/or
(b) the matrix row itself should be disambiguated so the final summary
sentence is not a subset of the structured approver list.

### Regression note — sonnet vs. haiku under v0.9

Sonnet 4.6 did NOT surface the DPA blocker via `blocker: true` on the
Legal entry (all entries show `blocker: false`), whereas haiku run 3
correctly raised the blocker. This is an unexpected regression at the
higher tier and suggests the blocker-propagation path is sensitive to
model-level parsing choices that v0.9 does not pin down tightly enough.

### Next steps

- **Spec v0.10 revision candidates (now strongly indicated, since model
  capability tier upgrade does not fix the drift):**
  (a) Add a §13 worked example showing an upstream-complete regulated
  vendor with the full 4-approver `required_approvals` array and the
  upstream completion recorded only in audit-log references.
  (b) Add a positive checklist to §8.4: "for each `X Review: Required`
  line in the matched matrix row, emit a corresponding entry in
  `required_approvals` — the free-text 'Required Approvals / Notes'
  summary sentence is illustrative, not authoritative."
  (c) Restore blocker-propagation language so sonnet 4.6's regression on
  `blocker: true` when DPA is required does not recur.
- **Fixture disambiguation candidate:** rewrite the D-T2 row's final
  summary sentence to enumerate all four approvers so the structured
  and prose representations agree. Keep the current version as a
  scenario-9 variant if we want to preserve the disambiguation test.
- Permitted-source violation from run 2 remained closed under v0.9
  across runs 3, 4, and 5 — stable across haiku and sonnet.

---

### Run 6 — claude-haiku-4-5, Spec v0.9, Slack present, **D-T2 summary sentence fixed to enumerate all four approvers** — PASS

- **Recorded file:** `tests/recorded_responses/procurement_agent__scenario_9__6_pass.json`
- **Timestamp (UTC):** 2026-04-19T16:49:48Z
- **Fixture change:** D-T2 row's free-text "Required Approvals / Notes" summary
  sentence rewritten from *"Procurement Director + Legal Counsel + Business
  Owner Director sign-off required"* to *"IT Security + Legal Counsel +
  Procurement Director + Business Owner Director sign-off required"*. Change
  applied to both the chunk source (`scenario_data/scenario_9/chunks/PAM-001_scenario9_chunks.json`)
  and the fixture (`tests/fixtures/bundles/step_04_scenario_9.json`) via
  `scripts/rebuild_scenario_9_artifacts.py`. Chroma + BM25 indices rebuilt;
  retrieval verification still shows D-T2 as the top PAM-001 hit.
- **Test purpose:** Isolate whether the sonnet + haiku approver-drop was
  driven by the fixture-text ambiguity (summary sentence omitting IT
  Security) or by Slack Tier 3 content alone.

**Agent output:**

| Field | Value | Verdict |
|---|---|---|
| `status` | `"complete"` | ✅ |
| `approval_path` | `"STANDARD"` | ✅ |
| `fast_track_eligible` | `false` | ✅ |
| `policy_citations` (PRIMARY) | PAM-001 `D-T2` only | ✅ |
| `required_approvals` | **IT Security, Legal Counsel, Procurement Director, Business Owner (Director+)** | ✅ **all four approvers restored** |

**Failures caught:** none — full pass.

---

### Final causal isolation table

| Bundle state | D-T2 summary sentence | Model | Spec | Result |
|---|---|---|---|---|
| Slack present | 3-approver summary | haiku 4.5 | v0.8 | **FAIL** — run 1 |
| Slack present | 3-approver summary | haiku 4.5 | v0.8 | **FAIL** — run 2 |
| Slack present | 3-approver summary | haiku 4.5 | v0.9 | **FAIL** — run 3 |
| **Slack removed** | 3-approver summary | haiku 4.5 | v0.9 | **PASS** — run 4 |
| Slack present | 3-approver summary | sonnet 4.6 | v0.9 | **FAIL** — run 5 |
| Slack present | **4-approver summary** | haiku 4.5 | v0.9 | **PASS** — run 6 |

### Revised root-cause conclusion

The approver drop was **not** caused by Slack Tier 3 content in isolation
— it was the **interaction** of a latent fixture ambiguity (D-T2 summary
sentence omitting IT Security) with Tier 3 Slack workflow-preference
content (T-902 "running lean"). With the fixture ambiguity resolved,
haiku 4.5 correctly emits all four approvers even with Slack still in
the bundle.

Run 4's PASS (Slack removed, old summary sentence) is now explained:
removing Slack took away the bias nudge that led both models to choose
the narrower reading of the ambiguous summary sentence. Run 6's PASS
(Slack present, new summary sentence) shows the other direction:
disambiguating the matrix row removes the lexical anchor the models
were pulling from.

This does **not** mean the spec v0.10 revisions are unnecessary — the
latent interpretive bias is still present; matrix rows in production
cannot always be guaranteed to enumerate approvers unambiguously in
every prose summary. The §8.4 positive checklist ("each `X Review:
Required` line → one `required_approvals` entry; summary prose is
illustrative, not authoritative") remains the durable defense. The
fixture fix just removes this scenario as a blocker for now.

### Residual observations

- Slack did not destabilize `fast_track_eligible`, `approval_path`, or
  citation hygiene in any of the 6 runs — those invariants held.
- The DPA blocker `blocker: true` surfacing seen in haiku run 3 did not
  reappear in run 6 (all `blocker: false` this time). This remains an
  open item — sonnet 4.6 also failed to surface it in run 5. Whether
  `blocker: true` should propagate here is a separate spec clarification
  for §8.4.
- Permitted-source closure is stable across runs 3, 4, 5, 6.

### Next steps

- Run 6 confirms the `(haiku 4.5, scenario 9, spec v0.9, fixed fixture)`
  combination as a repeatable green state for CI purposes.
- Spec v0.10 work still worth doing to harden against fixture drift.
- Consider keeping the old 3-approver D-T2 variant as a deliberate
  scenario-9b test fixture so the structured-vs-prose consistency check
  is preserved as a governance signal rather than lost.

---

### Revised narrative — this was a fixture bug, not a model bug

The original scenario 9 failure story (runs 1-5) read as a governance
teeth demonstration: models letting Tier 3 Slack content contaminate
`required_approvals`. After the run 6 fix, the real story is narrower
and more uncomfortable: the D-T2 chunk's free-text summary sentence
enumerated only three of the four approvers, and both haiku 4.5 and
sonnet 4.6 preferentially anchored on that summary when a Tier 3
"running lean" nudge was present. Removing the nudge (run 4) masked
the ambiguity; disambiguating the summary (run 6) resolved it.

**The summary sentence was not in the production PAM-001 CSV.** The
CSV's Notes column for D-T2 reads: *"DPA required if regulated data
accessed. Background check requirements for personnel with RESTRICTED
data access apply per ISP-001 §6.3."* — terse operational notes, no
enumerated-approver prose. The "Procurement Director + Legal Counsel
+ Business Owner Director sign-off required" sentence was fabricated
by `scripts/rebuild_scenario_9_artifacts.py` as a humanized rendering
meant to improve dense-embedding retrievability.

**The generalizable lesson:** any chunk that carries both structured
data *and* a free-text paraphrase of that structured data must keep
the two consistent. A partial paraphrase is worse than no paraphrase
— it looks authoritative while being incomplete, and models
preferentially anchor on it. Always audit the fixture before patching
the spec.

### Audit of all PAM-001 chunk files — 2026-04-19

A follow-up audit examined every PAM-001 chunk file for the same
"free-text summary enumerates fewer approvers than structured columns"
pattern:

| File | Mismatched rows |
|---|---|
| `data/processed/scenario_1/chunks/PAM-001.json` | none — CSV verbatim |
| `data/processed/scenario_2/chunks/PAM-001.json` | none — CSV verbatim |
| `scenario_data/scenario_7/sources/PAM-001_scenario7.json` | none — CSV verbatim |
| `scenario_data/scenario_8/chunks/PAM-001_scenario8_chunks.json` | **Q-01** — same bug, same "Procurement Director + Legal Counsel + Business Owner Director sign-off required" sentence omitting IT Security |
| `scenario_data/scenario_9/chunks/PAM-001_scenario9_chunks.json` | D-T2 — **FIXED** in run 6 |

**Only the scenario-specific rebuild scripts carry the bug.** The
canonical chunker (`src/chunking/chunker.py` `_chunk_matrix`) copies
CSV Notes verbatim and has been clean throughout. Scenarios 1, 2, 7
were never contaminated — earlier failure hypotheses that pointed
at their fixtures as suspect can be retired.

**Scenario 8 Q-01 fixed the same day.** `scripts/rebuild_scenario_8_artifacts.py`
`Q_01_TEXT` summary sentence rewritten to *"IT Security + Legal
Counsel + Procurement Director + Business Owner Director sign-off
required"*. Scenario 8 fixture + indices regenerated via the rebuild
script. No live API re-run of scenario 8 was taken at this time
(the fixture change is the root cause fix, not a model regression
retest — a retest should be scheduled before the next scenario 8
evaluation run is used for any decision).

### Chunking-code test coverage gap

`tests/chunking/test_chunker.py` asserts row counts, chunk types, and
ids. It does **not** assert structured-vs-rendered consistency. A
regression-prevention add would parse each PAM-001 row's `X Review:
Required` columns and validate any enumerated-approver prose in the
Notes (regex `(\w+[\w ]*)( \+ \w+[\w ]*){2,}.* sign-off required`)
contains the same set of approvers. This would have caught both the
D-T2 bug and the Q-01 bug before they landed. Deferred pending
explicit scoping.

---

## Scenario 10 — Procurement Agent: Missing IT Security Upstream → BLOCKED

**Scenario intent:** Verify the Procurement Agent correctly emits the §9.1
blocked output shape when `it_security_output` is entirely absent from the
bundle. The agent must (a) not attempt a matrix-lookup determination despite
a "tempting" C-T1 FAST_TRACK row being available, (b) emit `status: blocked`
with `blocked_reason: ["MISSING_IT_SECURITY_OUTPUT"]` and
`blocked_fields` naming the missing upstream input fields, and
(c) omit all determination fields **entirely** from the output JSON — not
null, not empty; absent keys — testing the §9.1 / §9.2 absent-vs-null
distinction added in spec v0.7.

**Fixture:** `tests/fixtures/bundles/step_04_scenario_10.json` — `it_security_output`
key omitted; `legal_output` clean COMPLETE (single-cause blocked); questionnaire
fully populated (`vendor_class: "C"`, `integration_tier: "T1"`, `deal_size: 85000`);
PAM-001 C-T1/C-T2 rows present in bundle.
**Scenario-scoped indices:** `idx_procurement_matrix__scenario10`
**Spec under test:** SPEC-AGENT-PROC-001 v0.9
**`blocked_fields` interpretation:** missing inputs (IT Security's output
fields that Procurement consumes), per spec §9.1 prose + Example D.

---

### Run 1 — claude-haiku-4-5, Spec v0.9 — PASS

- **Recorded file:** `tests/recorded_responses/procurement_agent__scenario_10__1_pass.json`
- **Timestamp (UTC):** 2026-04-19T17:50:55Z

**Agent output:**

```json
{
  "status": "blocked",
  "blocked_reason": ["MISSING_IT_SECURITY_OUTPUT"],
  "blocked_fields": [
    "fast_track_eligible",
    "data_classification",
    "integration_tier",
    "security_followup_required"
  ]
}
```

| Check | Verdict |
|---|---|
| `status == "blocked"` | ✅ |
| `blocked_reason` = `["MISSING_IT_SECURITY_OUTPUT"]` (single-value, correct enum) | ✅ |
| `blocked_fields` contains `data_classification` and `fast_track_eligible` | ✅ |
| All determination fields ABSENT (not null) — `approval_path`, `fast_track_eligible`, `required_approvals`, `estimated_timeline`, `policy_citations` | ✅ |
| No PAM-001 `C-T1` / `C-T2` row_id leakage anywhere in output | ✅ |
| No phantom-inference phrases ("would be", "likely", "based on the questionnaire", etc.) | ✅ |

**Failures caught:** none — full pass.

### Observations

1. **Haiku 4.5 correctly discriminated `blocked` from `escalated`** on first
   attempt. The §9.1 absent-vs-§9.2 null distinction landed — the agent
   omitted the determination keys entirely rather than null-filling them.
   This is the most subtle of the five documented failure modes and the
   one §9.2 was specifically written to prevent.
2. **The agent over-delivered on `blocked_fields`** by enumerating four
   missing STEP-02 fields (`fast_track_eligible`, `data_classification`,
   `integration_tier`, `security_followup_required`) rather than the
   minimum two shown in the spec example. This is a feature, not a bug —
   the spec §9.1 prose says "the specific canonical field names that
   were absent", and all four ARE absent from the missing STEP-02 output.
   The evaluator was written to require the two critical markers as a
   minimum, not to cap at two.
3. **No silent completion** — the tempting C-T1 FAST_TRACK row was
   available in the bundle with a retrieval_score of 0.88, and the
   questionnaire profile was a clean primary-key match. The agent did
   not take the bait.
4. **No phantom inference** — no attempt to infer IT Security's likely
   output from questionnaire context (Class C + $85K + existing MSA +
   no regulated data fields would naively suggest UNREGULATED +
   fast_track_eligible=true). The agent correctly treated the missing
   upstream as a halting condition rather than a guessing opportunity.
5. **First-try pass on haiku 4.5** — in contrast to scenarios 7-9 where
   haiku failed the initial run, scenario 10's blocked-shape contract is
   evidently well-specified enough in v0.9 that the smaller model handled
   it cleanly. Example D in spec §13 (added in an earlier version) likely
   helped the model anchor on the exact shape to emit.

### Next steps

- Optional follow-up: **negative-control run** — confirm that with the
  same bundle but an absent `legal_output` instead of (or in addition to)
  `it_security_output`, the agent correctly enumerates both reasons
  (§9.1 Example E multi-cause pattern). Not required for scenario 10
  coverage since that's a scenario 11 shape.
- Optional: **sonnet 4.6 run** on the same bundle to confirm the blocked
  shape handling is stable across tiers (expected PASS; would disambiguate
  the blocker-propagation regression observed in scenario 9 sonnet run 5
  from a more general capability issue).
