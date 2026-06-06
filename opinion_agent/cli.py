from __future__ import annotations

import argparse
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .briefing.generator import generate_briefing_markdown
from .collectors.sample import load_sample_evidence
from .config import ConfigError, load_briefing_plan
from .conversation import ConversationPolicy, ConversationSession
from .evidence.store import EvidenceStore
from .reports.generator import generate_report_markdown


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="opinion_agent")
    subparsers = parser.add_subparsers(dest="command", required=True)

    brief = subparsers.add_parser("brief", help="Generate a sample Markdown briefing")
    brief.add_argument("--plan", required=True, help="Path to briefing plan JSON")
    brief.add_argument(
        "--output-dir",
        default="output",
        help="Base output directory. Briefings are written under its briefings subdirectory.",
    )
    report = subparsers.add_parser("report", help="Generate a citation-gated Markdown report")
    report.add_argument("--topic", required=True, help="Bounded report topic")
    report.add_argument("--evidence", required=True, help="JSONL evidence store path")
    report.add_argument("--claims", required=True, help="JSON claims file")
    report.add_argument(
        "--output-dir",
        default="output",
        help="Base output directory. Reports are written under its reports subdirectory.",
    )
    conversation = subparsers.add_parser(
        "conversation",
        help="Run a bounded scripted conversation and export its transcript",
    )
    conversation.add_argument("--policy", required=True, help="Conversation policy JSON")
    conversation.add_argument("--turns", required=True, help="Scripted turns JSON")
    conversation.add_argument("--evidence", required=True, help="JSONL evidence store path")
    conversation.add_argument(
        "--output-dir",
        default="output",
        help="Base output directory. Transcripts are written under conversations.",
    )

    args = parser.parse_args(argv)
    if args.command == "brief":
        return _brief(args.plan, args.output_dir)
    if args.command == "report":
        return _report(args.topic, args.evidence, args.claims, args.output_dir)
    if args.command == "conversation":
        return _conversation(
            args.policy,
            args.turns,
            args.evidence,
            args.output_dir,
        )
    return 2


def _brief(plan_path: str, output_dir: str) -> int:
    try:
        plan = load_briefing_plan(plan_path)
        evidence = load_sample_evidence(plan.evidence_path)
    except ConfigError as exc:
        print(f"Config error: {exc}")
        return 2
    except OSError as exc:
        print(f"File error: {exc}")
        return 2

    markdown = generate_briefing_markdown(plan, evidence)
    briefings_dir = Path(output_dir) / "briefings"
    briefings_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{_slug(plan.topic)}_briefing.md"
    output_path = briefings_dir / filename
    output_path.write_text(markdown, encoding="utf-8")
    print(output_path)
    return 0


def _slug(value: str) -> str:
    slug = "".join(character.lower() if character.isalnum() else "-" for character in value)
    return "-".join(part for part in slug.split("-") if part) or "briefing"


def _report(topic: str, evidence_path: str, claims_path: str, output_dir: str) -> int:
    try:
        claims = json.loads(Path(claims_path).read_text(encoding="utf-8"))
        if not isinstance(claims, list):
            raise ValueError("claims file must contain a JSON list")
        markdown = generate_report_markdown(topic, claims, EvidenceStore(evidence_path))
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"Report error: {exc}")
        return 2

    reports_dir = Path(output_dir) / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    output_path = reports_dir / f"{_slug(topic)}_report.md"
    output_path.write_text(markdown, encoding="utf-8")
    print(output_path)
    return 0


def _conversation(
    policy_path: str,
    turns_path: str,
    evidence_path: str,
    output_dir: str,
) -> int:
    try:
        policy_data = json.loads(Path(policy_path).read_text(encoding="utf-8"))
        turns = json.loads(Path(turns_path).read_text(encoding="utf-8"))
        if not isinstance(policy_data, dict):
            raise ValueError("conversation policy must be a JSON object")
        if not isinstance(turns, list):
            raise ValueError("conversation turns must be a JSON list")

        topic_boundary = policy_data.get("topic_boundary")
        duration_minutes = policy_data.get("duration_minutes")
        principles = policy_data.get("principles")
        allowed_tools = policy_data.get("allowed_tools")
        if not isinstance(topic_boundary, str):
            raise ValueError("conversation policy topic_boundary must be a string")
        if type(duration_minutes) is not int:
            raise ValueError("conversation policy duration_minutes must be an integer")
        if not isinstance(principles, list):
            raise ValueError("conversation policy principles must be a JSON list")
        if not isinstance(allowed_tools, list):
            raise ValueError("conversation policy allowed_tools must be a JSON list")

        policy = ConversationPolicy(
            topic_boundary=topic_boundary,
            duration_minutes=duration_minutes,
            principles=principles,
            allowed_tools=allowed_tools,
        )
        started_at = datetime.now(timezone.utc)
        session = ConversationSession(
            policy,
            EvidenceStore(evidence_path),
            started_at=started_at,
        )
        for index, turn in enumerate(turns, start=1):
            if not isinstance(turn, dict):
                raise ValueError("each conversation turn must be a JSON object")
            turn_time = started_at + timedelta(seconds=index)
            role = turn.get("role")
            topic = turn.get("topic")
            content = turn.get("content")
            if not isinstance(role, str):
                raise ValueError("conversation turn role must be a string")
            if not isinstance(topic, str):
                raise ValueError("conversation turn topic must be a string")
            if not isinstance(content, str):
                raise ValueError("conversation turn content must be a string")
            role = role.strip().lower()
            if role == "user":
                session.add_user_turn(content, topic=topic, now=turn_time)
            elif role == "assistant":
                kind = turn.get("kind")
                evidence_ids = turn.get("evidence_ids", [])
                if not isinstance(kind, str):
                    raise ValueError("assistant turn kind must be a string")
                if not isinstance(evidence_ids, list):
                    raise ValueError(
                        "assistant turn evidence_ids must be a JSON list"
                    )
                session.add_assistant_turn(
                    content,
                    topic=topic,
                    kind=kind,
                    evidence_ids=evidence_ids,
                    now=turn_time,
                )
            else:
                raise ValueError("conversation turn role must be user or assistant")
    except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
        print(f"Conversation error: {exc}")
        return 2

    conversations_dir = Path(output_dir) / "conversations"
    conversations_dir.mkdir(parents=True, exist_ok=True)
    output_path = conversations_dir / f"{_slug(policy.topic_boundary)}_conversation.md"
    output_path.write_text(session.to_markdown(), encoding="utf-8")
    print(output_path)
    return 0
