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

**Notes:** optional free-text notes
```

---

