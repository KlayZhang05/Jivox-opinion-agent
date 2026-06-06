from __future__ import annotations

import asyncio

from opinion_agent.agents.models import (
    ResearchPlan,
    ResearchTask,
    SubagentResult,
)
from opinion_agent.llm.protocols import ModelOutputError


class BarrierStructuredModel:
    def __init__(
        self,
        *,
        plan: ResearchPlan,
        failing_task_id: str | None = None,
    ) -> None:
        self.plan = plan
        self.failing_task_id = failing_task_id
        self.started_task_ids: set[str] = set()
        self.worker_overlap_observed = False
        self._release = asyncio.Event()

    async def ainvoke(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        output_schema,
    ):
        if output_schema is ResearchPlan:
            return self.plan
        if output_schema is not SubagentResult:
            raise AssertionError(f"Unexpected output schema: {output_schema}")

        task = self._task_from_prompt(user_prompt)
        self.started_task_ids.add(task.task_id)
        if len(self.started_task_ids) >= 2:
            self.worker_overlap_observed = True
            self._release.set()
        try:
            await asyncio.wait_for(self._release.wait(), timeout=1)
        except TimeoutError as exc:
            raise AssertionError("Subagent calls did not overlap") from exc

        if task.task_id == self.failing_task_id:
            raise ModelOutputError(f"forced failure for {task.task_id}")
        return SubagentResult(
            task_id=task.task_id,
            role_id=task.role_id,
            summary=f"Completed {task.objective}",
            evidence_ids=(f"evidence-{task.task_id}",),
        )

    def _task_from_prompt(self, user_prompt: str) -> ResearchTask:
        for task in self.plan.tasks:
            if task.task_id in user_prompt:
                return task
        raise AssertionError(f"No task ID found in prompt: {user_prompt}")
