# Parallel Evidence Research Agent Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the resume-ready LangGraph workflow in which a Forum Host selects fixed agent roles, launches real parallel LLM subagent calls, enforces role-specific Skills and Tool Sets, verifies evidence, and writes an auditable Markdown report.

**Architecture:** Use an explicit async `StateGraph`. The Forum Host returns structured research tasks constrained to a fixed role registry; a conditional edge returns one `Send` per task; isolated subagent invocations run concurrently and append results through reducers. Provider adapters, tools, evidence verification, and trace persistence remain behind testable protocols so unit tests need no network credentials.

**Tech Stack:** Python 3.11+, LangGraph, LangChain OpenAI-compatible chat models, Pydantic 2, pydantic-settings, httpx, pytest, pytest-asyncio

---

## File Structure

- `opinion_agent/settings.py`: generic LLM/search configuration.
- `opinion_agent/agents/models.py`: structured research task and result models.
- `opinion_agent/agents/registry.py`: immutable fixed role registry.
- `opinion_agent/agents/skills.py`: predefined Skill instructions.
- `opinion_agent/tools/registry.py`: tool definitions and role permission checks.
- `opinion_agent/tools/search.py`: generic Anspire-compatible search adapter.
- `opinion_agent/llm/protocols.py`: injectable structured-model protocol.
- `opinion_agent/llm/openai_compatible.py`: real OpenAI-compatible implementation.
- `opinion_agent/graph/state.py`: graph state and reducers.
- `opinion_agent/graph/research.py`: executable LangGraph workflow.
- `opinion_agent/tracing/run_trace.py`: JSON execution trace.
- `opinion_agent/research/service.py`: end-to-end orchestration boundary.
- `tests/fakes.py`: deterministic fake LLM and tools.

### Task 1: Generic Runtime Configuration

**Files:**
- Modify: `pyproject.toml`
- Create: `.env.example`
- Create: `opinion_agent/settings.py`
- Create: `tests/test_settings.py`

- [ ] **Step 1: Write failing configuration tests**

Cover generic `LLM_*`, `SEARCH_*`, optional `TIKHUB_*`, integer limits, secret
redaction, and missing-variable errors. No role-specific environment names are
allowed.

```python
def test_loads_generic_llm_and_search_settings(tmp_path):
    env = write_env(tmp_path, {
        "LLM_API_KEY": "secret",
        "LLM_BASE_URL": "https://llm.test/v1",
        "LLM_MODEL_NAME": "test-model",
        "SEARCH_PROVIDER": "anspire",
        "SEARCH_API_KEY": "search-secret",
        "SEARCH_BASE_URL": "https://search.test",
    })
    settings = load_settings(env)
    assert settings.llm.model_name == "test-model"
    assert settings.search.provider == "anspire"
    assert "secret" not in repr(settings)
```

- [ ] **Step 2: Verify red**

Run:

```powershell
python -m pytest tests\test_settings.py -v
```

Expected: import failure for `opinion_agent.settings`.

- [ ] **Step 3: Add dependencies and implementation**

Add:

```toml
dependencies = [
  "httpx>=0.27,<1",
  "langchain-openai>=0.3,<2",
  "langgraph>=0.6,<2",
  "pydantic>=2.7,<3",
  "pydantic-settings>=2.2,<3",
]

[project.optional-dependencies]
test = ["pytest>=8", "pytest-asyncio>=0.24"]
```

Implement `RuntimeSettings` with generic nested immutable configurations and
`load_settings(env_file=None)`. Do not load or mention BettaFish paths.

- [ ] **Step 4: Verify green**

```powershell
python -m pytest tests\test_settings.py -v
```

- [ ] **Step 5: Commit**

```powershell
git add pyproject.toml .env.example opinion_agent/settings.py tests/test_settings.py
git commit -m "feat: add generic runtime settings"
```

### Task 2: Fixed Roles, Skills, And Tool Sets

**Files:**
- Create: `opinion_agent/agents/__init__.py`
- Create: `opinion_agent/agents/models.py`
- Create: `opinion_agent/agents/skills.py`
- Create: `opinion_agent/agents/registry.py`
- Create: `tests/test_agent_registry.py`

- [ ] **Step 1: Write failing registry tests**

Assert the exact seven roles:

```python
EXPECTED_ROLES = {
    "forum_host",
    "query_agent",
    "database_researcher",
    "multimedia_researcher",
    "citation_agent",
    "report_writer",
    "tikhub_researcher",
}
```

Verify each role has a system prompt, non-empty Skill IDs, a frozen Tool Set,
input/output model names, and limits. Verify unknown roles and runtime role
creation are rejected.

- [ ] **Step 2: Verify red**

