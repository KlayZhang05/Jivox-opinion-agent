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

    tool_id: str = Field(min_length=1)
    arguments: dict = Field(default_factory=dict)


class SubagentActionPlan(BaseModel):
    model_config = ConfigDict(frozen=True)

    task_id: str = Field(min_length=1)
    role_id: ResearchRoleId
    tool_calls: tuple[ToolCallRecord, ...] = Field(min_length=1)


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


class ReportOutline(BaseModel):
    model_config = ConfigDict(frozen=True)

    title: str = Field(min_length=1)
    ordered_claim_ids: tuple[str, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_unique_claim_ids(self):
        if len(self.ordered_claim_ids) != len(set(self.ordered_claim_ids)):
            raise ValueError("Report outline claim IDs must be unique")
        return self
