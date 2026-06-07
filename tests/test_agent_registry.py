from types import MappingProxyType

import pytest
from pydantic import ValidationError

from opinion_agent.agents.models import (
    ReportOutline,
    ResearchPlan,
    ResearchTask,
    SubagentActionPlan,
    ToolCallRecord,
)
from opinion_agent.agents.registry import (
    ROLE_REGISTRY,
    WORKER_ROLE_IDS,
    get_role,
    list_roles,
)
from opinion_agent.agents.skills import SKILL_REGISTRY, render_skill_bundle


EXPECTED_ROLES = {
    "forum_host",
    "query_agent",
    "database_researcher",
    "multimedia_researcher",
    "citation_agent",
    "report_writer",
    "tikhub_researcher",
}


def test_fixed_registry_contains_only_approved_roles():
    assert isinstance(ROLE_REGISTRY, MappingProxyType)
    assert set(ROLE_REGISTRY) == EXPECTED_ROLES
    assert set(WORKER_ROLE_IDS) == EXPECTED_ROLES - {"forum_host"}
    assert [role.role_id for role in list_roles()] == list(ROLE_REGISTRY)


def test_each_role_binds_skills_tools_contracts_and_limits():
    for role in ROLE_REGISTRY.values():
        assert role.responsibility.strip()
        assert role.system_prompt.strip()
        assert role.skill_ids
        assert all(skill_id in SKILL_REGISTRY for skill_id in role.skill_ids)
        assert isinstance(role.tool_ids, frozenset)
        assert role.input_schema.strip()
        assert role.output_schema.strip()
        assert role.model_profile_id == "shared"
        assert role.max_instances >= 1
        assert render_skill_bundle(role.skill_ids).strip()


def test_role_and_skill_registries_are_immutable():
    with pytest.raises(TypeError):
        ROLE_REGISTRY["invented_role"] = get_role("query_agent")

    with pytest.raises(TypeError):
        SKILL_REGISTRY["invented_skill"] = SKILL_REGISTRY["web_research"]

    with pytest.raises(ValidationError):
        get_role("query_agent").tool_ids = frozenset({"write_report"})


def test_unknown_role_is_rejected():
    with pytest.raises(KeyError, match="Unknown agent role"):
        get_role("invented_role")


def test_research_plan_rejects_forum_host_as_worker_and_duplicate_task_ids():
    with pytest.raises(ValidationError, match="forum_host"):
        ResearchPlan(
            topic="Bounded event",
            tasks=(
                ResearchTask(
                    task_id="task-1",
                    role_id="forum_host",
                    objective="Research itself.",
                    rationale="Invalid worker role.",
                ),
            ),
        )

    with pytest.raises(ValidationError, match="task_id"):
        ResearchPlan(
            topic="Bounded event",
            tasks=(
                ResearchTask(
                    task_id="task-1",
                    role_id="query_agent",
                    objective="Find primary reporting.",
                    rationale="Establish event facts.",
                ),
                ResearchTask(
                    task_id="task-1",
                    role_id="database_researcher",
                    objective="Inspect stored evidence.",
                    rationale="Reuse prior material.",
                ),
            ),
        )


def test_research_task_accepts_only_registered_worker_roles():
    with pytest.raises(ValidationError):
        ResearchTask(
            task_id="task-1",
            role_id="invented_role",
            objective="Do unsupported work.",
            rationale="This must not create a role.",
        )

    with pytest.raises(ValidationError):
        ResearchTask(
            task_id="task-2",
            role_id="report_writer",
            objective="Write before evidence collection.",
            rationale="Pipeline roles are not research fan-out workers.",
        )


def test_tool_call_contract_rejects_runtime_invented_tool_ids():
    with pytest.raises(ValidationError):
        ToolCallRecord(
            tool_id="call_search_001",
            arguments={"query": "event"},
        )


def test_subagent_action_plan_limits_tool_calls():
    calls = tuple(
        ToolCallRecord(
            tool_id="web_search",
            arguments={"query": f"event {index}"},
        )
        for index in range(4)
    )

    with pytest.raises(ValidationError):
        SubagentActionPlan(
            task_id="task-1",
            role_id="query_agent",
            tool_calls=calls,
        )


def test_report_outline_rejects_model_authored_prose():
    with pytest.raises(ValidationError):
        ReportOutline.model_validate(
            {
                "title": "Safe title\n\n## Unsupported conclusion",
                "ordered_claim_ids": ["claim-1"],
            }
        )
