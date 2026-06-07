from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from opinion_agent.citations.models import ClaimInput


ResearchRoleId = Literal[
    "query_agent",
    "database_researcher",
    "multimedia_researcher",
    "tikhub_researcher",
]
ToolId = Literal[
    "web_search",
    "store_evidence",
    "search_evidence",
    "read_evidence",
    "inspect_media",
    "verify_citations",
    "verify_claim_support",
    "write_report",
    "tikhub_search",
]


class ResearchTask(BaseModel):
    model_config = ConfigDict(frozen=True)

    task_id: str = Field(min_length=1)
    role_id: ResearchRoleId
    objective: str = Field(min_length=1)
    rationale: str = Field(min_length=1)


class ResearchPlan(BaseModel):
    model_config = ConfigDict(frozen=True)

    topic: str = Field(min_length=1)
    tasks: tuple[ResearchTask, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_unique_task_ids(self):
        task_ids = [task.task_id for task in self.tasks]
        if len(task_ids) != len(set(task_ids)):
            raise ValueError("Research plan task_id values must be unique")
        return self


class ToolCallRecord(BaseModel):
    model_config = ConfigDict(frozen=True)

    tool_id: ToolId
    arguments: dict = Field(default_factory=dict)


class SubagentActionPlan(BaseModel):
    model_config = ConfigDict(frozen=True)

    task_id: str = Field(min_length=1)
    role_id: ResearchRoleId
    tool_calls: tuple[ToolCallRecord, ...] = Field(
        min_length=1,
        max_length=3,
    )


class SubagentResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    task_id: str = Field(min_length=1)
    role_id: ResearchRoleId
    summary: str = Field(min_length=1)
    evidence_ids: tuple[str, ...] = ()
    tool_calls: tuple[ToolCallRecord, ...] = ()
    errors: tuple[str, ...] = ()


class ClaimBundle(BaseModel):
    model_config = ConfigDict(frozen=True)

    claims: tuple[ClaimInput, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_unique_claim_ids(self):
        claim_ids = [claim.claim_id for claim in self.claims]
        if len(claim_ids) != len(set(claim_ids)):
            raise ValueError("Claim IDs must be unique")
        return self


class CitationSelection(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    claim_id: str = Field(min_length=1)
    candidate_id: str = Field(min_length=1)


class CitationSelectionBundle(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    selections: tuple[CitationSelection, ...] = Field(
        min_length=1,
        max_length=1,
    )


class ReportOutline(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    ordered_claim_ids: tuple[str, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_unique_claim_ids(self):
        if len(self.ordered_claim_ids) != len(set(self.ordered_claim_ids)):
            raise ValueError("Report outline claim IDs must be unique")
        return self
