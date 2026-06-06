from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Protocol

from pydantic import ValidationError

from opinion_agent.citations.evaluators import SupportEvaluator
from opinion_agent.citations.models import (
    CitationVerificationResult,
    ClaimInput,
    ClaimVerificationResult,
    SupportAssessment,
)


class EvidenceLookup(Protocol):
    def exists(self, evidence_id: str) -> bool:
        ...

    def get_many(self, evidence_ids) -> list[dict[str, Any]]:
        ...


def verify_citations(
    claim: Mapping[str, Any],
    evidence_store: EvidenceLookup,
) -> CitationVerificationResult:
    evidence_ids = claim.get("evidence_ids")
    if not evidence_ids:
        return CitationVerificationResult(
            valid=False,
            errors=("Claim must cite at least one evidence_id",),
        )
    if not isinstance(evidence_ids, list):
        return CitationVerificationResult(
            valid=False,
            errors=("Claim evidence_ids must be a list of evidence IDs",),
        )

    errors: list[str] = []
    for evidence_id in evidence_ids:
        if not isinstance(evidence_id, str) or not evidence_id.strip():
            errors.append("Invalid evidence_id: expected non-empty string")
        elif not evidence_store.exists(evidence_id):
            errors.append(f"Unknown evidence_id: {evidence_id}")
    return CitationVerificationResult(
        valid=not errors,
        errors=tuple(errors),
    )


def verify_claim_support(
    claim: ClaimInput | Mapping[str, Any],
    evidence_store: EvidenceLookup,
    support_evaluator: SupportEvaluator,
) -> ClaimVerificationResult:
    try:
        validated_claim = (
            claim
            if isinstance(claim, ClaimInput)
            else ClaimInput.model_validate(claim)
        )
    except ValidationError as exc:
        return ClaimVerificationResult(
            valid=False,
            errors=(f"Malformed claim input: {exc}",),
        )

    try:
        evidence = evidence_store.get_many(validated_claim.evidence_ids)
    except ValueError as exc:
        return ClaimVerificationResult(
            valid=False,
            claim=validated_claim,
            errors=(str(exc),),
        )

    try:
        raw_assessment = support_evaluator.assess(validated_claim, evidence)
        assessment = SupportAssessment.model_validate(raw_assessment)
    except Exception as exc:
        assessment = SupportAssessment(
            claim_id=validated_claim.claim_id,
            claim_type=validated_claim.claim_type,
            scope=validated_claim.scope,
            verdict="indeterminate",
            reason=f"Evaluator failed: {type(exc).__name__}",
            evaluator="failed_evaluator",
            evaluator_version="unknown",
        )
        return ClaimVerificationResult(
            valid=False,
            claim=validated_claim,
            assessment=assessment,
            errors=(f"{validated_claim.claim_id}: evaluator failure",),
        )

    errors = _validate_assessment(validated_claim, assessment, evidence)
    if assessment.verdict != "supported":
        errors.append(
            f"{validated_claim.claim_id}: support verdict is "
            f"{assessment.verdict}"
        )
    return ClaimVerificationResult(
        valid=not errors,
        claim=validated_claim,
        assessment=assessment,
        errors=tuple(errors),
    )


def _validate_assessment(
    claim: ClaimInput,
    assessment: SupportAssessment,
    evidence: list[dict[str, Any]],
) -> list[str]:
    errors = []
    if assessment.claim_id != claim.claim_id:
        errors.append(f"{claim.claim_id}: assessment claim_id mismatch")
    if assessment.claim_type != claim.claim_type:
        errors.append(f"{claim.claim_id}: assessment claim_type mismatch")
    if assessment.scope != claim.scope:
        errors.append(f"{claim.claim_id}: assessment scope mismatch")

    evidence_by_id = {record["evidence_id"]: record for record in evidence}
    for span in (
        *assessment.supporting_spans,
        *assessment.contradicting_spans,
    ):
        record = evidence_by_id.get(span.evidence_id)
        if record is None:
            errors.append(
                f"{claim.claim_id}: assessment references uncited evidence "
                f"{span.evidence_id}"
            )
            continue
        content = _normalize_line_endings(str(record.get("content") or ""))
        if _normalize_line_endings(span.quote) not in content:
            errors.append(
                f"{claim.claim_id}: quoted span is absent from evidence "
                f"{span.evidence_id}"
            )

    if assessment.verdict == "supported":
        if not assessment.supporting_spans:
            errors.append(
                f"{claim.claim_id}: supported verdict requires a supporting span"
            )
        if assessment.contradicting_spans:
            errors.append(
                f"{claim.claim_id}: supported verdict cannot contradict evidence"
            )
    if (
        assessment.verdict == "contradicted"
        and not assessment.contradicting_spans
    ):
        errors.append(
            f"{claim.claim_id}: contradicted verdict requires a contradicting span"
        )
    return errors


def _normalize_line_endings(text: str) -> str:
    return text.replace("\r\n", "\n").replace("\r", "\n")
