import pytest

from opinion_agent.evidence.store import EvidenceStore
from opinion_agent.reports.generator import generate_report_markdown


def evidence_record(evidence_id, title="Community update"):
    return {
        "evidence_id": evidence_id,
        "source_type": "news",
        "source_name": "Local News",
        "url": "https://example.test/update",
        "author": None,
        "published_at": "2026-06-05T08:00:00+08:00",
        "collected_at": "2026-06-05T09:00:00+08:00",
        "title": title,
        "content": "A traceable observation about the event.",
        "metadata": {"fixture": True},
    }


def test_generate_report_markdown_uses_verified_evidence(tmp_path):
    store = EvidenceStore(tmp_path / "evidence.jsonl")
    store.append(evidence_record("ev-1"))
    claims = [
        {
            "text": "Community discussion is measured rather than urgent.",
            "evidence_ids": ["ev-1"],
        }
    ]

    markdown = generate_report_markdown("Local event", claims, store)

    assert markdown.startswith("# Local event Public Opinion Report")
    assert "## Evidence-grounded claims" in markdown
    assert "Community discussion is measured rather than urgent." in markdown
    assert "Evidence: ev-1" in markdown
    assert "Local News" in markdown
    assert "No uncited claims were included." in markdown


def test_generate_report_markdown_rejects_unknown_evidence_id(tmp_path):
    store = EvidenceStore(tmp_path / "evidence.jsonl")
    claims = [{"text": "Unsupported claim.", "evidence_ids": ["ev-missing"]}]

    with pytest.raises(ValueError, match="Unknown evidence_id: ev-missing"):
        generate_report_markdown("Local event", claims, store)
