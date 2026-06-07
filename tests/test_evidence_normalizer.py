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


def test_normalizer_bounds_result_count_and_content_size():
    long_content = "relevant " * 1000
    result = ToolResult(
        tool_id="web_search",
        ok=True,
        data=SearchOutput(
            provider="anspire",
            query="bounded event",
            results=tuple(
                SearchResult(
                    title=f"Result {index}",
                    url=f"https://example.test/{index}",
                    content=long_content,
                )
                for index in range(10)
            ),
        ),
    )

    records = normalize_tool_result(
        result,
        task_id="task-1",
        role_id="query_agent",
    )

    assert len(records) == 3
    assert all(len(record["content"]) <= 4000 for record in records)
    assert all(record["metadata"]["content_truncated"] for record in records)
    assert all(
        record["metadata"]["original_content_chars"] == len(long_content)
        for record in records
    )


def test_evidence_id_uses_full_content_and_provider_metadata_cannot_override_provenance():
    common_prefix = "x" * 4000

    def normalize(suffix):
        return normalize_tool_result(
            ToolResult(
                tool_id="web_search",
                ok=True,
                data=SearchOutput(
                    provider="anspire",
                    query="bounded event",
                    provider_request_id="request-1",
                    results=(
                        SearchResult(
                            title="Result",
                            url="https://example.test/result",
                            content=common_prefix + suffix,
                            metadata={
                                "task_id": "provider-task",
                                "role_id": "provider-role",
                                "query": "provider-query",
                            },
                        ),
                    ),
                ),
            ),
            task_id="trusted-task",
            role_id="query_agent",
        )[0]

    first = normalize("first")
    second = normalize("second")

    assert first["evidence_id"] != second["evidence_id"]
    assert first["metadata"]["task_id"] == "trusted-task"
    assert first["metadata"]["role_id"] == "query_agent"
    assert first["metadata"]["query"] == "bounded event"
    assert first["metadata"]["provider_metadata"]["task_id"] == "provider-task"
