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
## Pipeline Run #3 — scenario_2 — 2026-04-20
**Overall verdict:** PASS
**Supervisor status:** ESCALATED
**Pipeline run id:** run_6984605057
**Halted at:** STEP-02

| Step | Agent | Status | Verdict | Elapsed | In tokens | Out tokens |
|------|-------|--------|---------|---------|-----------|------------|
| STEP-01 | intake (deterministic) | COMPLETE | n/a | — | — | — |
| STEP-02 | it_security_agent | ESCALATED | PASS | 7.06s | 20,199 | 739 |
| STEP-03 | legal_agent | PENDING | — | — | — | — |
| STEP-04 | procurement_agent | PENDING | — | — | — | — |
| STEP-05 | checklist_assembler | PENDING | — | — | — | — |
| STEP-06 | checkoff_agent | PENDING | — | — | — | — |

**Totals:** 1 agent call(s), 20,199 input tokens, 739 output tokens, 7.06s cumulative.

**Recorded responses:**
- STEP-02 → `tests/recorded_responses/full_pipeline/pipeline_3__it_security_agent__scenario_2_pass.json`
## Pipeline Run #4 — scenario_1 — 2026-04-27
**Overall verdict:** PASS
**Supervisor status:** COMPLETE
**Pipeline run id:** run_b0ae836897

| Step | Agent | Status | Verdict | Elapsed | In tokens | Out tokens |
|------|-------|--------|---------|---------|-----------|------------|
| STEP-01 | intake (deterministic) | COMPLETE | n/a | — | — | — |
| STEP-02 | it_security_agent | COMPLETE | PASS | 3.23s | 20,196 | 224 |
| STEP-03 | legal_agent | COMPLETE | PASS | 1.85s | 19,704 | 158 |
| STEP-04 | procurement_agent | COMPLETE | PASS | 3.20s | 20,639 | 302 |
| STEP-05 | checklist_assembler | COMPLETE | PASS | 38.77s | 39,412 | 477 |
| STEP-06 | checkoff_agent | COMPLETE | PASS | 26.67s | 7,448 | 724 |

**Totals:** 5 agent call(s), 107,399 input tokens, 1,885 output tokens, 73.72s cumulative.

**Recorded responses:**
- STEP-02 → `tests/recorded_responses/full_pipeline/pipeline_4__it_security_agent__scenario_1_pass.json`
- STEP-03 → `tests/recorded_responses/full_pipeline/pipeline_4__legal_agent__scenario_1_pass.json`
- STEP-04 → `tests/recorded_responses/full_pipeline/pipeline_4__procurement_agent__scenario_1_pass.json`
- STEP-05 → `tests/recorded_responses/full_pipeline/pipeline_4__checklist_assembler__scenario_1_pass.json`
- STEP-06 → `tests/recorded_responses/full_pipeline/pipeline_4__checkoff_agent__scenario_1_pass.json`
## Pipeline Run #5 — scenario_2 — 2026-04-27
**Overall verdict:** PASS
**Supervisor status:** ESCALATED
**Pipeline run id:** run_46b0736b8b
**Halted at:** STEP-02

| Step | Agent | Status | Verdict | Elapsed | In tokens | Out tokens |
|------|-------|--------|---------|---------|-----------|------------|
| STEP-01 | intake (deterministic) | COMPLETE | n/a | — | — | — |
| STEP-02 | it_security_agent | ESCALATED | PASS | 10.11s | 20,199 | 757 |
| STEP-03 | legal_agent | PENDING | — | — | — | — |
| STEP-04 | procurement_agent | PENDING | — | — | — | — |
| STEP-05 | checklist_assembler | PENDING | — | — | — | — |
| STEP-06 | checkoff_agent | PENDING | — | — | — | — |

**Totals:** 1 agent call(s), 20,199 input tokens, 757 output tokens, 10.11s cumulative.

**Recorded responses:**
- STEP-02 → `tests/recorded_responses/full_pipeline/pipeline_5__it_security_agent__scenario_2_pass.json`
## Pipeline Run #6 — scenario_2 — 2026-04-27
**Overall verdict:** PASS
**Supervisor status:** ESCALATED
**Pipeline run id:** run_a97dfc0bee
**Halted at:** STEP-03

