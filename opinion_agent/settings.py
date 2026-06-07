from __future__ import annotations

from pathlib import Path

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    SecretStr,
    ValidationError,
    field_validator,
    model_validator,
)
from pydantic_settings import BaseSettings, SettingsConfigDict


class SettingsError(ValueError):
    """Raised when runtime credentials or limits are incomplete."""


class LLMSettings(BaseModel):
    model_config = ConfigDict(frozen=True)

    api_key: SecretStr
    base_url: str
    model_name: str


class SearchSettings(BaseModel):
    model_config = ConfigDict(frozen=True)

    provider: str
    api_key: SecretStr
    base_url: str


class TikHubSettings(BaseModel):
    model_config = ConfigDict(frozen=True)

    api_key: SecretStr
    base_url: str


class RuntimeLimits(BaseModel):
    model_config = ConfigDict(frozen=True)

    max_parallel_subagents: int
    llm_request_timeout: int
    search_timeout: int


class RuntimeSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="",
        case_sensitive=False,
        extra="ignore",
    )

    llm_api_key: SecretStr | None = Field(None, validation_alias="LLM_API_KEY")
    llm_base_url: str | None = Field(None, validation_alias="LLM_BASE_URL")
    llm_model_name: str | None = Field(None, validation_alias="LLM_MODEL_NAME")

    search_provider: str | None = Field(
        None, validation_alias="SEARCH_PROVIDER"
    )
    search_api_key: SecretStr | None = Field(
        None, validation_alias="SEARCH_API_KEY"
    )
    search_base_url: str | None = Field(
        None, validation_alias="SEARCH_BASE_URL"
    )

    tikhub_api_key: SecretStr | None = Field(
        None, validation_alias="TIKHUB_API_KEY"
    )
    tikhub_base_url: str | None = Field(
        None, validation_alias="TIKHUB_BASE_URL"
    )

    max_parallel_subagents: int = Field(
        4, ge=1, le=32, validation_alias="MAX_PARALLEL_SUBAGENTS"
    )
    llm_request_timeout: int = Field(
        180, ge=1, validation_alias="LLM_REQUEST_TIMEOUT"
    )
    search_timeout: int = Field(
        30, ge=1, validation_alias="SEARCH_TIMEOUT"
    )

    @field_validator("*", mode="before")
    @classmethod
    def normalize_strings(cls, value):
        if isinstance(value, str):
            normalized = value.strip()
            return normalized or None
        return value

    @model_validator(mode="after")
    def validate_complete_integrations(self):
        missing = [
            name
            for name, value in (
                ("LLM_API_KEY", self.llm_api_key),
                ("LLM_BASE_URL", self.llm_base_url),
                ("LLM_MODEL_NAME", self.llm_model_name),
                ("SEARCH_PROVIDER", self.search_provider),
                ("SEARCH_API_KEY", self.search_api_key),
                ("SEARCH_BASE_URL", self.search_base_url),
            )
            if value is None
        ]
        if missing:
            raise ValueError(
                "Missing required runtime settings: " + ", ".join(missing)
            )

        tikhub_values = {
            "TIKHUB_API_KEY": self.tikhub_api_key,
            "TIKHUB_BASE_URL": self.tikhub_base_url,
        }
        configured_tikhub = [
            name for name, value in tikhub_values.items() if value is not None
        ]
        if configured_tikhub and len(configured_tikhub) != len(tikhub_values):
            missing_tikhub = [
                name for name, value in tikhub_values.items() if value is None
            ]
            raise ValueError(
                "Incomplete optional TikHub settings: "
                + ", ".join(missing_tikhub)
            )
        return self

    @property
    def llm(self) -> LLMSettings:
        return LLMSettings(
            api_key=self.llm_api_key,
            base_url=self.llm_base_url,
            model_name=self.llm_model_name,
        )

    @property
    def search(self) -> SearchSettings:
        return SearchSettings(
            provider=self.search_provider,
            api_key=self.search_api_key,
            base_url=self.search_base_url,
        )

    @property
    def tikhub(self) -> TikHubSettings | None:
        if self.tikhub_api_key is None:
            return None
        return TikHubSettings(
            api_key=self.tikhub_api_key,
            base_url=self.tikhub_base_url,
        )

    @property
    def limits(self) -> RuntimeLimits:
        return RuntimeLimits(
            max_parallel_subagents=self.max_parallel_subagents,
            llm_request_timeout=self.llm_request_timeout,
            search_timeout=self.search_timeout,
        )


def load_settings(env_file: str | Path | None = None) -> RuntimeSettings:
    selected_env = (
        Path(env_file)
        if env_file is not None
        else Path(__file__).resolve().parents[1] / ".env"
    )
    try:
        return RuntimeSettings(
            _env_file=selected_env,
            _env_file_encoding="utf-8",
        )
    except ValidationError as exc:
        messages = [
            str(error["ctx"]["error"])
            for error in exc.errors(include_url=False, include_input=False)
            if error.get("ctx", {}).get("error")
        ]
        detail = "; ".join(messages) or "invalid values"
        raise SettingsError(f"Invalid runtime settings: {detail}") from exc
