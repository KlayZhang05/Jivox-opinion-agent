from __future__ import annotations

import httpx
import pytest
from pydantic import BaseModel, ConfigDict, Field

from opinion_agent.settings import SearchSettings
from opinion_agent.tools.registry import (
    ToolDefinition,
    ToolPermissionError,
    ToolRegistry,
    UnknownToolError,
)
from opinion_agent.tools.search import AnspireSearchTool, SearchRequest


class EchoInput(BaseModel):
    model_config = ConfigDict(frozen=True)

    text: str = Field(min_length=1)


class CountingHandler:
    def __init__(self):
        self.calls = 0

    async def __call__(self, arguments: EchoInput):
        self.calls += 1
        return {"echo": arguments.text}


@pytest.mark.asyncio
async def test_permission_is_checked_before_tool_handler_runs():
    handler = CountingHandler()
    registry = ToolRegistry(
        [
            ToolDefinition(
                tool_id="web_search",
                description="Search the web.",
                input_model=EchoInput,
                handler=handler,
            )
        ]
    )

    with pytest.raises(ToolPermissionError, match="report_writer"):
        await registry.invoke(
            role_id="report_writer",
            tool_id="web_search",
            arguments={"text": "event"},
        )

    assert handler.calls == 0


@pytest.mark.asyncio
async def test_registered_and_permitted_tool_validates_and_executes():
    handler = CountingHandler()
    registry = ToolRegistry(
        [
            ToolDefinition(
                tool_id="web_search",
                description="Search the web.",
                input_model=EchoInput,
                handler=handler,
            )
        ]
    )

    result = await registry.invoke(
        role_id="query_agent",
        tool_id="web_search",
        arguments={"text": "event"},
    )

    assert result.ok is True
    assert result.data == {"echo": "event"}
    assert result.error is None
    assert handler.calls == 1


@pytest.mark.asyncio
async def test_unknown_tool_is_rejected():
    registry = ToolRegistry([])

    with pytest.raises(UnknownToolError, match="missing_tool"):
        await registry.invoke(
            role_id="query_agent",
            tool_id="missing_tool",
            arguments={},
        )


@pytest.mark.asyncio
async def test_handler_failure_becomes_typed_tool_result():
    async def failing_handler(arguments: EchoInput):
        raise RuntimeError("provider exploded")

    registry = ToolRegistry(
        [
            ToolDefinition(
                tool_id="web_search",
                description="Search the web.",
                input_model=EchoInput,
                handler=failing_handler,
            )
        ]
    )

    result = await registry.invoke(
        role_id="query_agent",
        tool_id="web_search",
        arguments={"text": "event"},
    )

    assert result.ok is False
    assert result.error is not None
    assert result.error.kind == "execution_error"
    assert "provider exploded" in result.error.message


@pytest.mark.asyncio
async def test_anspire_adapter_preserves_source_metadata():
    def respond(request: httpx.Request) -> httpx.Response:
        assert request.headers["Authorization"] == "Bearer search-secret"
        assert request.url.params["query"] == "bounded event"
        return httpx.Response(
            200,
            json={
                "Uuid": "conversation-1",
                "results": [
                    {
                        "title": "Primary report",
                        "url": "https://example.test/report",
                        "content": "A traceable source excerpt.",
                        "date": "2026-06-06",
                        "score": 0.91,
                    }
                ],
            },
        )

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(respond)
    ) as client:
        tool = AnspireSearchTool(
            settings=SearchSettings(
                provider="anspire",
                api_key="search-secret",
                base_url="https://search.example.test",
            ),
            timeout_seconds=5,
            client=client,
        )
        output = await tool(SearchRequest(query="bounded event", max_results=3))

    assert output.provider == "anspire"
    assert output.query == "bounded event"
    assert output.provider_request_id == "conversation-1"
    assert len(output.results) == 1
    result = output.results[0]
    assert result.title == "Primary report"
    assert result.url == "https://example.test/report"
    assert result.content == "A traceable source excerpt."
    assert result.published_at == "2026-06-06"
    assert result.metadata == {"score": 0.91}


@pytest.mark.asyncio
async def test_anspire_adapter_rejects_malformed_provider_output():
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(200, json={"results": "not-a-list"})
        )
    ) as client:
        tool = AnspireSearchTool(
            settings=SearchSettings(
                provider="anspire",
                api_key="search-secret",
                base_url="https://search.example.test",
            ),
            timeout_seconds=5,
            client=client,
        )

        with pytest.raises(ValueError, match="results must be a list"):
            await tool(SearchRequest(query="bounded event"))
