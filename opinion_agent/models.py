from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class BriefingPlan:
    topic: str
    keywords: list[str]
    schedule: str
    max_items: int
    tone: str
    evidence_path: str = "examples/sample_evidence.jsonl"


@dataclass(frozen=True)
class EvidenceItem:
    evidence_id: str
    source_type: str
    title: str
    source_name: str
    url: str
    published_at: str
    content: str
