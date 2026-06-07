# Real Provider Smoke Verification

Date: 2026-06-07

## Command

The ignored local `.env` supplied one OpenAI-compatible model profile and one
Anspire-compatible search profile. HTTP and HTTPS traffic used the user's
local proxy.

```powershell
python -m opinion_agent research `
  --topic "OpenAI's May 13, 2024 announcement of GPT-4o" `
  --adapter real `
  --output-dir .real-smoke
```

No credential value, request header, hidden reasoning, or full provider payload
is stored in this document.

## Result

- Run ID: `run-45ff64e0d152`
- Status: `completed`
- Research tasks: 3 `query_agent` instances
- Persisted evidence records: 23
- Final report claims: 1
- Support assessments: 1 `supported`
- Artifacts produced:
  - `evidence.jsonl`
  - `report.md`
  - `report_verification.json`
  - `trace.json`
- Sensitive trace markers checked:
  - `api_key`: absent
  - `authorization`: absent
  - `system_prompt`: absent
  - `user_prompt`: absent
  - `hidden_reasoning`: absent

## Parallel Call Evidence

The following intervals were reconstructed from each
`SubagentActionPlan` completion timestamp and recorded `duration_ms`:

| Task | Start (UTC) | End (UTC) | Duration |
|---|---|---|---:|
| `task_01_features` | 2026-06-07 07:11:27.957779 | 07:11:30.556804 | 2599.025 ms |
| `task_02_commercial` | 2026-06-07 07:11:27.958558 | 07:11:31.486303 | 3527.745 ms |
| `task_03_safety` | 2026-06-07 07:11:27.959037 | 07:11:32.412995 | 4453.958 ms |

All three real model-call intervals overlap. This confirms that the LangGraph
fan-out executed isolated worker LLM calls concurrently rather than serially.

## Gate Evidence

The Citation Agent selected one deterministic source-span candidate by ID.
Application code materialized that exact span as a `direct_quote` claim. Its
complete text occurred in the cited persisted evidence record, and the
verification sidecar recorded:

```json
{
  "evaluator": "exact_quote",
  "evaluator_version": "1.0",
  "verdict": "supported"
}
```

The generated runtime directory was intentionally excluded from Git after this
audit. Deterministic sample artifacts remain under `examples/`.
