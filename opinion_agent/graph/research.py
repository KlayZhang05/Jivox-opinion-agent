from __future__ import annotations

import json
import time
from collections import Counter

from langgraph.graph import END, START, StateGraph
from langgraph.types import Send

from opinion_agent.agents.models import (
    ResearchPlan,
    SubagentActionPlan,
    SubagentResult,
)
from opinion_agent.agents.registry import get_role
from opinion_agent.agents.skills import render_skill_bundle
from opinion_agent.evidence.normalizer import normalize_tool_result
from opinion_agent.graph.state import (
    ResearchState,
    SubagentInput,
    TraceEvent,
)
from opinion_agent.llm.protocols import ModelOutputError, StructuredModel
from opinion_agent.tools.registry import ToolRegistry


class ResearchPlanLimitError(ValueError):
    """Raised when a model-generated plan exceeds configured role limits."""


class ResearchPlanCapabilityError(ValueError):
    """Raised when a plan selects a role without installed tool adapters."""


def fan_out_research_tasks(state: ResearchState) -> list[Send]:
    plan = state.get("plan")
    if plan is None:
        raise ValueError("Research plan is required before fan-out")
    topic = state["topic"]
    return [
        Send(
            "run_subagent",
            {
                "topic": topic,
                "task": task,
            },
        )
        for task in plan.tasks
    ]


