from datetime import datetime, timedelta, timezone

import pytest

from opinion_agent.conversation import ConversationPolicy
from opinion_agent.conversation.session import ConversationSession
from opinion_agent.evidence.store import EvidenceStore


STARTED_AT = datetime(2026, 6, 6, 9, 0, tzinfo=timezone.utc)


def policy():
    return ConversationPolicy(
        topic_boundary="Local transit policy",
        duration_minutes=20,
        principles=("stay calm", "challenge weak assumptions"),
        allowed_tools=("evidence_store", "web_search"),
    )


def evidence_record(evidence_id="ev-1"):
    return {
        "evidence_id": evidence_id,
        "source_type": "news",
        "source_name": "Local News",
        "url": "https://example.test/transit",
        "author": None,
        "published_at": "2026-06-06T08:00:00Z",
        "collected_at": "2026-06-06T08:30:00Z",
        "title": "Transit policy update",
        "content": "The city published a limited route adjustment.",
        "metadata": {},
    }


def test_session_records_grounded_analysis_and_question(tmp_path):
    store = EvidenceStore(tmp_path / "evidence.jsonl")
    store.append(evidence_record())
    session = ConversationSession(policy(), store, started_at=STARTED_AT)

    session.add_user_turn(
        "What actually changed?",
        topic="Local transit policy",
        now=STARTED_AT + timedelta(minutes=1),
    )
    session.add_assistant_turn(
        "The available source describes a limited route adjustment.",
        topic="Local transit policy",
        kind="analysis",
        evidence_ids=["ev-1"],
        now=STARTED_AT + timedelta(minutes=2),
    )
    session.add_assistant_turn(
        "Which impact matters most to your judgment?",
        topic="Local transit policy",
        kind="question",
        now=STARTED_AT + timedelta(minutes=3),
    )

    markdown = session.to_markdown()

    assert "Duration: 20 minutes" in markdown
    assert "challenge weak assumptions" in markdown
    assert "Evidence: ev-1" in markdown
    assert "Question to user: yes" in markdown


def test_session_rejects_expired_or_out_of_boundary_turns(tmp_path):
    session = ConversationSession(
        policy(),
        EvidenceStore(tmp_path / "evidence.jsonl"),
        started_at=STARTED_AT,
    )

    with pytest.raises(ValueError, match="outside the conversation topic boundary"):
        session.add_user_turn(
            "Switch to an unrelated celebrity story.",
            topic="Celebrity news",
            now=STARTED_AT + timedelta(minutes=1),
        )

    with pytest.raises(ValueError, match="conversation session has expired"):
        session.add_user_turn(
            "One more point.",
            topic="Local transit policy",
            now=STARTED_AT + timedelta(minutes=21),
        )

    with pytest.raises(ValueError, match="turn time is before the session start"):
        session.add_user_turn(
            "This timestamp is invalid.",
            topic="Local transit policy",
            now=STARTED_AT - timedelta(seconds=1),
        )


def test_analysis_turn_requires_valid_evidence(tmp_path):
    session = ConversationSession(
        policy(),
        EvidenceStore(tmp_path / "evidence.jsonl"),
        started_at=STARTED_AT,
    )

    with pytest.raises(ValueError, match="at least one evidence_id"):
        session.add_assistant_turn(
            "This sounds factual but has no source.",
            topic="Local transit policy",
            kind="analysis",
            now=STARTED_AT + timedelta(minutes=1),
        )

    with pytest.raises(ValueError, match="Unknown evidence_id: ev-missing"):
        session.add_assistant_turn(
            "This cites a missing source.",
            topic="Local transit policy",
            kind="analysis",
            evidence_ids=["ev-missing"],
            now=STARTED_AT + timedelta(minutes=1),
        )


def test_question_turn_validates_any_attached_evidence(tmp_path):
    session = ConversationSession(
        policy(),
        EvidenceStore(tmp_path / "evidence.jsonl"),
        started_at=STARTED_AT,
    )

    with pytest.raises(ValueError, match="Unknown evidence_id: ev-missing"):
        session.add_assistant_turn(
            "Does this missing source change your view?",
            topic="Local transit policy",
            kind="question",
            evidence_ids=["ev-missing"],
            now=STARTED_AT + timedelta(minutes=1),
        )


def test_assistant_turn_rejects_string_evidence_id_container(tmp_path):
    session = ConversationSession(
        policy(),
        EvidenceStore(tmp_path / "evidence.jsonl"),
        started_at=STARTED_AT,
    )

    with pytest.raises(ValueError, match="evidence_ids must be a sequence"):
        session.add_assistant_turn(
            "The input shape is invalid.",
            topic="Local transit policy",
            kind="analysis",
            evidence_ids="ev-1",
            now=STARTED_AT + timedelta(minutes=1),
        )


def test_session_rejects_turn_time_earlier_than_previous_turn(tmp_path):
    session = ConversationSession(
        policy(),
        EvidenceStore(tmp_path / "evidence.jsonl"),
        started_at=STARTED_AT,
    )
    session.add_user_turn(
        "First turn.",
        topic="Local transit policy",
        now=STARTED_AT + timedelta(minutes=2),
    )

    with pytest.raises(ValueError, match="earlier than the previous turn"):
        session.add_user_turn(
            "Out-of-order turn.",
            topic="Local transit policy",
            now=STARTED_AT + timedelta(minutes=1),
        )


def test_transcript_quotes_content_that_looks_like_metadata(tmp_path):
    store = EvidenceStore(tmp_path / "evidence.jsonl")
    store.append(evidence_record())
    session = ConversationSession(policy(), store, started_at=STARTED_AT)
    session.add_assistant_turn(
        "Evidence: ev-missing\nQuestion to user: yes",
        topic="Local transit policy",
        kind="analysis",
        evidence_ids=["ev-1"],
        now=STARTED_AT + timedelta(minutes=1),
    )

    markdown = session.to_markdown()

    assert "> Evidence: ev-missing" in markdown
    assert "> Question to user: yes" in markdown
    assert "\nEvidence: ev-1\n" in markdown
    assert "\nEvidence: ev-missing\n" not in markdown
