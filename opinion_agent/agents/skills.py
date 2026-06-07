from __future__ import annotations

from types import MappingProxyType
from typing import Final, Mapping

from pydantic import BaseModel, ConfigDict, Field


class SkillDefinition(BaseModel):
    model_config = ConfigDict(frozen=True)

    skill_id: str = Field(min_length=1)
    purpose: str = Field(min_length=1)
    instructions: tuple[str, ...] = Field(min_length=1)


_SKILLS = {
    "research_planning": SkillDefinition(
        skill_id="research_planning",
        purpose="Decompose a bounded topic into independent evidence tasks.",
        instructions=(
            "Create only tasks that materially reduce a named evidence gap.",
            "Choose roles from the fixed registry and keep tasks independently executable.",
            "Prefer fewer well-scoped tasks over broad role fan-out.",
        ),
    ),
    "gap_analysis": SkillDefinition(
        skill_id="gap_analysis",
        purpose="Identify evidence gaps while planning the bounded research round.",
        instructions=(
            "Name the unresolved question before creating a task.",
            "Do not repeat a completed query without a concrete reason.",
        ),
    ),
    "web_research": SkillDefinition(
        skill_id="web_research",
        purpose="Find traceable web sources for a bounded research question.",
        instructions=(
            "Prefer primary and attributable sources.",
            "Preserve title, URL, publication time, and relevant source text.",
            "Do not treat provider-generated summaries as source evidence.",
        ),
    ),
    "source_triage": SkillDefinition(
        skill_id="source_triage",
        purpose="Separate useful source material from noise.",
        instructions=(
            "Reject results that do not address the assigned objective.",
            "State uncertainty when source metadata is incomplete.",
        ),
    ),
    "evidence_retrieval": SkillDefinition(
        skill_id="evidence_retrieval",
        purpose="Retrieve prior evidence without altering its provenance.",
        instructions=(
            "Return stable evidence IDs and source metadata.",
            "Do not rewrite stored evidence as if it were a new source.",
        ),
    ),
    "prior_report_review": SkillDefinition(
        skill_id="prior_report_review",
        purpose="Use prior reports as leads rather than primary evidence.",
        instructions=(
            "Trace report claims back to stored evidence IDs.",
            "Mark report-only statements as secondary material.",
        ),
    ),
    "multimedia_inspection": SkillDefinition(
        skill_id="multimedia_inspection",
        purpose="Extract bounded observations from image or video material.",
        instructions=(
            "Separate visible observations from interpretation.",
            "Record media identity and extraction method.",
        ),
    ),
    "claim_atomization": SkillDefinition(
        skill_id="claim_atomization",
        purpose="Split prose into independently verifiable claims.",
        instructions=(
            "Assign one stable claim ID per assertion.",
            "Keep claim type and declared scope explicit.",
        ),
    ),
    "citation_audit": SkillDefinition(
        skill_id="citation_audit",
        purpose="Verify citation existence and claim-to-evidence support.",
        instructions=(
            "Fail closed when evidence is missing or indeterminate.",
            "Never invent a source span or evidence ID.",
        ),
    ),
    "evidence_synthesis": SkillDefinition(
        skill_id="evidence_synthesis",
        purpose="Synthesize only verified claims.",
        instructions=(
            "Preserve disagreements and uncertainty.",
            "Do not widen platform, time, or sample scope.",
        ),
    ),
    "report_writing": SkillDefinition(
        skill_id="report_writing",
        purpose="Write a concise evidence-grounded Markdown report.",
        instructions=(
            "Attach evidence IDs to every factual claim.",
            "Keep unsupported material out of the report.",
        ),
    ),
    "social_media_research": SkillDefinition(
        skill_id="social_media_research",
        purpose="Collect bounded social-media records through TikHub.",
        instructions=(
            "Preserve platform identifiers, author, timestamps, and engagement metadata.",
            "Do not generalize a sample to the whole public.",
        ),
    ),
}

SKILL_REGISTRY: Final[Mapping[str, SkillDefinition]] = MappingProxyType(_SKILLS)


def render_skill_bundle(skill_ids: tuple[str, ...]) -> str:
    sections = []
    for skill_id in skill_ids:
        try:
            skill = SKILL_REGISTRY[skill_id]
        except KeyError as exc:
            raise KeyError(f"Unknown skill: {skill_id}") from exc
        instructions = "\n".join(f"- {item}" for item in skill.instructions)
        sections.append(f"## {skill.skill_id}\n{skill.purpose}\n{instructions}")
    return "\n\n".join(sections)
