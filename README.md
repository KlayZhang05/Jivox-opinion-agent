# Personal Opinion Agent

Personal Opinion Agent is a Python project for personal public-opinion observation, with LangGraph-compatible runtime hooks planned around a deterministic core.

The project goal is to provide a cleaner alternative to social-media scrolling. Social media is useful, but it is also noisy, sticky, and emotionally amplifying. This agent is designed around mental hygiene: calm briefings by default, intentional depth only when requested, and reports that are grounded in traceable evidence.

The system has three main product functions:

- scheduled low-noise briefings for social events and public-opinion signals
- bounded, time-boxed conversations when deeper judgment is needed
- evidence-grounded public-opinion reports with citation controls

Current design and implementation plan:

- `docs/superpowers/specs/2026-06-05-personal-opinion-agent-design.md`
- `docs/superpowers/plans/2026-06-05-personal-opinion-agent-implementation.md`

## Repository Scope

This repository is intentionally separate from `D:\NLPIR`.

Only code, specs, tests, examples, and documentation for the personal opinion agent should be committed here. Existing research projects, logs, API keys, exported conversations, generated reports, and unrelated workspace files should stay outside this repository.

## Suggested GitHub Repository Name

Use `personal-opinion-agent` rather than `NLPIR`.

## Current Status

First runnable slice available:

- deterministic sample briefing
- JSONL evidence store
- citation verification
- bounded conversation policy
- LangGraph-compatible runtime skeleton

## Run Locally

Run tests:

```powershell
python -m pytest tests -v
```

Generate a sample low-stimulation briefing:

```powershell
python -m opinion_agent brief --plan examples\briefing_plan.example.json
```

The generated Markdown file is written under `output/briefings/`.
