from opinion_agent.citations.evaluators import ExactQuoteEvaluator
from opinion_agent.citations.models import (
    ClaimInput,
    ClaimScope,
    EvidenceSpan,
    SupportAssessment,
)
from opinion_agent.citations.verifier import verify_claim_support
from opinion_agent.evidence.store import EvidenceStore


def evidence_record(evidence_id="ev-1"):
    return {
        "evidence_id": evidence_id,
        "source_type": "news",
        "source_name": "Local News",
        "url": "https://example.test/update",
        "published_at": "2026-06-06",
        "title": "Community update",
        "content": "Officials said the route adjustment is limited.",
        "metadata": {},
    }


def direct_quote_claim(**changes):
    data = {
        "claim_id": "claim-1",
        "claim_type": "direct_quote",
        "text": "the route adjustment is limited",
        "scope": {
            "platform": "local_news",
            "sample": "single report",
        },
        "evidence_ids": ["ev-1"],
    }
    data.update(changes)
    return ClaimInput.model_validate(data)


def test_exact_quote_evaluator_supports_only_exact_direct_quote(tmp_path):
    store = EvidenceStore(tmp_path / "evidence.jsonl")
    store.append(evidence_record())
    claim = direct_quote_claim()

    result = verify_claim_support(claim, store, ExactQuoteEvaluator())

    assert result.valid is True
    assert result.assessment is not None
    assert result.assessment.verdict == "supported"
    assert result.assessment.scope == claim.scope
    assert result.assessment.supporting_spans == (
        EvidenceSpan(
            evidence_id="ev-1",
            quote="the route adjustment is limited",
        ),
    )


def test_exact_quote_evaluator_returns_indeterminate_for_semantic_claim(tmp_path):
    store = EvidenceStore(tmp_path / "evidence.jsonl")
    store.append(evidence_record())
    claim = direct_quote_claim(
        claim_type="factual_statement",
        text="The change has a narrow scope.",
    )

    result = verify_claim_support(claim, store, ExactQuoteEvaluator())

    assert result.valid is False
    assert result.assessment is not None
    assert result.assessment.verdict == "indeterminate"


class InventedSpanEvaluator:
    def assess(self, claim, evidence):
        return SupportAssessment(
            claim_id=claim.claim_id,
            claim_type=claim.claim_type,
            scope=claim.scope,
            verdict="supported",
            reason="Invented quote.",
            supporting_spans=(
                EvidenceSpan(
                    evidence_id="ev-1",
                    quote="This text does not exist.",
                ),
            ),
            evaluator="fixture",
            evaluator_version="1",
        )


def test_verifier_rejects_invented_supporting_span(tmp_path):
    store = EvidenceStore(tmp_path / "evidence.jsonl")
    store.append(evidence_record())

    result = verify_claim_support(
        direct_quote_claim(),
        store,
        InventedSpanEvaluator(),
    )

    assert result.valid is False
    assert any("absent from evidence ev-1" in error for error in result.errors)


class CountingEvaluator:
    def __init__(self):
        self.calls = 0

    def assess(self, claim, evidence):
        self.calls += 1
        raise AssertionError("must not be called")


def test_missing_evidence_is_rejected_before_evaluator_call(tmp_path):
    store = EvidenceStore(tmp_path / "evidence.jsonl")
    evaluator = CountingEvaluator()

    result = verify_claim_support(
        direct_quote_claim(evidence_ids=["ev-missing"]),
        store,
        evaluator,
    )

    assert result.valid is False
    assert evaluator.calls == 0
    assert "ev-missing" in result.errors[0]


def test_scope_validates_and_preserves_declared_fields():
    scope = ClaimScope.model_validate(
        {
            "platform": "forum",
            "time_window": {
                "start": "2026-06-01T00:00:00Z",
                "end": "2026-06-06T00:00:00Z",
            },
            "sample": "20 public posts",
        }
    )

    assert scope.platform == "forum"
    assert scope.time_window.start == "2026-06-01T00:00:00Z"
    assert scope.sample == "20 public posts"