def build_research_graph(
    *,
    model: StructuredModel,
    tool_registry: ToolRegistry,
    max_parallel_subagents: int,
):
    if max_parallel_subagents < 1:
        raise ValueError("max_parallel_subagents must be greater than 0")
    installed_tool_ids = {
        definition.tool_id for definition in tool_registry.list_tools()
    }
    executable_role_ids = tuple(
        role_id
        for role_id in (
            "query_agent",
            "database_researcher",
            "multimedia_researcher",
            "tikhub_researcher",
        )
        if get_role(role_id).tool_ids & installed_tool_ids
    )
    if not executable_role_ids:
        raise ValueError("At least one research role needs an installed tool")

    async def plan_research(state: ResearchState):
        topic = state.get("topic", "").strip()
        if not topic:
            raise ValueError("Research topic must not be empty")
        role = get_role("forum_host")
        model_started = time.perf_counter()
        plan = await model.ainvoke(
            system_prompt=(
                f"{role.system_prompt}\n\n"
                f"{render_skill_bundle(role.skill_ids)}"
            ),
            user_prompt=(
                "Create a bounded research plan for this topic:\n"
                f"{topic}\n\n"
                "Copy the requested topic verbatim into the plan topic field. "
                "Use only these currently executable roles from the fixed "
                f"registry: {', '.join(executable_role_ids)}."
            ),
            output_schema=ResearchPlan,
        )
        if plan.topic != topic:
            plan = plan.model_copy(update={"topic": topic})
        _validate_plan_limits(plan, max_parallel_subagents)
        _validate_plan_capabilities(plan, executable_role_ids)
        return {
            "plan": plan,
            "stage": "planned",
            "trace_events": [
                TraceEvent(
                    event_type="role_instance_started",
                    role_id="forum_host",
                    metadata={"instance_id": "forum_host"},
                ),
                TraceEvent(
                    event_type="model_call_completed",
                    role_id="forum_host",
                    metadata={
                        "output_schema": "ResearchPlan",
                        "duration_ms": _elapsed_ms(model_started),
                    },
                ),
                TraceEvent(
                    event_type="research_plan_created",
                    role_id="forum_host",
                    metadata={
                        "task_count": len(plan.tasks),
                        "tasks": [
                            task.model_dump(mode="json")
                            for task in plan.tasks
                        ],
                    },
                )
            ],
        }

    async def run_subagent(state: SubagentInput):
        task = state["task"]
        role = get_role(task.role_id)
        permitted_tools = tuple(
            sorted(role.tool_ids & installed_tool_ids)
        )
        prompt_payload = {
            "topic": state["topic"],
            "task_id": task.task_id,
            "objective": task.objective,
            "rationale": task.rationale,
            "permitted_tools": permitted_tools,
        }
        try:
            action_started = time.perf_counter()
            action_plan = await model.ainvoke(
                system_prompt=(
                    f"{role.system_prompt}\n\n"
                    f"{render_skill_bundle(role.skill_ids)}\n\n"
                    "Propose only the tool calls needed for this task. Use only "
                    "the permitted tools listed in the task payload. The tool_id "
                    "must exactly equal one of those names; do not create a call ID."
                ),
                user_prompt=json.dumps(
                    prompt_payload,
                    ensure_ascii=False,
                    sort_keys=True,
                ),
                output_schema=SubagentActionPlan,
            )
            action_plan = action_plan.model_copy(
                update={
                    "task_id": task.task_id,
                    "role_id": task.role_id,
                }
            )
            evidence_records = []
            tool_payloads = []
            trace_events = [
                TraceEvent(
                    event_type="role_instance_started",
                    role_id=task.role_id,
                    task_id=task.task_id,
                    metadata={"instance_id": task.task_id},
                ),
                TraceEvent(
                    event_type="model_call_completed",
                    role_id=task.role_id,
                    task_id=task.task_id,
                    metadata={
                        "output_schema": "SubagentActionPlan",
                        "duration_ms": _elapsed_ms(action_started),
                    },
                )
            ]
            for tool_call in action_plan.tool_calls:
                if tool_call.tool_id not in permitted_tools:
                    raise ModelOutputError(
                        f"Tool {tool_call.tool_id} is not currently available "
                        f"to role {task.role_id}"
                    )
                tool_started = time.perf_counter()
                tool_result = await tool_registry.invoke(
                    role_id=task.role_id,
                    tool_id=tool_call.tool_id,
                    arguments=tool_call.arguments,
                )
                normalized = normalize_tool_result(
                    tool_result,
                    task_id=task.task_id,
                    role_id=task.role_id,
                )
                evidence_records.extend(normalized)
                tool_payloads.append(_jsonable(tool_result))
                trace_events.append(
                    TraceEvent(
                        event_type="tool_call_completed",
                        role_id=task.role_id,
                        task_id=task.task_id,
                        metadata={
                            "tool_id": tool_call.tool_id,
                            "arguments": tool_call.arguments,
                            "ok": tool_result.ok,
                            "evidence_count": len(normalized),
                            "duration_ms": _elapsed_ms(tool_started),
                        },
                    )
                )

            available_ids = tuple(
                record["evidence_id"] for record in evidence_records
            )
            synthesis_payload = {
                **prompt_payload,
                "tool_results": tool_payloads,
                "available_evidence_ids": available_ids,
            }
            synthesis_started = time.perf_counter()
            result = await model.ainvoke(
                system_prompt=(
                    f"{role.system_prompt}\n\n"
                    f"{render_skill_bundle(role.skill_ids)}\n\n"
                    "Summarize only the supplied tool results. Cite only IDs "
                    "listed in available_evidence_ids."
                ),
                user_prompt=json.dumps(
                    synthesis_payload,
                    ensure_ascii=False,
                    sort_keys=True,
                ),
                output_schema=SubagentResult,
            )
            trace_events.append(
                TraceEvent(
                    event_type="model_call_completed",
                    role_id=task.role_id,
                    task_id=task.task_id,
                    metadata={
                        "output_schema": "SubagentResult",
                        "duration_ms": _elapsed_ms(synthesis_started),
                    },
                )
            )
            result = result.model_copy(
                update={
                    "task_id": task.task_id,
                    "role_id": task.role_id,
                }
            )
            unavailable_ids = sorted(set(result.evidence_ids) - set(available_ids))
            if unavailable_ids:
                raise ModelOutputError(
                    "Subagent cited unavailable evidence IDs: "
                    + ", ".join(unavailable_ids)
                )
            result = result.model_copy(
                update={"tool_calls": action_plan.tool_calls}
            )
            trace_events.extend(
                TraceEvent(
                    event_type="evidence_normalized",
                    role_id=task.role_id,
                    task_id=task.task_id,
                    metadata={"evidence_id": evidence_id},
                )
                for evidence_id in available_ids
            )
            trace_events.append(
                TraceEvent(
                    event_type="subagent_completed",
                    role_id=task.role_id,
                    task_id=task.task_id,
                    metadata={
                        "evidence_count": len(result.evidence_ids),
                        "tool_call_count": len(result.tool_calls),
                    },
                )
            )
            return {
                "subagent_results": [result],
                "evidence_records": evidence_records,
                "trace_events": trace_events,
            }
        except Exception as exc:
            message = str(exc)
            failed_result = SubagentResult(
                task_id=task.task_id,
                role_id=task.role_id,
                summary=f"Subagent {task.task_id} failed.",
                errors=(message,),
            )
            return {
                "subagent_results": [failed_result],
                "errors": [f"{task.task_id}: {message}"],
                "trace_events": [
                    TraceEvent(
                        event_type="subagent_failed",
                        role_id=task.role_id,
                        task_id=task.task_id,
                        metadata={"error": message},
                    )
                ],
            }

    async def prepare_claims(state: ResearchState):
        results = state.get("subagent_results", [])
        return {
            "stage": "research_complete",
            "trace_events": [
                TraceEvent(
                    event_type="research_fan_in_completed",
                    metadata={"result_count": len(results)},
                )
            ],
        }

    builder = StateGraph(ResearchState)
    builder.add_node("plan_research", plan_research)
    builder.add_node(
        "run_subagent",
        run_subagent,
        input_schema=SubagentInput,
    )
    builder.add_node("prepare_claims", prepare_claims)
    builder.add_edge(START, "plan_research")
    builder.add_conditional_edges("plan_research", fan_out_research_tasks)
    builder.add_edge("run_subagent", "prepare_claims")
    builder.add_edge("prepare_claims", END)
    return builder.compile(name="parallel_evidence_research")


def _jsonable(value):
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    return value


def _elapsed_ms(started: float) -> float:
    return round((time.perf_counter() - started) * 1000, 3)


def _validate_plan_limits(
    plan: ResearchPlan,
    max_parallel_subagents: int,
) -> None:
    if len(plan.tasks) > max_parallel_subagents:
        raise ResearchPlanLimitError(
            "Research plan contains "
            f"{len(plan.tasks)} tasks but the global limit is "
            f"{max_parallel_subagents}"
        )

    role_counts = Counter(task.role_id for task in plan.tasks)
    for role_id, count in role_counts.items():
        role_limit = get_role(role_id).max_instances
        if count > role_limit:
            raise ResearchPlanLimitError(
                f"Research plan assigns {count} instances to {role_id}, "
                f"exceeding its limit of {role_limit}"
            )


def _validate_plan_capabilities(
    plan: ResearchPlan,
    executable_role_ids: tuple[str, ...],
) -> None:
    unavailable = sorted(
        {
            task.role_id
            for task in plan.tasks
            if task.role_id not in executable_role_ids
        }
    )
    if unavailable:
        raise ResearchPlanCapabilityError(
            "Research plan selected role(s) without installed tool adapters: "
            + ", ".join(unavailable)
        )
