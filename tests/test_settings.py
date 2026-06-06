from pathlib import Path

import pytest

from opinion_agent.settings import SettingsError, load_settings


ENV_NAMES = {
    "LLM_API_KEY",
    "LLM_BASE_URL",
    "LLM_MODEL_NAME",
    "SEARCH_PROVIDER",
    "SEARCH_API_KEY",
    "SEARCH_BASE_URL",
    "TIKHUB_API_KEY",
    "TIKHUB_BASE_URL",
    "MAX_PARALLEL_SUBAGENTS",
    "MAX_RESEARCH_ROUNDS",
    "LLM_REQUEST_TIMEOUT",
    "SEARCH_TIMEOUT",
}


@pytest.fixture(autouse=True)
def clear_runtime_environment(monkeypatch):
    for name in ENV_NAMES:
        monkeypatch.delenv(name, raising=False)


def write_env(path: Path, values: dict[str, str]) -> Path:
    path.write_text(
        "\n".join(f"{name}={value}" for name, value in values.items()) + "\n",
        encoding="utf-8",
    )
    return path


def test_loads_generic_llm_and_search_settings_without_leaking_secrets(tmp_path):
    env_file = write_env(
        tmp_path / ".env",
        {
            "LLM_API_KEY": "llm-secret",
            "LLM_BASE_URL": "https://llm.example.test/v1",
            "LLM_MODEL_NAME": "test-model",
            "SEARCH_PROVIDER": "anspire",
            "SEARCH_API_KEY": "search-secret",
            "SEARCH_BASE_URL": "https://search.example.test",
        },
    )

    settings = load_settings(env_file)

    assert settings.llm.model_name == "test-model"
    assert settings.llm.base_url == "https://llm.example.test/v1"
    assert settings.llm.api_key.get_secret_value() == "llm-secret"
    assert settings.search.provider == "anspire"
    assert settings.search.api_key.get_secret_value() == "search-secret"
    assert "llm-secret" not in repr(settings)
    assert "search-secret" not in repr(settings)


def test_missing_required_llm_or_search_values_fail_closed(tmp_path):
    env_file = write_env(
        tmp_path / ".env",
        {
            "LLM_API_KEY": "llm-secret",
            "SEARCH_PROVIDER": "anspire",
        },
    )

    with pytest.raises(SettingsError) as exc_info:
        load_settings(env_file)

    message = str(exc_info.value)
    assert "LLM_BASE_URL" in message
    assert "LLM_MODEL_NAME" in message
    assert "SEARCH_API_KEY" in message
    assert "SEARCH_BASE_URL" in message
    assert "llm-secret" not in message


def test_tikhub_is_optional_and_preserved_when_configured(tmp_path):
    base_values = {
        "LLM_API_KEY": "llm-secret",
        "LLM_BASE_URL": "https://llm.example.test/v1",
        "LLM_MODEL_NAME": "test-model",
        "SEARCH_PROVIDER": "anspire",
        "SEARCH_API_KEY": "search-secret",
        "SEARCH_BASE_URL": "https://search.example.test",
    }

    without_tikhub = load_settings(write_env(tmp_path / "first.env", base_values))
    assert without_tikhub.tikhub is None

    with_tikhub = load_settings(
        write_env(
            tmp_path / "second.env",
            {
                **base_values,
                "TIKHUB_API_KEY": "tikhub-secret",
                "TIKHUB_BASE_URL": "https://tikhub.example.test",
            },
        )
    )
    assert with_tikhub.tikhub is not None
    assert with_tikhub.tikhub.api_key.get_secret_value() == "tikhub-secret"


def test_partial_tikhub_configuration_is_rejected(tmp_path):
    env_file = write_env(
        tmp_path / ".env",
        {
            "LLM_API_KEY": "llm-secret",
            "LLM_BASE_URL": "https://llm.example.test/v1",
            "LLM_MODEL_NAME": "test-model",
            "SEARCH_PROVIDER": "anspire",
            "SEARCH_API_KEY": "search-secret",
            "SEARCH_BASE_URL": "https://search.example.test",
            "TIKHUB_API_KEY": "tikhub-secret",
        },
    )

    with pytest.raises(SettingsError, match="TIKHUB_BASE_URL"):
        load_settings(env_file)


def test_runtime_limits_are_typed_and_bounded(tmp_path):
    env_file = write_env(
        tmp_path / ".env",
        {
            "LLM_API_KEY": "llm-secret",
            "LLM_BASE_URL": "https://llm.example.test/v1",
            "LLM_MODEL_NAME": "test-model",
            "SEARCH_PROVIDER": "anspire",
            "SEARCH_API_KEY": "search-secret",
            "SEARCH_BASE_URL": "https://search.example.test",
            "MAX_PARALLEL_SUBAGENTS": "6",
            "MAX_RESEARCH_ROUNDS": "3",
            "LLM_REQUEST_TIMEOUT": "120",
            "SEARCH_TIMEOUT": "45",
        },
    )

    settings = load_settings(env_file)

    assert settings.limits.max_parallel_subagents == 6
    assert settings.limits.max_research_rounds == 3
    assert settings.limits.llm_request_timeout == 120
    assert settings.limits.search_timeout == 45


def test_environment_template_uses_generic_names_and_empty_secrets():
    values = {}
    for line in Path(".env.example").read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith("#"):
            name, value = stripped.split("=", 1)
            values[name] = value

    assert {
        "LLM_API_KEY",
        "LLM_BASE_URL",
        "LLM_MODEL_NAME",
        "SEARCH_PROVIDER",
        "SEARCH_API_KEY",
        "SEARCH_BASE_URL",
        "TIKHUB_API_KEY",
        "TIKHUB_BASE_URL",
    }.issubset(values)
    assert values["LLM_API_KEY"] == ""
    assert values["SEARCH_API_KEY"] == ""
    assert values["TIKHUB_API_KEY"] == ""
    assert not any(name.startswith("FORUM_HOST_") for name in values)
    assert not any(name.startswith("QUERY_ENGINE_") for name in values)
