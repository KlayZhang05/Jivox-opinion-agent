from __future__ import annotations

import argparse
import json
from pathlib import Path

from .briefing.generator import generate_briefing_markdown
from .collectors.sample import load_sample_evidence
from .config import ConfigError, load_briefing_plan
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

    args = parser.parse_args(argv)
    if args.command == "brief":
        return _brief(args.plan, args.output_dir)
    if args.command == "report":
        return _report(args.topic, args.evidence, args.claims, args.output_dir)
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
