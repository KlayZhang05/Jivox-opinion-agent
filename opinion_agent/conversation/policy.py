from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence


@dataclass(frozen=True)
class ConversationPolicy:
    topic_boundary: str
    duration_minutes: int
    principles: Sequence[str] = ()
    allowed_tools: Sequence[str] = ()


def validate_conversation_policy(policy: ConversationPolicy) -> ConversationPolicy:
    if not policy.topic_boundary.strip():
        raise ValueError("topic_boundary is required")
    if policy.duration_minutes <= 0:
        raise ValueError("duration_minutes must be greater than 0")
    principles = tuple(item.strip() for item in policy.principles if item.strip())
    allowed_tools = tuple(item.strip() for item in policy.allowed_tools if item.strip())
    if not principles:
        raise ValueError("at least one dialogue principle is required")
    if not allowed_tools:
        raise ValueError("at least one allowed tool is required")

    return ConversationPolicy(
        topic_boundary=policy.topic_boundary.strip(),
        duration_minutes=policy.duration_minutes,
        principles=principles,
        allowed_tools=allowed_tools,
    )
