# Chinese Project Documentation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a Chinese repository README and a comprehensive graduate-interview project guide grounded in the current implementation.

**Architecture:** Keep the public repository overview and the study manual separate. Build both documents from a shared fact map covering runtime code, tests, specifications, Git history, and the real-provider smoke record; then cross-check capability status, links, terminology, and security boundaries before pushing.

**Tech Stack:** Markdown, Python 3.11+, LangGraph, Pydantic, pytest, Git

---

### Task 1: Build The Implementation Fact Map

**Files:**
- Read: `README.md`
- Read: `docs/superpowers/specs/2026-06-06-evidence-research-agent-resume-scope-design.md`
- Read: `docs/superpowers/specs/2026-06-06-claim-evidence-support-gate-design.md`
- Read: `docs/verification/2026-06-07-real-provider-smoke.md`
- Read: `opinion_agent/agents/`
- Read: `opinion_agent/graph/`
- Read: `opinion_agent/tools/`
- Read: `opinion_agent/evidence/`
- Read: `opinion_agent/citations/`
- Read: `opinion_agent/research/`
- Read: `opinion_agent/reports/`
- Read: `opinion_agent/tracing/`
- Read: `tests/`

- [ ] **Step 1: Map each active capability to code and tests**

Record the source path and verification path for fixed roles, Skills, Tool
Sets, graph fan-out/fan-in, permission checks, evidence normalization,
claim-support verification, reporting, tracing, and real/fake adapters.

- [ ] **Step 2: Classify every capability statement**

Use exactly these categories while drafting:

```text
implemented and tested
real-provider integration verified
contract defined but adapter not implemented
historical prototype outside active scope
future work
```

- [ ] **Step 3: Extract route-evolution evidence**

Use the specifications and Git log to explain the shift from a broad personal
opinion-monitoring product to a bounded, auditable evidence-research slice.

- [ ] **Step 4: Check the fact map against the English README**

Ensure no Chinese statement expands the current English claims about TikHub,
multimedia, database retrieval, semantic support, replayability, scheduling, or
production readiness.

### Task 2: Write The Chinese Repository README

**Files:**
- Create: `README.zh-CN.md`
- Modify: `README.md`

- [ ] **Step 1: Add language navigation and project positioning**

Open with links between English and Chinese versions, then state that the
project is a portfolio-scale LangGraph evidence-research agent rather than a
production public-opinion platform.

- [ ] **Step 2: Explain architecture and capability status**

Include an end-to-end text diagram, a fixed-role status table, and concise
explanations of Skills, Tool Sets, structured schemas, two-stage workers,
stable evidence IDs, candidate quote selection, support verification, and
fail-closed output.

- [ ] **Step 3: Add reproducible setup and execution**

Document:

```powershell
python -m pip install -e ".[test]"
python -m pytest tests -q
python -m opinion_agent research `
  --topic "A bounded social event" `
  --adapter fake `
  --output-dir output\research
