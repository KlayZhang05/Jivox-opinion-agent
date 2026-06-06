from __future__ import annotations

import hashlib
import json
from typing import Any

from opinion_agent.tools.registry import ToolResult
from opinion_agent.tools.search import SearchOutput


def normalize_tool_result(
    result: ToolResult,
    *,
    task_id: str,
    role_id: str,
) -> list[dict[str, Any]]:
    if not result.ok or not isinstance(result.data, SearchOutput):
        return []

    records = []
    for item in result.data.results:
        identity = {
            "source_type": result.tool_id,
            "source_name": result.data.provider,
            "url": item.url,
            "title": item.title,
            "published_at": item.published_at,
            "content": item.content,
        }
        digest = hashlib.sha256(
            json.dumps(
                identity,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest()
        records.append(
            {
                "evidence_id": f"ev-{digest[:24]}",
                **identity,
                "author": None,
                "metadata": {
                    "task_id": task_id,
                    "role_id": role_id,
                    "query": result.data.query,
                    "provider_request_id": result.data.provider_request_id,
                    **item.metadata,
                },
            }
        )
    return records