| Step | Agent | Status | Verdict | Elapsed | In tokens | Out tokens |
|------|-------|--------|---------|---------|-----------|------------|
| STEP-01 | intake (deterministic) | COMPLETE | n/a | — | — | — |
| STEP-02 | it_security_agent | COMPLETE | PASS | 5.01s | 20,230 | 531 |
| STEP-03 | legal_agent | ESCALATED | PASS | 2.66s | 19,842 | 328 |
| STEP-04 | procurement_agent | PENDING | — | — | — | — |
| STEP-05 | checklist_assembler | PENDING | — | — | — | — |
| STEP-06 | checkoff_agent | PENDING | — | — | — | — |

**Totals:** 2 agent call(s), 40,072 input tokens, 859 output tokens, 7.67s cumulative.

**Recorded responses:**
- STEP-02 → `tests/recorded_responses/full_pipeline/pipeline_6__it_security_agent__scenario_2_pass.json`
- STEP-03 → `tests/recorded_responses/full_pipeline/pipeline_6__legal_agent__scenario_2_pass.json`
## Pipeline Run #7 — scenario_blocked_demo — 2026-04-27
**Overall verdict:** PASS
**Supervisor status:** BLOCKED
**Pipeline run id:** run_500e817423
**Halted at:** STEP-04

| Step | Agent | Status | Verdict | Elapsed | In tokens | Out tokens |
|------|-------|--------|---------|---------|-----------|------------|
| STEP-01 | intake (deterministic) | COMPLETE | n/a | — | — | — |
| STEP-02 | it_security_agent | COMPLETE | PASS | 5.51s | 26,043 | 664 |
| STEP-03 | legal_agent | COMPLETE | PASS | 2.21s | 20,943 | 154 |
| STEP-04 | procurement_agent | BLOCKED | PASS | 1.48s | 16,699 | 51 |
| STEP-05 | checklist_assembler | PENDING | — | — | — | — |
| STEP-06 | checkoff_agent | PENDING | — | — | — | — |

**Totals:** 3 agent call(s), 63,685 input tokens, 869 output tokens, 9.19s cumulative.

**Recorded responses:**
- STEP-02 → `tests/recorded_responses/full_pipeline/pipeline_7__it_security_agent__scenario_blocked_demo_pass.json`
- STEP-03 → `tests/recorded_responses/full_pipeline/pipeline_7__legal_agent__scenario_blocked_demo_pass.json`
- STEP-04 → `tests/recorded_responses/full_pipeline/pipeline_7__procurement_agent__scenario_blocked_demo_pass.json`
## Pipeline Run #8 — scenario_escalated_step4_demo — 2026-04-27
**Overall verdict:** PASS
**Supervisor status:** BLOCKED
**Pipeline run id:** run_8213dd83cf
**Halted at:** STEP-04

| Step | Agent | Status | Verdict | Elapsed | In tokens | Out tokens |
|------|-------|--------|---------|---------|-----------|------------|
| STEP-01 | intake (deterministic) | COMPLETE | n/a | — | — | — |
| STEP-02 | it_security_agent | COMPLETE | PASS | 7.25s | 26,043 | 739 |
| STEP-03 | legal_agent | COMPLETE | PASS | 1.58s | 20,943 | 154 |
| STEP-04 | procurement_agent | BLOCKED | PASS | 1.52s | 20,768 | 52 |
| STEP-05 | checklist_assembler | PENDING | — | — | — | — |
| STEP-06 | checkoff_agent | PENDING | — | — | — | — |

**Totals:** 3 agent call(s), 67,754 input tokens, 945 output tokens, 10.35s cumulative.

**Recorded responses:**
- STEP-02 → `tests/recorded_responses/full_pipeline/pipeline_8__it_security_agent__scenario_escalated_step4_demo_pass.json`
- STEP-03 → `tests/recorded_responses/full_pipeline/pipeline_8__legal_agent__scenario_escalated_step4_demo_pass.json`
- STEP-04 → `tests/recorded_responses/full_pipeline/pipeline_8__procurement_agent__scenario_escalated_step4_demo_pass.json`
## Pipeline Run #9 — scenario_escalated_step4_demo — 2026-04-27
**Overall verdict:** PASS
**Supervisor status:** ESCALATED
**Pipeline run id:** run_baa1f4802d
**Halted at:** STEP-04

