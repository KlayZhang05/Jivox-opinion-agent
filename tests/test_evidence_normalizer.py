from opinion_agent.evidence.normalizer import normalize_tool_result
from opinion_agent.tools.registry import ToolResult
from opinion_agent.tools.search import SearchOutput, SearchResult


def test_search_results_receive_stable_evidence_ids():
    tool_result = ToolResult(
        tool_id="web_search",
        ok=True,
        data=SearchOutput(
            provider="anspire",
            query="bounded event",
            provider_request_id="request-1",
            results=(
                SearchResult(
                    title="Primary report",
                    url="https://example.test/report",
                    content="A direct source excerpt.",
                    published_at="2026-06-06",
                    metadata={"score": 0.91},
                ),
            ),
        ),
    )

    first = normalize_tool_result(
        tool_result,
        task_id="task-1",
        role_id="query_agent",
    )
    second = normalize_tool_result(
        tool_result,
        task_id="task-2",
        role_id="query_agent",
    )

    assert first[0]["evidence_id"] == second[0]["evidence_id"]
    assert first[0]["content"] == "A direct source excerpt."
    assert first[0]["source_name"] == "anspire"
    assert first[0]["metadata"]["provider_request_id"] == "request-1"
    assert first[0]["metadata"]["task_id"] == "task-1"


def test_failed_tool_result_produces_no_evidence():
    assert normalize_tool_result(
        ToolResult(tool_id="web_search", ok=False),
        task_id="task-1",
        role_id="query_agent",
    ) == []