```powershell
python -m pytest tests\test_agent_registry.py -v
```

- [ ] **Step 3: Implement role and Skill contracts**

Use frozen Pydantic models:

```python
class RoleDefinition(BaseModel):
    model_config = ConfigDict(frozen=True)
    role_id: RoleId
    responsibility: str
    system_prompt: str
    skill_ids: tuple[str, ...]
    tool_ids: frozenset[str]
    input_schema: str
    output_schema: str
    max_instances: int
```

The registry is a `MappingProxyType`; expose `get_role()` and `list_roles()`
only. The Forum Host is not eligible as a worker.

- [ ] **Step 4: Verify green**

```powershell
python -m pytest tests\test_agent_registry.py -v
```

- [ ] **Step 5: Commit**

```powershell
git add opinion_agent/agents tests/test_agent_registry.py
git commit -m "feat: add fixed agent role registry"
```

### Task 3: Tool Registry And Permission Enforcement

**Files:**
- Create: `opinion_agent/tools/__init__.py`
- Create: `opinion_agent/tools/registry.py`
- Create: `opinion_agent/tools/search.py`
- Create: `tests/test_tool_registry.py`

- [ ] **Step 1: Write failing permission and search parsing tests**

Required behavior:

- only registered tools can execute;
- role Tool Set is checked before invocation;
- denial occurs before the tool handler runs;
- search output retains title, URL, content, date, and provider metadata;
- timeout or malformed provider output returns a typed tool error.

```python
with pytest.raises(ToolPermissionError):
    registry.invoke(
        role_id="report_writer",
        tool_id="web_search",
        arguments={"query": "event"},
    )
assert handler.calls == 0
```

- [ ] **Step 2: Verify red**

```powershell
python -m pytest tests\test_tool_registry.py -v
```

- [ ] **Step 3: Implement registry and Anspire-compatible adapter**

Define `ToolDefinition`, `ToolCall`, `ToolResult`, and `ToolRegistry`. Implement
an async `web_search` handler using `httpx.AsyncClient`, generic
`SEARCH_API_KEY/SEARCH_BASE_URL`, and Anspire's `query/top_k` response shape.
Provider response parsing must not trust an AI-generated answer as evidence.

- [ ] **Step 4: Verify green**

```powershell
python -m pytest tests\test_tool_registry.py -v
```

- [ ] **Step 5: Commit**

```powershell
git add opinion_agent/tools tests/test_tool_registry.py
git commit -m "feat: enforce role tool permissions"
```

### Task 4: Structured Model Boundary And Real Adapter

**Files:**
- Create: `opinion_agent/llm/__init__.py`
- Create: `opinion_agent/llm/protocols.py`
- Create: `opinion_agent/llm/openai_compatible.py`
- Create: `tests/test_llm_adapter.py`

- [ ] **Step 1: Write failing model-boundary tests**

Define a fake structured model and verify:

- Forum Host planning returns validated `ResearchPlan`;
- worker output returns validated `SubagentResult`;
- malformed JSON/schema output raises `ModelOutputError`;
- API key never appears in exceptions or repr.

- [ ] **Step 2: Verify red**

```powershell
python -m pytest tests\test_llm_adapter.py -v
```

- [ ] **Step 3: Implement injectable structured model**

```python
class StructuredModel(Protocol):
    async def ainvoke(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        output_schema: type[BaseModel],
    ) -> BaseModel: ...
```

The real adapter wraps `ChatOpenAI(...).with_structured_output(schema)` using
generic runtime settings. It does not bind tools; the graph owns tool
permission and evidence normalization.

- [ ] **Step 4: Verify green**

```powershell
python -m pytest tests\test_llm_adapter.py -v
```

- [ ] **Step 5: Commit**

```powershell
git add opinion_agent/llm tests/test_llm_adapter.py
git commit -m "feat: add structured model adapter"
```

### Task 5: Dynamic Parallel LangGraph Workflow

**Files:**
- Create: `opinion_agent/graph/state.py`
- Create: `opinion_agent/graph/research.py`
- Replace: `tests/test_graph_runtime.py`
- Create: `tests/fakes.py`
- Create: `tests/test_research_graph.py`

- [ ] **Step 1: Write failing graph and concurrency tests**

Test:

- Forum Host may select only worker roles from the fixed registry;
- task count obeys per-role and global limits;
- conditional fan-out returns one `Send("run_subagent", task_state)` per task;
- reducers preserve every subagent result;
- two fake LLM calls overlap in time;
- one failed worker is recorded without losing successful workers;
- graph reaches citation preparation only after fan-out completes.

Use an async fake with an `asyncio.Event` barrier so the concurrency assertion
does not rely on elapsed-time thresholds.

