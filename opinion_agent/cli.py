from __future__ import annotations

import argparse
from pathlib import Path

from .briefing.generator import generate_briefing_markdown
from .collectors.sample import load_sample_evidence
from .config import ConfigError, load_briefing_plan


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

    args = parser.parse_args(argv)
    if args.command == "brief":
        return _brief(args.plan, args.output_dir)
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
