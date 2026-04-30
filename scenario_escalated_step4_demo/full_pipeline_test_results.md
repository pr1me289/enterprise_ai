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