```

Describe generic real-provider environment variables without exposing local
values or provider secrets.

- [ ] **Step 4: Add artifacts, repository map, verification, and limitations**

Explain `evidence.jsonl`, `report.md`, `report_verification.json`, and
`trace.json`; link the real-provider smoke record and interview guide; state
the exact implemented boundary and follow-on directions.

- [ ] **Step 5: Add a Chinese link to the English README**

Modify the top of `README.md` so GitHub readers can discover
`README.zh-CN.md`.

### Task 3: Write The Graduate Interview Knowledge Manual

**Files:**
- Create: `docs/PROJECT_INTERVIEW_GUIDE.zh-CN.md`

- [ ] **Step 1: Write the project mental model and evolution**

Cover motivation, scope reduction, active thesis, success criteria, and the
distinction between the original product vision and the implemented resume
slice.

- [ ] **Step 2: Teach foundational concepts before project details**

Define LLM, Agent, workflow, tool calling, structured output, schema
validation, multi-agent systems, temporary instances, LangGraph state/nodes/
edges/`Send`/reducers, async concurrency, provenance, evidence, claims,
citations, support, and auditability.

- [ ] **Step 3: Explain the complete runtime with source references**

Trace:

```text
topic -> ResearchPlan -> Send fan-out -> SubagentActionPlan
-> authorized tools -> normalized evidence -> SubagentResult
-> deterministic quote candidates -> CitationSelectionBundle
-> ClaimInput -> ExactQuoteEvaluator -> ReportOutline
-> report + verification sidecar + trace
```

For each transition, identify who controls it, which schema crosses the
boundary, and which failures are rejected.

- [ ] **Step 4: Explain design decisions and guarantees**

Cover fixed roles, role-scoped Skills and Tool Sets, least privilege, model/
tool separation, stable evidence identity, exact-span claims, scope metadata,
fail-closed semantics, atomic run directories, output sanitization, and
deterministic report rendering.

- [ ] **Step 5: Explain concurrency and testing rigor**

Distinguish concurrency from parallel CPU execution, explain LangGraph fan-out
and reducer merging, describe the `asyncio.Event` barrier test, and explain the
real overlapping model-call intervals without treating timing alone as the
unit-test proof.

- [ ] **Step 6: Document concrete development difficulties**

Include the observed or reviewed failure modes and their fixes:

```text
model copying quote text unreliably
model-authored report title/prose widening the trusted surface
nested or stringified secrets in trace data
same run ID mixing artifacts
unbounded tool-call plans
evidence ID collisions caused by hashing truncated content
provider metadata overriding trusted provenance
Markdown structural injection
roles selected without installed adapters
unknown evidence IDs and unsupported claim types
```

- [ ] **Step 7: Document edge cases and limits**

Explain malformed schemas, duplicate IDs, empty evidence, partial worker
failure, unsupported semantic claims, source truth versus textual support,
representativeness, prompt injection boundaries, one-round research, missing
checkpoints, and unavailable production adapters.

- [ ] **Step 8: Add interview preparation sections**

Provide foundational questions, architecture questions, challenge questions,
follow-up chains, answer frameworks, oral explanations of 30 seconds,
2 minutes, and 5 minutes, a code-reading map, and a glossary. Do not write
resume bullets.

### Task 4: Cross-Check Documentation

**Files:**
- Verify: `README.md`
- Verify: `README.zh-CN.md`
- Verify: `docs/PROJECT_INTERVIEW_GUIDE.zh-CN.md`

- [ ] **Step 1: Check paths and relative links**

Run:

```powershell
@'
from pathlib import Path
import re

root = Path(".")
for source in [root / "README.md", root / "README.zh-CN.md",
               root / "docs/PROJECT_INTERVIEW_GUIDE.zh-CN.md"]:
    text = source.read_text(encoding="utf-8")
    for target in re.findall(r"\[[^\]]+\]\(([^)]+)\)", text):
        if "://" in target or target.startswith("#"):
            continue
        path = (source.parent / target.split("#", 1)[0]).resolve()
        assert path.exists(), f"{source}: missing {target}"
print("documentation links ok")
'@ | python -
```

Expected: `documentation links ok`

- [ ] **Step 2: Scan placeholders and sensitive material**

Run:

```powershell
rg -n "TBD|TODO|待补充|稍后补充|Bearer |api[_-]?key\s*[:=]" `
  README.md README.zh-CN.md docs/PROJECT_INTERVIEW_GUIDE.zh-CN.md
```

Expected: no placeholder or credential value. Generic environment variable
names such as `LLM_API_KEY` may appear.

- [ ] **Step 3: Check Markdown and Git whitespace**

Run:

```powershell
git diff --check
```

Expected: exit code `0`.

- [ ] **Step 4: Run the full regression suite**

Run:

```powershell
python -m pytest tests -q -p no:cacheprovider
```

Expected: all tests pass.

### Task 5: Commit And Publish

**Files:**
- Commit: `README.md`
- Commit: `README.zh-CN.md`
- Commit: `docs/PROJECT_INTERVIEW_GUIDE.zh-CN.md`
- Commit: `docs/superpowers/plans/2026-06-07-chinese-project-documentation.md`

- [ ] **Step 1: Inspect the final diff**

Run:

```powershell
git status --short
git diff --stat
git diff --check
```

Expected: only intended documentation files are modified or added.

- [ ] **Step 2: Commit**

Run:

```powershell
git add README.md README.zh-CN.md `
  docs/PROJECT_INTERVIEW_GUIDE.zh-CN.md `
  docs/superpowers/plans/2026-06-07-chinese-project-documentation.md
git commit -m "docs: add Chinese project and interview guides"
```

- [ ] **Step 3: Push and verify**

Run:

```powershell
git push origin main
git ls-remote origin refs/heads/main
git status --short
```

Expected: remote `main` points to the new commit and the worktree is clean.