| Step | Agent | Status | Verdict | Elapsed | In tokens | Out tokens |
|------|-------|--------|---------|---------|-----------|------------|
| STEP-01 | intake (deterministic) | COMPLETE | n/a | — | — | — |
| STEP-02 | it_security_agent | COMPLETE | PASS | 4.83s | 26,043 | 586 |
| STEP-03 | legal_agent | COMPLETE | PASS | 1.47s | 20,873 | 154 |
| STEP-04 | procurement_agent | ESCALATED | PASS | 1.21s | 18,980 | 68 |
| STEP-05 | checklist_assembler | PENDING | — | — | — | — |
| STEP-06 | checkoff_agent | PENDING | — | — | — | — |

**Totals:** 3 agent call(s), 65,896 input tokens, 808 output tokens, 7.52s cumulative.

**Recorded responses:**
- STEP-02 → `tests/recorded_responses/full_pipeline/pipeline_9__it_security_agent__scenario_escalated_step4_demo_pass.json`
- STEP-03 → `tests/recorded_responses/full_pipeline/pipeline_9__legal_agent__scenario_escalated_step4_demo_pass.json`
- STEP-04 → `tests/recorded_responses/full_pipeline/pipeline_9__procurement_agent__scenario_escalated_step4_demo_pass.json`
## Pipeline Run #18 — scenario_1 — 2026-04-29
**Overall verdict:** PASS
**Supervisor status:** ESCALATED
**Pipeline run id:** run_f34d44fae2
**Halted at:** STEP-04

| Step | Agent | Status | Verdict | Elapsed | In tokens | Out tokens |
|------|-------|--------|---------|---------|-----------|------------|
| STEP-01 | intake (deterministic) | COMPLETE | n/a | — | — | — |
| STEP-02 | it_security_agent | COMPLETE | PASS | 2.72s | 20,196 | 224 |
| STEP-03 | legal_agent | COMPLETE | PASS | 2.21s | 19,704 | 158 |
| STEP-04 | procurement_agent | ESCALATED | PASS | 1.43s | 22,019 | 68 |
| STEP-05 | checklist_assembler | PENDING | — | — | — | — |
| STEP-06 | checkoff_agent | PENDING | — | — | — | — |

**Totals:** 3 agent call(s), 61,919 input tokens, 450 output tokens, 6.36s cumulative.

**Recorded responses:**
- STEP-02 → `tests/recorded_responses/full_pipeline/pipeline_18__it_security_agent__scenario_1_pass.json`
- STEP-03 → `tests/recorded_responses/full_pipeline/pipeline_18__legal_agent__scenario_1_pass.json`
- STEP-04 → `tests/recorded_responses/full_pipeline/pipeline_18__procurement_agent__scenario_1_pass.json`
## Pipeline Run #19 — scenario_2 — 2026-04-29
**Overall verdict:** PASS
**Supervisor status:** ESCALATED
**Pipeline run id:** run_6bd6c20ca3
**Halted at:** STEP-03

| Step | Agent | Status | Verdict | Elapsed | In tokens | Out tokens |
|------|-------|--------|---------|---------|-----------|------------|
| STEP-01 | intake (deterministic) | COMPLETE | n/a | — | — | — |
| STEP-02 | it_security_agent | COMPLETE | PASS | 29.89s | 20,230 | 606 |
| STEP-03 | legal_agent | ESCALATED | PASS | 19.28s | 19,842 | 328 |
| STEP-04 | procurement_agent | PENDING | — | — | — | — |
| STEP-05 | checklist_assembler | PENDING | — | — | — | — |
| STEP-06 | checkoff_agent | PENDING | — | — | — | — |

**Totals:** 2 agent call(s), 40,072 input tokens, 934 output tokens, 49.18s cumulative.

