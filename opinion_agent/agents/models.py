from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


WorkerRoleId = Literal[
    "query_agent",
    "database_researcher",
    "multimedia_researcher",
    "citation_agent",
    "report_writer",
    "tikhub_researcher",
]


class ResearchTask(BaseModel):
    model_config = ConfigDict(frozen=True)

    task_id: str = Field(min_length=1)
    role_id: WorkerRoleId
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


class SubagentResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    task_id: str = Field(min_length=1)
    role_id: WorkerRoleId
    summary: str = Field(min_length=1)
    evidence_ids: tuple[str, ...] = ()
    tool_calls: tuple[ToolCallRecord, ...] = ()
    errors: tuple[str, ...] = ()
