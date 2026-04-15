# LLM Agent Testing Procedure

## Pre-Run Rule — No Exceptions

Before any live API call, tell me exactly which agent, which test file, and which fixture you are about to run. Wait for explicit confirmation before proceeding. Do not run `pytest -m api`, any live API call, the per-agent test environment, or the full pipeline automatically under any circumstances.

## Scope Rules

- Run the smallest possible scope: one agent, one fixture, one scenario at a time
- Only escalate to a broader scope after I confirm the narrow run passed
- Never run the full end-to-end pipeline more than once per scenario without my explicit instruction
- Do not loop, retry, or re-run anything on failure — stop and report what failed

## Response Recording

Record every raw API response to `tests/recorded_responses/` before any evaluation logic runs. If a test needs to be re-run for any reason other than a change to the bundle, system prompt, or model, load the recorded response instead of calling the API again.

## Results Logging

After each confirmed test run, append a brief entry to `results/test_results.md` using this structure:

```
## [Agent Name] — [Scenario] — [Date]
**Status:** PASS / FAIL
**Required fields present:** YES / NO — list any missing
**Status signal:** complete / escalated / blocked — expected vs. actual
**Semantic validity:** PASS / FAIL — one line on any contradiction found
**Notes:** one or two sentences max on anything notable or flagged
```

Keep entries short. The recorded response is the source of truth — the results file is a summary only. Evaluations must stay consistent with `llm_agent_output_evaluation_checklist.md`.
