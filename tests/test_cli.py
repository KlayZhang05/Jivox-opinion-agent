import subprocess
import sys
import json


def test_brief_command_writes_markdown_under_output_briefings(tmp_path):
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "opinion_agent",
            "brief",
            "--plan",
            "examples/briefing_plan.example.json",
            "--output-dir",
            str(tmp_path),
        ],
        cwd=".",
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    briefings_dir = tmp_path / "briefings"
    files = list(briefings_dir.glob("*.md"))
    assert len(files) == 1
    assert "# Personal public-opinion observation Briefing" in files[0].read_text(
        encoding="utf-8"
    )


def test_report_command_writes_citation_gated_markdown(tmp_path):
    evidence_path = tmp_path / "evidence.jsonl"
    evidence_path.write_text(
        json.dumps(
            {
                "evidence_id": "ev-1",
                "source_type": "news",
                "source_name": "Local News",
                "url": "https://example.test/update",
                "author": None,
                "published_at": "2026-06-05T08:00:00+08:00",
                "collected_at": "2026-06-05T09:00:00+08:00",
                "title": "Community update",
                "content": "A traceable observation about the event.",
                "metadata": {"fixture": True},
            }
        ),
        encoding="utf-8",
    )
    claims_path = tmp_path / "claims.json"
    claims_path.write_text(
        json.dumps(
            [
                {
                    "text": "Community discussion is measured rather than urgent.",
                    "evidence_ids": ["ev-1"],
                }
            ]
        ),
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "opinion_agent",
            "report",
            "--topic",
            "Local event",
            "--evidence",
            str(evidence_path),
            "--claims",
            str(claims_path),
            "--output-dir",
            str(tmp_path),
        ],
        cwd=".",
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    reports_dir = tmp_path / "reports"
    files = list(reports_dir.glob("*.md"))
    assert len(files) == 1
    assert "Evidence: ev-1" in files[0].read_text(encoding="utf-8")


def test_report_command_rejects_unknown_evidence_without_writing_file(tmp_path):
    evidence_path = tmp_path / "evidence.jsonl"
    evidence_path.write_text("", encoding="utf-8")
    claims_path = tmp_path / "claims.json"
    claims_path.write_text(
        json.dumps([{"text": "Unsupported.", "evidence_ids": ["ev-missing"]}]),
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "opinion_agent",
            "report",
            "--topic",
            "Local event",
            "--evidence",
            str(evidence_path),
            "--claims",
            str(claims_path),
            "--output-dir",
            str(tmp_path),
        ],
        cwd=".",
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 2
    assert "Unknown evidence_id: ev-missing" in result.stdout
    assert not (tmp_path / "reports").exists()


def test_conversation_command_writes_bounded_transcript(tmp_path):
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "opinion_agent",
            "conversation",
            "--policy",
            "examples/conversation_policy.example.json",
            "--turns",
            "examples/conversation_turns.example.json",
            "--evidence",
            "examples/sample_evidence.jsonl",
            "--output-dir",
            str(tmp_path),
        ],
        cwd=".",
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    transcripts = list((tmp_path / "conversations").glob("*.md"))
    assert len(transcripts) == 1
    markdown = transcripts[0].read_text(encoding="utf-8")
    assert "# Bounded Conversation: Personal public-opinion observation" in markdown
    assert "Evidence: sample-001" in markdown
    assert "Question to user: yes" in markdown


def test_conversation_command_rejects_invalid_policy_json_types(tmp_path):
    policy_path = tmp_path / "policy.json"
    policy_path.write_text(
        json.dumps(
            {
                "topic_boundary": None,
                "duration_minutes": 20.5,
                "principles": "stay calm",
                "allowed_tools": ["evidence_store"],
            }
        ),
        encoding="utf-8",
    )
    turns_path = tmp_path / "turns.json"
    turns_path.write_text("[]", encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "opinion_agent",
            "conversation",
            "--policy",
            str(policy_path),
            "--turns",
            str(turns_path),
            "--evidence",
            "examples/sample_evidence.jsonl",
            "--output-dir",
            str(tmp_path),
        ],
        cwd=".",
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 2
    assert "topic_boundary must be a string" in result.stdout
    assert not (tmp_path / "conversations").exists()


def test_conversation_command_rejects_invalid_turn_json_types(tmp_path):
    turns_path = tmp_path / "turns.json"
    turns_path.write_text(
        json.dumps(
            [
                {
                    "role": "assistant",
                    "topic": "Personal public-opinion observation",
                    "content": None,
                    "kind": "analysis",
                    "evidence_ids": "sample-001",
                }
            ]
        ),
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "opinion_agent",
            "conversation",
            "--policy",
            "examples/conversation_policy.example.json",
            "--turns",
            str(turns_path),
            "--evidence",
            "examples/sample_evidence.jsonl",
            "--output-dir",
            str(tmp_path),
        ],
        cwd=".",
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 2
    assert "conversation turn content must be a string" in result.stdout
    assert not (tmp_path / "conversations").exists()