**Recorded responses:**
- STEP-02 → `tests/recorded_responses/full_pipeline/pipeline_19__it_security_agent__scenario_2_pass.json`
- STEP-03 → `tests/recorded_responses/full_pipeline/pipeline_19__legal_agent__scenario_2_pass.json`
## Pipeline Run #20 — scenario_blocked_demo — 2026-04-29
**Overall verdict:** PASS
**Supervisor status:** BLOCKED
**Pipeline run id:** run_c5411eb653
**Halted at:** STEP-04

| Step | Agent | Status | Verdict | Elapsed | In tokens | Out tokens |
|------|-------|--------|---------|---------|-----------|------------|
| STEP-01 | intake (deterministic) | COMPLETE | n/a | — | — | — |
| STEP-02 | it_security_agent | COMPLETE | PASS | 31.53s | 26,043 | 609 |
| STEP-03 | legal_agent | COMPLETE | PASS | 24.48s | 20,943 | 154 |
| STEP-04 | procurement_agent | BLOCKED | PASS | 22.75s | 18,079 | 51 |
| STEP-05 | checklist_assembler | PENDING | — | — | — | — |
| STEP-06 | checkoff_agent | PENDING | — | — | — | — |

**Totals:** 3 agent call(s), 65,065 input tokens, 814 output tokens, 78.77s cumulative.

**Recorded responses:**
- STEP-02 → `tests/recorded_responses/full_pipeline/pipeline_20__it_security_agent__scenario_blocked_demo_pass.json`
- STEP-03 → `tests/recorded_responses/full_pipeline/pipeline_20__legal_agent__scenario_blocked_demo_pass.json`
- STEP-04 → `tests/recorded_responses/full_pipeline/pipeline_20__procurement_agent__scenario_blocked_demo_pass.json`
## Pipeline Run #21 — scenario_escalated_step4_demo — 2026-04-29
**Overall verdict:** PASS
**Supervisor status:** ESCALATED
**Pipeline run id:** run_7cb7d49a0d
**Halted at:** STEP-04

| Step | Agent | Status | Verdict | Elapsed | In tokens | Out tokens |
|------|-------|--------|---------|---------|-----------|------------|
| STEP-01 | intake (deterministic) | COMPLETE | n/a | — | — | — |
| STEP-02 | it_security_agent | COMPLETE | PASS | 30.75s | 26,043 | 527 |
| STEP-03 | legal_agent | COMPLETE | PASS | 24.57s | 20,873 | 154 |
| STEP-04 | procurement_agent | ESCALATED | PASS | 23.65s | 20,360 | 67 |
| STEP-05 | checklist_assembler | PENDING | — | — | — | — |
| STEP-06 | checkoff_agent | PENDING | — | — | — | — |

**Totals:** 3 agent call(s), 67,276 input tokens, 748 output tokens, 78.97s cumulative.

**Recorded responses:**
- STEP-02 → `tests/recorded_responses/full_pipeline/pipeline_21__it_security_agent__scenario_escalated_step4_demo_pass.json`
- STEP-03 → `tests/recorded_responses/full_pipeline/pipeline_21__legal_agent__scenario_escalated_step4_demo_pass.json`
- STEP-04 → `tests/recorded_responses/full_pipeline/pipeline_21__procurement_agent__scenario_escalated_step4_demo_pass.json`
## Pipeline Run #22 — scenario_1 — 2026-04-30
**Overall verdict:** FAIL
**Supervisor status:** COMPLETE
**Pipeline run id:** run_d389b807a4

| Step | Agent | Status | Verdict | Elapsed | In tokens | Out tokens |
|------|-------|--------|---------|---------|-----------|------------|
| STEP-01 | intake (deterministic) | COMPLETE | n/a | — | — | — |
| STEP-02 | it_security_agent | COMPLETE | PASS | 3.20s | 20,196 | 290 |
| STEP-03 | legal_agent | COMPLETE | PASS | 1.68s | 19,770 | 158 |
| STEP-04 | procurement_agent | COMPLETE | FAIL | 3.56s | 34,126 | 354 |
| STEP-05 | checklist_assembler | COMPLETE | PASS | 58.76s | 51,732 | 611 |
| STEP-06 | checkoff_agent | COMPLETE | PASS | 37.11s | 7,699 | 964 |

**Totals:** 5 agent call(s), 133,523 input tokens, 2,377 output tokens, 104.32s cumulative.

