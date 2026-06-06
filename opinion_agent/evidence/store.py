import json
from copy import deepcopy
from pathlib import Path
from typing import Any, Sequence


class EvidenceStore:
    """Append-only JSONL store keyed by stable evidence_id values."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    def append(self, record: dict[str, Any]) -> bool:
        evidence_id = record.get("evidence_id")
        if not isinstance(evidence_id, str) or not evidence_id.strip():
            raise ValueError("evidence_id is required")

        if self.exists(evidence_id):
            return False

        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True))
            handle.write("\n")
        return True

    def read_all(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []

        records: list[dict[str, Any]] = []
        with self.path.open("r", encoding="utf-8") as handle:
            for line in handle:
                if line.strip():
                    records.append(json.loads(line))
        return records

    def exists(self, evidence_id: str) -> bool:
        return evidence_id in self.evidence_ids()

    def evidence_ids(self) -> set[str]:
        ids: set[str] = set()
        for record in self.read_all():
            evidence_id = record.get("evidence_id")
            if isinstance(evidence_id, str):
                ids.add(evidence_id)
        return ids

    def get_many(
        self,
        evidence_ids: Sequence[str],
    ) -> list[dict[str, Any]]:
        requested = list(evidence_ids)
        if len(requested) != len(set(requested)):
            raise ValueError("Duplicate evidence IDs are not allowed")

        records_by_id = {
            record["evidence_id"]: record for record in self.read_all()
        }
        missing = [
            evidence_id
            for evidence_id in requested
            if evidence_id not in records_by_id
        ]
        if missing:
            raise ValueError("Missing evidence IDs: " + ", ".join(missing))
        return [deepcopy(records_by_id[evidence_id]) for evidence_id in requested]
