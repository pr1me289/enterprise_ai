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
