from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

from opinion_agent.citations.evaluators import SupportEvaluator
from opinion_agent.citations.models import ClaimInput, ClaimVerificationResult
from opinion_agent.citations.verifier import verify_claim_support
from opinion_agent.evidence.store import EvidenceStore


@dataclass(frozen=True)
class ReportArtifacts:
    report_path: Path
    verification_path: Path


def write_report_artifacts(
    *,
    topic: str,
    report_title: str | None = None,
    claims: list[dict[str, Any] | ClaimInput],
    evidence_store: EvidenceStore,
    evaluator: SupportEvaluator,
    report_path: str | Path,
) -> ReportArtifacts:
    destination = Path(report_path)
    verification_path = destination.with_name(
        f"{destination.stem}_verification.json"
    )
    validated_claims = [
        claim if isinstance(claim, ClaimInput) else ClaimInput.model_validate(claim)
        for claim in claims
    ]
    claim_ids = [claim.claim_id for claim in validated_claims]
    if len(claim_ids) != len(set(claim_ids)):
        raise ValueError("Duplicate claim_id values are not allowed")

    results = [
        verify_claim_support(claim, evidence_store, evaluator)
        for claim in validated_claims
    ]
    errors = [error for result in results for error in result.errors]
    if errors:
        raise ValueError("; ".join(errors))

    markdown = _render_markdown(
        topic,
        results,
        evidence_store,
        report_title=report_title,
    )
    sidecar = {
        "schema_version": "1.0",
        "topic": topic,
        "claims": [
            claim.model_dump(mode="json") for claim in validated_claims
        ],
        "assessments": [
            result.assessment.model_dump(mode="json")
            for result in results
            if result.assessment is not None
        ],
    }
    destination.parent.mkdir(parents=True, exist_ok=True)
    report_temp = destination.with_suffix(destination.suffix + ".tmp")
    verification_temp = verification_path.with_suffix(
        verification_path.suffix + ".tmp"
    )
    report_temp.write_text(markdown, encoding="utf-8")
    verification_temp.write_text(
        json.dumps(sidecar, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    verification_temp.replace(verification_path)
    report_temp.replace(destination)
    return ReportArtifacts(
        report_path=destination,
        verification_path=verification_path,
    )


def _render_markdown(
    topic: str,
    results: list[ClaimVerificationResult],
    evidence_store: EvidenceStore,
    *,
    report_title: str | None = None,
) -> str:
    lines = [
        f"# {report_title or f'{topic} Public Opinion Report'}",
        "",
        f"Date: {date.today().isoformat()}",
        "",
        "## Evidence-grounded claims",
        "",
    ]
    for result in results:
        claim = result.claim
        assessment = result.assessment
        if claim is None or assessment is None:
            raise ValueError("Only validated claims can be rendered")
        evidence_by_id = {
            record["evidence_id"]: record
            for record in evidence_store.get_many(claim.evidence_ids)
        }
        lines.append(f"### {claim.claim_id}")
        lines.append("")
        lines.append(claim.text)
        lines.append("")
        lines.append(f"Claim type: {claim.claim_type}")
        if claim.scope is not None:
            if claim.scope.platform:
                lines.append(f"Platform: {claim.scope.platform}")
            if claim.scope.sample:
                lines.append(f"Sample: {claim.scope.sample}")
            if claim.scope.time_window:
                lines.append(
                    "Time window: "
                    f"{claim.scope.time_window.start or 'unspecified'} to "
                    f"{claim.scope.time_window.end or 'unspecified'}"
                )
        for span in assessment.supporting_spans:
            evidence = evidence_by_id[span.evidence_id]
            lines.extend(
                [
                    f"Evidence: {span.evidence_id}",
                    f"Exact excerpt: {span.quote}",
                    f"Source: {evidence.get('source_name', '')}",
                    f"Source type: {evidence.get('source_type', '')}",
                    f"Title: {evidence.get('title', '')}",
                    f"URL: {evidence.get('url') or 'not provided'}",
                ]
            )
        lines.append("")

    lines.extend(
        [
            "## Citation and support gate",
            "",
            "Every included claim passed citation resolution and support "
            "verification within its declared scope.",
            "",
        ]
    )
    return "\n".join(lines)
