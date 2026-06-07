from __future__ import annotations

import hashlib
import json
from typing import Any

from opinion_agent.tools.registry import ToolResult
from opinion_agent.tools.search import SearchOutput


MAX_EVIDENCE_PER_TOOL_CALL = 3
MAX_EVIDENCE_CONTENT_CHARS = 4000


def normalize_tool_result(
    result: ToolResult,
    *,
    task_id: str,
    role_id: str,
) -> list[dict[str, Any]]:
    if not result.ok or not isinstance(result.data, SearchOutput):
        return []

    records = []
    for item in result.data.results[:MAX_EVIDENCE_PER_TOOL_CALL]:
        original_content = item.content
        content = original_content[:MAX_EVIDENCE_CONTENT_CHARS]
        stored_identity = {
            "source_type": result.tool_id,
            "source_name": result.data.provider,
            "url": item.url,
            "title": item.title,
            "published_at": item.published_at,
            "content": content,
        }
        hash_identity = {
            **stored_identity,
            "content_sha256": hashlib.sha256(
                original_content.encode("utf-8")
            ).hexdigest(),
        }
        digest = hashlib.sha256(
            json.dumps(
                hash_identity,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest()
        records.append(
            {
                "evidence_id": f"ev-{digest[:24]}",
                **stored_identity,
                "author": None,
                "metadata": {
                    "provider_metadata": item.metadata,
                    "task_id": task_id,
                    "role_id": role_id,
                    "query": result.data.query,
                    "provider_request_id": result.data.provider_request_id,
                    "content_truncated": len(content) < len(original_content),
                    "original_content_chars": len(original_content),
                },
            }
        )
    return records
