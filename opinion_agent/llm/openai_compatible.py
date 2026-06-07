from __future__ import annotations

from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, ValidationError

from opinion_agent.llm.protocols import ModelOutputError, OutputModel
from opinion_agent.settings import LLMSettings


class OpenAICompatibleStructuredModel:
    def __init__(
        self,
        *,
        settings: LLMSettings,
        timeout_seconds: int,
        chat_model: Any | None = None,
    ) -> None:
        self._settings = settings
        self._timeout_seconds = timeout_seconds
        self._chat_model = chat_model or ChatOpenAI(
            api_key=settings.api_key.get_secret_value(),
            base_url=settings.base_url,
            model=settings.model_name,
            temperature=0,
            timeout=timeout_seconds,
            max_retries=2,
        )

    def __repr__(self) -> str:
        return (
            "OpenAICompatibleStructuredModel("
            f"model_name={self._settings.model_name!r}, "
            f"base_url={self._settings.base_url!r}, "
            f"timeout_seconds={self._timeout_seconds!r})"
        )

    async def ainvoke(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        output_schema: type[OutputModel],
    ) -> OutputModel:
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt),
        ]
        try:
            runnable = self._chat_model.with_structured_output(output_schema)
            raw_output = await runnable.ainvoke(messages)
        except Exception as exc:
            message = self._redact(str(exc))
            raise ModelOutputError(
                f"{output_schema.__name__} provider call failed: {message}"
            ) from exc

        try:
            if isinstance(raw_output, BaseModel):
                return output_schema.model_validate(raw_output.model_dump())
            return output_schema.model_validate(raw_output)
        except ValidationError as exc:
            raise ModelOutputError(
                f"{output_schema.__name__} structured output was invalid: "
                f"{exc.error_count()} validation error(s)"
            ) from exc

    def _redact(self, message: str) -> str:
        secret = self._settings.api_key.get_secret_value()
        return message.replace(secret, "***")
