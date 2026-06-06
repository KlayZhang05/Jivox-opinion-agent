import json

from opinion_agent.graph.state import TraceEvent
from opinion_agent.tracing.run_trace import write_run_trace


def test_trace_writer_omits_sensitive_and_hidden_reasoning_fields(tmp_path):
    path = tmp_path / "trace.json"

    write_run_trace(
        path=path,
        run_id="run-1",
        topic="Bounded event",
        status="completed",
        events=[
            TraceEvent(
                event_type="fixture",
                metadata={
                    "count": 1,
                    "api_key": "secret-value",
                    "authorization": "Bearer secret-value",
                    "hidden_reasoning": "private chain",
                    "nested": {"system_prompt": "private prompt", "ok": True},
                },
            )
        ],
        errors=[],
    )

    payload = json.loads(path.read_text(encoding="utf-8"))
    metadata = payload["events"][0]["metadata"]
    assert metadata == {"count": 1, "nested": {"ok": True}}
    assert "secret-value" not in path.read_text(encoding="utf-8")
