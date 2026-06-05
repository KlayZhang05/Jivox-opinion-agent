# Personal Opinion Agent MVP Design

Date: 2026-06-05

## Purpose

Build a personal public-opinion observation agent that acts as a clean information entrance for social events.

The product exists because personal observation of social events is a real need, but social media is a poor default interface. It overloads the user with low-quality information, encourages long scrolling sessions, and amplifies emotion. The agent should support mental hygiene: it should provide concise, low-stimulation briefings by default, and only open deeper analysis when the user intentionally asks for it.

The system has three main functions:

1. Scheduled briefings: collect public information on a configurable plan and generate low-cost modular briefs.
2. Bounded conversations: when the user wants depth, start a time-boxed conversation with explicit topic boundaries and configurable dialogue principles.
3. Evidence-grounded reports: write public-opinion analysis reports only from traceable evidence, with citation checks to reduce hallucinated comments and sources.

## Product Principles

- Calm by default: do not optimize for engagement, outrage, or urgency.
- User-controlled depth: brief first, deep dive only after user intent.
- Evidence before prose: reports must be assembled from verified evidence bundles.
- Bounded interaction: conversations have scope, time limits, and explicit principles.
- Critique is allowed: the model may challenge the user's assumptions and ask clarifying questions.
- Extensible data: social posts, news, web pages, reports, structured multimodal records, and future source types should fit the same evidence model.

## MVP Scope

### In Scope

- Independent Python project in this repository.
- Conservative Python implementation with testable standard-library core.
- LangGraph Runtime integration points and graph skeletons.
- Configurable briefing plan and topic definition.
- Local sample collector for deterministic development.
- Normalized event, source item, evidence, citation, report, and conversation models.
- JSONL evidence store.
- Citation verifier that rejects report claims without supporting evidence IDs.
- Basic briefing generation from collected evidence.
- Bounded conversation session policy: topic boundary, duration, principles, and source access policy.
- Tests for config, evidence storage, citation verification, briefing generation, and conversation policy.

### Out Of Scope For First MVP

- Production TikHub API ingestion.
- Full web dashboard.
- Real-time browser automation UI.
- Complex private databases.
- Fully autonomous large-scale crawler.
- Unverified LLM-only report writing.

## Architecture

The implementation should be modular and agent-role oriented without hard-coding permanent team structures.

Planned roles:

- Forum Host / Research Lead: decomposes research tasks and coordinates temporary sub-agent threads.
- Query Agent: searches news and web sources.
- Database Research Agent: retrieves previously collected evidence and prior reports.
- Multimedia Research Agent: placeholder for image, video, and structured multimodal understanding.
- TikHub Agent: future adapter for TikHub API social-media data.
- Citation Agent: builds evidence bundles and verifies claim-to-source support.
- Report Writer Agent: writes only from verified evidence bundles.
- Conversation Agent: runs bounded conversations under configurable dialogue principles.

MVP implementation should provide deterministic Python services first, then wrap them with LangGraph nodes. LLM calls should remain optional until the evidence layer is reliable.

## Evidence Model

Every external fact, post, comment, or media observation must become an evidence record before it can be used in reports.

Required fields:

- `evidence_id`: stable ID.
- `source_type`: `news`, `social_post`, `comment`, `web_page`, `report`, `multimodal_record`, or `sample`.
- `source_name`: platform or dataset name.
- `url`: optional source URL.
- `author`: optional author or account.
- `published_at`: optional ISO timestamp.
- `collected_at`: ISO timestamp.
- `title`: optional title.
- `content`: text content or extracted description.
- `metadata`: source-specific JSON object.

Claims in reports must cite one or more `evidence_id` values. The citation verifier must fail closed: if an evidence ID does not exist, the claim is invalid.

## Core Data Flow

```text
briefing plan
  -> collectors
  -> evidence normalization
  -> evidence store
  -> low-stimulation briefing

deep-dive request
  -> bounded conversation session
  -> query/database/multimedia tools
  -> evidence store
  -> verified claims
  -> report draft
  -> citation verification
```

## LangGraph Direction

Use LangGraph Runtime conservatively:

- Graph state should contain topic, constraints, evidence IDs, verified claims, and output paths.
- Deterministic Python tools should own parsing, storage, citation checks, and report assembly.
- LLM nodes should decide strategy and prose, not invent evidence.
- Temporary sub-agent threads should be created by the Forum Host based on task needs, not by fixed dead roles.

## Delivery Criteria For The First Development Slice

The first working slice is complete when:

- The package imports as `opinion_agent`.
- `python -m pytest tests -v` passes.
- A sample briefing can be generated from local sample evidence.
- A claim with a missing evidence ID is rejected by tests.
- A bounded conversation session config validates topic, duration, and principles.
- README explains the personal mental-hygiene purpose and current commands.

## Future Extensions

- Real TrendRadar collector.
- TikHub API collector.
- Web search/browser collector.
- LLM report writer with citation-gated generation.
- Scheduled daily briefings.
- Conversation transcript export.
- Streamlit or browser dashboard.
- Multimodal extraction pipeline.
