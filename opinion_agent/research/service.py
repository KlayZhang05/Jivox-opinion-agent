from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from opinion_agent.agents.models import ClaimBundle, ReportOutline
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
    ) -> None:
        self.model = model
        self.tool_registry = tool_registry
        self.evaluator = evaluator
        self.max_parallel_subagents = max_parallel_subagents
        self.run_id_factory = run_id_factory or (
            lambda: f"run-{uuid.uuid4().hex[:12]}"
        )

    async def run(
        self,
        topic: str,
        output_dir: str | Path,
    ) -> ResearchRunResult:
        run_id = self.run_id_factory()
        run_dir = Path(output_dir) / run_id
        evidence_path = run_dir / "evidence.jsonl"
        trace_path = run_dir / "trace.json"
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

            claims = await self._create_claims(
                topic=topic,
                evidence=evidence_store.read_all(),
                events=events,
            )
            verification_results = [
                verify_claim_support(claim, evidence_store, self.evaluator)
                for claim in claims.claims
            ]
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
                errors.extend(result.errors)
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
                report_title=outline.title,
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

    async def _create_claims(
        self,
        *,
        topic: str,
        evidence: list[dict],
        events: list[TraceEvent],
    ) -> ClaimBundle:
        role = get_role("citation_agent")
        events.append(
            TraceEvent(
                event_type="role_instance_started",
                role_id=role.role_id,
                metadata={"instance_id": "citation_agent"},
            )
        )
        bundle = await self.model.ainvoke(
            system_prompt=(
                f"{role.system_prompt}\n\n"
                f"{render_skill_bundle(role.skill_ids)}\n\n"
                "The configured evaluator supports only direct_quote claims. "
                "Return atomic exact spans and cite only supplied evidence IDs."
            ),
            user_prompt=json.dumps(
                {"topic": topic, "evidence": evidence},
                ensure_ascii=False,
                sort_keys=True,
            ),
            output_schema=ClaimBundle,
        )
        events.append(
            TraceEvent(
                event_type="model_call_completed",
                role_id=role.role_id,
                metadata={"output_schema": "ClaimBundle"},
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
        outline = await self.model.ainvoke(
            system_prompt=(
                f"{role.system_prompt}\n\n"
                f"{render_skill_bundle(role.skill_ids)}\n\n"
                "Return only a report title and an ordering of the supplied "
                "verified claim IDs. Do not add report claims."
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
                metadata={"output_schema": "ReportOutline"},
            )
        )
        return outline

    @staticmethod
    def _finish(
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
