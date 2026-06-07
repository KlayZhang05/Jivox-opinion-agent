from __future__ import annotations

import asyncio
import hashlib
import json

from opinion_agent.agents.models import (
    CitationSelectionBundle,
    ReportOutline,
    ResearchPlan,
    ResearchTask,
    SubagentActionPlan,
    SubagentResult,
    ToolCallRecord,
)
from opinion_agent.tools.registry import ToolDefinition, ToolRegistry
from opinion_agent.tools.search import SearchOutput, SearchRequest, SearchResult


class FakeResearchModel:
    async def ainvoke(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        output_schema,
    ):
        if output_schema is ResearchPlan:
            topic = _topic_from_planning_prompt(user_prompt)
            return ResearchPlan(
                topic=topic,
                tasks=(
                    ResearchTask(
                        task_id="web-facts",
                        role_id="query_agent",
                        objective=f"Find direct reporting about {topic}.",
                        rationale="Establish a traceable factual source.",
                    ),
                    ResearchTask(
                        task_id="web-reaction",
                        role_id="query_agent",
                        objective=f"Find a bounded public reaction to {topic}.",
                        rationale="Capture a separate attributable observation.",
                    ),
                ),
            )

        payload = json.loads(user_prompt)
        if output_schema is SubagentActionPlan:
            await asyncio.sleep(0)
            return SubagentActionPlan(
                task_id=payload["task_id"],
                role_id="query_agent",
                tool_calls=(
                    ToolCallRecord(
                        tool_id="web_search",
                        arguments={"query": payload["objective"], "max_results": 1},
                    ),
                ),
            )
        if output_schema is SubagentResult:
            return SubagentResult(
                task_id=payload["task_id"],
                role_id="query_agent",
                summary="Collected one attributable fixture source.",
                evidence_ids=tuple(payload["available_evidence_ids"]),
            )
        if output_schema is CitationSelectionBundle:
            return CitationSelectionBundle.model_validate(
                {
                    "selections": [
                        {
                            "claim_id": "claim-1",
                            "candidate_id": payload["candidates"][0][
                                "candidate_id"
                            ],
                        }
                    ]
                }
            )
        if output_schema is ReportOutline:
            claim_ids = tuple(
                claim["claim_id"] for claim in payload["verified_claims"]
            )
            return ReportOutline(
                ordered_claim_ids=claim_ids,
            )
        raise AssertionError(f"Unexpected output schema: {output_schema}")


async def fake_search(request: SearchRequest) -> SearchOutput:
    digest = hashlib.sha256(request.query.encode("utf-8")).hexdigest()[:12]
    content = f"Fixture source observation for query: {request.query}"
    return SearchOutput(
        provider="deterministic_fixture",
        query=request.query,
        provider_request_id=f"fixture-{digest}",
        results=(
            SearchResult(
                title="Deterministic research fixture",
                url=f"https://example.test/research/{digest}",
                content=content,
                published_at="2026-06-06",
                metadata={"fixture": True},
            ),
        ),
    )


def build_fake_tool_registry() -> ToolRegistry:
    return ToolRegistry(
        [
            ToolDefinition(
                tool_id="web_search",
                description="Return deterministic fixture search evidence.",
                input_model=SearchRequest,
                handler=fake_search,
            )
        ]
    )


def _topic_from_planning_prompt(prompt: str) -> str:
    marker = "Create a bounded research plan for this topic:\n"
    remainder = prompt.split(marker, 1)[-1]
    return remainder.split("\n\n", 1)[0].strip()
