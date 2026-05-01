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
