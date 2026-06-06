from __future__ import annotations

from typing import Protocol, TypeVar

from pydantic import BaseModel


OutputModel = TypeVar("OutputModel", bound=BaseModel)


class ModelOutputError(RuntimeError):
    """Raised when a provider call or structured output validation fails."""


class StructuredModel(Protocol):
    async def ainvoke(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        output_schema: type[OutputModel],
    ) -> OutputModel:
        ...
