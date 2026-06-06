from __future__ import annotations

import pytest

from opinion_agent.agents.models import ResearchPlan, ResearchTask
from opinion_agent.graph.research import (
    ResearchPlanLimitError,
    build_research_graph,
    fan_out_research_tasks,
)
from tests.fakes import BarrierStructuredModel


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
    graph = build_research_graph(model=model, max_parallel_subagents=4)

    result = await graph.ainvoke({"topic": "Bounded event"})

    assert model.worker_overlap_observed is True
    assert model.started_task_ids == {"task-1", "task-2"}
    assert {item.task_id for item in result["subagent_results"]} == {
        "task-1",
        "task-2",
    }
    assert result["stage"] == "research_complete"
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
    graph = build_research_graph(model=model, max_parallel_subagents=4)

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
        max_parallel_subagents=4,
    )

    with pytest.raises(ResearchPlanLimitError, match="database_researcher"):
        await graph.ainvoke({"topic": "Bounded event"})
