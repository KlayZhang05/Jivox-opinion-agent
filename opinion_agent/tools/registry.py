from __future__ import annotations

from collections.abc import Awaitable, Callable, Iterable, Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any

from pydantic import BaseModel, ConfigDict, ValidationError

from opinion_agent.agents.registry import get_role


class UnknownToolError(KeyError):
    """Raised when an invocation references a tool outside the registry."""


class ToolPermissionError(PermissionError):
    """Raised before execution when a role is not allowed to use a tool."""


class ToolError(BaseModel):
    model_config = ConfigDict(frozen=True)

    kind: str
    message: str


class ToolResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    tool_id: str
    ok: bool
    data: Any = None
    error: ToolError | None = None


ToolHandler = Callable[[BaseModel], Awaitable[Any]]


@dataclass(frozen=True)
class ToolDefinition:
    tool_id: str
    description: str
    input_model: type[BaseModel]
    handler: ToolHandler

    def __post_init__(self) -> None:
        if not self.tool_id.strip():
            raise ValueError("tool_id must not be empty")
        if not self.description.strip():
            raise ValueError("tool description must not be empty")


class ToolRegistry:
    def __init__(self, definitions: Iterable[ToolDefinition]) -> None:
        tools: dict[str, ToolDefinition] = {}
        for definition in definitions:
            if definition.tool_id in tools:
                raise ValueError(f"Duplicate tool_id: {definition.tool_id}")
            tools[definition.tool_id] = definition
        self._tools: Mapping[str, ToolDefinition] = MappingProxyType(tools)

    def list_tools(self) -> tuple[ToolDefinition, ...]:
        return tuple(self._tools.values())

    def get(self, tool_id: str) -> ToolDefinition:
        try:
            return self._tools[tool_id]
        except KeyError as exc:
            raise UnknownToolError(f"Unknown tool: {tool_id}") from exc

    async def invoke(
        self,
        *,
        role_id: str,
        tool_id: str,
        arguments: dict[str, Any],
    ) -> ToolResult:
        definition = self.get(tool_id)
        role = get_role(role_id)
        if tool_id not in role.tool_ids:
            raise ToolPermissionError(
                f"Agent role {role_id} is not permitted to use tool {tool_id}"
            )

        try:
            validated = definition.input_model.model_validate(arguments)
        except ValidationError as exc:
            return ToolResult(
                tool_id=tool_id,
                ok=False,
                error=ToolError(
                    kind="validation_error",
                    message=str(exc),
                ),
            )

        try:
            data = await definition.handler(validated)
        except Exception as exc:
            return ToolResult(
                tool_id=tool_id,
                ok=False,
                error=ToolError(
                    kind="execution_error",
                    message=str(exc),
                ),
            )
        return ToolResult(tool_id=tool_id, ok=True, data=data)
