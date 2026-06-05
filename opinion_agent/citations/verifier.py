from typing import Any, Protocol


class EvidenceLookup(Protocol):
    def exists(self, evidence_id: str) -> bool:
        ...


def verify_claim(claim: dict[str, Any], evidence_store: EvidenceLookup) -> dict[str, Any]:
    evidence_ids = claim.get("evidence_ids")
    if not evidence_ids:
        return {"valid": False, "errors": ["Claim must cite at least one evidence_id"]}
    if not isinstance(evidence_ids, list):
        return {
            "valid": False,
            "errors": ["Claim evidence_ids must be a list of evidence IDs"],
        }

    errors: list[str] = []
    for evidence_id in evidence_ids:
        if not isinstance(evidence_id, str) or not evidence_id.strip():
            errors.append("Invalid evidence_id: expected non-empty string")
        elif not evidence_store.exists(evidence_id):
            errors.append(f"Unknown evidence_id: {evidence_id}")

    return {"valid": not errors, "errors": errors}
