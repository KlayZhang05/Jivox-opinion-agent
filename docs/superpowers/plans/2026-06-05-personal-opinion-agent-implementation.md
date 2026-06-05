# Personal Opinion Agent Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the first runnable slice of the personal public-opinion observation agent.

**Architecture:** Implement deterministic Python core services first, then expose LangGraph-compatible orchestration skeletons. Keep data models, evidence verification, and conversation policy independent so workers can develop them in parallel.

**Tech Stack:** Python 3.11+, pytest, optional LangGraph dependency behind an adapter boundary.

---

## File Structure

- `pyproject.toml`: project metadata and pytest config.
- `opinion_agent/models.py`: dataclasses/enums for evidence, claims, briefings, and conversation policies.
- `opinion_agent/config.py`: JSON config loaders and validation.
- `opinion_agent/evidence/store.py`: JSONL evidence store.
- `opinion_agent/citations/verifier.py`: claim citation validation.
- `opinion_agent/briefing/generator.py`: low-stimulation briefing generation.
- `opinion_agent/conversation/policy.py`: bounded conversation policy validation.
- `opinion_agent/graph/runtime.py`: LangGraph-compatible skeleton that imports without LangGraph installed.
- `opinion_agent/collectors/sample.py`: deterministic sample collector.
- `opinion_agent/cli.py` and `opinion_agent/__main__.py`: CLI entry points.
- `tests/`: focused tests for each unit.

## Parallel Work Slices

### Slice 1: Core Domain, Config, Sample Briefing

Owned paths:

- `pyproject.toml`
- `opinion_agent/__init__.py`
- `opinion_agent/__main__.py`
- `opinion_agent/cli.py`
- `opinion_agent/models.py`
- `opinion_agent/config.py`
- `opinion_agent/collectors/sample.py`
- `opinion_agent/briefing/generator.py`
- `examples/briefing_plan.example.json`
- `examples/sample_evidence.jsonl`
- `tests/test_config.py`
- `tests/test_briefing.py`
- `tests/test_cli.py`

Required behavior:

- Load a briefing plan with `topic`, `keywords`, `schedule`, `max_items`, and `tone`.
- Reject empty topic or empty keywords.
- Generate a calm briefing from sample evidence.
- CLI command `python -m opinion_agent brief --plan examples/briefing_plan.example.json` writes a Markdown file under `output/briefings/`.

### Slice 2: Evidence Store And Citation Verification

Owned paths:

- `opinion_agent/evidence/__init__.py`
- `opinion_agent/evidence/store.py`
- `opinion_agent/citations/__init__.py`
- `opinion_agent/citations/verifier.py`
- `tests/test_evidence_store.py`
- `tests/test_citation_verifier.py`

Required behavior:

- Append/read evidence records as JSONL.
- Stable IDs are required.
- Duplicate evidence IDs are not written twice.
- A claim citing an unknown evidence ID is invalid.
- A claim citing existing evidence IDs is valid.
- Verification returns explicit error messages.

### Slice 3: Conversation Policy And LangGraph Skeleton

Owned paths:

- `opinion_agent/conversation/__init__.py`
- `opinion_agent/conversation/policy.py`
- `opinion_agent/graph/__init__.py`
- `opinion_agent/graph/runtime.py`
- `tests/test_conversation_policy.py`
- `tests/test_graph_runtime.py`

Required behavior:

- Validate a bounded conversation policy with topic boundary, duration minutes, principles, and allowed tools.
- Reject duration <= 0 and missing topic boundary.
- Provide `build_runtime_graph()` that returns a lightweight graph descriptor when LangGraph is unavailable.
- Keep the graph skeleton explicit about roles: forum host, query agent, database researcher, multimedia researcher, citation agent, report writer, conversation agent.

## Integration Tasks

- Ensure imports do not require network, API keys, or LangGraph installation.
- Run `python -m pytest tests -v`.
- Run the sample CLI smoke command.
- Update README with current commands and project purpose.
- Commit and push once tests pass.
