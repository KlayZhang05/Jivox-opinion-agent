from opinion_agent.graph.runtime import describe_runtime_graph


def test_runtime_graph_declares_required_agent_roles():
    graph = describe_runtime_graph()

    assert graph.roles == (
        "forum_host",
        "query_agent",
        "database_researcher",
        "multimedia_researcher",
        "citation_agent",
        "report_writer",
        "tikhub_researcher",
    )
    assert graph.nodes["forum_host"] == "Forum Host / Research Lead"
    assert graph.entrypoint == "plan_research"
    assert "run_subagent" in graph.runtime_nodes
    assert "prepare_claims" in graph.runtime_nodes
