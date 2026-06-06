from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable

from opinion_agent.graph.state import TraceEvent


_FORBIDDEN_KEYS = {
    "api_key",
    "authorization",
    "headers",
    "hidden_reasoning",
    "reasoning",
    "system_prompt",
    "user_prompt",
}


def write_run_trace(
    *,
    path: str | Path,
    run_id: str,
    topic: str,
    status: str,
    events: Iterable[TraceEvent | dict[str, Any]],
    errors: Iterable[str],
) -> Path:
    destination = Path(path)
    payload = {
        "schema_version": "1.0",
        "run_id": run_id,
        "topic": topic,
        "status": status,
        "events": [
            _sanitize(
                event.model_dump(mode="json")
                if isinstance(event, TraceEvent)
                else event
            )
            for event in events
        ],
        "errors": list(errors),
    }
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    temporary.replace(destination)
    return destination


def _sanitize(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: _sanitize(item)
            for key, item in value.items()
            if key.casefold() not in _FORBIDDEN_KEYS
        }
    if isinstance(value, list):
        return [_sanitize(item) for item in value]
    if isinstance(value, tuple):
        return [_sanitize(item) for item in value]
    return value