**Per-step failures:**
- [STEP-04] scenario_1: PRIMARY PAM-001 row_id='C-T2' does NOT match the vendor profile's primary keys (vendor_class='Class C', integration_tier='TIER_1' → expected row_id='C-T1'). Per §8.3 strict primary-key matching, substituting a non-matching row when a matching row is present in the candidate set is silent wrong-row selection — the Class-level mirror of scenario_7's silent path fabrication failure mode. §14 A-04: no approval_path may be asserted from a row that does not match on both primary keys.

**Recorded responses:**
- STEP-02 → `tests/recorded_responses/full_pipeline/pipeline_22__it_security_agent__scenario_1_pass.json`
- STEP-03 → `tests/recorded_responses/full_pipeline/pipeline_22__legal_agent__scenario_1_pass.json`
- STEP-04 → `tests/recorded_responses/full_pipeline/pipeline_22__procurement_agent__scenario_1_fail.json`
- STEP-05 → `tests/recorded_responses/full_pipeline/pipeline_22__checklist_assembler__scenario_1_pass.json`
- STEP-06 → `tests/recorded_responses/full_pipeline/pipeline_22__checkoff_agent__scenario_1_pass.json`
## Pipeline Run #23 — scenario_2 — 2026-04-30
**Overall verdict:** PASS
**Supervisor status:** ESCALATED
**Pipeline run id:** run_6ba1ba0b72
**Halted at:** STEP-03

| Step | Agent | Status | Verdict | Elapsed | In tokens | Out tokens |
|------|-------|--------|---------|---------|-----------|------------|
| STEP-01 | intake (deterministic) | COMPLETE | n/a | — | — | — |
| STEP-02 | it_security_agent | COMPLETE | PASS | 4.93s | 20,230 | 661 |
| STEP-03 | legal_agent | ESCALATED | PASS | 30.98s | 19,842 | 328 |
| STEP-04 | procurement_agent | PENDING | — | — | — | — |
| STEP-05 | checklist_assembler | PENDING | — | — | — | — |
| STEP-06 | checkoff_agent | PENDING | — | — | — | — |

**Totals:** 2 agent call(s), 40,072 input tokens, 989 output tokens, 35.91s cumulative.

**Recorded responses:**
- STEP-02 → `tests/recorded_responses/full_pipeline/pipeline_23__it_security_agent__scenario_2_pass.json`
- STEP-03 → `tests/recorded_responses/full_pipeline/pipeline_23__legal_agent__scenario_2_pass.json`
## Pipeline Run #24 — scenario_blocked_demo — 2026-04-30
**Overall verdict:** PASS
**Supervisor status:** BLOCKED
**Pipeline run id:** run_605da83c92
**Halted at:** STEP-04

| Step | Agent | Status | Verdict | Elapsed | In tokens | Out tokens |
|------|-------|--------|---------|---------|-----------|------------|
| STEP-01 | intake (deterministic) | COMPLETE | n/a | — | — | — |
| STEP-02 | it_security_agent | COMPLETE | PASS | 34.02s | 26,043 | 696 |
| STEP-03 | legal_agent | COMPLETE | PASS | 22.56s | 20,943 | 154 |
| STEP-04 | procurement_agent | BLOCKED | PASS | 21.39s | 18,079 | 51 |
| STEP-05 | checklist_assembler | PENDING | — | — | — | — |
| STEP-06 | checkoff_agent | PENDING | — | — | — | — |

**Totals:** 3 agent call(s), 65,065 input tokens, 901 output tokens, 77.97s cumulative.

**Recorded responses:**
- STEP-02 → `tests/recorded_responses/full_pipeline/pipeline_24__it_security_agent__scenario_blocked_demo_pass.json`
- STEP-03 → `tests/recorded_responses/full_pipeline/pipeline_24__legal_agent__scenario_blocked_demo_pass.json`
- STEP-04 → `tests/recorded_responses/full_pipeline/pipeline_24__procurement_agent__scenario_blocked_demo_pass.json`
## Pipeline Run #25 — scenario_escalated_step4_demo — 2026-04-30
**Overall verdict:** PASS
**Supervisor status:** ESCALATED
**Pipeline run id:** run_876bbc7ebd
**Halted at:** STEP-04

