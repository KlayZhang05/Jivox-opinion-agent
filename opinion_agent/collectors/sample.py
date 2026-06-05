from __future__ import annotations

import json
from pathlib import Path

from opinion_agent.models import EvidenceItem


def load_sample_evidence(path: str | Path) -> list[EvidenceItem]:
    evidence_path = Path(path)
    items: list[EvidenceItem] = []
    for line in evidence_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        raw = json.loads(line)
        evidence_id = str(raw.get("evidence_id", "")).strip()
        if not evidence_id:
            raise ValueError("evidence_id is required")

        items.append(
            EvidenceItem(
                evidence_id=evidence_id,
                source_type=str(raw.get("source_type", "sample")).strip() or "sample",
                title=str(raw.get("title", "")).strip(),
                source_name=str(raw.get("source_name") or raw.get("source") or "").strip(),
                url=str(raw.get("url", "")).strip(),
                published_at=str(raw.get("published_at", "")).strip(),
                content=str(raw.get("content", "")).strip(),
            )
        )
    return items
