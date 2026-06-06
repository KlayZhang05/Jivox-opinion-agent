from __future__ import annotations

from typing import Any

import httpx
from pydantic import BaseModel, ConfigDict, Field

from opinion_agent.settings import SearchSettings


class SearchRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    query: str = Field(min_length=1)
    max_results: int = Field(default=10, ge=1, le=50)
    site: str | None = None
    from_time: str | None = None
    to_time: str | None = None


class SearchResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    title: str
    url: str
    content: str
    published_at: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class SearchOutput(BaseModel):
    model_config = ConfigDict(frozen=True)

    provider: str
    query: str
    provider_request_id: str | None = None
    results: tuple[SearchResult, ...]


class AnspireSearchTool:
    def __init__(
        self,
        *,
        settings: SearchSettings,
        timeout_seconds: int,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        if settings.provider.casefold() != "anspire":
            raise ValueError("AnspireSearchTool requires SEARCH_PROVIDER=anspire")
        self.settings = settings
        self.timeout_seconds = timeout_seconds
        self._client = client

    async def __call__(self, request: SearchRequest) -> SearchOutput:
        headers = {
            "Authorization": (
                f"Bearer {self.settings.api_key.get_secret_value()}"
            ),
            "Accept": "application/json",
        }
        params = {
            "query": request.query,
            "top_k": request.max_results,
            "Insite": request.site or "",
            "FromTime": request.from_time or "",
            "ToTime": request.to_time or "",
        }

        if self._client is not None:
            response = await self._client.get(
                self.settings.base_url,
                headers=headers,
                params=params,
                timeout=self.timeout_seconds,
            )
        else:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    self.settings.base_url,
                    headers=headers,
                    params=params,
                    timeout=self.timeout_seconds,
                )
        response.raise_for_status()
        payload = response.json()
        return self._parse_payload(payload, request.query)

    @staticmethod
    def _parse_payload(payload: Any, query: str) -> SearchOutput:
        if not isinstance(payload, dict):
            raise ValueError("Anspire response must be a JSON object")
        raw_results = payload.get("results", [])
        if not isinstance(raw_results, list):
            raise ValueError("Anspire response results must be a list")

        results = []
        for index, raw in enumerate(raw_results):
            if not isinstance(raw, dict):
                raise ValueError(
                    f"Anspire result at index {index} must be an object"
                )
            results.append(
                SearchResult(
                    title=str(raw.get("title") or ""),
                    url=str(raw.get("url") or ""),
                    content=str(raw.get("content") or ""),
                    published_at=(
                        str(raw["date"]) if raw.get("date") is not None else None
                    ),
                    metadata={
                        "score": raw.get("score")
                    }
                    if raw.get("score") is not None
                    else {},
                )
            )

        request_id = payload.get("Uuid")
        return SearchOutput(
            provider="anspire",
            query=query,
            provider_request_id=str(request_id) if request_id else None,
            results=tuple(results),
        )
