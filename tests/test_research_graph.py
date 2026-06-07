from __future__ import annotations

import json

import pytest
from pydantic import BaseModel, ConfigDict

from opinion_agent.agents.models import (
    ResearchPlan,
    ResearchTask,
    SubagentActionPlan,
    SubagentResult,
    ToolCallRecord,
)
from opinion_agent.graph.research import (
    ResearchPlanCapabilityError,
    ResearchPlanLimitError,
    build_research_graph,
    fan_out_research_tasks,
)
from opinion_agent.tools.registry import ToolDefinition, ToolRegistry
from opinion_agent.tools.search import SearchOutput, SearchResult
from tests.fakes import BarrierStructuredModel


class ResearchToolInput(BaseModel):
    model_config = ConfigDict(frozen=True)

    query: str


async def research_tool(arguments: ResearchToolInput) -> SearchOutput:
    return SearchOutput(
        provider="fixture",
        query=arguments.query,
        results=(
            SearchResult(
                title=f"Source for {arguments.query}",
                url=f"https://example.test/{arguments.query.replace(' ', '-')}",
                content=f"Evidence content for {arguments.query}",
            ),
        ),
    )


def tool_registry() -> ToolRegistry:
    return ToolRegistry(
        [
            ToolDefinition(
                tool_id=tool_id,
                description=f"Fixture {tool_id}.",
                input_model=ResearchToolInput,
                handler=research_tool,
            )
            for tool_id in ("web_search", "search_evidence")
        ]
    )


def two_task_plan() -> ResearchPlan:
    return ResearchPlan(
        topic="Bounded event",
        tasks=(
            ResearchTask(
                task_id="task-1",
                role_id="query_agent",
                objective="Find primary reporting.",
                rationale="Establish event facts.",
            ),
            ResearchTask(
                task_id="task-2",
                role_id="database_researcher",
                objective="Inspect stored evidence.",
                rationale="Find prior context.",
            ),
        ),
    )


def test_fan_out_returns_one_send_per_research_task():
    sends = fan_out_research_tasks(
        {
            "topic": "Bounded event",
            "plan": two_task_plan(),
        }
    )

    assert [send.node for send in sends] == ["run_subagent", "run_subagent"]
    assert [send.arg["task"].task_id for send in sends] == ["task-1", "task-2"]
    assert all(send.arg["topic"] == "Bounded event" for send in sends)


@pytest.mark.asyncio
async def test_graph_runs_real_parallel_subagent_calls_and_reduces_results():
    model = BarrierStructuredModel(plan=two_task_plan())
    graph = build_research_graph(
        model=model,
        tool_registry=tool_registry(),
        max_parallel_subagents=4,
    )

    result = await graph.ainvoke({"topic": "Bounded event"})

    assert model.worker_overlap_observed is True
    assert model.started_task_ids == {"task-1", "task-2"}
    assert {item.task_id for item in result["subagent_results"]} == {
        "task-1",
        "task-2",
    }
    assert result["stage"] == "research_complete"
    assert len(result["evidence_records"]) == 2
    assert {
        record["evidence_id"] for record in result["evidence_records"]
    } == {
        evidence_id
        for item in result["subagent_results"]
        for evidence_id in item.evidence_ids
    }
    completed = [
        event
        for event in result["trace_events"]
        if event.event_type == "research_fan_in_completed"
    ]
    assert len(completed) == 1
    assert completed[0].metadata["result_count"] == 2


@pytest.mark.asyncio
async def test_failed_worker_is_recorded_without_losing_successful_worker():
    model = BarrierStructuredModel(
        plan=two_task_plan(),
        failing_task_id="task-2",
    )
    graph = build_research_graph(
        model=model,
        tool_registry=tool_registry(),
        max_parallel_subagents=4,
    )

    result = await graph.ainvoke({"topic": "Bounded event"})

    assert len(result["subagent_results"]) == 2
    by_task = {item.task_id: item for item in result["subagent_results"]}
    assert by_task["task-1"].errors == ()
    assert "forced failure" in by_task["task-2"].errors[0]
    assert any("task-2" in error for error in result["errors"])


@pytest.mark.asyncio
async def test_graph_rejects_plan_above_global_parallel_limit():
    tasks = tuple(
        ResearchTask(
            task_id=f"task-{index}",
            role_id="query_agent",
            objective=f"Research angle {index}.",
            rationale="Cover an independent angle.",
        )
        for index in range(1, 4)
    )
    graph = build_research_graph(
        model=BarrierStructuredModel(
            plan=ResearchPlan(topic="Bounded event", tasks=tasks)
        ),
        tool_registry=tool_registry(),
        max_parallel_subagents=2,
    )

    with pytest.raises(ResearchPlanLimitError, match="2"):
        await graph.ainvoke({"topic": "Bounded event"})


