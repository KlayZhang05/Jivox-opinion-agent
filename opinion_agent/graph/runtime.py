from __future__ import annotations

from dataclasses import dataclass
from importlib.util import find_spec


@dataclass(frozen=True)
class RuntimeGraphDescriptor:
    kind: str
    langgraph_available: bool
    entrypoint: str
    roles: tuple[str, ...]
    nodes: dict[str, str]
    edges: tuple[tuple[str, str], ...]


ROLES: tuple[str, ...] = (
    "forum_host",
    "query_agent",
    "database_researcher",
    "multimedia_researcher",
    "citation_agent",
    "report_writer",
    "conversation_agent",
)

NODES: dict[str, str] = {
    "forum_host": "Forum Host / Research Lead",
    "query_agent": "Query Agent",
    "database_researcher": "Database Research Agent",
    "multimedia_researcher": "Multimedia Research Agent",
    "citation_agent": "Citation Agent",
    "report_writer": "Report Writer Agent",
    "conversation_agent": "Conversation Agent",
}

EDGES: tuple[tuple[str, str], ...] = (
    ("forum_host", "query_agent"),
    ("forum_host", "database_researcher"),
    ("forum_host", "multimedia_researcher"),
    ("query_agent", "citation_agent"),
    ("database_researcher", "citation_agent"),
    ("multimedia_researcher", "citation_agent"),
    ("citation_agent", "report_writer"),
    ("conversation_agent", "forum_host"),
)


def build_runtime_graph() -> RuntimeGraphDescriptor:
    return RuntimeGraphDescriptor(
        kind="runtime_graph_descriptor",
        langgraph_available=find_spec("langgraph") is not None,
        entrypoint="forum_host",
        roles=ROLES,
        nodes=dict(NODES),
        edges=EDGES,
    )