- [ ] **Step 2: Verify red**

```powershell
python -m pytest tests\test_research_graph.py tests\test_graph_runtime.py -v
```

- [ ] **Step 3: Implement graph**

State includes:

```python
class ResearchState(TypedDict):
    topic: str
    plan: ResearchPlan | None
    subagent_results: Annotated[list[SubagentResult], operator.add]
    evidence_records: Annotated[list[dict], operator.add]
    trace_events: Annotated[list[TraceEvent], operator.add]
    errors: Annotated[list[str], operator.add]
    report_path: str | None
```

Build:

```text
START -> plan_research
plan_research -> Send(run_subagent, task)*
run_subagent -> prepare_claims
prepare_claims -> verify_claims
verify_claims -> write_report | END
write_report -> END
```

Each `run_subagent` invocation resolves its immutable role definition, injects
the role's Skill text and Tool Set, calls the real/fake model independently,
and returns one reducer update.

- [ ] **Step 4: Verify green**

```powershell
python -m pytest tests\test_research_graph.py tests\test_graph_runtime.py -v
```

- [ ] **Step 5: Commit**

```powershell
git add opinion_agent/graph tests/fakes.py tests/test_graph_runtime.py tests/test_research_graph.py
git commit -m "feat: run dynamic parallel research subagents"
```

### Task 6: Evidence Gate, Report, And Trace Integration

**Files:**
- Modify: `opinion_agent/evidence/store.py`
- Create: `opinion_agent/tracing/__init__.py`
- Create: `opinion_agent/tracing/run_trace.py`
- Create: `opinion_agent/research/__init__.py`
- Create: `opinion_agent/research/service.py`
- Modify: `opinion_agent/reports/generator.py`
- Modify: `opinion_agent/citations/`
- Create: `tests/test_research_service.py`

- [ ] **Step 1: Write failing end-to-end service tests**

Cover:

- normalized tool results receive stable evidence IDs;
- subagent prose cannot enter a report without claim/evidence binding;
- unsupported claims write no report;
- supported claims produce Markdown and verification sidecar;
- trace records planning, role instance, model call, tool call, evidence,
  verification, and report events;
- trace omits secrets and raw hidden reasoning.

- [ ] **Step 2: Verify red**

```powershell
python -m pytest tests\test_research_service.py -v
```

- [ ] **Step 3: Implement the service boundary**

`ResearchService.run(topic, output_dir)` invokes the compiled graph with a
generated run ID. Integrate the separately approved claim-evidence support gate
design. Preserve the existing JSONL store and write trace JSON atomically.

- [ ] **Step 4: Verify green**

```powershell
python -m pytest tests\test_research_service.py -v
```

- [ ] **Step 5: Commit**

```powershell
git add opinion_agent/evidence opinion_agent/citations opinion_agent/reports opinion_agent/research opinion_agent/tracing tests/test_research_service.py
git commit -m "feat: integrate evidence-gated research reports"
```

### Task 7: CLI, Repository Narrative, And Real Smoke Test

**Files:**
- Modify: `opinion_agent/cli.py`
- Modify: `README.md`
- Create: `examples/research_request.example.json`
- Create: `examples/sample_research_report.md`
- Modify: `tests/test_cli.py`

- [ ] **Step 1: Write failing CLI tests**

Required command:

```powershell
python -m opinion_agent research --topic "A bounded social event" --output-dir output
```

Test fake-adapter mode writes:

- report Markdown;
- verification JSON;
- trace JSON;
- evidence JSONL.

- [ ] **Step 2: Verify red**

```powershell
python -m pytest tests\test_cli.py -v
```

- [ ] **Step 3: Implement CLI and rewrite README around the active project**

README must lead with:

> LangGraph-based evidence-constrained public-opinion research agent with
> dynamic parallel subagents.

Include architecture, fixed roles, Skill/Tool permission model, `Send`
fan-out, evidence gate, setup, one command, tests, sample output, trade-offs,
and resume-ready bullets. Move briefing/conversation commands to a clearly
marked historical prototype section.

- [ ] **Step 4: Run deterministic verification**

```powershell
python -m pytest tests -v
python -m opinion_agent research --topic "Sample event" --adapter fake --output-dir output-smoke
git diff --check
```

- [ ] **Step 5: Run optional real integration smoke**

With the ignored local `.env`:

```powershell
python -m opinion_agent research --topic "A current bounded event" --output-dir output-real-smoke
```

Do not commit generated output or credentials. If provider access fails, record
the exact integration limitation while keeping deterministic verification
green.

- [ ] **Step 6: Final review and push**

```powershell
git status --short
git log --oneline --decorate -10
git push origin HEAD
```
