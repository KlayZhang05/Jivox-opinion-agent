from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .models import BriefingPlan


class ConfigError(ValueError):
    """Raised when a briefing plan is missing required usable values."""


def load_briefing_plan(path: str | Path) -> BriefingPlan:
    plan_path = Path(path)
    try:
        raw = json.loads(plan_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ConfigError(f"Invalid JSON in briefing plan: {exc.msg}") from exc
    except OSError as exc:
        raise ConfigError(f"Could not read briefing plan: {plan_path}") from exc

    if not isinstance(raw, dict):
        raise ConfigError("Briefing plan must be a JSON object")

    topic = _required_text(raw, "topic")
    keywords = _keywords(raw.get("keywords"))
    schedule = _required_text(raw, "schedule")
    tone = _required_text(raw, "tone")
    max_items = _max_items(raw.get("max_items"))
    evidence_path = str(raw.get("evidence_path") or "examples/sample_evidence.jsonl")

    return BriefingPlan(
        topic=topic,
        keywords=keywords,
        schedule=schedule,
        max_items=max_items,
        tone=tone,
        evidence_path=evidence_path,
    )


def _required_text(raw: dict[str, Any], field: str) -> str:
    value = raw.get(field)
    if not isinstance(value, str) or not value.strip():
        raise ConfigError(f"Briefing plan {field} must not be empty")
    return value.strip()


def _keywords(value: Any) -> list[str]:
    if not isinstance(value, list):
        raise ConfigError("Briefing plan keywords must be a non-empty list")
    keywords = [item.strip() for item in value if isinstance(item, str) and item.strip()]
    if not keywords:
        raise ConfigError("Briefing plan keywords must not be empty")
    return keywords


def _max_items(value: Any) -> int:
    if not isinstance(value, int) or value < 1:
        raise ConfigError("Briefing plan max_items must be a positive integer")
    return value
