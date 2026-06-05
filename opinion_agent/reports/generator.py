from __future__ import annotations

from datetime import date
from typing import Any

from opinion_agent.citations.verifier import verify_claim
from opinion_agent.evidence.store import EvidenceStore


def generate_report_markdown(
    topic: str, claims: list[dict[str, Any]], evidence_store: EvidenceStore
) -> str:
    evidence_by_id = {
        record["evidence_id"]: record for record in evidence_store.read_all()
    }
    verified_claims: list[dict[str, Any]] = []
    errors: list[str] = []

    for claim in claims:
        result = verify_claim(claim, evidence_store)
        if result["valid"]:
            verified_claims.append(claim)
        else:
            errors.extend(result["errors"])

    if errors:
        raise ValueError("; ".join(errors))

    lines = [
        f"# {topic} Public Opinion Report",
        "",
        f"Date: {date.today().isoformat()}",
        "",
        "## Evidence-grounded claims",
        "",
    ]

    if not verified_claims:
        lines.append("No verified claims were provided.")
    else:
        for claim in verified_claims:
            lines.append(f"- {claim.get('text', '').strip()}")
            for evidence_id in claim["evidence_ids"]:
                evidence = evidence_by_id[evidence_id]
                lines.extend(
                    [
                        f"  Evidence: {evidence_id}",
                        f"  Source: {evidence.get('source_name', '')}",
                        f"  Source type: {evidence.get('source_type', '')}",
                        f"  Title: {evidence.get('title', '')}",
                        f"  URL: {evidence.get('url') or 'not provided'}",
                    ]
                )

    lines.extend(
        [
            "",
            "## Citation gate",
            "",
            "No uncited claims were included.",
            "",
        ]
    )
    return "\n".join(lines)
