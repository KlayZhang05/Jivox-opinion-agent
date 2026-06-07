# Chinese Project Documentation Design

Date: 2026-06-07
Status: Approved direction

## Purpose

Create two complementary Chinese documents for an AI-related graduate-school
interview:

1. `README.zh-CN.md` introduces the repository to a GitHub visitor.
2. `docs/PROJECT_INTERVIEW_GUIDE.zh-CN.md` teaches the project deeply enough
   that its author can answer foundational, architectural, implementation,
   iteration, limitation, and challenge questions.

The documents explain the real implementation. They do not manufacture resume
claims, replace a resume, or describe planned integrations as completed work.

## Audience

The primary audience is an AI-related graduate-program interviewer who may:

- test basic knowledge of LLM applications and software engineering;
- ask why a particular architecture was chosen;
- trace data and control flow through the implementation;
- challenge whether the claimed concurrency and hallucination controls are
  real;
- ask about failed approaches, edge cases, limitations, and future research;
- inspect the GitHub repository after the interview.

The secondary audience is the project author using the guide for systematic
review.

## Document One: Chinese README

`README.zh-CN.md` will be a standalone Chinese repository entry point. It will
link to the English README and the interview guide.

It will contain:

1. project positioning and explicit scope;
2. the problem being solved;
3. architecture and end-to-end data flow;
4. fixed roles and runtime implementation status;
5. Skills, Tool Sets, structured contracts, and permission enforcement;
6. evidence identity, claim contracts, and the fail-closed support gate;
7. installation, deterministic execution, real-provider configuration, and
   generated artifacts;
8. repository structure and code-reading path;
9. testing and real-provider smoke-verification results;
10. design trade-offs, limitations, and follow-on directions.

The README will remain useful as a repository overview. It will not expand
every concept into a textbook chapter.

## Document Two: Project Interview Guide

`docs/PROJECT_INTERVIEW_GUIDE.zh-CN.md` will be a long-form, layered knowledge
manual rather than a list of polished resume bullets.

It will contain:

1. a one-page mental model of the project;
2. project motivation, scope reduction, and technical-route evolution;
3. foundational concepts:
   - LLM, Agent, tool calling, structured output, schema validation;
   - workflow versus autonomous agent;
   - multi-agent systems and temporary subagent instances;
   - LangGraph state, node, edge, `Send`, reducer, and fan-out/fan-in;
   - concurrency, parallelism, asynchronous I/O, and isolation;
   - evidence, claim, citation, support, provenance, and auditability;
4. complete control flow and data flow tied to real source files;
5. fixed role registry, Skills, Tool Sets, schemas, and least privilege;
6. two-stage worker execution and why model output cannot directly become
   evidence;
7. deterministic evidence normalization and identity;
8. citation existence versus claim support;
9. exact-quote verification, claim types, scope metadata, and fail-closed
   report generation;
10. report rendering, verification sidecar, trace sanitization, and atomic
    output;
11. concurrency implementation and proof methodology;
12. configuration, provider abstraction, and real/fake adapters;
13. testing strategy and what each test class establishes;
14. concrete failures and fixes encountered during development;
15. edge cases and adversarial boundaries;
16. trade-offs, unimplemented capabilities, invalid claims, and research
    limitations;
17. future work separated into engineering extensions and research questions;
18. layered interview questions with answer frameworks and follow-up chains;
19. 30-second, 2-minute, and 5-minute oral-explanation structures;
20. a code-reading map and glossary.

## Truth And Scope Rules

Every capability statement must use one of these implicit categories:

- **Implemented and tested:** code and deterministic tests exist.
- **Integration verified:** a real-provider smoke record exists.
- **Contract defined:** role/schema/extension point exists, but the production
  adapter is not implemented.
- **Historical prototype:** retained code exists but is outside the active
  resume scope.
- **Future work:** no claim of current completion.

The documents must state clearly that:

- the active workflow is a bounded evidence-research agent, not a production
  monitoring platform;
- the real adapter currently exposes web search;
- database, multimedia, and TikHub roles are extension contracts;
- the exact evaluator supports only direct quotes;
- claim support does not prove source truth, credibility, independence, or
  sample representativeness;
- the current implementation uses one bounded research round;
- traces are inspectable but not a complete replay/checkpoint system;
- the repository contains historical briefing and conversation prototypes
  outside the active project narrative.

## Evidence Sources

Documentation claims will be checked against:

- `README.md`;
- approved specifications and implementation plans;
- `opinion_agent/agents/`;
- `opinion_agent/graph/`;
- `opinion_agent/tools/`;
- `opinion_agent/evidence/`;
- `opinion_agent/citations/`;
- `opinion_agent/research/`;
- `opinion_agent/reports/`;
- `opinion_agent/tracing/`;
- relevant tests;
- `docs/verification/2026-06-07-real-provider-smoke.md`;
- Git history for route-evolution claims.

No secret value, ignored runtime artifact, provider request payload, or hidden
reasoning will enter either document.

## Style

- Chinese is the main language; retain exact English identifiers where they
  map to code.
- Explain fundamentals before project-specific details.
- Use diagrams, tables, examples, and question-answer structures where they
  reduce ambiguity.
- Distinguish deterministic guarantees from probabilistic model behavior.
- Prefer defensible technical language over promotional wording.
- Define terms before using them in advanced discussion.
- Link claims to source files and tests where practical.

## Verification

Before submission:

1. check all referenced paths and Markdown links;
2. scan for contradictions with the English README and current code;
3. scan for secrets and local absolute credential paths;
4. scan for placeholder text;
5. run the full test suite to ensure documentation changes did not accompany
   accidental code changes;
6. inspect Git diff and push only the intended documentation files.

## Acceptance Criteria

The work is complete when:

1. both documents exist and cross-link correctly;
2. the Chinese README can independently orient and run the repository;
3. the guide covers foundations, architecture, implementation, iteration,
   failures, edge cases, limitations, and interview questions;
4. all statements accurately distinguish implemented, verified, contracted,
   historical, and future capabilities;
5. no resume bullets are written as the primary deliverable;
6. Markdown, links, tests, Git state, and remote push are verified.
