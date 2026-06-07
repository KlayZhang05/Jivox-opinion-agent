from __future__ import annotations

import pytest

from opinion_agent.agents.models import ResearchPlan, ResearchTask
from opinion_agent.llm.openai_compatible import OpenAICompatibleStructuredModel
from opinion_agent.llm.protocols import ModelOutputError
from opinion_agent.settings import LLMSettings


class FakeStructuredRunnable:
    def __init__(self, response):
        self.response = response
        self.messages = None

    async def ainvoke(self, messages):
        self.messages = messages
        return self.response


class FakeChatModel:
    def __init__(self, response):
        self.runnable = FakeStructuredRunnable(response)
        self.schema = None

    def with_structured_output(self, schema):
        self.schema = schema
        return self.runnable


@pytest.mark.asyncio
async def test_adapter_requests_and_returns_validated_structured_output():
    response = {
        "topic": "Bounded event",
        "tasks": [
            {
                "task_id": "task-1",
                "role_id": "query_agent",
                "objective": "Find primary reporting.",
                "rationale": "Establish event facts.",
            }
        ],
    }
    chat_model = FakeChatModel(response)
    adapter = OpenAICompatibleStructuredModel(
        settings=LLMSettings(
            api_key="llm-secret",
            base_url="https://llm.example.test/v1",
            model_name="test-model",
        ),
        timeout_seconds=30,
        chat_model=chat_model,
    )

    result = await adapter.ainvoke(
        system_prompt="Plan research.",
        user_prompt="Research the bounded event.",
        output_schema=ResearchPlan,
    )

    assert isinstance(result, ResearchPlan)
    assert result.tasks[0].role_id == "query_agent"
    assert chat_model.schema is ResearchPlan
    assert chat_model.runnable.messages[0].content == "Plan research."
    assert chat_model.runnable.messages[1].content == "Research the bounded event."
    assert "llm-secret" not in repr(adapter)


@pytest.mark.asyncio
async def test_adapter_rejects_malformed_structured_output():
    adapter = OpenAICompatibleStructuredModel(
        settings=LLMSettings(
            api_key="llm-secret",
            base_url="https://llm.example.test/v1",
            model_name="test-model",
        ),
        timeout_seconds=30,
        chat_model=FakeChatModel(
            {
                "topic": "Bounded event",
                "tasks": [
                    {
                        "task_id": "task-1",
                        "role_id": "invented_role",
                        "objective": "Do unsupported work.",
                        "rationale": "Invalid role.",
                    }
                ],
            }
        ),
    )

    with pytest.raises(ModelOutputError, match="ResearchPlan") as exc_info:
        await adapter.ainvoke(
            system_prompt="Plan research.",
            user_prompt="Research the bounded event.",
            output_schema=ResearchPlan,
        )

    assert "llm-secret" not in str(exc_info.value)


@pytest.mark.asyncio
async def test_adapter_wraps_provider_failures_without_exposing_api_key():
    class FailingRunnable:
        async def ainvoke(self, messages):
            raise RuntimeError("provider unavailable")

    class FailingChatModel:
        def with_structured_output(self, schema):
            return FailingRunnable()

    adapter = OpenAICompatibleStructuredModel(
        settings=LLMSettings(
            api_key="llm-secret",
            base_url="https://llm.example.test/v1",
            model_name="test-model",
        ),
        timeout_seconds=30,
        chat_model=FailingChatModel(),
    )

    with pytest.raises(ModelOutputError, match="provider unavailable") as exc_info:
        await adapter.ainvoke(
            system_prompt="Plan research.",
            user_prompt="Research the bounded event.",
            output_schema=ResearchPlan,
        )

    assert "llm-secret" not in str(exc_info.value)


def test_research_plan_schema_is_usable_by_structured_models():
    plan = ResearchPlan(
        topic="Bounded event",
        tasks=(
            ResearchTask(
                task_id="task-1",
                role_id="query_agent",
                objective="Find primary reporting.",
                rationale="Establish event facts.",
            ),
        ),
    )

    assert ResearchPlan.model_validate(plan.model_dump()) == plan


def test_real_adapter_uses_deterministic_temperature(monkeypatch):
    captured = {}

    class ConstructorFixture:
        def __init__(self, **kwargs):
            captured.update(kwargs)

    monkeypatch.setattr(
        "opinion_agent.llm.openai_compatible.ChatOpenAI",
        ConstructorFixture,
    )

    OpenAICompatibleStructuredModel(
        settings=LLMSettings(
            api_key="llm-secret",
            base_url="https://llm.example.test/v1",
            model_name="test-model",
        ),
        timeout_seconds=30,
    )

    assert captured["temperature"] == 0