| Step | Agent | Status | Verdict | Elapsed | In tokens | Out tokens |
|------|-------|--------|---------|---------|-----------|------------|
| STEP-01 | intake (deterministic) | COMPLETE | n/a | — | — | — |
| STEP-02 | it_security_agent | COMPLETE | PASS | 33.33s | 26,043 | 586 |
| STEP-03 | legal_agent | COMPLETE | PASS | 23.10s | 20,873 | 154 |
| STEP-04 | procurement_agent | ESCALATED | PASS | 23.48s | 20,360 | 67 |
| STEP-05 | checklist_assembler | PENDING | — | — | — | — |
| STEP-06 | checkoff_agent | PENDING | — | — | — | — |

**Totals:** 3 agent call(s), 67,276 input tokens, 807 output tokens, 79.92s cumulative.

**Recorded responses:**
- STEP-02 → `tests/recorded_responses/full_pipeline/pipeline_25__it_security_agent__scenario_escalated_step4_demo_pass.json`
- STEP-03 → `tests/recorded_responses/full_pipeline/pipeline_25__legal_agent__scenario_escalated_step4_demo_pass.json`
- STEP-04 → `tests/recorded_responses/full_pipeline/pipeline_25__procurement_agent__scenario_escalated_step4_demo_pass.json`
## Pipeline Run #26 — scenario_1 — 2026-04-30
**Overall verdict:** FAIL
**Supervisor status:** COMPLETE
**Pipeline run id:** run_b05ae34d2d

| Step | Agent | Status | Verdict | Elapsed | In tokens | Out tokens |
|------|-------|--------|---------|---------|-----------|------------|
| STEP-01 | intake (deterministic) | COMPLETE | n/a | — | — | — |
| STEP-02 | it_security_agent | COMPLETE | PASS | 3.01s | 20,590 | 290 |
| STEP-03 | legal_agent | COMPLETE | PASS | 1.92s | 19,770 | 158 |
| STEP-04 | procurement_agent | COMPLETE | FAIL | 3.37s | 34,126 | 352 |
| STEP-05 | checklist_assembler | COMPLETE | PASS | 59.37s | 51,773 | 612 |
| STEP-06 | checkoff_agent | COMPLETE | PASS | 38.66s | 7,701 | 960 |

**Totals:** 5 agent call(s), 133,960 input tokens, 2,372 output tokens, 106.34s cumulative.

**Per-step failures:**
- [STEP-04] scenario_1: PRIMARY PAM-001 row_id='C-T2' does NOT match the vendor profile's primary keys (vendor_class='Class C', integration_tier='TIER_1' → expected row_id='C-T1'). Per §8.3 strict primary-key matching, substituting a non-matching row when a matching row is present in the candidate set is silent wrong-row selection — the Class-level mirror of scenario_7's silent path fabrication failure mode. §14 A-04: no approval_path may be asserted from a row that does not match on both primary keys.

**Recorded responses:**
- STEP-02 → `tests/recorded_responses/full_pipeline/pipeline_26__it_security_agent__scenario_1_pass.json`
- STEP-03 → `tests/recorded_responses/full_pipeline/pipeline_26__legal_agent__scenario_1_pass.json`
- STEP-04 → `tests/recorded_responses/full_pipeline/pipeline_26__procurement_agent__scenario_1_fail.json`
- STEP-05 → `tests/recorded_responses/full_pipeline/pipeline_26__checklist_assembler__scenario_1_pass.json`
- STEP-06 → `tests/recorded_responses/full_pipeline/pipeline_26__checkoff_agent__scenario_1_pass.json`
## Pipeline Run #27 — scenario_2 — 2026-04-30
**Overall verdict:** PASS
**Supervisor status:** ESCALATED
**Pipeline run id:** run_1247dc1222
**Halted at:** STEP-03

