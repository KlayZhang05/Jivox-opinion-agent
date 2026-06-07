from __future__ import annotations

from opinion_agent.citations.evaluators import ExactQuoteEvaluator
from opinion_agent.llm.openai_compatible import (
    OpenAICompatibleStructuredModel,
)
from opinion_agent.research.fake import (
    FakeResearchModel,
    build_fake_tool_registry,
)
from opinion_agent.research.service import ResearchService
from opinion_agent.settings import RuntimeSettings
from opinion_agent.tools.registry import ToolDefinition, ToolRegistry
from opinion_agent.tools.search import AnspireSearchTool, SearchRequest


def build_fake_research_service() -> ResearchService:
    return ResearchService(
        model=FakeResearchModel(),
        tool_registry=build_fake_tool_registry(),
        evaluator=ExactQuoteEvaluator(),
        max_parallel_subagents=4,
    )


def build_real_research_service(
    settings: RuntimeSettings,
) -> ResearchService:
    search = AnspireSearchTool(
        settings=settings.search,
        timeout_seconds=settings.limits.search_timeout,
    )
    tools = ToolRegistry(
        [
            ToolDefinition(
                tool_id="web_search",
                description="Search attributable web sources.",
                input_model=SearchRequest,
                handler=search,
            )
        ]
    )
    model = OpenAICompatibleStructuredModel(
        settings=settings.llm,
        timeout_seconds=settings.limits.llm_request_timeout,
    )
    return ResearchService(
        model=model,
        tool_registry=tools,
        evaluator=ExactQuoteEvaluator(),
        max_parallel_subagents=settings.limits.max_parallel_subagents,
        trace_redactions=tuple(
            secret
            for secret in (
                settings.llm.api_key.get_secret_value(),
                settings.search.api_key.get_secret_value(),
                (
                    settings.tikhub.api_key.get_secret_value()
                    if settings.tikhub is not None
                    else ""
                ),
            )
            if secret
        ),
    )
