from opinion_agent.graph import runtime


def test_build_runtime_graph_returns_lightweight_descriptor_when_langgraph_unavailable(
    monkeypatch,
):
    monkeypatch.setattr(runtime, "find_spec", lambda name: None)

    graph = runtime.build_runtime_graph()

    assert graph.kind == "runtime_graph_descriptor"
    assert graph.langgraph_available is False
    assert graph.entrypoint == "forum_host"


def test_runtime_graph_declares_required_agent_roles():
    graph = runtime.build_runtime_graph()

    assert graph.roles == (
        "forum_host",
        "query_agent",
        "database_researcher",
        "multimedia_researcher",
        "citation_agent",
        "report_writer",
        "conversation_agent",
    )
    assert graph.nodes["forum_host"] == "Forum Host / Research Lead"
    assert ("forum_host", "query_agent") in graph.edges
    assert ("citation_agent", "report_writer") in graph.edges
    assert ("conversation_agent", "forum_host") in graph.edges