| Step | Agent | Status | Verdict | Elapsed | In tokens | Out tokens |
|------|-------|--------|---------|---------|-----------|------------|
| STEP-01 | intake (deterministic) | COMPLETE | n/a | — | — | — |
| STEP-02 | it_security_agent | COMPLETE | PASS | 6.08s | 20,624 | 702 |
| STEP-03 | legal_agent | ESCALATED | PASS | 28.95s | 19,842 | 328 |
| STEP-04 | procurement_agent | PENDING | — | — | — | — |
| STEP-05 | checklist_assembler | PENDING | — | — | — | — |
| STEP-06 | checkoff_agent | PENDING | — | — | — | — |

**Totals:** 2 agent call(s), 40,466 input tokens, 1,030 output tokens, 35.03s cumulative.

**Recorded responses:**
- STEP-02 → `tests/recorded_responses/full_pipeline/pipeline_27__it_security_agent__scenario_2_pass.json`
- STEP-03 → `tests/recorded_responses/full_pipeline/pipeline_27__legal_agent__scenario_2_pass.json`
## Pipeline Run #28 — scenario_blocked_demo — 2026-04-30
**Overall verdict:** PASS
**Supervisor status:** BLOCKED
**Pipeline run id:** run_269b14ab88
**Halted at:** STEP-04

| Step | Agent | Status | Verdict | Elapsed | In tokens | Out tokens |
|------|-------|--------|---------|---------|-----------|------------|
| STEP-01 | intake (deterministic) | COMPLETE | n/a | — | — | — |
| STEP-02 | it_security_agent | COMPLETE | PASS | 33.91s | 26,437 | 718 |
| STEP-03 | legal_agent | COMPLETE | PASS | 22.65s | 20,943 | 154 |
| STEP-04 | procurement_agent | BLOCKED | PASS | 23.28s | 18,079 | 51 |
| STEP-05 | checklist_assembler | PENDING | — | — | — | — |
| STEP-06 | checkoff_agent | PENDING | — | — | — | — |

**Totals:** 3 agent call(s), 65,459 input tokens, 923 output tokens, 79.84s cumulative.

**Recorded responses:**
- STEP-02 → `tests/recorded_responses/full_pipeline/pipeline_28__it_security_agent__scenario_blocked_demo_pass.json`
- STEP-03 → `tests/recorded_responses/full_pipeline/pipeline_28__legal_agent__scenario_blocked_demo_pass.json`
- STEP-04 → `tests/recorded_responses/full_pipeline/pipeline_28__procurement_agent__scenario_blocked_demo_pass.json`
## Pipeline Run #29 — scenario_escalated_step4_demo — 2026-04-30
**Overall verdict:** PASS
**Supervisor status:** ESCALATED
**Pipeline run id:** run_5847f6845c
**Halted at:** STEP-04

| Step | Agent | Status | Verdict | Elapsed | In tokens | Out tokens |
|------|-------|--------|---------|---------|-----------|------------|
| STEP-01 | intake (deterministic) | COMPLETE | n/a | — | — | — |
| STEP-02 | it_security_agent | COMPLETE | PASS | 31.44s | 26,437 | 470 |
| STEP-03 | legal_agent | COMPLETE | PASS | 24.46s | 20,873 | 154 |
| STEP-04 | procurement_agent | ESCALATED | PASS | 23.91s | 20,360 | 67 |
| STEP-05 | checklist_assembler | PENDING | — | — | — | — |
| STEP-06 | checkoff_agent | PENDING | — | — | — | — |

**Totals:** 3 agent call(s), 67,670 input tokens, 691 output tokens, 79.81s cumulative.

**Recorded responses:**
- STEP-02 → `tests/recorded_responses/full_pipeline/pipeline_29__it_security_agent__scenario_escalated_step4_demo_pass.json`
- STEP-03 → `tests/recorded_responses/full_pipeline/pipeline_29__legal_agent__scenario_escalated_step4_demo_pass.json`
- STEP-04 → `tests/recorded_responses/full_pipeline/pipeline_29__procurement_agent__scenario_escalated_step4_demo_pass.json`
## Pipeline Run #30 — scenario_1 — 2026-04-30
**Overall verdict:** FAIL
**Supervisor status:** COMPLETE
**Pipeline run id:** run_de83b8f284

