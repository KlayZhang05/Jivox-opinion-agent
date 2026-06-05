import pytest

from opinion_agent.conversation import (
    ConversationPolicy,
    validate_conversation_policy,
)


def test_accepts_bounded_conversation_policy():
    policy = validate_conversation_policy(
        ConversationPolicy(
            topic_boundary="Follow only the current public-opinion event.",
            duration_minutes=20,
            principles=("calm tone", "challenge weak assumptions"),
            allowed_tools=("evidence_store", "citation_verifier"),
        )
    )

    assert policy.topic_boundary == "Follow only the current public-opinion event."
    assert policy.duration_minutes == 20
    assert policy.principles == ("calm tone", "challenge weak assumptions")
    assert policy.allowed_tools == ("evidence_store", "citation_verifier")


def test_rejects_non_positive_duration():
    with pytest.raises(ValueError, match="duration_minutes"):
        validate_conversation_policy(
            ConversationPolicy(
                topic_boundary="Stay on the event.",
                duration_minutes=0,
                principles=("be concise",),
                allowed_tools=("evidence_store",),
            )
        )


def test_rejects_missing_topic_boundary():
    with pytest.raises(ValueError, match="topic_boundary"):
        validate_conversation_policy(
            ConversationPolicy(
                topic_boundary=" ",
                duration_minutes=15,
                principles=("be concise",),
                allowed_tools=("evidence_store",),
            )
        )


def test_rejects_missing_principles_or_allowed_tools():
    with pytest.raises(ValueError, match="at least one dialogue principle"):
        validate_conversation_policy(
            ConversationPolicy(
                topic_boundary="Stay on the event.",
                duration_minutes=15,
                principles=(),
                allowed_tools=("evidence_store",),
            )
        )

    with pytest.raises(ValueError, match="at least one allowed tool"):
        validate_conversation_policy(
            ConversationPolicy(
                topic_boundary="Stay on the event.",
                duration_minutes=15,
                principles=("be concise",),
                allowed_tools=(),
            )
        )
