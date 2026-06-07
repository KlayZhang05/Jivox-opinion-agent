# JiWen Opinion Agent



LangGraph-based evidence-constrained public-opinion research agent with
dynamic parallel subagents.

![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white)
![LangGraph](https://img.shields.io/badge/LangGraph-Agent_Runtime-1C3C3C)
![Pydantic](https://img.shields.io/badge/Pydantic-Structured_Output-E92063)
![Tests](https://img.shields.io/badge/tests-99%20passed-2EA44F)

[简体中文](README.zh-CN.md) | English

## Architecture

```text
research topic
  -> Forum Host: structured ResearchPlan
  -> LangGraph Send fan-out
       -> query_agent instance A -> authorized tools -> evidence
       -> query_agent instance B -> authorized tools -> evidence
       -> other registered research roles when adapters are available
  -> reducer fan-in
  -> deterministic candidate spans
  -> Citation Agent: candidate ID selection
  -> code materializes atomic ClaimInput records
  -> citation existence + claim support verification
  -> Report Writer: verified-claim ordering only
  -> Markdown report + verification JSON + evidence JSONL + trace JSON
```

The concurrency test uses an `asyncio.Event` barrier to prove that two worker
LLM calls overlap. It does not infer concurrency from elapsed time.

## Fixed Roles

Runtime role creation is prohibited. The immutable registry contains:

| Role | Responsibility | Current runtime status |
|---|---|---|
| `forum_host` | Plan bounded research and select registered roles | Active |
| `query_agent` | Retrieve attributable web material | Active |
| `database_researcher` | Retrieve prior local evidence | Contract defined |
| `multimedia_researcher` | Inspect bounded media evidence | Contract defined |
| `citation_agent` | Atomize claims and audit support | Active |
| `report_writer` | Order verified claims without adding new claims | Active |
| `tikhub_researcher` | Collect bounded social records through TikHub | Contract defined |

Each role binds a system prompt, predefined Skills, a Tool Set whitelist,
structured input/output schemas, and an instance limit. The Forum Host can
choose among registered research roles and create multiple instances, but
cannot invent a role or modify its permissions.

The runnable real adapter currently exposes `web_search`. Database,
multimedia, and TikHub tool adapters are explicit extension points, not
simulated production integrations.

## Evidence Controls

The worker path is deliberately two-stage:

1. The LLM proposes structured tool calls.
2. Deterministic code enforces the role Tool Set and executes tools.
3. Tool output receives stable evidence IDs.
4. The LLM summarizes only those results and may cite only generated IDs.

A model-generated or unknown evidence ID is rejected.

Reports use a separate claim support gate:

- `ClaimInput` declares `claim_type`, optional `scope`, and evidence IDs.
- The Citation Agent selects a bounded candidate ID; it cannot author quote
  text or evidence IDs.
- Deterministic code materializes the exact source span as `ClaimInput.text`.
- `ExactQuoteEvaluator` supports only `direct_quote`.
- `factual_statement`, `opinion_summary`, and `analytic_inference` return
  `indeterminate` until a semantic evaluator is configured.
- Supporting spans are checked against persisted evidence text.
- Any malformed, missing, unsupported, contradicted, or indeterminate claim
  prevents all report artifacts.

This proves source-span support within declared scope. It does not prove that a
source is truthful or that a sample represents the wider population.

## Run

Requires Python 3.11 or newer.

```powershell
python -m pip install -e ".[test]"
python -m pytest tests -q
```

Run the complete deterministic pipeline without credentials:

```powershell
python -m opinion_agent research `
  --topic "A bounded social event" `
  --adapter fake `
  --output-dir output\research
```

Run with an OpenAI-compatible model and Anspire-compatible search endpoint:

```powershell
Copy-Item .env.example .env
# Fill generic LLM_* and SEARCH_* values locally.
python -m opinion_agent research `
  --topic "A bounded social event" `
  --output-dir output\research
```

Each run creates:

```text
output/research/run-<id>/
  evidence.jsonl
  report.md
  report_verification.json
  trace.json
```

`trace.json` records UTC event times, model/tool durations, role instances,
fan-out/fan-in, evidence IDs, verification verdicts, and report completion. It
omits API keys, prompts, authorization headers, and hidden reasoning.

## Repository Map

```text
opinion_agent/
  agents/       fixed roles, Skills, and structured contracts
  graph/        LangGraph StateGraph, Send fan-out, reducers
  tools/        registry, permission gate, search adapter
  evidence/     stable normalization and append-only JSONL store
  citations/    claim contracts and support evaluators
  research/     end-to-end orchestration and fake/real factories
  reports/      fail-closed Markdown and verification sidecar
  tracing/      sanitized atomic JSON trace
tests/          deterministic unit, concurrency, and end-to-end tests
```

The approved active scope is documented in
`docs/superpowers/specs/2026-06-06-evidence-research-agent-resume-scope-design.md`.
A successful real-provider integration run, including measured overlapping
worker call intervals, is recorded in
`docs/verification/2026-06-07-real-provider-smoke.md`.

## Design Trade-offs

- One shared model profile keeps the project focused on orchestration;
  behavioral specialization comes from role prompts, Skills, Tool Sets, and
  schemas.
- JSONL is sufficient for auditable local evidence and avoids adding a
  database that does not strengthen the portfolio story.
- Exact quote verification is narrow but reproducible. The evaluator protocol
  leaves room for a later LLM or NLI semantic verifier without weakening the
  current gate.
- Source credibility, representativeness, scheduling, a frontend, production
  multimedia ingestion, and full TikHub ingestion are out of scope.

## Resume Summary

- Built a LangGraph public-opinion research agent using structured planning,
  dynamic `Send` fan-out, reducer-based fan-in, and real parallel LLM
  subagent calls selected from an immutable role registry.
- Designed role-scoped Skills and Tool Sets, deterministic evidence identity,
  fail-closed claim support verification, and inspectable sanitized traces for
  auditable report generation.

## Historical Prototypes

The repository retains earlier deterministic `brief`, `report`, and
`conversation` commands for experimentation. They are not part of the active
resume scope; `research` is the primary workflow.
