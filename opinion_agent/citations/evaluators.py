from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any, Protocol

from opinion_agent.citations.models import (
    ClaimInput,
    EvidenceSpan,
    SupportAssessment,
)


class SupportEvaluator(Protocol):
    def assess(
        self,
        claim: ClaimInput,
        evidence: Sequence[Mapping[str, Any]],
    ) -> SupportAssessment:
        ...


class ExactQuoteEvaluator:
    evaluator_id = "exact_quote"
    evaluator_version = "1.0"

    def assess(
        self,
        claim: ClaimInput,
        evidence: Sequence[Mapping[str, Any]],
    ) -> SupportAssessment:
        if claim.claim_type != "direct_quote":
            return SupportAssessment(
                claim_id=claim.claim_id,
                claim_type=claim.claim_type,
                scope=claim.scope,
                verdict="indeterminate",
                reason=(
                    "ExactQuoteEvaluator supports only direct_quote claims."
                ),
                evaluator=self.evaluator_id,
                evaluator_version=self.evaluator_version,
            )

        normalized_claim = _normalize_line_endings(claim.text)
        for record in evidence:
            content = str(record.get("content") or "")
            if normalized_claim in _normalize_line_endings(content):
                return SupportAssessment(
                    claim_id=claim.claim_id,
                    claim_type=claim.claim_type,
                    scope=claim.scope,
                    verdict="supported",
                    reason="The complete claim is an exact cited evidence span.",
                    supporting_spans=(
                        EvidenceSpan(
                            evidence_id=str(record["evidence_id"]),
                            quote=claim.text,
                        ),
                    ),
                    evaluator=self.evaluator_id,
                    evaluator_version=self.evaluator_version,
                )

        return SupportAssessment(
            claim_id=claim.claim_id,
            claim_type=claim.claim_type,
            scope=claim.scope,
            verdict="unsupported",
            reason="The complete claim is absent from cited evidence.",
            evaluator=self.evaluator_id,
            evaluator_version=self.evaluator_version,
        )


def _normalize_line_endings(text: str) -> str:
    return text.replace("\r\n", "\n").replace("\r", "\n")
