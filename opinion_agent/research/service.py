from __future__ import annotations

import json
import re
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from opinion_agent.agents.models import (
    CitationSelectionBundle,
    ClaimBundle,
    ReportOutline,
)
from opinion_agent.citations.models import ClaimInput
from opinion_agent.agents.registry import get_role
from opinion_agent.agents.skills import render_skill_bundle
from opinion_agent.citations.evaluators import SupportEvaluator
from opinion_agent.citations.verifier import verify_claim_support
from opinion_agent.evidence.store import EvidenceStore
from opinion_agent.graph.research import build_research_graph
from opinion_agent.graph.state import TraceEvent
from opinion_agent.llm.protocols import StructuredModel
from opinion_agent.reports.generator import write_report_artifacts
from opinion_agent.tools.registry import ToolRegistry
from opinion_agent.tracing.run_trace import write_run_trace


@dataclass(frozen=True)
class ResearchRunResult:
    run_id: str
    status: str
    evidence_path: Path
    trace_path: Path
    report_path: Path | None = None
    verification_path: Path | None = None
    errors: tuple[str, ...] = ()


class ResearchService:
    def __init__(
        self,
        *,
        model: StructuredModel,
        tool_registry: ToolRegistry,
        evaluator: SupportEvaluator,
        max_parallel_subagents: int,
        run_id_factory: Callable[[], str] | None = None,
        trace_redactions: tuple[str, ...] = (),
    ) -> None:
        self.model = model
        self.tool_registry = tool_registry
        self.evaluator = evaluator
        self.max_parallel_subagents = max_parallel_subagents
        self.run_id_factory = run_id_factory or (
            lambda: f"run-{uuid.uuid4().hex[:12]}"
        )
        self.trace_redactions = trace_redactions

    async def run(
        self,
        topic: str,
        output_dir: str | Path,
    ) -> ResearchRunResult:
        run_id = self.run_id_factory()
        run_dir = Path(output_dir) / run_id
        try:
            run_dir.mkdir(parents=True, exist_ok=False)
        except FileExistsError as exc:
            raise FileExistsError(
                f"Research run already exists: {run_id}"
            ) from exc
        evidence_path = run_dir / "evidence.jsonl"
        trace_path = run_dir / "trace.json"
        evidence_path.touch(exist_ok=True)
        evidence_store = EvidenceStore(evidence_path)
        events: list[TraceEvent] = []
        errors: list[str] = []

        try:
            graph = build_research_graph(
                model=self.model,
                tool_registry=self.tool_registry,
                max_parallel_subagents=self.max_parallel_subagents,
            )
            state = await graph.ainvoke({"topic": topic})
            events.extend(state.get("trace_events", []))
            errors.extend(state.get("errors", []))
            for record in state.get("evidence_records", []):
                evidence_store.append(record)
            if errors:
                events.append(
                    TraceEvent(
                        event_type="run_rejected",
                        metadata={"error_count": len(errors)},
                    )
                )
                return self._finish(
                    run_id=run_id,
                    topic=topic,
                    status="rejected",
                    evidence_path=evidence_path,
                    trace_path=trace_path,
                    events=events,
                    errors=errors,
                )
            if not evidence_store.read_all():
                errors = ["No evidence was collected"]
                events.append(
                    TraceEvent(
                        event_type="run_rejected",
                        metadata={"error_count": len(errors)},
                    )
                )
                return self._finish(
                    run_id=run_id,
                    topic=topic,
                    status="rejected",
                    evidence_path=evidence_path,
                    trace_path=trace_path,
                    events=events,
                    errors=errors,
                )

            evidence = evidence_store.read_all()
            candidates = _build_quote_candidates(evidence)
            if not candidates:
                raise ValueError("No usable quote candidates were found")
            claims = None
            claim_errors: list[str] = []
            for attempt in range(1, 3):
                try:
                    selections = await self._select_claims(
                        topic=topic,
                        candidates=candidates,
                        events=events,
                        attempt=attempt,
                        feedback=claim_errors,
                    )
                    claims = _materialize_claims(
                        selections,
                        candidates,
                    )
                except ValueError as exc:
                    claim_errors = [str(exc)]
                    if attempt == 1:
                        events.append(
                            TraceEvent(
                                event_type="claim_repair_requested",
                                role_id="citation_agent",
                                metadata={
                                    "attempt": attempt + 1,
                                    "rejected_claim_count": 1,
                                },
                            )
                        )
                    continue
                verification_results = [
                    verify_claim_support(
                        claim,
                        evidence_store,
                        self.evaluator,
                    )
                    for claim in claims.claims
                ]
                claim_errors = []
                for result in verification_results:
                    verdict = (
                        result.assessment.verdict
                        if result.assessment is not None
                        else "indeterminate"
                    )
                    events.append(
                        TraceEvent(
                            event_type="claim_verification_completed",
                            role_id="citation_agent",
                            metadata={
                                "attempt": attempt,
                                "claim_id": (
                                    result.claim.claim_id
                                    if result.claim is not None
                                    else None
                                ),
                                "verdict": verdict,
                                "valid": result.valid,
                            },
                        )
                    )
                    claim_errors.extend(result.errors)
                if not claim_errors:
                    break
                if attempt == 1:
                    events.append(
                        TraceEvent(
                            event_type="claim_repair_requested",
                            role_id="citation_agent",
                            metadata={
                                "attempt": attempt + 1,
                                "rejected_claim_count": sum(
                                    not result.valid
                                    for result in verification_results
                                ),
                            },
                        )
                    )

            if claim_errors:
                errors.extend(claim_errors)
                events.append(
                    TraceEvent(
                        event_type="run_rejected",
                        metadata={"error_count": len(errors)},
                    )
                )
                return self._finish(
                    run_id=run_id,
                    topic=topic,
                    status="rejected",
                    evidence_path=evidence_path,
                    trace_path=trace_path,
                    events=events,
                    errors=errors,
                )
            if claims is None:
                raise RuntimeError("Citation Agent did not produce claims")

            outline = await self._create_report_outline(
                topic=topic,
                claims=claims,
                events=events,
            )
            claim_by_id = {claim.claim_id: claim for claim in claims.claims}
            if set(outline.ordered_claim_ids) != set(claim_by_id):
                raise ValueError(
                    "Report outline must reference every verified claim exactly once"
                )
            ordered_claims = [
                claim_by_id[claim_id]
                for claim_id in outline.ordered_claim_ids
            ]
            artifacts = write_report_artifacts(
                topic=topic,
                claims=ordered_claims,
                evidence_store=evidence_store,
                evaluator=self.evaluator,
                report_path=run_dir / "report.md",
            )
            events.append(
                TraceEvent(
                    event_type="report_written",
                    role_id="report_writer",
                    metadata={
                        "claim_count": len(ordered_claims),
                        "report_file": artifacts.report_path.name,
                        "verification_file": artifacts.verification_path.name,
                    },
                )
            )
            return self._finish(
                run_id=run_id,
                topic=topic,
                status="completed",
                evidence_path=evidence_path,
                trace_path=trace_path,
                events=events,
                errors=errors,
                report_path=artifacts.report_path,
                verification_path=artifacts.verification_path,
            )
        except Exception as exc:
            errors.append(f"{type(exc).__name__}: {exc}")
            events.append(
                TraceEvent(
                    event_type="run_failed",
                    metadata={"error_type": type(exc).__name__},
                )
            )
            return self._finish(
                run_id=run_id,
                topic=topic,
                status="failed",
                evidence_path=evidence_path,
                trace_path=trace_path,
                events=events,
                errors=errors,
            )

    async def _select_claims(
        self,
        *,
        topic: str,
        candidates: list[dict],
        events: list[TraceEvent],
        attempt: int = 1,
        feedback: list[str] | None = None,
    ) -> CitationSelectionBundle:
        role = get_role("citation_agent")
        events.append(
            TraceEvent(
                event_type="role_instance_started",
                role_id=role.role_id,
                metadata={"instance_id": f"citation_agent:{attempt}"},
            )
        )
        model_started = time.perf_counter()
        bundle = await self.model.ainvoke(
            system_prompt=(
                f"{role.system_prompt}\n\n"
                f"{render_skill_bundle(role.skill_ids)}\n\n"
                "Select exactly one candidate quote for the bounded topic. "
                "Return only its candidate_id and a stable claim_id. Do not "
                "author, copy, paraphrase, or combine quote text."
            ),
            user_prompt=json.dumps(
                {
                    "topic": topic,
                    "candidates": candidates,
                    "attempt": attempt,
                    "previous_gate_errors": feedback or [],
                },
                ensure_ascii=False,
                sort_keys=True,
            ),
            output_schema=CitationSelectionBundle,
        )
        events.append(
            TraceEvent(
                event_type="model_call_completed",
                role_id=role.role_id,
                metadata={
                    "output_schema": "CitationSelectionBundle",
                    "duration_ms": _elapsed_ms(model_started),
                },
            )
        )
        return bundle

    async def _create_report_outline(
        self,
        *,
        topic: str,
        claims: ClaimBundle,
        events: list[TraceEvent],
    ) -> ReportOutline:
        role = get_role("report_writer")
        events.append(
            TraceEvent(
                event_type="role_instance_started",
                role_id=role.role_id,
                metadata={"instance_id": "report_writer"},
            )
        )
        model_started = time.perf_counter()
        outline = await self.model.ainvoke(
            system_prompt=(
                f"{role.system_prompt}\n\n"
                f"{render_skill_bundle(role.skill_ids)}\n\n"
                "Return only an ordering of the supplied verified claim IDs. "
                "Do not add report claims or any report prose."
            ),
            user_prompt=json.dumps(
                {
                    "topic": topic,
                    "verified_claims": [
                        claim.model_dump(mode="json")
                        for claim in claims.claims
                    ],
                },
                ensure_ascii=False,
                sort_keys=True,
            ),
            output_schema=ReportOutline,
        )
        events.append(
            TraceEvent(
                event_type="model_call_completed",
                role_id=role.role_id,
                metadata={
                    "output_schema": "ReportOutline",
                    "duration_ms": _elapsed_ms(model_started),
                },
            )
        )
        return outline

    def _finish(
        self,
        *,
        run_id: str,
        topic: str,
        status: str,
        evidence_path: Path,
        trace_path: Path,
        events: list[TraceEvent],
        errors: list[str],
        report_path: Path | None = None,
        verification_path: Path | None = None,
    ) -> ResearchRunResult:
        write_run_trace(
            path=trace_path,
            run_id=run_id,
            topic=topic,
            status=status,
            events=events,
            errors=errors,
            secret_values=self.trace_redactions,
        )
        return ResearchRunResult(
            run_id=run_id,
            status=status,
            evidence_path=evidence_path,
            trace_path=trace_path,
            report_path=report_path,
            verification_path=verification_path,
            errors=tuple(errors),
        )


