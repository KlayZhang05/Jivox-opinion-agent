from __future__ import annotations

from dataclasses import dataclass

from opinion_agent.agents.registry import ROLE_REGISTRY


@dataclass(frozen=True)
class RuntimeGraphDescriptor:
    entrypoint: str
    roles: tuple[str, ...]
    nodes: dict[str, str]
    runtime_nodes: tuple[str, ...]


ROLE_LABELS = {
    "forum_host": "Forum Host / Research Lead",
    "query_agent": "Query Agent",
    "database_researcher": "Database Research Agent",
    "multimedia_researcher": "Multimedia Research Agent",
    "citation_agent": "Citation Agent",
    "report_writer": "Report Writer Agent",
    "tikhub_researcher": "TikHub Research Agent",
}


def describe_runtime_graph() -> RuntimeGraphDescriptor:
    return RuntimeGraphDescriptor(
        entrypoint="plan_research",
        roles=tuple(ROLE_REGISTRY),
        nodes=dict(ROLE_LABELS),
        runtime_nodes=(
            "plan_research",
            "run_subagent",
            "prepare_claims",
        ),
    )