@pytest.mark.asyncio
async def test_graph_rejects_plan_above_role_instance_limit():
    tasks = tuple(
        ResearchTask(
            task_id=f"task-{index}",
            role_id="database_researcher",
            objective=f"Inspect evidence partition {index}.",
            rationale="Cover independent stored evidence.",
        )
        for index in range(1, 4)
    )
    graph = build_research_graph(
        model=BarrierStructuredModel(
            plan=ResearchPlan(topic="Bounded event", tasks=tasks)
        ),
        tool_registry=tool_registry(),
        max_parallel_subagents=4,
    )

    with pytest.raises(ResearchPlanLimitError, match="database_researcher"):
        await graph.ainvoke({"topic": "Bounded event"})


@pytest.mark.asyncio
async def test_graph_rejects_role_without_an_installed_tool_adapter():
    plan = ResearchPlan(
        topic="Bounded event",
        tasks=(
            ResearchTask(
                task_id="task-1",
                role_id="tikhub_researcher",
                objective="Collect platform posts.",
                rationale="Inspect a bounded social sample.",
            ),
        ),
    )
    graph = build_research_graph(
        model=BarrierStructuredModel(plan=plan),
        tool_registry=tool_registry(),
        max_parallel_subagents=4,
    )

    with pytest.raises(ResearchPlanCapabilityError, match="tikhub_researcher"):
        await graph.ainvoke({"topic": "Bounded event"})


class FabricatingModel:
    def __init__(
        self,
        *,
        plan_topic="Bounded event",
        rewrite_identity=False,
        fabricate_evidence=True,
    ):
        self.plan_topic = plan_topic
        self.rewrite_identity = rewrite_identity
        self.fabricate_evidence = fabricate_evidence

    async def ainvoke(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        output_schema,
    ):
        if output_schema is ResearchPlan:
            return ResearchPlan(
                topic=self.plan_topic,
                tasks=(
                    ResearchTask(
                        task_id="task-1",
                        role_id="query_agent",
                        objective="Find a source.",
                        rationale="Establish facts.",
                    ),
                ),
            )
        if output_schema is SubagentActionPlan:
            return SubagentActionPlan(
                task_id=(
                    "rewritten-task" if self.rewrite_identity else "task-1"
                ),
                role_id=(
                    "database_researcher"
                    if self.rewrite_identity
                    else "query_agent"
                ),
                tool_calls=(
                    ToolCallRecord(
                        tool_id="web_search",
                        arguments={"query": "bounded event"},
                    ),
                ),
            )
        if output_schema is SubagentResult:
            payload = json.loads(user_prompt)
            evidence_ids = (
                ("ev-does-not-exist",)
                if self.fabricate_evidence
                else tuple(payload["available_evidence_ids"])
            )
            return SubagentResult(
                task_id=(
                    "rewritten-task" if self.rewrite_identity else "task-1"
                ),
                role_id=(
                    "database_researcher"
                    if self.rewrite_identity
                    else "query_agent"
                ),
                summary="A fabricated citation.",
                evidence_ids=evidence_ids,
            )
        raise AssertionError(output_schema)


@pytest.mark.asyncio
async def test_graph_rejects_model_generated_evidence_ids():
    graph = build_research_graph(
        model=FabricatingModel(),
        tool_registry=tool_registry(),
        max_parallel_subagents=2,
    )

    result = await graph.ainvoke({"topic": "Bounded event"})

    assert result["subagent_results"][0].evidence_ids == ()
    assert "unavailable evidence IDs" in result["subagent_results"][0].errors[0]
    assert any("ev-does-not-exist" in error for error in result["errors"])


@pytest.mark.asyncio
async def test_requested_topic_remains_canonical_when_planner_rewrites_it():
    graph = build_research_graph(
        model=FabricatingModel(
            plan_topic="Rewritten topic with extra interpretation"
        ),
        tool_registry=tool_registry(),
        max_parallel_subagents=2,
    )

    result = await graph.ainvoke({"topic": "Bounded event"})

    assert result["plan"].topic == "Bounded event"


@pytest.mark.asyncio
async def test_runtime_assignment_remains_canonical_when_worker_rewrites_identity():
    graph = build_research_graph(
        model=FabricatingModel(
            rewrite_identity=True,
            fabricate_evidence=False,
        ),
        tool_registry=tool_registry(),
        max_parallel_subagents=2,
    )

    result = await graph.ainvoke({"topic": "Bounded event"})

    worker = result["subagent_results"][0]
    assert worker.task_id == "task-1"
    assert worker.role_id == "query_agent"
    assert worker.errors == ()
    assert worker.evidence_ids
