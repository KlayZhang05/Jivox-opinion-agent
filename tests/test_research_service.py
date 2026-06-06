from __future__ import annotations

import json

import pytest
from pydantic import BaseModel, ConfigDict

from opinion_agent.agents.models import (
    ClaimBundle,
    ReportOutline,
    ResearchPlan,
    ResearchTask,
    SubagentActionPlan,
    SubagentResult,
    ToolCallRecord,
)
from opinion_agent.citations.evaluators import ExactQuoteEvaluator
from opinion_agent.citations.models import ClaimInput
from opinion_agent.research.service import ResearchService
from opinion_agent.tools.registry import ToolDefinition, ToolRegistry
from opinion_agent.tools.search import SearchOutput, SearchResult


class SearchInput(BaseModel):
    model_config = ConfigDict(frozen=True)

    query: str


async def search_fixture(arguments: SearchInput) -> SearchOutput:
    return SearchOutput(
        provider="fixture",
        query=arguments.query,
        provider_request_id="fixture-request",
        results=(
            SearchResult(
                title="Bounded source",
                url="https://example.test/bounded-source",
                content="The route adjustment is limited.",
                published_at="2026-06-06",
            ),
        ),
    )


def tool_registry() -> ToolRegistry:
    return ToolRegistry(
        [
            ToolDefinition(
                tool_id="web_search",
                description="Search fixture sources.",
                input_model=SearchInput,
                handler=search_fixture,
            )
        ]
    )


class EndToEndModel:
    def __init__(self, *, claim_type="direct_quote") -> None:
        self.claim_type = claim_type
        self.schemas = []

    async def ainvoke(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        output_schema,
    ):
        self.schemas.append(output_schema)
        if output_schema is ResearchPlan:
            return ResearchPlan(
                topic="Bounded event",
                tasks=(
                    ResearchTask(
                        task_id="task-1",
                        role_id="query_agent",
                        objective="Find the bounded source.",
                        rationale="Establish a direct source span.",
                    ),
                ),
            )
        if output_schema is SubagentActionPlan:
            return SubagentActionPlan(
                task_id="task-1",
                role_id="query_agent",
                tool_calls=(
                    ToolCallRecord(
                        tool_id="web_search",
                        arguments={"query": "bounded event"},
                    ),
                ),
            )
        payload = json.loads(user_prompt)
        if output_schema is SubagentResult:
            return SubagentResult(
                task_id="task-1",
                role_id="query_agent",
                summary="Found a direct source span.",
                evidence_ids=tuple(payload["available_evidence_ids"]),
            )
        if output_schema is ClaimBundle:
            evidence_id = payload["evidence"][0]["evidence_id"]
            text = (
                "The route adjustment is limited."
                if self.claim_type == "direct_quote"
                else "The response was cautious."
            )
            return ClaimBundle(
                claims=(
                    ClaimInput(
                        claim_id="claim-1",
                        claim_type=self.claim_type,
                        text=text,
                        scope={"platform": "fixture", "sample": "one source"},
                        evidence_ids=(evidence_id,),
                    ),
                )
            )
        if output_schema is ReportOutline:
            return ReportOutline(
                title="Bounded event public-opinion report",
                ordered_claim_ids=("claim-1",),
            )
        raise AssertionError(output_schema)


@pytest.mark.asyncio
async def test_service_writes_auditable_end_to_end_artifacts(tmp_path):
    model = EndToEndModel()
    service = ResearchService(
        model=model,
        tool_registry=tool_registry(),
        evaluator=ExactQuoteEvaluator(),
        max_parallel_subagents=2,
        run_id_factory=lambda: "run-fixed",
    )

    result = await service.run("Bounded event", tmp_path)

    assert result.status == "completed"
    assert result.run_id == "run-fixed"
    assert result.report_path is not None and result.report_path.exists()
    assert (
        result.verification_path is not None
        and result.verification_path.exists()
    )
    assert result.evidence_path.exists()
    assert result.trace_path.exists()
    evidence = [
        json.loads(line)
        for line in result.evidence_path.read_text(encoding="utf-8").splitlines()
    ]
    assert len(evidence) == 1
    assert evidence[0]["content"] == "The route adjustment is limited."
    assert "The route adjustment is limited." in result.report_path.read_text(
        encoding="utf-8"
    )
    trace = json.loads(result.trace_path.read_text(encoding="utf-8"))
    event_types = {event["event_type"] for event in trace["events"]}
    assert {
        "research_plan_created",
        "role_instance_started",
        "model_call_completed",
        "tool_call_completed",
        "evidence_normalized",
        "claim_verification_completed",
        "report_written",
    } <= event_types
    assert ClaimBundle in model.schemas
    assert ReportOutline in model.schemas
    serialized_trace = json.dumps(trace).casefold()
    assert "system_prompt" not in serialized_trace
    assert "hidden_reasoning" not in serialized_trace
    assert "api_key" not in serialized_trace


@pytest.mark.asyncio
async def test_service_fails_closed_without_report_for_unsupported_claim(
    tmp_path,
):
    service = ResearchService(
        model=EndToEndModel(claim_type="analytic_inference"),
        tool_registry=tool_registry(),
        evaluator=ExactQuoteEvaluator(),
        max_parallel_subagents=2,
        run_id_factory=lambda: "run-rejected",
    )

    result = await service.run("Bounded event", tmp_path)

    assert result.status == "rejected"
    assert result.report_path is None
    assert result.verification_path is None
    assert result.evidence_path.exists()
    assert result.trace_path.exists()
    assert list(tmp_path.rglob("*.md")) == []
    assert list(tmp_path.rglob("*_verification.json")) == []
    trace = json.loads(result.trace_path.read_text(encoding="utf-8"))
    assert trace["events"][-1]["event_type"] == "run_rejected"
    assert "indeterminate" in result.errors[0]
