from __future__ import annotations

import operator
from typing import Annotated, Any, TypedDict

from pydantic import BaseModel, ConfigDict, Field

from opinion_agent.agents.models import (
    ResearchPlan,
    ResearchTask,
    SubagentResult,
)


class TraceEvent(BaseModel):
    model_config = ConfigDict(frozen=True)

    event_type: str = Field(min_length=1)
    role_id: str | None = None
    task_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ResearchState(TypedDict, total=False):
    topic: str
    plan: ResearchPlan
    subagent_results: Annotated[list[SubagentResult], operator.add]
    evidence_records: Annotated[list[dict[str, Any]], operator.add]
    trace_events: Annotated[list[TraceEvent], operator.add]
    errors: Annotated[list[str], operator.add]
    stage: str


class SubagentInput(TypedDict):
    topic: str
    task: ResearchTask
