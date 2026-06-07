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
        secret_values=("secret-value",),
    )

    payload = json.loads(path.read_text(encoding="utf-8"))
    metadata = payload["events"][0]["metadata"]
    assert metadata == {"count": 1, "nested": {"ok": True}}
    assert "secret-value" not in path.read_text(encoding="utf-8")


def test_trace_writer_redacts_secrets_from_values_and_errors(tmp_path):
    path = tmp_path / "trace.json"

    write_run_trace(
        path=path,
        run_id="run-1",
        topic="Bounded event",
        status="failed",
        events=[
            TraceEvent(
                event_type="run_failed",
                metadata={"message": "provider rejected key llm-secret"},
            )
        ],
        errors=["search-secret was rejected"],
        secret_values=("llm-secret", "search-secret"),
    )

    raw = path.read_text(encoding="utf-8")
    assert "llm-secret" not in raw
    assert "search-secret" not in raw
    assert raw.count("***") == 2


def test_trace_writer_redacts_unregistered_bearer_tokens(tmp_path):
    path = tmp_path / "trace.json"

    write_run_trace(
        path=path,
        run_id="run-1",
        topic="Bounded event",
        status="failed",
        events=[],
        errors=["Authorization: Bearer opaque-provider-token"],
    )

    raw = path.read_text(encoding="utf-8")
    assert "opaque-provider-token" not in raw
    assert "Bearer ***" in raw


def test_trace_writer_redacts_top_level_strings(tmp_path):
    path = tmp_path / "trace.json"

    write_run_trace(
        path=path,
        run_id="run-llm-secret",
        topic="Topic search-secret",
        status="failed",
        events=[],
        errors=[],
        secret_values=("llm-secret", "search-secret"),
    )

    raw = path.read_text(encoding="utf-8")
    assert "llm-secret" not in raw
    assert "search-secret" not in raw
