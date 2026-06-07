# Evidence Research Agent Resume Scope Design

Date: 2026-06-06
Status: Approved baseline
Supersedes: `2026-06-05-personal-opinion-agent-design.md` as the active project scope

## Positioning

Build a resume-focused public-opinion research agent that demonstrates the
complete engineering workflow for a LangGraph application.

The project is not a production monitoring platform and does not need a live
demo. Its primary deliverables are a readable GitHub repository, defensible
architecture, tested agent behavior, and a concise resume story.

## Core Demonstration

```text
research question
  -> Forum Host plans bounded research tasks
  -> fixed role registry selects eligible subagent roles
  -> real parallel LLM subagent calls
  -> role-specific Skills and Tool Sets
  -> normalized evidence records
  -> claim and citation verification
  -> evidence-grounded Markdown report
  -> inspectable execution trace
```

## Fixed Role Registry

The Forum Host may instantiate only these predefined roles:

- `forum_host`
- `query_agent`
- `database_researcher`
- `multimedia_researcher`
- `citation_agent`
- `report_writer`
- `tikhub_researcher`

Roles cannot be created at runtime. The Forum Host may omit unnecessary roles,
and start multiple instances of one role within one bounded research round.

Each role definition binds:

- a stable role ID and responsibility;
- a system prompt;
- one or more predefined Skills;
- a Tool Set whitelist;
- input and output schemas;
- a model profile ID;
- instance and tool-call limits.

The Forum Host assigns tasks but cannot modify a role's Skills or Tool Set.

## Runtime Boundary

LangGraph owns structured planning, dynamic research fan-out, worker execution,
and reducer-based fan-in. A deterministic service boundary owns evidence
persistence, Citation Agent invocation, support verification, Report Writer
ordering, and atomic artifact output.

This resume slice intentionally runs one bounded research round. Iterative
gap-driven rounds and monetary token budgets are follow-on work.

## Parallel Subagents

Subagents are real, isolated LLM calls, not role labels in one prompt.
LangGraph dynamic fan-out uses `Send` or an equivalent graph primitive. Results
are merged through explicit reducers. The execution trace records role ID,
instance ID, task, tools used, evidence IDs returned, timing, and outcome.

## Configuration Direction

Role architecture and provider credentials are independent.

The first implementation uses one shared OpenAI-compatible model profile:

- `LLM_API_KEY`
- `LLM_BASE_URL`
- `LLM_MODEL_NAME`

All roles may use this profile while remaining behaviorally distinct through
their system prompts, Skills, Tool Sets, and structured contracts. This keeps
the resume project focused on agent orchestration instead of provider routing.

The local ignored `.env` may be initialized from one already working LLM
endpoint in `D:\NLPIR\BettaFish\.env`. This is a local convenience only:
BettaFish variable names are not part of this project's public architecture.

The first web-search adapter uses whichever already configured BettaFish search
provider is selected locally. Its credentials are copied into this project's
generic provider settings. No secret value or absolute BettaFish path is
committed.

TikHub credentials remain separate because they authorize a data tool, not an
LLM role:

- `TIKHUB_API_KEY`
- `TIKHUB_BASE_URL`

Secrets live only in `.env` or process environment. `.env.example` contains
empty generic placeholders and is safe to commit.

## In Scope

- executable LangGraph workflow;
- fixed role registry;
- dynamic real parallel LLM subagents;
- role-specific Skill and Tool Set definitions;
- one web-search adapter;
- local evidence-store retrieval;
- claim/citation gate;
- Markdown report;
- execution trace;
- deterministic tests with fake model and tool adapters;
- one optional integration smoke test using real credentials.

## Explicitly Out Of Scope

- scheduled monitoring and daily briefings as the main product;
- full bounded-chat product;
- production TrendRadar ingestion;
- full TikHub implementation;
- production multimedia pipeline;
- frontend dashboard;
- vector database, message queue, or distributed scheduler;
- source-credibility and representativeness scoring.

Existing briefing and conversation code may remain as historical prototypes,
but they are not part of the active README or resume narrative.

## Resume-Level Success Criteria

The repository is ready to cite when:

1. One command runs a bounded research workflow.
2. The Forum Host chooses roles from the fixed registry.
3. At least two subagent instances execute concurrently.
4. Tool access is rejected when a role lacks permission.
5. Every report claim points to stored evidence.
6. Unsupported claims fail closed.
7. The trace makes planning, fan-out, tool use, verification, and report
   generation inspectable.
8. Unit tests run without network credentials.
9. README explains architecture, trade-offs, setup, command, sample output, and
   test results.
