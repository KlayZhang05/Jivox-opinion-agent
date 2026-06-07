from __future__ import annotations

import asyncio
import json

import pytest
from pydantic import BaseModel, ConfigDict

from opinion_agent.agents.models import (
    CitationSelectionBundle,
    ReportOutline,
    ResearchPlan,
    ResearchTask,
    SubagentActionPlan,
    SubagentResult,
    ToolCallRecord,
)
from opinion_agent.citations.evaluators import ExactQuoteEvaluator
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
    def __init__(
        self,
        *,
        invalid_candidate=False,
    ) -> None:
        self.invalid_candidate = invalid_candidate
        self.schemas = []
        self.system_prompts = []

    async def ainvoke(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        output_schema,
    ):
        self.schemas.append(output_schema)
        self.system_prompts.append((output_schema, system_prompt))
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
        if output_schema is CitationSelectionBundle:
            candidate_id = (
                "missing-candidate"
                if self.invalid_candidate
                else payload["candidates"][0]["candidate_id"]
            )
            return CitationSelectionBundle.model_validate(
                {
                    "selections": [
                        {
                            "claim_id": "claim-1",
                            "candidate_id": candidate_id,
                        }
                    ]
                }
            )
        if output_schema is ReportOutline:
            return ReportOutline(
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
        trace_redactions=("llm-secret", "search-secret"),
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
    plan_event = next(
        event
        for event in trace["events"]
        if event["event_type"] == "research_plan_created"
    )
    assert plan_event["metadata"]["tasks"][0]["objective"]
    tool_event = next(
        event
        for event in trace["events"]
        if event["event_type"] == "tool_call_completed"
    )
    assert tool_event["metadata"]["arguments"]["query"]
    assert all(event["occurred_at"] for event in trace["events"])
    timed_events = [
        event
        for event in trace["events"]
        if event["event_type"] in {
            "model_call_completed",
            "tool_call_completed",
        }
    ]
    assert timed_events
    assert all(event["metadata"]["duration_ms"] >= 0 for event in timed_events)
    assert CitationSelectionBundle in model.schemas
    assert ReportOutline in model.schemas
    citation_prompts = [
        prompt
        for schema, prompt in model.system_prompts
        if schema is CitationSelectionBundle
    ]
    assert "Select exactly one candidate quote" in citation_prompts[0]
    serialized_trace = json.dumps(trace).casefold()
    assert "system_prompt" not in serialized_trace
    assert "hidden_reasoning" not in serialized_trace
    assert "api_key" not in serialized_trace
    assert "llm-secret" not in serialized_trace
    assert "search-secret" not in serialized_trace


@pytest.mark.asyncio
async def test_service_fails_closed_without_report_for_unsupported_claim(
    tmp_path,
):
    service = ResearchService(
        model=EndToEndModel(invalid_candidate=True),
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
    assert "Unknown citation candidate" in result.errors[0]


class EmptyEvidenceModel(EndToEndModel):
    async def ainvoke(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        output_schema,
    ):
        if output_schema is CitationSelectionBundle:
            raise AssertionError("Citation Agent must not run without evidence")
        return await super().ainvoke(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            output_schema=output_schema,
        )


@pytest.mark.asyncio
async def test_service_rejects_before_citation_agent_when_no_evidence(tmp_path):
    async def empty_search(arguments: SearchInput) -> SearchOutput:
        return SearchOutput(
            provider="fixture",
            query=arguments.query,
            results=(),
        )

    registry = ToolRegistry(
        [
            ToolDefinition(
                tool_id="web_search",
                description="Return no results.",
                input_model=SearchInput,
                handler=empty_search,
            )
        ]
    )
    service = ResearchService(
        model=EmptyEvidenceModel(),
        tool_registry=registry,
        evaluator=ExactQuoteEvaluator(),
        max_parallel_subagents=2,
        run_id_factory=lambda: "run-empty",
    )

    result = await service.run("Bounded event", tmp_path)

    assert result.status == "rejected"
    assert result.report_path is None
    assert result.errors == ("No evidence was collected",)


class RepairingClaimModel(EndToEndModel):
    def __init__(self):
        super().__init__()
        self.claim_attempts = 0

    async def ainvoke(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        output_schema,
    ):
        if output_schema is CitationSelectionBundle:
            self.claim_attempts += 1
            payload = json.loads(user_prompt)
            candidate_id = (
                "missing-candidate"
                if self.claim_attempts == 1
                else payload["candidates"][0]["candidate_id"]
            )
            return CitationSelectionBundle.model_validate(
                {
                    "selections": [
                        {
                            "claim_id": "claim-1",
                            "candidate_id": candidate_id,
                        }
                    ]
                }
            )
        return await super().ainvoke(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            output_schema=output_schema,
        )


@pytest.mark.asyncio
async def test_service_retries_entire_claim_bundle_after_gate_rejection(
    tmp_path,
):
    model = RepairingClaimModel()
    service = ResearchService(
        model=model,
        tool_registry=tool_registry(),
        evaluator=ExactQuoteEvaluator(),
        max_parallel_subagents=2,
        run_id_factory=lambda: "run-repaired",
    )

    result = await service.run("Bounded event", tmp_path)

    assert result.status == "completed"
    assert model.claim_attempts == 2
    trace = json.loads(result.trace_path.read_text(encoding="utf-8"))
    assert any(
        event["event_type"] == "claim_repair_requested"
        for event in trace["events"]
    )


@pytest.mark.asyncio
async def test_citation_agent_selects_id_but_cannot_author_quote_text(tmp_path):
    model = EndToEndModel()
    service = ResearchService(
        model=model,
        tool_registry=tool_registry(),
        evaluator=ExactQuoteEvaluator(),
        max_parallel_subagents=2,
        run_id_factory=lambda: "run-selection",
    )

    result = await service.run("Bounded event", tmp_path)
    verification = json.loads(
        result.verification_path.read_text(encoding="utf-8")
    )

    assert verification["claims"][0]["text"] == (
        "The route adjustment is limited."
    )
    assert verification["claims"][0]["evidence_ids"] == [
        json.loads(
            result.evidence_path.read_text(encoding="utf-8").splitlines()[0]
        )["evidence_id"]
    ]


@pytest.mark.asyncio
async def test_service_rejects_reused_run_id_without_touching_existing_artifacts(
    tmp_path,
):
    run_dir = tmp_path / "run-fixed"
    run_dir.mkdir()
    existing = run_dir / "evidence.jsonl"
    existing.write_text("existing-data\n", encoding="utf-8")
    service = ResearchService(
        model=EndToEndModel(),
        tool_registry=tool_registry(),
        evaluator=ExactQuoteEvaluator(),
        max_parallel_subagents=2,
        run_id_factory=lambda: "run-fixed",
    )

    with pytest.raises(FileExistsError, match="run-fixed"):
        await service.run("Bounded event", tmp_path)

    assert existing.read_text(encoding="utf-8") == "existing-data\n"


@pytest.mark.asyncio
async def test_concurrent_runs_cannot_claim_the_same_run_directory(tmp_path):
    service = ResearchService(
        model=EndToEndModel(),
        tool_registry=tool_registry(),
        evaluator=ExactQuoteEvaluator(),
        max_parallel_subagents=2,
        run_id_factory=lambda: "run-collision",
    )

    results = await asyncio.gather(
        service.run("Bounded event", tmp_path),
        service.run("Bounded event", tmp_path),
        return_exceptions=True,
    )

    completed = [
        result
        for result in results
        if not isinstance(result, BaseException)
    ]
    failures = [
        result
        for result in results
        if isinstance(result, FileExistsError)
    ]
    assert len(completed) == 1
    assert completed[0].status == "completed"
    assert len(failures) == 1
