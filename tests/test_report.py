import json

import pytest

from opinion_agent.citations.evaluators import ExactQuoteEvaluator
from opinion_agent.evidence.store import EvidenceStore
from opinion_agent.reports.generator import write_report_artifacts


def evidence_record(evidence_id="ev-1"):
    return {
        "evidence_id": evidence_id,
        "source_type": "news",
        "source_name": "Local News",
        "url": "https://example.test/update",
        "published_at": "2026-06-06",
        "title": "Community update",
        "content": "The route adjustment is limited.",
        "metadata": {},
    }


def direct_quote_claim(**changes):
    claim = {
        "claim_id": "claim-1",
        "claim_type": "direct_quote",
        "text": "The route adjustment is limited.",
        "scope": {"platform": "local_news", "sample": "single report"},
        "evidence_ids": ["ev-1"],
    }
    claim.update(changes)
    return claim


def test_supported_claim_writes_markdown_and_verification_sidecar(tmp_path):
    store = EvidenceStore(tmp_path / "evidence.jsonl")
    store.append(evidence_record())
    report_path = tmp_path / "report.md"

    artifacts = write_report_artifacts(
        topic="Local event",
        claims=[direct_quote_claim()],
        evidence_store=store,
        evaluator=ExactQuoteEvaluator(),
        report_path=report_path,
    )

    markdown = report_path.read_text(encoding="utf-8")
    sidecar = json.loads(artifacts.verification_path.read_text(encoding="utf-8"))
    assert "The route adjustment is limited." in markdown
    assert "Evidence: ev-1" in markdown
    assert "Exact excerpt: The route adjustment is limited." in markdown
    assert "Platform: local_news" in markdown
    assert sidecar["schema_version"] == "1.0"
    assert sidecar["claims"][0]["claim_type"] == "direct_quote"
    assert sidecar["claims"][0]["scope"]["sample"] == "single report"
    assert sidecar["assessments"][0]["verdict"] == "supported"


def test_unsupported_claim_writes_no_artifacts(tmp_path):
    store = EvidenceStore(tmp_path / "evidence.jsonl")
    store.append(evidence_record())
    report_path = tmp_path / "report.md"
    sidecar_path = tmp_path / "report_verification.json"

    with pytest.raises(ValueError, match="indeterminate"):
        write_report_artifacts(
            topic="Local event",
            claims=[
                direct_quote_claim(
                    claim_type="analytic_inference",
                    text="The response was cautious.",
                )
            ],
            evidence_store=store,
            evaluator=ExactQuoteEvaluator(),
            report_path=report_path,
        )

    assert report_path.exists() is False
    assert sidecar_path.exists() is False


def test_duplicate_claim_ids_write_no_artifacts(tmp_path):
    store = EvidenceStore(tmp_path / "evidence.jsonl")
    store.append(evidence_record())
    report_path = tmp_path / "report.md"

    with pytest.raises(ValueError, match="Duplicate claim_id"):
        write_report_artifacts(
            topic="Local event",
            claims=[direct_quote_claim(), direct_quote_claim()],
            evidence_store=store,
            evaluator=ExactQuoteEvaluator(),
            report_path=report_path,
        )

    assert report_path.exists() is False


def test_report_title_is_deterministic_and_not_model_authored(tmp_path):
    store = EvidenceStore(tmp_path / "evidence.jsonl")
    store.append(evidence_record())

    artifacts = write_report_artifacts(
        topic="Local event",
        claims=[direct_quote_claim()],
        evidence_store=store,
        evaluator=ExactQuoteEvaluator(),
        report_path=tmp_path / "report.md",
    )

    markdown = artifacts.report_path.read_text(encoding="utf-8")
    assert markdown.startswith("# Local event Public Opinion Report")


def test_report_escapes_markdown_structure_from_untrusted_text(tmp_path):
    store = EvidenceStore(tmp_path / "evidence.jsonl")
    record = evidence_record()
    record.update(
        {
            "source_name": "Source\n## Injected source",
            "title": "<script>alert(1)</script>",
            "content": "Quoted text\n## Injected claim",
        }
    )
    store.append(record)

    artifacts = write_report_artifacts(
        topic="Local event\n## Injected topic",
        claims=[
            direct_quote_claim(text="Quoted text\n## Injected claim")
        ],
        evidence_store=store,
        evaluator=ExactQuoteEvaluator(),
        report_path=tmp_path / "report.md",
    )

    markdown = artifacts.report_path.read_text(encoding="utf-8")
    assert "\n## Injected topic" not in markdown
    assert "\n## Injected claim" not in markdown
    assert "\n## Injected source" not in markdown
    assert "<script>" not in markdown
    assert "&lt;script&gt;" in markdown


def test_report_claim_text_cannot_become_a_thematic_break(tmp_path):
    store = EvidenceStore(tmp_path / "evidence.jsonl")
    record = evidence_record()
    record["content"] = "---"
    store.append(record)

    artifacts = write_report_artifacts(
        topic="Local event",
        claims=[direct_quote_claim(text="---")],
        evidence_store=store,
        evaluator=ExactQuoteEvaluator(),
        report_path=tmp_path / "report.md",
    )

    markdown = artifacts.report_path.read_text(encoding="utf-8")
    assert "\n---\n" not in markdown
    assert "Claim: ---" in markdown