| Step | Agent | Status | Verdict | Elapsed | In tokens | Out tokens |
|------|-------|--------|---------|---------|-----------|------------|
| STEP-01 | intake (deterministic) | COMPLETE | n/a | — | — | — |
| STEP-02 | it_security_agent | COMPLETE | PASS | 2.67s | 20,670 | 298 |
| STEP-03 | legal_agent | COMPLETE | PASS | 2.10s | 19,778 | 158 |
| STEP-04 | procurement_agent | COMPLETE | FAIL | 3.10s | 34,134 | 351 |
| STEP-05 | checklist_assembler | COMPLETE | PASS | 60.56s | 51,729 | 615 |
| STEP-06 | checkoff_agent | COMPLETE | PASS | 38.71s | 7,708 | 1,151 |

**Totals:** 5 agent call(s), 134,019 input tokens, 2,573 output tokens, 107.14s cumulative.

**Per-step failures:**
- [STEP-04] scenario_1: PRIMARY PAM-001 row_id='C-T2' does NOT match the vendor profile's primary keys (vendor_class='Class C', integration_tier='TIER_1' → expected row_id='C-T1'). Per §8.3 strict primary-key matching, substituting a non-matching row when a matching row is present in the candidate set is silent wrong-row selection — the Class-level mirror of scenario_7's silent path fabrication failure mode. §14 A-04: no approval_path may be asserted from a row that does not match on both primary keys.

**Recorded responses:**
- STEP-02 → `tests/recorded_responses/full_pipeline/pipeline_30__it_security_agent__scenario_1_pass.json`
- STEP-03 → `tests/recorded_responses/full_pipeline/pipeline_30__legal_agent__scenario_1_pass.json`
- STEP-04 → `tests/recorded_responses/full_pipeline/pipeline_30__procurement_agent__scenario_1_fail.json`
- STEP-05 → `tests/recorded_responses/full_pipeline/pipeline_30__checklist_assembler__scenario_1_pass.json`
- STEP-06 → `tests/recorded_responses/full_pipeline/pipeline_30__checkoff_agent__scenario_1_pass.json`
## Pipeline Run #31 — scenario_1 — 2026-04-30
**Overall verdict:** FAIL
**Supervisor status:** COMPLETE
**Pipeline run id:** run_6a16fea73a

| Step | Agent | Status | Verdict | Elapsed | In tokens | Out tokens |
|------|-------|--------|---------|---------|-----------|------------|
| STEP-01 | intake (deterministic) | COMPLETE | n/a | — | — | — |
| STEP-02 | it_security_agent | COMPLETE | PASS | 6.07s | 20,670 | 552 |
| STEP-03 | legal_agent | COMPLETE | PASS | 1.90s | 19,770 | 158 |
| STEP-04 | procurement_agent | COMPLETE | FAIL | 3.61s | 34,126 | 356 |
| STEP-05 | checklist_assembler | COMPLETE | PASS | 56.51s | 52,316 | 873 |
| STEP-06 | checkoff_agent | COMPLETE | PASS | 46.00s | 8,240 | 1,778 |

**Totals:** 5 agent call(s), 135,122 input tokens, 3,717 output tokens, 114.09s cumulative.

**Per-step failures:**
- [STEP-04] scenario_1: PRIMARY PAM-001 row_id='C-T2' does NOT match the vendor profile's primary keys (vendor_class='Class C', integration_tier='TIER_1' → expected row_id='C-T1'). Per §8.3 strict primary-key matching, substituting a non-matching row when a matching row is present in the candidate set is silent wrong-row selection — the Class-level mirror of scenario_7's silent path fabrication failure mode. §14 A-04: no approval_path may be asserted from a row that does not match on both primary keys.

**Recorded responses:**
- STEP-02 → `tests/recorded_responses/full_pipeline/pipeline_31__it_security_agent__scenario_1_pass.json`
- STEP-03 → `tests/recorded_responses/full_pipeline/pipeline_31__legal_agent__scenario_1_pass.json`
- STEP-04 → `tests/recorded_responses/full_pipeline/pipeline_31__procurement_agent__scenario_1_fail.json`
- STEP-05 → `tests/recorded_responses/full_pipeline/pipeline_31__checklist_assembler__scenario_1_pass.json`
- STEP-06 → `tests/recorded_responses/full_pipeline/pipeline_31__checkoff_agent__scenario_1_pass.json`
