import json

import pytest

from opinion_agent.config import ConfigError, load_briefing_plan


def test_load_briefing_plan_reads_required_fields(tmp_path):
    plan_path = tmp_path / "plan.json"
    plan_path.write_text(
        json.dumps(
            {
                "topic": "Local transit changes",
                "keywords": ["transit", "bus"],
                "schedule": "daily",
                "max_items": 3,
                "tone": "calm",
            }
        ),
        encoding="utf-8",
    )

    plan = load_briefing_plan(plan_path)

    assert plan.topic == "Local transit changes"
    assert plan.keywords == ["transit", "bus"]
    assert plan.schedule == "daily"
    assert plan.max_items == 3
    assert plan.tone == "calm"


@pytest.mark.parametrize(
    ("payload", "message"),
    [
        (
            {
                "topic": " ",
                "keywords": ["transit"],
                "schedule": "daily",
                "max_items": 3,
                "tone": "calm",
            },
            "topic",
        ),
        (
            {
                "topic": "Local transit changes",
                "keywords": [],
                "schedule": "daily",
                "max_items": 3,
                "tone": "calm",
            },
            "keywords",
        ),
    ],
)
def test_load_briefing_plan_rejects_empty_topic_or_keywords(tmp_path, payload, message):
    plan_path = tmp_path / "plan.json"
    plan_path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ConfigError, match=message):
        load_briefing_plan(plan_path)
