from __future__ import annotations

from types import MappingProxyType
from typing import Final, Literal, Mapping

from pydantic import BaseModel, ConfigDict, Field


RoleId = Literal[
    "forum_host",
    "query_agent",
    "database_researcher",
    "multimedia_researcher",
    "citation_agent",
    "report_writer",
    "tikhub_researcher",
]


class RoleDefinition(BaseModel):
    model_config = ConfigDict(frozen=True)

    role_id: RoleId
    responsibility: str = Field(min_length=1)
    system_prompt: str = Field(min_length=1)
    skill_ids: tuple[str, ...] = Field(min_length=1)
    tool_ids: frozenset[str]
    input_schema: str = Field(min_length=1)
    output_schema: str = Field(min_length=1)
    model_profile_id: str = "shared"
    max_instances: int = Field(ge=1, le=16)


_ROLES = {
    "forum_host": RoleDefinition(
        role_id="forum_host",
        responsibility="Plan bounded research and coordinate temporary subagents.",
        system_prompt=(
            "You are the Forum Host. Decompose the topic into the smallest useful "
            "set of independent research tasks. Select only registered worker roles."
        ),
        skill_ids=("research_planning", "gap_analysis"),
        tool_ids=frozenset(),
        input_schema="ResearchRequest",
        output_schema="ResearchPlan",
        max_instances=1,
    ),
    "query_agent": RoleDefinition(
        role_id="query_agent",
        responsibility="Search the web and return attributable source material.",
        system_prompt=(
            "You are a web research subagent. Use permitted search tools and "
            "return traceable sources, not unsupported conclusions."
        ),
        skill_ids=("web_research", "source_triage"),
        tool_ids=frozenset({"web_search", "store_evidence"}),
        input_schema="ResearchTask",
        output_schema="SubagentResult",
        max_instances=4,
    ),
    "database_researcher": RoleDefinition(
        role_id="database_researcher",
        responsibility="Retrieve prior evidence and reports from local storage.",
        system_prompt=(
            "You are a database research subagent. Retrieve existing evidence "
            "while preserving provenance and stable identifiers."
        ),
        skill_ids=("evidence_retrieval", "prior_report_review"),
        tool_ids=frozenset({"search_evidence", "read_evidence"}),
        input_schema="ResearchTask",
        output_schema="SubagentResult",
        max_instances=2,
    ),
    "multimedia_researcher": RoleDefinition(
        role_id="multimedia_researcher",
        responsibility="Extract bounded observations from multimedia evidence.",
        system_prompt=(
            "You are a multimedia research subagent. Separate direct observations "
            "from interpretation and preserve media provenance."
        ),
        skill_ids=("multimedia_inspection", "source_triage"),
        tool_ids=frozenset({"inspect_media", "store_evidence"}),
        input_schema="ResearchTask",
        output_schema="SubagentResult",
        max_instances=2,
    ),
    "citation_agent": RoleDefinition(
        role_id="citation_agent",
        responsibility="Select bounded source spans for deterministic claims.",
        system_prompt=(
            "You are the citation subagent. Select only supplied source-span "
            "candidates and fail closed when none fits the bounded topic."
        ),
        skill_ids=("claim_atomization", "citation_audit"),
        tool_ids=frozenset(
            {"read_evidence", "verify_citations", "verify_claim_support"}
        ),
        input_schema="EvidenceBundle",
        output_schema="CitationSelectionBundle",
        max_instances=2,
    ),
    "report_writer": RoleDefinition(
        role_id="report_writer",
        responsibility="Write reports exclusively from verified claims.",
        system_prompt=(
            "You are the report writer. Use only verified claims and preserve "
            "their evidence IDs, scope, uncertainty, and disagreements."
        ),
        skill_ids=("evidence_synthesis", "report_writing"),
        tool_ids=frozenset({"read_evidence", "write_report"}),
        input_schema="VerifiedClaims",
        output_schema="ReportDraft",
        max_instances=1,
    ),
    "tikhub_researcher": RoleDefinition(
        role_id="tikhub_researcher",
        responsibility="Collect bounded social-media records through TikHub.",
        system_prompt=(
            "You are a TikHub research subagent. Preserve platform metadata and "
            "never generalize beyond the collected sample."
        ),
        skill_ids=("social_media_research", "source_triage"),
        tool_ids=frozenset({"tikhub_search", "store_evidence"}),
        input_schema="ResearchTask",
        output_schema="SubagentResult",
        max_instances=3,
    ),
}

ROLE_REGISTRY: Final[Mapping[str, RoleDefinition]] = MappingProxyType(_ROLES)
WORKER_ROLE_IDS: Final[tuple[str, ...]] = tuple(
    role_id for role_id in ROLE_REGISTRY if role_id != "forum_host"
)


def get_role(role_id: str) -> RoleDefinition:
    try:
        return ROLE_REGISTRY[role_id]
    except KeyError as exc:
        raise KeyError(f"Unknown agent role: {role_id}") from exc


def list_roles() -> tuple[RoleDefinition, ...]:
    return tuple(ROLE_REGISTRY.values())
