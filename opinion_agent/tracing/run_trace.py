from __future__ import annotations

import json
import re
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
    secret_values: Iterable[str] = (),
) -> Path:
    secrets = tuple(secret for secret in secret_values if secret)
    destination = Path(path)
    payload = {
        "schema_version": "1.0",
        "run_id": _redact(run_id, secrets),
        "topic": _redact(topic, secrets),
        "status": _redact(status, secrets),
        "events": [
            _sanitize(
                event.model_dump(mode="json")
                if isinstance(event, TraceEvent)
                else event,
                secrets,
            )
            for event in events
        ],
        "errors": [_redact(error, secrets) for error in errors],
    }
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    temporary.replace(destination)
    return destination


def _sanitize(value: Any, secrets: tuple[str, ...]) -> Any:
    if isinstance(value, dict):
        return {
            key: _sanitize(item, secrets)
            for key, item in value.items()
            if key.casefold() not in _FORBIDDEN_KEYS
        }
    if isinstance(value, list):
        return [_sanitize(item, secrets) for item in value]
    if isinstance(value, tuple):
        return [_sanitize(item, secrets) for item in value]
    if isinstance(value, str):
        return _redact(value, secrets)
    return value


def _redact(value: str, secrets: tuple[str, ...]) -> str:
    redacted = value
    for secret in secrets:
        redacted = redacted.replace(secret, "***")
    return re.sub(
        r"(?i)\bBearer\s+[A-Za-z0-9._~+/=-]+",
        "Bearer ***",
        redacted,
    )
