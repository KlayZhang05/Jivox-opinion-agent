from __future__ import annotations

from datetime import date

from opinion_agent.models import BriefingPlan, EvidenceItem


def generate_briefing_markdown(
    plan: BriefingPlan, evidence_items: list[EvidenceItem]
) -> str:
    matches = _matching_items(plan, evidence_items)[: plan.max_items]
    lines = [
        f"# {plan.topic} Briefing",
        "",
        f"Date: {date.today().isoformat()}",
        f"Schedule: {plan.schedule}",
        f"Tone: {plan.tone}",
        "",
        "## Low-stimulation summary",
        "",
        _summary_sentence(matches),
        "No urgent action is suggested from this sample briefing.",
        "",
        "## Items to notice",
        "",
    ]

    if not matches:
        lines.append("No matching evidence items were found.")
    else:
        for item in matches:
            lines.extend(
                [
                    f"- {item.title}",
                    f"  Evidence: {item.evidence_id}",
                    f"  Source type: {item.source_type}",
                    f"  Source: {item.source_name}",
                    f"  Published: {item.published_at}",
                    f"  Link: {item.url}",
                    f"  Note: {_first_sentence(item.content)}",
                ]
            )

    lines.extend(["", "## Keywords monitored", "", ", ".join(plan.keywords), ""])
    return "\n".join(lines)


def _matching_items(plan: BriefingPlan, evidence_items: list[EvidenceItem]) -> list[EvidenceItem]:
    keywords = [keyword.casefold() for keyword in plan.keywords]
    return [
        item
        for item in evidence_items
        if any(keyword in f"{item.title} {item.content}".casefold() for keyword in keywords)
    ]


def _summary_sentence(matches: list[EvidenceItem]) -> str:
    if not matches:
        return "There are no matching sample items to review right now."
    item_word = "item" if len(matches) == 1 else "items"
    return f"{len(matches)} matching {item_word} found. Review them when convenient."


def _first_sentence(content: str) -> str:
    first, separator, _rest = content.partition(".")
    sentence = first.strip()
    if not sentence:
        return "No summary text was provided."
    return f"{sentence}{separator}"