def _elapsed_ms(started: float) -> float:
    return round((time.perf_counter() - started) * 1000, 3)


def _build_quote_candidates(evidence: list[dict]) -> list[dict]:
    candidates = []
    for record in evidence:
        content = str(record.get("content") or "")
        spans = [
            match.group(0).strip()
            for match in re.finditer(
                r"[^.!?。！？\r\n]{20,500}[.!?。！？]?",
                content,
            )
            if match.group(0).strip()
        ][:3]
        if not spans and content.strip():
            spans = [content.strip()[:500]]
        for index, text in enumerate(spans):
            candidates.append(
                {
                    "candidate_id": f"{record['evidence_id']}:{index}",
                    "evidence_id": record["evidence_id"],
                    "text": text,
                    "source_name": record.get("source_name"),
                    "title": record.get("title"),
                    "published_at": record.get("published_at"),
                }
            )
    return candidates


def _materialize_claims(
    selections: CitationSelectionBundle,
    candidates: list[dict],
) -> ClaimBundle:
    candidate_by_id = {
        candidate["candidate_id"]: candidate for candidate in candidates
    }
    claims = []
    for selection in selections.selections:
        candidate = candidate_by_id.get(selection.candidate_id)
        if candidate is None:
            raise ValueError(
                f"Unknown citation candidate: {selection.candidate_id}"
            )
        published_at = candidate.get("published_at")
        scope = {
            "platform": str(candidate.get("source_name") or "unknown"),
            "sample": "single collected source excerpt",
        }
        if published_at:
            scope["time_window"] = {
                "start": str(published_at),
                "end": str(published_at),
            }
        claims.append(
            ClaimInput(
                claim_id=selection.claim_id,
                claim_type="direct_quote",
                text=candidate["text"],
                scope=scope,
                evidence_ids=(candidate["evidence_id"],),
            )
        )
    return ClaimBundle(claims=tuple(claims))
