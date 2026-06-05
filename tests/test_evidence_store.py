import json

import pytest

from opinion_agent.evidence.store import EvidenceStore


def sample_record(evidence_id="ev-001"):
    return {
        "evidence_id": evidence_id,
        "source_type": "sample",
        "source_name": "local fixture",
        "url": None,
        "author": None,
        "published_at": None,
        "collected_at": "2026-06-05T00:00:00Z",
        "title": "Sample item",
        "content": "A traceable public-opinion observation.",
        "metadata": {"topic": "test"},
    }


def test_appends_and_reads_evidence_records_as_jsonl(tmp_path):
    store_path = tmp_path / "evidence.jsonl"
    store = EvidenceStore(store_path)
    record = sample_record()

    assert store.append(record) is True

    assert store.read_all() == [record]
    raw_line = store_path.read_text(encoding="utf-8").strip()
    assert json.loads(raw_line) == record


def test_rejects_evidence_without_stable_id(tmp_path):
    store = EvidenceStore(tmp_path / "evidence.jsonl")
    record = sample_record()
    record["evidence_id"] = ""

    with pytest.raises(ValueError, match="evidence_id is required"):
        store.append(record)


def test_duplicate_evidence_ids_are_not_written_twice(tmp_path):
    store_path = tmp_path / "evidence.jsonl"
    store = EvidenceStore(store_path)

    assert store.append(sample_record("ev-dup")) is True
    assert store.append(sample_record("ev-dup")) is False

    assert store.read_all() == [sample_record("ev-dup")]
    assert len(store_path.read_text(encoding="utf-8").splitlines()) == 1
