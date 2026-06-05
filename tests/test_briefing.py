import json

import pytest

from opinion_agent.briefing.generator import generate_briefing_markdown
from opinion_agent.collectors.sample import load_sample_evidence
from opinion_agent.models import BriefingPlan


def test_generate_briefing_is_calm_low_stimulation_and_limited(tmp_path):
    evidence_path = tmp_path / "evidence.jsonl"
    evidence_path.write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "evidence_id": "ev-transit-1",
                        "source_type": "news",
                        "title": "Transit board approves quiet service trial",
                        "source_name": "Local News",
                        "url": "https://example.test/transit",
                        "published_at": "2026-06-05T08:00:00+08:00",
                        "content": "The bus update focuses on reliability without major disruption.",
                    }
                ),
                json.dumps(
                    {
                        "evidence_id": "ev-sports-1",
                        "source_type": "news",
                        "title": "Unrelated sports result",
                        "source_name": "Sports Wire",
                        "url": "https://example.test/sports",
                        "published_at": "2026-06-05T09:00:00+08:00",
                        "content": "The match went into overtime.",
                    }
                ),
                json.dumps(
                    {
                        "evidence_id": "ev-bus-1",
                        "source_type": "social_post",
                        "title": "Bus riders ask for clearer route notices",
                        "source_name": "Community Forum",
                        "url": "https://example.test/forum",
                        "published_at": "2026-06-05T10:00:00+08:00",
                        "content": "Residents want earlier notice before route adjustments.",
                    }
                ),
            ]
        ),
        encoding="utf-8",
    )
    plan = BriefingPlan(
        topic="Local transit changes",
        keywords=["transit", "bus"],
        schedule="daily",
        max_items=1,
        tone="calm",
    )

    markdown = generate_briefing_markdown(plan, load_sample_evidence(evidence_path))

    assert markdown.startswith("# Local transit changes Briefing")
    assert "Low-stimulation summary" in markdown
    assert "No urgent action is suggested" in markdown
    assert "Transit board approves quiet service trial" in markdown
    assert "Evidence: ev-transit-1" in markdown
    assert "Source type: news" in markdown
    assert "Bus riders ask for clearer route notices" not in markdown
    assert "Unrelated sports result" not in markdown
    assert "!!!" not in markdown


def test_sample_evidence_loader_rejects_blank_evidence_id(tmp_path):
    evidence_path = tmp_path / "evidence.jsonl"
    evidence_path.write_text(
        json.dumps(
            {
                "evidence_id": "",
                "source_type": "news",
                "source_name": "Local News",
                "title": "Missing evidence ID",
                "content": "This should fail closed.",
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="evidence_id is required"):
        load_sample_evidence(evidence_path)
