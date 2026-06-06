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
    if not isinstance(policy.topic_boundary, str):
        raise ValueError("topic_boundary must be a string")
    if not policy.topic_boundary.strip():
        raise ValueError("topic_boundary is required")
    if type(policy.duration_minutes) is not int:
        raise ValueError("duration_minutes must be an integer")
    if policy.duration_minutes <= 0:
        raise ValueError("duration_minutes must be greater than 0")
    if isinstance(policy.principles, (str, bytes)):
        raise ValueError("principles must be a sequence of strings")
    if isinstance(policy.allowed_tools, (str, bytes)):
        raise ValueError("allowed_tools must be a sequence of strings")
    if any(not isinstance(item, str) for item in policy.principles):
        raise ValueError("principles must be a sequence of strings")
    if any(not isinstance(item, str) for item in policy.allowed_tools):
        raise ValueError("allowed_tools must be a sequence of strings")

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
