# Full Pipeline Test Results

Per-run log of `tests/full_pipeline/test_end_to_end.py` runs against the real Anthropic API. Each block captures overall verdict, supervisor status, per-step status + verdict + telemetry, per-step evaluator failures, and pointers to the recorded-response files under `tests/recorded_responses/full_pipeline/`.

Sibling file: `results/test_results.md` captures per-agent isolated runs (one block per agent/scenario). This file captures full-pipeline runs (one block per pipeline run across all six supervisor steps).

Block format:

```
## Pipeline Run #{N} — {scenario} — {YYYY-MM-DD}
**Overall verdict:** PASS | FAIL
**Supervisor status:** COMPLETE | ESCALATED | BLOCKED
**Pipeline run id:** {uuid}
**Halted at:** STEP-XX (only when supervisor halted before STEP-06)

| Step | Agent | Status | Verdict | Elapsed | In tokens | Out tokens |
|------|-------|--------|---------|---------|-----------|------------|
| STEP-01 | intake (deterministic) | COMPLETE | n/a | — | — | — |
| STEP-02 | it_security_agent | COMPLETE | PASS | 1.42s | 2,340 | 512 |
| ...

**Totals:** 5 agent call(s), 11,920 input tokens, 2,430 output tokens, 9.30s cumulative.

**Per-step failures:** (only when verdict is FAIL for one or more steps)
- [STEP-03] {failure 1}
- [STEP-04] {failure 2}

**Recorded responses:**
- STEP-02 → `tests/recorded_responses/full_pipeline/pipeline_1__it_security_agent__scenario_1_pass.json`
- ...

**Notes:** the coding agent running these tests for me-- I want you to detail here what you think went wrong (if the test was a failure).
    Do some preliminary analysis and put a brief excerpt here in recording your response.
```

---

## Pipeline Run #1 — scenario_1 — 2026-04-20
**Overall verdict:** FAIL
**Supervisor status:** COMPLETE
**Pipeline run id:** run_43b7c962a7

| Step | Agent | Status | Verdict | Elapsed | In tokens | Out tokens |
|------|-------|--------|---------|---------|-----------|------------|
| STEP-01 | intake (deterministic) | COMPLETE | n/a | — | — | — |
| STEP-02 | it_security_agent | COMPLETE | PASS | 3.04s | 20,196 | 290 |
| STEP-03 | legal_agent | COMPLETE | PASS | 2.02s | 19,770 | 158 |
| STEP-04 | procurement_agent | COMPLETE | FAIL | 3.47s | 20,703 | 347 |
| STEP-05 | checklist_assembler | COMPLETE | FAIL | 41.46s | 39,316 | 608 |
| STEP-06 | checkoff_agent | COMPLETE | PASS | 30.95s | 7,688 | 1,040 |

**Totals:** 5 agent call(s), 107,673 input tokens, 2,443 output tokens, 80.94s cumulative.

**Per-step failures:**
- [STEP-04] scenario_1: PRIMARY PAM-001 row_id='A-T2' does NOT match the vendor profile's primary keys (vendor_class='Class C', integration_tier='TIER_1' → expected row_id='C-T1'). Per §8.3 strict primary-key matching, substituting a non-matching row when a matching row is present in the candidate set is silent wrong-row selection — the Class-level mirror of scenario_7's silent path fabrication failure mode. §14 A-04: no approval_path may be asserted from a row that does not match on both primary keys.
- [STEP-05] inherited field missing: 'dpa_blocker'

**Recorded responses:**
- STEP-02 → `tests/recorded_responses/full_pipeline/pipeline_1__it_security_agent__scenario_1_pass.json`
- STEP-03 → `tests/recorded_responses/full_pipeline/pipeline_1__legal_agent__scenario_1_pass.json`
- STEP-04 → `tests/recorded_responses/full_pipeline/pipeline_1__procurement_agent__scenario_1_fail.json`
- STEP-05 → `tests/recorded_responses/full_pipeline/pipeline_1__checklist_assembler__scenario_1_fail.json`
- STEP-06 → `tests/recorded_responses/full_pipeline/pipeline_1__checkoff_agent__scenario_1_pass.json`
## Pipeline Run #2 — scenario_1 — 2026-04-20
**Overall verdict:** FAIL
**Supervisor status:** COMPLETE
**Pipeline run id:** run_889cd34708

| Step | Agent | Status | Verdict | Elapsed | In tokens | Out tokens |
|------|-------|--------|---------|---------|-----------|------------|
| STEP-01 | intake (deterministic) | COMPLETE | n/a | — | — | — |
| STEP-02 | it_security_agent | COMPLETE | PASS | 2.85s | 20,196 | 224 |
| STEP-03 | legal_agent | COMPLETE | PASS | 1.74s | 19,704 | 158 |
| STEP-04 | procurement_agent | COMPLETE | FAIL | 4.04s | 20,637 | 409 |
| STEP-05 | checklist_assembler | COMPLETE | FAIL | 35.05s | 39,192 | 586 |
| STEP-06 | checkoff_agent | COMPLETE | PASS | 30.72s | 7,665 | 1,200 |

**Totals:** 5 agent call(s), 107,394 input tokens, 2,577 output tokens, 74.40s cumulative.

**Per-step failures:**
- [STEP-04] scenario_1: PRIMARY PAM-001 row_id='A-T2' does NOT match the vendor profile's primary keys (vendor_class='Class C', integration_tier='TIER_1' → expected row_id='C-T1'). Per §8.3 strict primary-key matching, substituting a non-matching row when a matching row is present in the candidate set is silent wrong-row selection — the Class-level mirror of scenario_7's silent path fabrication failure mode. §14 A-04: no approval_path may be asserted from a row that does not match on both primary keys.
- [STEP-05] inherited field missing: 'dpa_blocker'

**Recorded responses:**
- STEP-02 → `tests/recorded_responses/full_pipeline/pipeline_2__it_security_agent__scenario_1_pass.json`
- STEP-03 → `tests/recorded_responses/full_pipeline/pipeline_2__legal_agent__scenario_1_pass.json`
- STEP-04 → `tests/recorded_responses/full_pipeline/pipeline_2__procurement_agent__scenario_1_fail.json`
- STEP-05 → `tests/recorded_responses/full_pipeline/pipeline_2__checklist_assembler__scenario_1_fail.json`
- STEP-06 → `tests/recorded_responses/full_pipeline/pipeline_2__checkoff_agent__scenario_1_pass.json`
