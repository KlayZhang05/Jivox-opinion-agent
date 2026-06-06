from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Sequence

from opinion_agent.citations.verifier import verify_citations
from opinion_agent.conversation.policy import (
    ConversationPolicy,
    validate_conversation_policy,
)
from opinion_agent.evidence.store import EvidenceStore


@dataclass(frozen=True)
class ConversationTurn:
    role: str
    content: str
    topic: str
    kind: str
    evidence_ids: tuple[str, ...]
    created_at: datetime
    asks_user: bool


class ConversationSession:
    def __init__(
        self,
        policy: ConversationPolicy,
        evidence_store: EvidenceStore,
        *,
        started_at: datetime | None = None,
    ) -> None:
        self.policy = validate_conversation_policy(policy)
        self.evidence_store = evidence_store
        self.started_at = started_at or datetime.now(timezone.utc)
        if self.started_at.tzinfo is None:
            raise ValueError("started_at must be timezone-aware")
        self.expires_at = self.started_at + timedelta(
            minutes=self.policy.duration_minutes
        )
        self.turns: list[ConversationTurn] = []

    def add_user_turn(
        self,
        content: str,
        *,
        topic: str,
        now: datetime | None = None,
    ) -> ConversationTurn:
        return self._append_turn(
            role="user",
            content=content,
            topic=topic,
            kind="statement",
            evidence_ids=(),
            asks_user=False,
            now=now,
        )

    def add_assistant_turn(
        self,
        content: str,
        *,
        topic: str,
        kind: str,
        evidence_ids: Sequence[str] = (),
        now: datetime | None = None,
    ) -> ConversationTurn:
        if not isinstance(kind, str):
            raise ValueError("assistant turn kind must be a string")
        normalized_kind = kind.strip().lower()
        if normalized_kind not in {"analysis", "question"}:
            raise ValueError("assistant turn kind must be analysis or question")

        if isinstance(evidence_ids, (str, bytes)) or not isinstance(
            evidence_ids, Sequence
        ):
            raise ValueError("evidence_ids must be a sequence of strings")
        if any(not isinstance(evidence_id, str) for evidence_id in evidence_ids):
            raise ValueError("evidence_ids must be a sequence of strings")
        normalized_ids = tuple(evidence_id.strip() for evidence_id in evidence_ids)
        if normalized_kind == "analysis" or normalized_ids:
            result = verify_citations(
                {"text": content, "evidence_ids": list(normalized_ids)},
                self.evidence_store,
            )
            if not result.valid:
                raise ValueError("; ".join(result.errors))

        return self._append_turn(
            role="assistant",
            content=content,
            topic=topic,
            kind=normalized_kind,
            evidence_ids=normalized_ids,
            asks_user=normalized_kind == "question",
            now=now,
        )

    def to_markdown(self) -> str:
        lines = [
            f"# Bounded Conversation: {self.policy.topic_boundary}",
            "",
            f"Started: {self.started_at.isoformat()}",
            f"Expires: {self.expires_at.isoformat()}",
            f"Duration: {self.policy.duration_minutes} minutes",
            "",
            "## Dialogue principles",
            "",
            *[f"- {principle}" for principle in self.policy.principles],
            "",
            "## Allowed tools",
            "",
            *[f"- {tool}" for tool in self.policy.allowed_tools],
            "",
            "## Transcript",
            "",
        ]

        if not self.turns:
            lines.append("No turns were recorded.")
        else:
            for turn in self.turns:
                quoted_content = [
                    f"> {line}" if line else ">" for line in turn.content.splitlines()
                ]
                lines.extend(
                    [
                        f"### {turn.role.title()} - {turn.kind}",
                        "",
                        *quoted_content,
                        "",
                        f"Time: {turn.created_at.isoformat()}",
                    ]
                )
                for evidence_id in turn.evidence_ids:
                    lines.append(f"Evidence: {evidence_id}")
                if turn.asks_user:
                    lines.append("Question to user: yes")
                lines.append("")

        return "\n".join(lines)

    def _append_turn(
        self,
        *,
        role: str,
        content: str,
        topic: str,
        kind: str,
        evidence_ids: tuple[str, ...],
        asks_user: bool,
        now: datetime | None,
    ) -> ConversationTurn:
        created_at = now or datetime.now(timezone.utc)
        if created_at.tzinfo is None:
            raise ValueError("turn time must be timezone-aware")
        if created_at < self.started_at:
            raise ValueError("turn time is before the session start")
        if created_at > self.expires_at:
            raise ValueError("conversation session has expired")
        if self.turns and created_at < self.turns[-1].created_at:
            raise ValueError("turn time is earlier than the previous turn")
        if not isinstance(topic, str):
            raise ValueError("turn topic must be a string")
        if topic.strip().casefold() != self.policy.topic_boundary.casefold():
            raise ValueError("turn is outside the conversation topic boundary")
        if not isinstance(content, str):
            raise ValueError("turn content must be a string")
        normalized_content = content.strip()
        if not normalized_content:
            raise ValueError("turn content must not be empty")

        turn = ConversationTurn(
            role=role,
            content=normalized_content,
            topic=self.policy.topic_boundary,
            kind=kind,
            evidence_ids=evidence_ids,
            created_at=created_at,
            asks_user=asks_user,
        )
        self.turns.append(turn)
        return turn
