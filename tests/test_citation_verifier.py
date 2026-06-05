from opinion_agent.citations.verifier import verify_claim
from opinion_agent.evidence.store import EvidenceStore


def sample_record(evidence_id):
    return {
        "evidence_id": evidence_id,
        "source_type": "sample",
        "source_name": "local fixture",
        "collected_at": "2026-06-05T00:00:00Z",
        "content": "A traceable observation.",
        "metadata": {},
    }


def test_claim_citing_unknown_evidence_id_is_invalid(tmp_path):
    store = EvidenceStore(tmp_path / "evidence.jsonl")
    claim = {"text": "The event generated discussion.", "evidence_ids": ["ev-missing"]}

    result = verify_claim(claim, store)

    assert result["valid"] is False
    assert result["errors"] == ["Unknown evidence_id: ev-missing"]


def test_claim_citing_existing_evidence_ids_is_valid(tmp_path):
    store = EvidenceStore(tmp_path / "evidence.jsonl")
    store.append(sample_record("ev-1"))
    store.append(sample_record("ev-2"))
    claim = {"text": "Two observations support this.", "evidence_ids": ["ev-1", "ev-2"]}

    result = verify_claim(claim, store)

    assert result == {"valid": True, "errors": []}


def test_claim_without_evidence_ids_is_invalid_with_explicit_error(tmp_path):
    store = EvidenceStore(tmp_path / "evidence.jsonl")
    claim = {"text": "Unsupported claim.", "evidence_ids": []}

    result = verify_claim(claim, store)

    assert result["valid"] is False
    assert result["errors"] == ["Claim must cite at least one evidence_id"]


def test_claim_with_non_list_evidence_ids_is_invalid(tmp_path):
    store = EvidenceStore(tmp_path / "evidence.jsonl")
    store.append(sample_record("ev-1"))
    claim = {"text": "Unsupported claim shape.", "evidence_ids": "ev-1"}

    result = verify_claim(claim, store)

    assert result["valid"] is False
    assert result["errors"] == ["Claim evidence_ids must be a list of evidence IDs"]
