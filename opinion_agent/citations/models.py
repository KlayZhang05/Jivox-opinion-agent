from __future__ import annotations

import re
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


ClaimType = Literal[
    "direct_quote",
    "factual_statement",
    "opinion_summary",
    "analytic_inference",
]
ID_PATTERN = r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$"
SupportVerdict = Literal[
    "supported",
    "unsupported",
    "contradicted",
    "indeterminate",
]


class TimeWindow(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    start: str | None = None
    end: str | None = None

    @field_validator("start", "end")
    @classmethod
    def validate_non_empty_time(cls, value: str | None):
        if value is not None and not value.strip():
            raise ValueError("time values must not be empty")
        return value


class ClaimScope(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    platform: str | None = None
    time_window: TimeWindow | None = None
    sample: str | None = None

    @field_validator("platform", "sample")
    @classmethod
    def validate_non_empty_text(cls, value: str | None):
        if value is not None and not value.strip():
            raise ValueError("scope text values must not be empty")
        return value


class ClaimInput(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    claim_id: str = Field(min_length=1, pattern=ID_PATTERN)
    claim_type: ClaimType
    text: str = Field(min_length=1)
    scope: ClaimScope | None = None
    evidence_ids: tuple[str, ...] = Field(min_length=1)

    @field_validator("claim_id", "text")
    @classmethod
    def validate_trimmed_text(cls, value: str):
        if not value.strip():
            raise ValueError("value must not be blank")
        return value

    @model_validator(mode="after")
    def validate_evidence_ids(self):
        if any(
            re.fullmatch(ID_PATTERN, evidence_id) is None
            for evidence_id in self.evidence_ids
        ):
            raise ValueError("evidence IDs contain unsupported characters")
        if len(self.evidence_ids) != len(set(self.evidence_ids)):
            raise ValueError("evidence IDs must be unique")
        return self


class EvidenceSpan(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    evidence_id: str = Field(min_length=1, pattern=ID_PATTERN)
    quote: str = Field(min_length=1)


class SupportAssessment(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    claim_id: str = Field(min_length=1)
    claim_type: ClaimType
    verdict: SupportVerdict
    reason: str = Field(min_length=1)
    scope: ClaimScope | None = None
    supporting_spans: tuple[EvidenceSpan, ...] = ()
    contradicting_spans: tuple[EvidenceSpan, ...] = ()
    evaluator: str = Field(min_length=1)
    evaluator_version: str = Field(min_length=1)


class CitationVerificationResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    valid: bool
    errors: tuple[str, ...] = ()


class ClaimVerificationResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    valid: bool
    claim: ClaimInput | None = None
    assessment: SupportAssessment | None = None
    errors: tuple[str, ...] = ()
